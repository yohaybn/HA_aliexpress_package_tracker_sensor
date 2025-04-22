"""Constants for the aliexpress_package_tracker integration."""

from __future__ import annotations
from __future__ import annotations

from datetime import timedelta
from typing import Final

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_ENTITY_ID


DOMAIN: Final = "aliexpress_package_tracker"
INTEGRATION_NAME: Final = "Aliexpress Package Tracker"

ATTRIBUTION: Final = "Information provided by Cainiao API"
ATTR_TRACKINGS: Final = "trackings"

STORAGE_KEY = f"{DOMAIN}_data"
STORAGE_VERSION = 1

CONF_LANG: Final = "language"
CONF_TITLE: Final = "title"
CONF_PACKAGE: Final = "Package"
CONF_AUTO_DELETE: Final = "AUTO_DELETE"
CONF_AUTO_DELETE_DAYS: Final = "AUTO_DELETE_DAYS"

CONF_TRACKING_NUMBER: Final = "tracking_number"

DEFAULT_NAME: Final = "aliexpress_package_tracker"
UPDATE_TOPIC: Final = f"{DOMAIN}_update"

ICON: Final = "mdi:package-variant-closed"

MIN_TIME_BETWEEN_UPDATES: Final = timedelta(
    hours=6
)  # alibaba start to block unusal traffic

SERVICE_ADD_TRACKING: Final = "add_tracking"
SERVICE_REMOVE_TRACKING: Final = "remove_tracking"

ADD_TRACKING_SERVICE_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_TRACKING_NUMBER): cv.string,
        vol.Optional(CONF_TITLE): cv.string,
    }
)

REMOVE_TRACKING_SERVICE_SCHEMA: Final = vol.Schema(
    {
        vol.Optional(CONF_TRACKING_NUMBER): cv.string,
        vol.Optional(CONF_ENTITY_ID): vol.Any(cv.string, list),
    }
)
# Define update interval for the coordinator
UPDATE_INTERVAL = timedelta(minutes=30)  # Or adjust as needed

# Key for storing coordinator in hass.data
COORDINATOR = "coordinator"

# Service Schemas (no changes needed here usually, but good to review)
ADD_TRACKING_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TRACKING_NUMBER): cv.string,
        vol.Optional(CONF_TITLE): cv.string,
    }
)

REMOVE_TRACKING_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_TRACKING_NUMBER, "tracker_id"): cv.string,
        vol.Exclusive(CONF_ENTITY_ID, "tracker_id"): cv.entity_ids,
    }
)

# Define schema for edit_title service if not already defined implicitly
EDIT_TITLE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Required("new_title"): cv.string,
    }
)
