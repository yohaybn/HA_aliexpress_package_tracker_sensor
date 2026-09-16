"""Regression tests for AliExpress package tracker fixes."""

import asyncio
import importlib.util
import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "custom_components" / "aliexpress_package_tracker"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class ResourceStorageCollection:
    """Storage-mode resource collection marker used by the integration."""


class _ConfigEntry:
    pass


class _HomeAssistant:
    pass


class _Store:
    pass


class _DataUpdateCoordinator:
    pass


class _UpdateFailed(Exception):
    pass


def _load_integration_module():
    package = _module("custom_components.aliexpress_package_tracker")
    package.__path__ = [str(PACKAGE)]

    aiohttp = _module("aiohttp", ClientError=Exception)
    aiohttp.ClientResponseError = Exception

    _module("homeassistant")
    _module("homeassistant.config_entries", ConfigEntry=_ConfigEntry)
    _module("homeassistant.core", HomeAssistant=_HomeAssistant)
    _module("homeassistant.helpers")
    _module(
        "homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda _: None
    )
    _module("homeassistant.helpers.storage", Store=_Store)
    _module("homeassistant.helpers.typing", ConfigType=dict)
    _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=_DataUpdateCoordinator,
        UpdateFailed=_UpdateFailed,
    )
    _module("homeassistant.components")
    _module("homeassistant.components.http", StaticPathConfig=object)
    _module("homeassistant.components.lovelace")
    _module(
        "homeassistant.components.lovelace.resources",
        ResourceStorageCollection=ResourceStorageCollection,
    )

    const = _module("custom_components.aliexpress_package_tracker.const")
    for name, value in {
        "CONF_LANG": "language",
        "CONF_PACKAGE": "Package",
        "CONF_TITLE": "title",
        "CONF_TRACKING_NUMBER": "tracking_number",
        "COORDINATOR": "coordinator",
        "DOMAIN": "aliexpress_package_tracker",
        "STORAGE_KEY": "storage",
        "STORAGE_VERSION": 1,
        "UPDATE_INTERVAL": 30,
    }.items():
        setattr(const, name, value)

    _module(
        "custom_components.aliexpress_package_tracker.helpers",
        _fetch_cainiao_data=AsyncMock(),
        extract_actual_tracking_number=lambda item: item.get("mailNo"),
        get_store=lambda hass: None,
    )

    spec = importlib.util.spec_from_file_location(
        "custom_components.aliexpress_package_tracker", PACKAGE / "__init__.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


INTEGRATION = _load_integration_module()


class MigrationTests(unittest.TestCase):
    def test_migration_keeps_original_and_actual_tracking_numbers(self):
        stored_data = {"OLD123": {"title": "Package", "tracking_number": "NEW456"}}

        INTEGRATION._migrate_stored_tracking_entry(stored_data, "OLD123", "NEW456")

        self.assertEqual(stored_data["NEW456"]["tracking_number"], "NEW456,OLD123")
        self.assertIsNot(stored_data["NEW456"], stored_data["OLD123"])

    def test_migration_deduplicates_existing_original_number(self):
        stored_data = {
            "OLD123": {
                "title": "Package",
                "tracking_number": "OLD123,NEW456",
            }
        }

        INTEGRATION._migrate_stored_tracking_entry(stored_data, "OLD123", "NEW456")

        self.assertEqual(stored_data["NEW456"]["tracking_number"], "NEW456,OLD123")


class LovelaceResourceTests(unittest.TestCase):
    def test_yaml_mode_is_skipped_with_clear_warning(self):
        resources = types.SimpleNamespace(
            async_get_info=AsyncMock(), async_create_item=AsyncMock()
        )
        hass = types.SimpleNamespace(
            data={"lovelace": types.SimpleNamespace(resources=resources)}
        )

        with self.assertLogs(INTEGRATION._LOGGER, logging.WARNING) as logs:
            result = asyncio.run(
                INTEGRATION.init_lovelace_resource(hass, "/local/card.js", "2.9.5")
            )

        self.assertFalse(result)
        resources.async_get_info.assert_not_awaited()
        resources.async_create_item.assert_not_awaited()
        self.assertIn("Lovelace is in YAML mode", " ".join(logs.output))
        self.assertIn("/local/card.js", " ".join(logs.output))

    def test_storage_mode_still_creates_resource(self):
        class StorageResources(ResourceStorageCollection):
            async_get_info = AsyncMock()
            async_create_item = AsyncMock()

            def async_items(self):
                return []

        resources = StorageResources()
        hass = types.SimpleNamespace(
            data={"lovelace": types.SimpleNamespace(resources=resources)}
        )

        result = asyncio.run(
            INTEGRATION.init_lovelace_resource(hass, "/local/card.js", "2.9.5")
        )

        self.assertTrue(result)
        resources.async_create_item.assert_awaited_once_with(
            {"res_type": "module", "url": "/local/card.js?v=2.9.5"}
        )


if __name__ == "__main__":
    unittest.main()


class ItalianCardAssetsTests(unittest.TestCase):
    def test_italian_card_translation_matches_english_schema(self):
        import json

        translations = PACKAGE / "dist" / "translations"
        english = json.loads((translations / "en.json").read_text())
        italian = json.loads((translations / "it.json").read_text())

        def leaf_keys(value, prefix=""):
            if not isinstance(value, dict):
                return {prefix}
            return {
                key
                for name, child in value.items()
                for key in leaf_keys(child, f"{prefix}.{name}" if prefix else name)
            }

        self.assertEqual(leaf_keys(italian), leaf_keys(english))

    def test_italian_language_and_poste_italiane_logo_are_registered(self):
        import json

        dist = PACKAGE / "dist"
        languages = json.loads((dist / "translations" / "index.json").read_text())
        carrier_logos = json.loads((dist / "carrier_logos.json").read_text())

        self.assertIn({"code": "it", "name": "Italiano"}, languages)
        self.assertEqual(
            carrier_logos["Poste Italiane"],
            "https://upload.wikimedia.org/wikipedia/commons/2/2c/Logo_Poste_Italiane.svg",
        )
