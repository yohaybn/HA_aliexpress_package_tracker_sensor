"""Support for aliexpress_package_tracker sensors."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import re
from typing import Final

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION,
    CONF_AUTO_DELETE,
    CONF_AUTO_DELETE_DAYS,
    CONF_PACKAGE,
    CONF_TITLE,
    CONF_TRACKING_NUMBER,
    DOMAIN,
    ICON,
    COORDINATOR,
    ADD_TRACKING_SERVICE_SCHEMA,
    REMOVE_TRACKING_SERVICE_SCHEMA,
    EDIT_TITLE_SERVICE_SCHEMA,
    SERVICE_ADD_TRACKING,
    SERVICE_REMOVE_TRACKING,
)
from .helpers import get_store, _clean_tracking_number, remove_entity_from_registry

_LOGGER: Final = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aliexpress package tracker sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    store = get_store(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("sensor_entities", {})

    # --- Création initiale des capteurs ---
    sensors = []
    if coordinator.data:
        for order_number in coordinator.data:
            unique_id = order_number.lower()
            if unique_id in hass.data[DOMAIN]["sensor_entities"]:
                continue
            sensor = AliexpressPackageSensor(coordinator, order_number)
            sensors.append(sensor)
            hass.data[DOMAIN]["sensor_entities"][unique_id] = sensor

    async_add_entities(sensors, True)

    # --- Listener pour mise à jour des capteurs ---
    @callback
    def async_update_sensors() -> None:
        """Met à jour les capteurs selon les données du coordinator."""
        if not coordinator.last_update_success:
            _LOGGER.warning("Coordinator update failed, not updating sensors.")
            return

        stored_data = coordinator.data or {}
        current_sensors = hass.data[DOMAIN]["sensor_entities"]
        new_sensors = []

        for order_number in stored_data:
            unique_id = order_number.lower()
            if unique_id in current_sensors:
                continue
            _LOGGER.debug("Adding new sensor for %s", order_number)
            sensor = AliexpressPackageSensor(coordinator, order_number)
            new_sensors.append(sensor)
            current_sensors[unique_id] = sensor

        if new_sensors:
            async_add_entities(new_sensors, True)

        # Supprime les capteurs qui ne sont plus dans le coordinator
        valid_ids = {k.lower() for k in stored_data.keys()}
        for uid in list(current_sensors.keys()):
            if uid not in valid_ids:
                del current_sensors[uid]

    config_entry.async_on_unload(coordinator.async_add_listener(async_update_sensors))

    # --- Services ---
    async def handle_add_tracking(call: ServiceCall) -> None:
        tracking_number = _clean_tracking_number(call.data.get(CONF_TRACKING_NUMBER))
        title = call.data.get(CONF_TITLE) or CONF_PACKAGE
        if not tracking_number:
            _LOGGER.error("Service '%s' failed: Tracking number missing", SERVICE_ADD_TRACKING)
            return
        loaded_data = await store.async_load() or {}
        loaded_data[tracking_number] = {
            CONF_TITLE: title,
            CONF_TRACKING_NUMBER: tracking_number,
        }
        await store.async_save(loaded_data)
        await coordinator.async_request_refresh()

    async def handle_remove_tracking(call: ServiceCall) -> None:
        tracking_number_to_remove = call.data.get(CONF_TRACKING_NUMBER)
        entity_ids_to_remove = call.data.get(CONF_ENTITY_ID)
        made_changes = False
        loaded_data = await store.async_load() or {}

        if tracking_number_to_remove:
            cleaned_number = _clean_tracking_number(tracking_number_to_remove)
            if cleaned_number in loaded_data:
                del loaded_data[cleaned_number]
                made_changes = True
                remove_entity_from_registry(hass, f"sensor.aliexpress_package_no_{cleaned_number.lower()}")
        elif entity_ids_to_remove:
            for entity_id in entity_ids_to_remove:
                number_from_entity = entity_id.split("aliexpress_package_no_")[-1].lower()
                if number_from_entity in loaded_data:
                    del loaded_data[number_from_entity]
                    made_changes = True
                    remove_entity_from_registry(hass, entity_id)

        if made_changes:
            await store.async_save(loaded_data)
            await coordinator.async_request_refresh()

    async def handle_edit_title(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id")
        new_title = call.data.get("new_title", "").strip()
        if not entity_ids or not new_title:
            _LOGGER.error("Service 'edit_title' missing parameters")
            return
        loaded_data = await store.async_load() or {}
        made_changes = False

        for entity_id in entity_ids:
            order_number = entity_id.split("aliexpress_package_no_")[-1].lower()
            if order_number in loaded_data:
                loaded_data[order_number][CONF_TITLE] = new_title
                made_changes = True
        if made_changes:
            await store.async_save(loaded_data)
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_ADD_TRACKING, handle_add_tracking, schema=ADD_TRACKING_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_TRACKING, handle_remove_tracking, schema=REMOVE_TRACKING_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "edit_title", handle_edit_title, schema=EDIT_TITLE_SERVICE_SCHEMA)


class AliexpressPackageSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Aliexpress package tracker sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_icon: str = ICON

    def __init__(self, coordinator: DataUpdateCoordinator, order_number: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._order_number = order_number
        self._attr_unique_id = order_number.lower()
        self._attr_name = f"Aliexpress Package No {order_number}"
        self._config_data = coordinator.hass.config_entries.async_get_entry(
            coordinator.config_entry.entry_id
        ).data
        self._update_internal_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()
        self.async_write_ha_state()

        if self._check_for_auto_delete():
            hass = self.coordinator.hass
            hass.async_create_task(
                hass.services.async_call(
                    DOMAIN,
                    SERVICE_REMOVE_TRACKING,
                    {CONF_TRACKING_NUMBER: self._order_number},
                    blocking=False,
                )
            )

    def _update_internal_state(self) -> None:
        """Update internal state attributes based on coordinator data."""
        data = self.coordinator.data.get(self._order_number, {})
        api_data = data.get("api_data", {}) if data else {}
        self._attr_native_value = api_data.get("statusDesc", "Unknown")
        self._attr_extra_state_attributes = {
            CONF_TITLE: data.get(CONF_TITLE, CONF_PACKAGE),
            "order_number": self._order_number,
            "status": api_data.get("statusDesc", "Unknown"),
            "status_english": api_data.get("status", "Unknown"),
            "last_update_status": api_data.get("latestTrace", {}).get("standerdDesc", "Unknown"),
            "carrier": api_data.get("destCpInfo", {}).get("cpName"),
            "last_update_time": self._parse_timestamp(api_data.get("latestTrace", {}).get("time")),
        }
        self._attr_available = bool(data)

    def _parse_timestamp(self, timestamp_ms: int | None) -> datetime | None:
        """Convert API timestamp to datetime."""
        if timestamp_ms and isinstance(timestamp_ms, (int, float)) and timestamp_ms > 0:
            try:
                return dt_util.utc_from_timestamp(timestamp_ms / 1000)
            except Exception:
                return None
        return None

    def _check_for_auto_delete(self) -> bool:
        """Determine if sensor should auto-delete based on config."""
        if not self._attr_available or not self._config_data.get(CONF_AUTO_DELETE):
            return False
        status = self.extra_state_attributes.get("status_english")
        last_update = self.extra_state_attributes.get("last_update_time")
        if status and "delivered" in status.lower() and isinstance(last_update, datetime):
            days_threshold = self._config_data.get(CONF_AUTO_DELETE_DAYS, 30)
            if (dt_util.utcnow() - last_update) > timedelta(days=days_threshold):
                return True
        return False