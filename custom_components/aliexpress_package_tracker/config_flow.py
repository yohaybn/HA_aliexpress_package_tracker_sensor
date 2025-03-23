import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.const import CONF_LANGUAGE
import logging
import voluptuous as vol
from homeassistant.core import callback
from .const import DOMAIN, INTEGRATION_NAME,CONF_AUTO_DELETE,CONF_AUTO_DELETE_DAYS
# Logger
_LOGGER = logging.getLogger(__name__)

# Link the options flow to the config entry
class AliexpressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the AliExpress package tracking integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where users enter configuration."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors = {}

        # Get default system language
        system_language = self.hass.config.language

        # Handle form submission
        if user_input is not None:
            auto_delete = user_input[CONF_AUTO_DELETE]
            auto_delete_days = user_input[CONF_AUTO_DELETE_DAYS]
            user_data={
                    CONF_LANGUAGE: user_input[CONF_LANGUAGE],
                    CONF_AUTO_DELETE: user_input[CONF_AUTO_DELETE],
                    CONF_AUTO_DELETE_DAYS: user_input[CONF_AUTO_DELETE_DAYS],
                }
            return self.async_create_entry(
                title=INTEGRATION_NAME,
                data=user_data,
                options=user_data,
            )

        # Show the form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_LANGUAGE, default=system_language): cv.string,
                    vol.Optional(CONF_AUTO_DELETE, default=False): cv.boolean,
                    vol.Optional(CONF_AUTO_DELETE_DAYS, default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
                }
            ),
            errors=errors,
        )
    @staticmethod
    @callback
    def async_get_options_flow( config_entry):
        """Return the options flow handler."""
        return AliexpressOptionsFlowHandler(config_entry)




class AliexpressOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to modify integration settings."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for the integration."""
        errors = {}

        # Get existing values
        current_language = self.config_entry.data.get(CONF_LANGUAGE, self.hass.config.language)
        current_auto_delete = self.config_entry.data.get(CONF_AUTO_DELETE, False)
        current_auto_delete_days = self.config_entry.data.get(CONF_AUTO_DELETE_DAYS, 7)

        if user_input is not None:
            #auto_delete = user_input[CONF_AUTO_DELETE]
            #auto_delete_days = user_input[CONF_AUTO_DELETE_DAYS]
            user_data={
                    CONF_LANGUAGE: user_input[CONF_LANGUAGE],
                    CONF_AUTO_DELETE: user_input[CONF_AUTO_DELETE],
                    CONF_AUTO_DELETE_DAYS: user_input[CONF_AUTO_DELETE_DAYS],
                }
            entry = self.hass.config_entries.async_get_entry(self.config_entry.entry_id)
            if entry:
                self.hass.config_entries.async_update_entry(entry, data=user_data, options=user_data)
                await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_create_entry(title="", data=user_data)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_LANGUAGE, default=current_language): cv.string,
                    vol.Optional(CONF_AUTO_DELETE, default=current_auto_delete): cv.boolean,
                    vol.Optional(CONF_AUTO_DELETE_DAYS, default=current_auto_delete_days): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
                }
            ),
            errors=errors,
        )
