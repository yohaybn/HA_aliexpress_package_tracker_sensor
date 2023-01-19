"""Support for  aliexpress_package_tracker."""
from __future__ import annotations

import logging
from typing import Any, Final
import json
from datetime import datetime


import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as BASE_PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry 
import aiohttp 

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .const import (
    ADD_TRACKING_SERVICE_SCHEMA,
    ATTR_TRACKINGS,
    ATTRIBUTION,
    CONF_TITLE,
    CONF_TRACKING_NUMBER,
    DEFAULT_NAME,
    DOMAIN,
    ICON,
    MIN_TIME_BETWEEN_UPDATES,
    REMOVE_TRACKING_SERVICE_SCHEMA,
    SERVICE_ADD_TRACKING,
    SERVICE_REMOVE_TRACKING,
    UPDATE_TOPIC,
    CONF_LANG,
)

_LOGGER: Final = logging.getLogger(__name__)

PLATFORM_SCHEMA: Final = BASE_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_LANG, default='en-US'): cv.string,
    }
)

_JSON_FILE='/config/custom_components/aliexpress_package_tracker/packages.json'
def read_packages_json():
    with open(_JSON_FILE) as f:
        data = json.load(f)
    _LOGGER.debug("data: %s", data)
    return data
def write_packages_json(data):
    json_object = json.dumps(data, indent=4)
    with open(_JSON_FILE, "w") as outfile:
        outfile.write(json_object)

async def add_to_packages_json(tracking_number,title):
    data= read_packages_json()
    data[tracking_number]=  {
                    "title": title,
                    "tracking_number": tracking_number,}
    write_packages_json(data)

async def remove_from_packages_json(tracking_number):
    data= read_packages_json()
    del data[tracking_number]
    write_packages_json(data)

async def track_packages(hass: HomeAssistant,order_numbers,lang='en-US'):
    """Fetch new state data for the sensor."""
    if order_numbers is not None:
        session = async_get_clientsession(hass)
        try:
            response = await session.get(f'https://global.cainiao.com/global/detail.json?mailNos={order_numbers}&lang={lang}')
            response.raise_for_status()
            data = await response.json()
            _LOGGER.debug("track_packages: %s",data)
            if data is not None:
                return data
            else:
                _LOGGER.error("Unable to retrieve package data for track_packages")
        except aiohttp.ClientError as error:
            _LOGGER.error("Error while retrieving package data for  track_packages: %s", error)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the aliexpress_package_tracker sensor platform."""

    lang = config[CONF_LANG]
    async def get_data(order_numbers):
        _LOGGER.debug("get_data start")
        try:
            data = await track_packages(hass,order_numbers,lang)
            _LOGGER.debug("get_data data: %s", data)
        except Exception as err:
            _LOGGER.error("No tracking data found. : %s", err)
            return
        sensors=[]
        for i in data['module']:
            sensors.append(AliexpressPackageSensor(i , i['mailNo'],hass))
        async_add_entities(sensors, True)


    async def handle_add_tracking(call: ServiceCall) -> None:
        """Call when a user adds a new Aftership tracking from Home Assistant."""
        _LOGGER.debug("handle_add_tracking")
        await add_to_packages_json(
            tracking_number=call.data[CONF_TRACKING_NUMBER],
            title=call.data.get(CONF_TITLE) or "Package" ,
            )
        await get_data(call.data[CONF_TRACKING_NUMBER])
        async_dispatcher_send(hass, UPDATE_TOPIC)


    async def handle_remove_tracking(call: ServiceCall) -> None:
        _LOGGER.debug("handle_remove_tracking")
        """Call when a user removes an Aftership tracking from Home Assistant."""
        await remove_from_packages_json(
            tracking_number=call.data[CONF_TRACKING_NUMBER],           
        )
        async_dispatcher_send(hass, UPDATE_TOPIC)
        
        entity_registry.async_get(hass).async_remove(f'sensor.Aliexpress_package_no_{call.data[CONF_TRACKING_NUMBER]}'.lower())
    

    order_numbers= ','.join(read_packages_json().keys())
    _LOGGER.debug("order_numbers %s",order_numbers)
    await get_data(order_numbers)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_TRACKING,
        handle_remove_tracking,
        schema=REMOVE_TRACKING_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TRACKING,
        handle_add_tracking,
        schema=ADD_TRACKING_SERVICE_SCHEMA,
    )



class AliexpressPackageSensor(SensorEntity):
    """Representation of a AliexpressPackage sensor."""

    _attr_attribution = ATTRIBUTION
    
    _attr_icon: str = ICON

    def __init__(self, data, order_number: str,hass) -> None:
        """Initialize the sensor."""
        _LOGGER.debug("AliexpressPackageSensor __init__ start")

        self._data=data
        self._attributes: dict[str, Any] = {}
        self._state: data['statusDesc'] | None = None,
        self._order_number=order_number
        self._attr_name = f'Aliexpress_package_no_{order_number}'
        self._hass = hass

    @property
    def friendly_name(self) -> str | None:
        return read_packages_json()[self._order_number]["title"]
    @property
    def unique_id(self) -> str | None:
        
        return self._order_number


    @property
    def state(self):
        """Return the state of the device."""
        if self._state is None:
            return "Unavilable"
        return self._state 
    @property
    def extra_state_attributes(self) -> dict[str, str]:
        if self._data is not None:
            self._attributes['estimated_max_delivery_date'] = datetime.fromtimestamp(self._data['globalEtaInfo']['deliveryMaxTime']/1000)
            self._attributes['last_update_time'] = datetime.fromtimestamp(self._data["latestTrace"]["time"]/1000)
            self._attributes['last_update_status'] = self._data["latestTrace"]["standerdDesc"]
            #self._attributes['more_info'] = self._data["detailList"]
            
        return self._attributes

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, UPDATE_TOPIC, self._force_update)
        )

    async def _force_update(self) -> None:
        """Force update of data."""
        await self.async_update(no_throttle=True)
        self.async_write_ha_state()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs: Any) -> None:
        """Get the latest data from the Canino API."""
        try:
            value = await track_packages(self._hass,self._order_number)
            value= value['module'][0]
            _LOGGER.debug("value - %s", value)
        except Exception as err:
            _LOGGER.error("Errors when querying Canino - %s", err)
            return

        self._attributes['estimated_max_delivery_date'] = datetime.fromtimestamp(value['globalEtaInfo']['deliveryMaxTime']/10000)
        self._attributes['last_update_time'] = datetime.fromtimestamp(value["latestTrace"]["time"]/1000)
        self._attributes['last_update_status'] = value["latestTrace"]["standerdDesc"]
        #self._attributes['more_info'] = self._data["detailList"]

        self._state = value["statusDesc"]
