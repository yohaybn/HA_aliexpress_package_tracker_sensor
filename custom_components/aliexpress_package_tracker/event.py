# custom_components/aliexpress_package_tracker/event.py

from homeassistant.components.event import EventEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# The EVENT_TYPE we will fire when a package updates
PACKAGE_UPDATE_EVENT = "package_update"

# The event entity will keep track of the last update time
class AliexpressPackageUpdateEvent(
    CoordinatorEntity, EventEntity
):
    """AliExpress Package Update Event Entity."""

    _attr_has_entity_name = True
    _attr_name = "Update Event"
    _attr_event_types = [PACKAGE_UPDATE_EVENT] # Define the possible event types

    def __init__(self, coordinator, config_entry):
        """Initialize the event entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.unique_id}_update_event"

        # Register a callback to fire the event when data is updated
        coordinator.async_add_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Find the package that was just updated.
        # This is a placeholder for your actual update logic to determine
        # which package triggered the update. For simplicity, we'll fire
        # a generic event, but in a real-world scenario, you'd iterate
        # through the coordinator data (self.coordinator.data) to check
        # for new statuses since the last update.

        # *** You would typically have a loop here to check all packages ***
        # *** that had a new event since the last poll. ***

        # This will fire the event entity event with the last update time as state
        # The extra state data will be accessible in automations
        self._trigger_event(
            PACKAGE_UPDATE_EVENT,
            # In your coordinator, you should store the detailed update data
            # to pass it here. This example uses dummy data.
            {"tracking_number": "ExampleCN", "status": "In Transit"}
        )
        self.async_write_ha_state()

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Event platform from a config entry."""
    # Assuming the data coordinator is stored in hass.data[DOMAIN][config_entry.entry_id]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AliexpressPackageUpdateEvent(coordinator, config_entry)])