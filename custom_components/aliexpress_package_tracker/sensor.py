"""""Support for  aliexpress_package_tracker."""
from __future__ import annotations

import logging
from typing import Any, Final
import re
from datetime import datetime,date
import aiohttp
from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.util import Throttle
from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change
from homeassistant.const import CONF_ENTITY_ID
from .const import (
    ADD_TRACKING_SERVICE_SCHEMA,
    ATTRIBUTION,
    CONF_TITLE,CONF_PACKAGE,
    CONF_LANG,CONF_AUTO_DELETE
    ,CONF_AUTO_DELETE_DAYS,
    CONF_TRACKING_NUMBER,
    DOMAIN,
    ICON,
    MIN_TIME_BETWEEN_UPDATES,
    REMOVE_TRACKING_SERVICE_SCHEMA,
    SERVICE_ADD_TRACKING,
    SERVICE_REMOVE_TRACKING,
    UPDATE_TOPIC,
    STORAGE_KEY ,
    STORAGE_VERSION,
)

_LOGGER: Final = logging.getLogger(__name__)

def get_store(hass: HomeAssistant) -> Store:
    return Store(hass, STORAGE_VERSION, STORAGE_KEY)


async def track_packages(hass: HomeAssistant, order_numbers, lang="en-US"):
    _LOGGER.debug(f"track_packages for order  numbers: {order_numbers}")
    session = async_get_clientsession(hass)
    try:
        response = await session.get(
            f"https://global.cainiao.com/global/detail.json?mailNos={order_numbers}&lang={lang}"
        )
        response.raise_for_status()
        return await response.json()
    except aiohttp.ClientError as error:
        _LOGGER.error("Error retrieving package data: %s", error)
def extract_realMailNo(string) -> str | None:
    regex = "(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})"
    match = re.search(regex, string)
    return match.group() if match else None


async def fix_duplicate_real_numbers(hass: HomeAssistant):
    store = get_store(hass)
    data =  await store.async_load() or {}
    new_data = {}
    for key, value in data.items():
        real_number = value.get("realMailNo", key)
        if real_number not in new_data:
            new_data[real_number] = {CONF_TITLE: value[CONF_TITLE], "tracking_number": value["tracking_number"]}
        else:
            new_data[real_number][CONF_TITLE] += f',{value[CONF_TITLE]}'
            entity_registry.async_get(hass).async_remove(f"sensor.aliexpress_package_no_{value['tracking_number'].lower()}")
    await store.async_save(new_data)
async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):

    def extract_actual_tracking_number(data) -> str | None:
        realMailNo= extract_realMailNo(data.get("realMailNo",""))
        _LOGGER.debug(f"realMailNo is: {realMailNo}")
        return realMailNo if realMailNo else data["mailNo"]



    async def state_change_listener(entity_id, old_state, new_state):
        if old_state and old_state != new_state:
            # Fire a custom event
            hass.bus.async_fire("aliexpress_package_data_updated", {
                "entity_id": entity_id,
                "old_state": old_state.state if old_state else None,
                "new_state": new_state.state if new_state else None,
            })

    async def get_data(order_numbers):
        lang = config.data.get(CONF_LANG)
        data = await track_packages(hass, order_numbers, lang)
        store = get_store(hass)
        stored_data= await store.async_load() or {}

        if not data or "module" not in data:
            return
        sensors = [AliexpressPackageSensor(i, extract_actual_tracking_number(i),
                                           stored_data.get(extract_actual_tracking_number(i),{}).get(CONF_TITLE,CONF_PACKAGE),

                                             hass,config.data)
                                             for i in data["module"] if i["mailNoSource"] != "EXTERNAL"]
        sensors_to_add=list({item.name: item for item in sensors}.values())
        async_add_entities(sensors_to_add, True)
        for sensor in sensors_to_add:
            async_track_state_change(hass, f"sensor.{sensor.name.lower()}", state_change_listener)

    async def add_tracking(income_data: ServiceCall, title=CONF_PACKAGE) -> None:
        tracking_number=income_data.data.get(CONF_TRACKING_NUMBER).strip()
        title=income_data.data.get(CONF_TITLE) or CONF_PACKAGE
        data = await store.async_load() or {}
        if tracking_number in data:
            current_title = data[tracking_number].get(CONF_TITLE, CONF_PACKAGE)
            data[tracking_number][CONF_TITLE] = current_title + f', {title}' if current_title != CONF_PACKAGE else title

        else:
            data[tracking_number] = {CONF_TITLE: title, "tracking_number": tracking_number}
        await store.async_save(data)
        await fix_duplicate_real_numbers(hass)
        await get_data(tracking_number)
        async_dispatcher_send(hass, UPDATE_TOPIC)

    async def remove_tracking(income_data: ServiceCall) -> None:
        tracking_number=income_data.data.get(CONF_TRACKING_NUMBER)
        entity_id=income_data.data.get(CONF_ENTITY_ID)
        data = await store.async_load() or {}
        if tracking_number:
            entity_registry.async_get(hass).async_remove(f"sensor.aliexpress_package_no_{tracking_number.lower()}")
            data.pop(tracking_number, None)
        elif entity_id:
            for entity in entity_id:
                tracking_number=hass.states.get(entity).attributes["orignal_track_id"]
                data.pop(tracking_number, None)
                entity_registry.async_get(hass).async_remove(entity)
        else:
            raise  KeyError("Both entity_id and tracking_number is empty")

        await store.async_save(data)

        async_dispatcher_send(hass, UPDATE_TOPIC)

    async def edit_title_service(call: ServiceCall):
        """Handle the service call to edit the title attribute of a sensor."""
        entity_id = call.data.get("entity_id")
        new_title = call.data.get("new_title")

        if not entity_id or not new_title:
            _LOGGER.error("Missing required parameters: entity_id or new_title")
            return
        entity_id = entity_id[0]
        # Get entity state
        entity = hass.states.get(entity_id)
        if not entity:
            _LOGGER.error(f"Entity {entity_id} not found")
            return

        # Update state attributes
        updated_attributes = dict(entity.attributes)
        updated_attributes["title"] = new_title

        # Apply changes
        hass.states.async_set(entity_id, entity.state, updated_attributes)
        _LOGGER.info(f"Updated title of {entity_id} to '{new_title}'")

    store = get_store(hass)
    stored_data = await store.async_load() or {}
    await fix_duplicate_real_numbers(hass)
    #await remove_from_packages_json("unavailable")
    order_numbers = ",".join(stored_data.keys())
    _LOGGER.debug("order_numbers %s", order_numbers)
    try:
        await get_data(order_numbers)
    except Exception as error:
        _LOGGER.error(
            "Error while retrieving package data for  track_packages: %s", error
        )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_TRACKING,
        remove_tracking,
        schema=REMOVE_TRACKING_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TRACKING,
        add_tracking,
        schema=ADD_TRACKING_SERVICE_SCHEMA,
    )
    hass.services.async_register(DOMAIN, "edit_title", edit_title_service)
class AliexpressPackageSensor(SensorEntity):
    _attr_attribution = ATTRIBUTION
    _attr_icon: str = ICON

    def __init__(self, data, order_number: str,title :str, hass: HomeAssistant, config_data) -> None:
        _LOGGER.debug(f"AliexpressPackageSensor created with order_number:{order_number}\ntitle: {title} \ndata: {data}")
        self._data = data
        self._attributes: dict[str, Any] = {}
        self._state = None
        self._order_number = order_number
        self._attr_name = f"Aliexpress_package_no_{order_number}"
        self._hass = hass
        self._lang=config_data.get(CONF_LANG)
        self._title=title or CONF_PACKAGE
        self._config_data=config_data

    @property
    def unique_id(self) -> str | None:
        return self._order_number

    @property
    def state(self):
        self._state =self._attributes.get("status", "Unavailable")
        return self._state

    async def set_title_attr(self, attrs) -> None:
        store = get_store(self._hass)
        stored_data= await store.async_load() or {}
        attrs.update({
            CONF_TITLE: stored_data.get(self._order_number,{}).get(CONF_TITLE, CONF_PACKAGE),
        })
    def get_trade_id(self,url) -> str | None:
        if url and "logisticsdetail" in url:
            return url.replace("https://track.aliexpress.com/logisticsdetail.htm?tradeId=","")
        return None
    def generate_order_url(self,url) -> str | None:
        trade_id=self.get_trade_id(url)
        if trade_id :
            return f"https://www.aliexpress.com/p/order/detail.html?orderId={trade_id}"
        return None
    def set_attr(self) -> None:
        data=self._data
        attrs= self._attributes
        attrs.update({
            CONF_TITLE: self._title,
            "order_number":self._order_number,
            "status": data.get("statusDesc", "Unknown"),
            "last_update_time": datetime.fromtimestamp(int(data.get("latestTrace", {}).get("time", 0) / 1000)) if "latestTrace" in data else None,
            "last_update_status": data.get("latestTrace", {}).get("standerdDesc", "Unknown"),
            "progressStatus" : data.get("processInfo", {}).get("progressStatus"),
            "carrier": data.get("destCpInfo", {}).get("cpName"),
            "carrier_url": data.get("destCpInfo", {}).get("url"),
            "daysNumber": data.get("daysNumber"),
            "orignal_track_id":data.get("mailNo")


        })
        real_mail_no = extract_realMailNo(data.get("realMailNo", ""))
        if real_mail_no is not None:
            attrs["realMailNo"] = real_mail_no
        order_url = self.generate_order_url(data.get("globalCurrentCardInfo", {}).get("pickUpGuideDTO",{}).get("url"))
        if order_url is not None:
            attrs["order_url"] = order_url
    @property
    def extra_state_attributes(self) -> dict[str, str]:
        self.set_attr( )
        return self._attributes or {}
    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, UPDATE_TOPIC, self._force_update))

    async def _force_update(self) -> None:
        await self.async_update(no_throttle=True)
        self.async_write_ha_state()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs: Any) -> None:
        _LOGGER.debug("async_update")
        try:
            value = await track_packages(self._hass, self._order_number,self._lang)
            if value and "module" in value and value["module"]:
                self._data=value["module"][0]
                self.set_attr()
                store = get_store(self.hass)
                data =  await store.async_load() or {}
                if self.check_for_auto_delete():
                    await self.async_remove()
                    data.pop( self._attributes["orignal_track_id"], None)
                    await store.async_save(data)
                    _LOGGER.warning(f"sensor.aliexpress_package_no_{self._order_number.lower()} was deleated!")
                    return
                await self.set_title_attr(self._attributes)
                if "realMailNo" in self._attributes:
                        data[self._order_number]["realMailNo"]=self._attributes["realMailNo"]
                        await store.async_save(data)
                        await fix_duplicate_real_numbers(self._hass)
        except Exception as err:
            _LOGGER.debug( err)
            _LOGGER.error("Error updating package data: %s", err)
    def check_for_auto_delete(self) -> bool:
        if self._config_data.get(CONF_AUTO_DELETE) and self.entity_id:
            status= self.state
            last_update_time= self._attributes["last_update_time"]
            now= datetime.now()
            return status=="Delivered" and  (now-last_update_time).days>self._config_data.get(CONF_AUTO_DELETE_DAYS)
        return False
    async def async_remove(self):
        """Remove the entity from Home Assistant."""
        await super().async_remove()
        entity_registry.async_get(self.hass).async_remove(self.entity_id)
        _LOGGER.info(f"Entity {self.entity_id} has been removed.")