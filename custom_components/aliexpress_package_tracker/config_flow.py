import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.const import CONF_LANGUAGE
import logging
import voluptuous as vol
from .const import DOMAIN, INTEGRATION_NAME
# Logger
_LOGGER = logging.getLogger(__name__)

class AliexpressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for your integration."""

    VERSION = 1

    def __init__(self):
        """Initialize the flow."""
        self.language = None

    async def async_step_user(self, user_input=None):
        """Handle user input to choose the language."""
        existing_entry = self._async_current_entries()
        if existing_entry:
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            self.language = user_input[CONF_LANGUAGE]
            return self.async_create_entry(
                title=INTEGRATION_NAME, data={CONF_LANGUAGE: self.language}
            )

        # Set default language to the system language
        system_language = self.hass.config.language
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_LANGUAGE, default=system_language): cv.string,
                }
            ),
        )
