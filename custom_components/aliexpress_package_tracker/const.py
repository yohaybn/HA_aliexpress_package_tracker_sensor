"""Constants for the aliexpress_package_tracker integration."""

from __future__ import annotations
from datetime import timedelta
from typing import Final
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
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

MIN_TIME_BETWEEN_UPDATES: Final = timedelta(hours=1)  # (days=1)

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
