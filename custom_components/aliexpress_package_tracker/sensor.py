"""Support for aliexpress_package_tracker sensors."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, Final
import re


from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.event import async_track_state_change_event

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util  # Import datetime utility

from .const import (
    ATTRIBUTION,
    CONF_AUTO_DELETE,
    CONF_AUTO_DELETE_DAYS,
    CONF_PACKAGE,
    CONF_TITLE,
    CONF_TRACKING_NUMBER,
    DOMAIN,
    ICON,
    COORDINATOR,  # Import coordinator key
    ADD_TRACKING_SERVICE_SCHEMA,
    REMOVE_TRACKING_SERVICE_SCHEMA,
    EDIT_TITLE_SERVICE_SCHEMA,  # Import service schema
    SERVICE_ADD_TRACKING,
    SERVICE_REMOVE_TRACKING,
)
from .helpers import (  # Import helpers
    get_store,
    _clean_tracking_number,
    extract_actual_tracking_number,  # Potentially needed for services
    remove_entity_from_registry,
)

_LOGGER: Final = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aliexpress package tracker sensor platform."""

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        COORDINATOR
    ]
    async def state_change_listener(event):
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        
        if old_state and new_state and old_state != new_state:
            # Fire a custom event
            hass.bus.async_fire("aliexpress_package_data_updated", {
                "entity_id": entity_id,
                "old_state": old_state.state if old_state else None,
                "new_state": new_state.state if new_state else None,
            })
            _LOGGER.debug(
                "State change detected for %s: %s -> %s",
                entity_id,
                old_state.state if old_state else "None",
                new_state.state,
            )
    store = get_store(hass)

    # Add sensors for existing data from the coordinator
    # The coordinator runs first refresh, so coordinator.data should be populated
    sensors = []
    if coordinator.data:
        for order_number, data in coordinator.data.items():
            sensors.append(AliexpressPackageSensor(coordinator, order_number))

    if sensors:
        for sensor in sensors:
            async_track_state_change_event(hass, f"sensor.{sensor.name.lower().replace(" ","_")}", state_change_listener)

    async_add_entities(sensors, True)  # Add initial sensors

    # Listener to add/remove sensors dynamically when coordinator data changes
    @callback
    def async_update_sensors() -> None:
        """Update sensors based on coordinator data."""
        if not coordinator.last_update_success:
            # Don't update sensors if the coordinator failed
            _LOGGER.warning("Coordinator update failed, not updating sensors.")
            return

        stored_data = coordinator.data or {}
        current_sensors = {
            entity.unique_id: entity
            for entity in hass.data[DOMAIN].get("sensor_entities", {}).values()
            if isinstance(entity, AliexpressPackageSensor)  # Ensure it's our sensor
        }
        new_sensors = []

        # Add new sensors or update existing ones implicitly via CoordinatorEntity
        for order_number in stored_data:
            if order_number not in current_sensors:
                _LOGGER.debug("Adding new sensor for %s", order_number)
                new_sensor = AliexpressPackageSensor(coordinator, order_number)
                new_sensors.append(new_sensor)
                # Store reference for removal tracking (optional but good practice)
                hass.data[DOMAIN].setdefault("sensor_entities", {})[order_number] = (
                    new_sensor
                )

        if new_sensors:
            async_add_entities(new_sensors, True)

        # Logic to remove sensors whose data is no longer in the coordinator
        # This is handled implicitly by CoordinatorEntity making sensors unavailable
        # If explicit removal is desired (e.g., from UI), add logic here to call
        # entity_registry.async_remove or similar for sensors not in stored_data.keys()
        # For now, let them become unavailable. Auto-delete handles actual removal.

        # Store current sensors for next update comparison (optional)
        hass.data[DOMAIN]["sensor_entities"] = {
            entity.unique_id: entity
            for entity in hass.data[DOMAIN].get("sensor_entities", {}).values()
            if isinstance(entity, AliexpressPackageSensor)
            and entity.unique_id in stored_data
        }
        hass.data[DOMAIN]["sensor_entities"].update(
            {s.unique_id: s for s in new_sensors}
        )

    # Register the listener
    config_entry.async_on_unload(coordinator.async_add_listener(async_update_sensors))

    # Initial sensor check after setup is complete
    # async_update_sensors() # Call once after initial sensors are added if needed

    # --- Service Handlers ---
    async def handle_add_tracking(call: ServiceCall) -> None:
        """Handle the service call to add a tracking number."""
        tracking_number = _clean_tracking_number(call.data.get(CONF_TRACKING_NUMBER))
        title = call.data.get(CONF_TITLE) or CONF_PACKAGE

        if not tracking_number:
            _LOGGER.error(
                "Service call '%s' failed: Tracking number is missing or invalid",
                SERVICE_ADD_TRACKING,
            )
            return

        _LOGGER.info(
            "Service '%s': Adding tracking number '%s' with title '%s'",
            SERVICE_ADD_TRACKING,
            tracking_number,
            title,
        )
        loaded_data = await store.async_load() or {}

        # Check if the number (or a potential merged version) already exists
        # This requires a check against coordinator data *and* store keys
        # For simplicity, we'll just check the store keys for adding
        if tracking_number in loaded_data:
            current_title = loaded_data[tracking_number].get(CONF_TITLE, CONF_PACKAGE)
            current_numbers = loaded_data[tracking_number].get(
                CONF_TRACKING_NUMBER, tracking_number
            )

            # Combine titles intelligently
            combined_titles = set(
                filter(
                    None,
                    [
                        t.strip()
                        for t in f"{current_title},{title}".split(",")
                        if t.strip() and t != CONF_PACKAGE
                    ],
                )
            )
            new_title = ", ".join(sorted(list(combined_titles))) or CONF_PACKAGE

            # Add tracking number to list if not present
            combined_nums = set(
                filter(
                    None,
                    [
                        n.strip()
                        for n in f"{current_numbers},{tracking_number}".split(",")
                    ],
                )
            )
            new_numbers = ",".join(sorted(list(combined_nums)))

            loaded_data[tracking_number][CONF_TITLE] = new_title
            loaded_data[tracking_number][CONF_TRACKING_NUMBER] = new_numbers
            _LOGGER.debug("Updated existing entry for %s", tracking_number)

        else:
            loaded_data[tracking_number] = {
                CONF_TITLE: title,
                CONF_TRACKING_NUMBER: tracking_number,  # Start with itself
            }
            _LOGGER.debug("Created new entry for %s", tracking_number)

        await store.async_save(loaded_data)
        # Request coordinator refresh to pick up the new number
        await coordinator.async_request_refresh()

    async def handle_remove_tracking(call: ServiceCall) -> None:
        """Handle the service call to remove a tracking number or entity."""
        tracking_number_to_remove = call.data.get(CONF_TRACKING_NUMBER)
        entity_ids_to_remove = call.data.get(CONF_ENTITY_ID)
        made_changes = False
        loaded_data = await store.async_load() or {}
        numbers_removed = set()

        if tracking_number_to_remove:
            cleaned_number = _clean_tracking_number(tracking_number_to_remove)
            if cleaned_number in loaded_data:
                _LOGGER.info(
                    "Service '%s': Removing tracking number '%s'",
                    SERVICE_REMOVE_TRACKING,
                    cleaned_number,
                )
                del loaded_data[cleaned_number]
                numbers_removed.add(cleaned_number)
                made_changes = True
                # Optionally remove from entity registry immediately
                entity_id = f"sensor.aliexpress_package_no_{cleaned_number.lower()}"
                remove_entity_from_registry(hass, entity_id)
            else:
                _LOGGER.warning(
                    "Service '%s': Tracking number '%s' not found in storage",
                    SERVICE_REMOVE_TRACKING,
                    cleaned_number,
                )

        elif entity_ids_to_remove:
            for entity_id in entity_ids_to_remove:
                # Find the sensor instance (if loaded)
                sensor_entity = (
                    hass.data[DOMAIN]
                    .get("sensor_entities", {})
                    .get(entity_id.split(".")[-1].replace("aliexpress_package_no_", ""))
                )  # Extract ID from entity_id
                state = hass.states.get(entity_id)

                # Determine the tracking number (key in storage/coordinator)
                number_from_state = None
                if state and state.attributes.get("order_number"):
                    number_from_state = state.attributes["order_number"]
                elif sensor_entity and hasattr(sensor_entity, "unique_id"):
                    number_from_state = sensor_entity.unique_id

                if number_from_state and number_from_state in loaded_data:
                    _LOGGER.info(
                        "Service '%s': Removing tracking number '%s' based on entity '%s'",
                        SERVICE_REMOVE_TRACKING,
                        number_from_state,
                        entity_id,
                    )
                    del loaded_data[number_from_state]
                    numbers_removed.add(number_from_state)
                    made_changes = True
                    remove_entity_from_registry(hass, entity_id)  # Remove from registry
                elif number_from_state:
                    _LOGGER.warning(
                        "Service '%s': Tracking number '%s' (from entity '%s') not found in storage",
                        SERVICE_REMOVE_TRACKING,
                        number_from_state,
                        entity_id,
                    )
                    # Still try removing from registry if state existed
                    if state:
                        remove_entity_from_registry(hass, entity_id)
                else:
                    _LOGGER.warning(
                        "Service '%s': Could not determine tracking number for entity '%s'",
                        SERVICE_REMOVE_TRACKING,
                        entity_id,
                    )
                    remove_entity_from_registry(
                        hass, entity_id
                    )  # Attempt removal anyway

        else:
            _LOGGER.error(
                "Service '%s' failed: Must provide either '%s' or '%s'",
                SERVICE_REMOVE_TRACKING,
                CONF_TRACKING_NUMBER,
                CONF_ENTITY_ID,
            )
            return

        if made_changes:
            await store.async_save(loaded_data)
            # Request refresh so coordinator stops tracking removed numbers
            await coordinator.async_request_refresh()
        _LOGGER.debug(
            "Service '%s' finished. Numbers removed: %s",
            SERVICE_REMOVE_TRACKING,
            numbers_removed,
        )

    async def handle_edit_title(call: ServiceCall) -> None:
        """Handle the service call to edit the title."""
        entity_ids = call.data.get("entity_id")
        new_title = call.data.get("new_title", "").strip()
        made_changes = False
        loaded_data = await store.async_load() or {}

        if not entity_ids:
            _LOGGER.error(
                "Service 'edit_title': Missing required parameter 'entity_id'"
            )
            return
        if not new_title:
            _LOGGER.error(
                "Service 'edit_title': Missing required parameter 'new_title' or it's empty"
            )
            return

        for entity_id in entity_ids:
            state = hass.states.get(entity_id)
            order_number = None
            if state and state.attributes.get("order_number"):
                order_number = state.attributes["order_number"]
            else:
                # Fallback: try extracting from entity_id if state is missing/incomplete
                match = re.search(r"aliexpress_package_no_(.+)", entity_id)
                if match:
                    order_number = match.group(1)

            if order_number and order_number in loaded_data:
                _LOGGER.info(
                    "Service 'edit_title': Updating title for '%s' (Order No: %s) to '%s'",
                    entity_id,
                    order_number,
                    new_title,
                )
                loaded_data[order_number][CONF_TITLE] = new_title
                made_changes = True
            elif order_number:
                _LOGGER.warning(
                    "Service 'edit_title': Order number '%s' (from entity '%s') not found in storage.",
                    order_number,
                    entity_id,
                )
            else:
                _LOGGER.warning(
                    "Service 'edit_title': Could not determine order number for entity '%s'. Cannot edit title.",
                    entity_id,
                )

        if made_changes:
            await store.async_save(loaded_data)
            # Request refresh so coordinator updates the title in its data structure
            await coordinator.async_request_refresh()

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TRACKING,
        handle_add_tracking,
        schema=ADD_TRACKING_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_TRACKING,
        handle_remove_tracking,
        schema=REMOVE_TRACKING_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "edit_title",  # Service name
        handle_edit_title,
        schema=EDIT_TITLE_SERVICE_SCHEMA,  # Use defined schema
    )


class AliexpressPackageSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Aliexpress package tracker sensor using CoordinatorEntity."""

    _attr_attribution = ATTRIBUTION
    _attr_icon: str = ICON
    # Sensor device class, state class can be set depending on the nature of 'status'
    # _attr_device_class = SensorDeviceClass.ENUM # If status has fixed values
    # _attr_state_class = SensorStateClass.MEASUREMENT # Or other if applicable

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        order_number: str,  # This is the key in coordinator.data
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._order_number = order_number
        self._attr_unique_id = order_number  # Use the coordinator key as unique_id
        self._attr_name = f"Aliexpress Package No {order_number}"  # More readable name
        self._config_data = coordinator.hass.config_entries.async_get_entry(
            coordinator.config_entry.entry_id
        ).data  # Access config via coordinator if needed

        # Initialize attributes from the first coordinator data if available
        self._update_internal_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Sensor %s received update from coordinator", self.entity_id)
        self._update_internal_state()
        self.async_write_ha_state()

        # Check for auto-deletion after state update
        if self._check_for_auto_delete():
            _LOGGER.info(
                "Auto-deleting sensor %s (Order: %s) due to delivered status and age.",
                self.entity_id,
                self._order_number,
            )
            # Call the remove service to handle cleanup consistently
            hass = self.coordinator.hass
            try:
                # Don't await this, run it in background not to block coordinator update
                hass.async_create_task(
                    hass.services.async_call(
                        DOMAIN,
                        SERVICE_REMOVE_TRACKING,
                        {CONF_TRACKING_NUMBER: self._order_number},
                        blocking=False,  # Run in background
                    )
                )
            except Exception as e:
                _LOGGER.error(
                    "Error triggering auto-delete service call for %s: %s",
                    self.entity_id,
                    e,
                )

    def _update_internal_state(self) -> None:
        """Update internal state attributes based on coordinator data."""
        coordinator_data = self.coordinator.data or {}
        sensor_data = coordinator_data.get(self._order_number)

        if sensor_data and isinstance(sensor_data, dict):
            api_data = sensor_data.get("api_data", {})  # Get the raw api data part
            self._attr_native_value = api_data.get(
                "statusDesc", "Unknown"
            )  # Sensor state

            # Process attributes
            new_attrs = {
                CONF_TITLE: sensor_data.get(CONF_TITLE, CONF_PACKAGE),
                "order_number": self._order_number,  # The actual ID used
                "orignal_track_ids": sensor_data.get(
                    "original_tracking_numbers", self._order_number
                ),
                "status": api_data.get("statusDesc", "Unknown"),
                "status_english": api_data.get(
                    "status", "Unknown"
                ),  # hold english status for auto delete
                "last_update_status": api_data.get("latestTrace", {}).get(
                    "standerdDesc", "Unknown"
                ),
                "progressStatus": api_data.get("processInfo", {}).get("progressStatus"),
                "carrier": api_data.get("destCpInfo", {}).get("cpName"),
                "carrier_url": api_data.get("destCpInfo", {}).get("url"),
                "daysNumber": api_data.get("daysNumber"),
                "originCountry": api_data.get("originCountry"),
                "destCountry": api_data.get("destCountry"),
                # Safely parse timestamp
                "last_update_time": None,
                "order_url": self._generate_order_url(
                    api_data.get("globalCurrentCardInfo", {})
                    .get("pickUpGuideDTO", {})
                    .get("url")
                ),
            }

            last_trace = api_data.get("latestTrace", {})
            timestamp_ms = last_trace.get("time")
            if (
                timestamp_ms
                and isinstance(timestamp_ms, (int, float))
                and timestamp_ms > 0
            ):
                try:
                    # Convert milliseconds to seconds and create datetime object
                    new_attrs["last_update_time"] = dt_util.utc_from_timestamp(
                        timestamp_ms / 1000
                    )
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Could not parse timestamp %s for %s",
                        timestamp_ms,
                        self.entity_id,
                    )
                    new_attrs["last_update_time"] = None
            else:
                new_attrs["last_update_time"] = (
                    None  # Ensure it's None if no valid time
                )

            self._attr_extra_state_attributes = new_attrs
            self._attr_available = True

        else:
            # Data for this sensor is not available in coordinator
            self._attr_native_value = (
                None  # Or keep last known state? Set to None for clarity.
            )
            self._attr_available = False
            _LOGGER.debug(
                "Data for sensor %s not found in coordinator update.", self.entity_id
            )

    def _get_trade_id(self, url: str | None) -> str | None:
        """Extract the trade ID from a URL."""
        if url and isinstance(url, str) and "logisticsdetail" in url:
            # Use regex for robustness
            match = re.search(r"tradeId=([^&]+)", url)
            if match:
                return match.group(1)
        return None

    def _generate_order_url(self, tracking_url: str | None) -> str | None:
        """Generate the Aliexpress order detail URL from a tracking URL."""
        trade_id = self._get_trade_id(tracking_url)
        if trade_id:
            return f"https://www.aliexpress.com/p/order/detail.html?orderId={trade_id}"
        return None

    def _check_for_auto_delete(self) -> bool:
        """Check if the entity should be automatically deleted."""
        if not self._attr_available:  # Don't delete if unavailable
            return False

        if self._config_data.get(CONF_AUTO_DELETE):
            status = self.extra_state_attributes.get("status_english")
            last_update_time = self.extra_state_attributes.get("last_update_time")

            # Check if status is 'Delivered' (adjust string if needed based on API)
            # and last_update_time is valid datetime
            if (
                status
                and "delivered" in status.lower()
                and isinstance(last_update_time, datetime)
            ):
                now = dt_util.utcnow()  # Use timezone-aware now
                days_threshold = self._config_data.get(
                    CONF_AUTO_DELETE_DAYS, 30
                )  # Default 30 days
                if (now - last_update_time) > timedelta(days=days_threshold):
                    return True
        return False
