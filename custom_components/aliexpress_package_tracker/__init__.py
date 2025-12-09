"""The aliexpress_package_tracker component."""

import aiohttp
import json
import logging
import os
import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection

from .const import (
    CONF_LANG,
    CONF_PACKAGE,
    CONF_TITLE,
    CONF_TRACKING_NUMBER,
    COORDINATOR,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)
from .helpers import (
    _fetch_cainiao_data,
    extract_actual_tracking_number,
    get_store,
)

PLATFORMS: list[str] = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def init_lovelace_resource(hass: HomeAssistant, url: str, version: str) -> bool:
    """Add/update lovelace resource with proper version handling.

    Based on the approach used by ha-simple-timer integration.
    """
    try:
        resources: ResourceStorageCollection = hass.data["lovelace"].resources
        await resources.async_get_info()
        url_with_version = f"{url}?v={version}"
        for item in resources.async_items():
            if not item.get("url", "").startswith(url):
                continue

            if item["url"].endswith(version):
                _LOGGER.info(
                    "✅ Aliexpress-package-tracker resource already at version %s",
                    version,
                )
                return False

            # Update to new version
            _LOGGER.info(
                "🔄 Updating Aliexpress-package-tracker resource from %s to %s",
                item["url"],
                url_with_version,
            )
            await resources.async_update_item(
                item["id"], {"res_type": "module", "url": url_with_version}
            )
            return True

        # Create new resource
        _LOGGER.info(
            "✅ Creating new Aliexpress-package-tracker resource: %s", url_with_version
        )
        await resources.async_create_item(
            {"res_type": "module", "url": url_with_version}
        )
        return True

    except Exception as err:
        _LOGGER.error("❌ Failed to register lovelace resource: %s", err)
        return False


async def _async_install_card(hass: HomeAssistant) -> None:
    """Install the card automatically."""
    try:
        # Get the integration path
        integration_path = Path(__file__).parent

        # Get version from manifest
        manifest_path = integration_path / "manifest.json"
        version = "1.0.0"
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
                version = manifest.get("version", "1.0.0")
        except Exception as err:
            _LOGGER.warning("Could not read version from manifest: %s", err)

        # Source files
        card_js_source = integration_path / "dist"

        # Destination directory
        www_dir = Path(hass.config.path("www"))
        card_dir = www_dir / "lovelace-aliexpress-package-card"

        # Create directory if it doesn't exist
        card_dir.mkdir(parents=True, exist_ok=True)

        # Copy files if they exist
        if card_js_source.exists():
            shutil.copytree(card_js_source, card_dir, dirs_exist_ok=True)
            _LOGGER.info(
                "Aliexpress-package-trackerCard installed to www/lovelace-aliexpress-package-card/"
            )
        else:
            _LOGGER.warning(
                "Aliexpress-package-tracker Card source file not found at %s. "
                "You may need to build the card first.",
                card_js_source,
            )

        _LOGGER.info(
            "✅ Aliexpress-package-tracker Card v%s files installed successfully to www/lovelace-aliexpress-package-card/",
            version,
        )

    except Exception as err:
        _LOGGER.error("Failed to install Aliexpress-package-tracker Card: %s", err)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Aliexpress-package-tracker component."""
    hass.data.setdefault(DOMAIN, {})

    # Install card files automatically
    await _async_install_card(hass)

    # Register static path for the card
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/local/lovelace-aliexpress-package-card/aliexpress_package_card.js",
                hass.config.path(
                    "www/lovelace-aliexpress-package-card/aliexpress_package_card.js"
                ),
                True,
            )
        ]
    )

    # Get version from manifest
    integration_path = Path(__file__).parent
    manifest_path = integration_path / "manifest.json"
    version = "1.0.0"
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
            version = manifest.get("version", "1.0.0")
    except Exception as err:
        _LOGGER.warning("Could not read version from manifest: %s", err)

    # Register lovelace resource
    _LOGGER.info(
        "🔵 Aliexpress-package-tracker: Registering lovelace resource (version %s)",
        version,
    )
    await init_lovelace_resource(
        hass,
        "/local/lovelace-aliexpress-package-card/aliexpress_package_card.js",
        version,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up aliexpress_package_tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    store = get_store(hass)

    async def _async_update_data():
        """Fetch data from API endpoint and process it."""
        _LOGGER.debug("Coordinator refreshing data")
        stored_data = await store.async_load() or {}

        order_numbers = ",".join(stored_data.keys())

        if not order_numbers:
            _LOGGER.debug("No tracking numbers stored, skipping API call")
            return {}  # Return empty dict if no numbers to track

        lang = entry.data.get(CONF_LANG, "en-US")  # Get lang from config entry

        try:
            api_data = await _fetch_cainiao_data(hass, order_numbers, lang)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching data: {err}") from err

        if not api_data or "module" not in api_data:
            _LOGGER.warning(
                "Received no or invalid data from Cainiao API for %s", order_numbers
            )
            # Return last known good data structure if possible, or empty
            # For simplicity, we return empty here, sensors will become unavailable
            # A more robust approach might keep old data but mark it stale.
            return {}

        processed_data = {}
        potentially_merged_track_ids = set()

        for item_data in api_data.get("module", []):
            if item_data.get("mailNoSource") == "EXTERNAL":
                continue  # Skip external entries if any

            original_mail_no = item_data.get("mailNo")
            actual_track_id = extract_actual_tracking_number(item_data)

            if not actual_track_id:
                _LOGGER.warning(
                    "Could not determine tracking ID for data: %s", item_data
                )
                continue

            # --- Merging logic during fetch ---
            if original_mail_no != actual_track_id and original_mail_no in stored_data:
                # This ID might have been merged into actual_track_id
                potentially_merged_track_ids.add(original_mail_no)
                if actual_track_id not in stored_data:
                    # If the new actual_track_id isn't explicitly stored,
                    # migrate data from the original_mail_no
                    _LOGGER.debug(
                        "Migrating stored data from %s to %s",
                        original_mail_no,
                        actual_track_id,
                    )
                    stored_data[actual_track_id] = stored_data[original_mail_no]
                    # Mark original for removal after loop if migration successful
                elif actual_track_id in stored_data:
                    # Combine titles/tracking numbers if both exist
                    _LOGGER.debug(
                        "Combining stored data for %s into %s",
                        original_mail_no,
                        actual_track_id,
                    )
                    orig_entry = stored_data[original_mail_no]
                    actual_entry = stored_data[actual_track_id]

                    # Combine Titles (avoid duplicates, handle default CONF_PACKAGE)
                    orig_title = orig_entry.get(CONF_TITLE, CONF_PACKAGE)
                    actual_title = actual_entry.get(CONF_TITLE, CONF_PACKAGE)
                    combined_titles = set(
                        filter(
                            None,
                            [
                                t
                                for t in f"{orig_title},{actual_title}".split(",")
                                if t.strip() and t != CONF_PACKAGE
                            ],
                        )
                    )
                    actual_entry[CONF_TITLE] = (
                        ", ".join(sorted(list(combined_titles))) or CONF_PACKAGE
                    )

                    # Combine Tracking Numbers (avoid duplicates)
                    orig_num = orig_entry.get(CONF_TRACKING_NUMBER, original_mail_no)
                    actual_num = actual_entry.get(CONF_TRACKING_NUMBER, actual_track_id)
                    combined_nums = set(
                        filter(
                            None,
                            [n.strip() for n in f"{orig_num},{actual_num}".split(",")],
                        )
                    )
                    actual_entry[CONF_TRACKING_NUMBER] = ",".join(
                        sorted(list(combined_nums))
                    )

                    stored_data[actual_track_id] = actual_entry  # Update stored data

            # --- Prepare data for coordinator ---
            title = stored_data.get(actual_track_id, {}).get(CONF_TITLE, CONF_PACKAGE)
            original_numbers = stored_data.get(actual_track_id, {}).get(
                CONF_TRACKING_NUMBER, actual_track_id
            )

            # Clean up original numbers string
            unique_orig_nums = set(
                filter(None, [n.strip() for n in original_numbers.split(",")])
            )
            cleaned_original_numbers = ", ".join(sorted(list(unique_orig_nums)))

            processed_data[actual_track_id] = {
                "api_data": item_data,  # Store the raw API data for this item
                CONF_TITLE: title,
                "original_tracking_numbers": cleaned_original_numbers,  # Store the originally added numbers
            }

        # --- Clean up merged entries from store ---
        if potentially_merged_track_ids:
            made_changes = False
            for merged_id in potentially_merged_track_ids:
                if merged_id in stored_data:
                    # Check if it was successfully migrated/combined before removing
                    target_id_found = any(
                        merged_id in v.get("original_tracking_numbers", "")
                        for v in processed_data.values()
                    )
                    if target_id_found:
                        _LOGGER.debug(
                            "Removing merged tracking ID %s from storage", merged_id
                        )
                        del stored_data[merged_id]
                        made_changes = True
                    else:
                        _LOGGER.warning(
                            "Skipping removal of %s as it wasn't found in processed data's original numbers",
                            merged_id,
                        )

            if made_changes:
                await store.async_save(stored_data)

        _LOGGER.debug(
            "Coordinator update finished, processed data: %s", processed_data.keys()
        )
        return processed_data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    # Fetch initial data so sensors are ready
    await coordinator.async_config_entry_first_refresh()

    # Setup sensors
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload listener
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading Aliexpress package tracker entry")
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    if unload_ok:
        # Clean up hass.data
        hass.data[DOMAIN].pop(entry.entry_id)
        # Note: We don't remove states here anymore, sensor platform handles its own cleanup.
        # Note: We don't clear the store here, it persists across reloads/restarts.

    _LOGGER.debug("Unload status: %s", unload_ok)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Reloading entry due to update listener: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
