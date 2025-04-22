"""Helper functions for the aliexpress_package_tracker component."""

import logging
import re
from string import printable
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers import entity_registry as er

from .const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    CONF_TITLE,
    CONF_TRACKING_NUMBER,
    CONF_PACKAGE,
    DOMAIN,  # Needed for entity_id generation
)


_LOGGER = logging.getLogger(__name__)


def get_store(hass: HomeAssistant) -> Store:
    """Retrieve the storage object."""
    return Store(hass, STORAGE_VERSION, STORAGE_KEY)


async def _fetch_cainiao_data(
    hass: HomeAssistant, order_numbers: str, lang: str = "en-US"
) -> dict | None:
    """Fetch package tracking data from the Cainiao API."""
    _LOGGER.debug("Fetching Cainiao data for: %s (lang: %s)", order_numbers, lang)
    session = async_get_clientsession(hass)
    url = f"https://global.cainiao.com/global/detail.json?mailNos={order_numbers}&lang={lang}"
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            _LOGGER.debug("Received data: %s", data)
            return data
    except aiohttp.ClientResponseError as error:
        _LOGGER.warning(
            "Error fetching package data for %s (%s): %s",
            order_numbers,
            error.status,
            error.message,
        )
        # Raise the error so the coordinator knows the update failed
        raise
    except aiohttp.ClientError as error:
        _LOGGER.error(
            "Client error fetching package data for %s: %s", order_numbers, error
        )
        raise
    except Exception as error:
        _LOGGER.error(
            "Unexpected error fetching package data for %s: %s", order_numbers, error
        )
        raise
    # Should not be reached if exceptions are raised properly
    return None


def extract_realMailNo(data: dict) -> str | None:
    """Extract the real mail number from API data."""
    # Prefer copyRealMailNo if available and looks valid
    copy_real_mail_no = data.get("copyRealMailNo")
    if (
        copy_real_mail_no
        and isinstance(copy_real_mail_no, str)
        and len(copy_real_mail_no) > 5
    ):  # Basic sanity check
        return copy_real_mail_no

    # Fallback to extracting from realMailNo string
    real_mail_no_str = data.get("realMailNo", "")
    if real_mail_no_str and isinstance(real_mail_no_str, str):
        # Regex improved slightly for flexibility
        regex = r"([A-Z]{0,3}\d{9,30}[A-Z]{0,2})"
        match = re.search(regex, real_mail_no_str)
        if match:
            return match.group(1)  # Use group 1 for the actual number

    # Final fallback to the original mailNo from the data item
    return data.get("mailNo")


def extract_actual_tracking_number(data: dict) -> str | None:
    """Determine the most likely actual tracking number from API data."""
    real_mail_no = extract_realMailNo(data)
    # Return realMailNo if found, otherwise fallback to mailNo
    return real_mail_no if real_mail_no else data.get("mailNo")


def _clean_tracking_number(tracking_number: str) -> str:
    """Clean the tracking number."""
    if not isinstance(tracking_number, str):
        return ""
    return "".join(char for char in tracking_number.strip() if char in printable)


def remove_entity_from_registry(hass: HomeAssistant, entity_id: str):
    """Remove an entity from the entity registry."""
    registry = er.async_get(hass)
    if registry.async_is_registered(entity_id):
        _LOGGER.debug("Removing entity '%s' from registry", entity_id)
        registry.async_remove(entity_id)
        _LOGGER.info("Successfully removed entity '%s' from registry", entity_id)
    else:
        _LOGGER.debug("Entity '%s' not found in registry, skipping removal", entity_id)

