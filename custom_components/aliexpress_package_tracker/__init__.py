"""The aliexpress_package_tracker component."""


import logging
from homeassistant.core import HomeAssistant

from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from .const import DOMAIN,    STORAGE_KEY ,    STORAGE_VERSION
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_setup(hass: HomeAssistant, config: ConfigType):
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_data = await store.async_load() or {}
    if entry.entry_id in hass.data[DOMAIN]:
        for key in stored_data.keys():
            _LOGGER.debug(f"async_remove(sensor.aliexpress_package_no_{key.lower()})")
            hass.states.async_remove(f"sensor.aliexpress_package_no_{key.lower()}")
        await store.async_save({})
        hass.data[DOMAIN].pop(entry.entry_id)
    return True
