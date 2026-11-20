import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_BRIDGE_URL, CONF_ELECTROMETER_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

class CezPndConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            url = user_input[CONF_BRIDGE_URL].strip().rstrip("/")
            meter = user_input[CONF_ELECTROMETER_ID].strip()
            if not url.startswith(("http://", "https://")):
                errors["base"] = "invalid_url"
            elif not meter.isdigit():
                errors["base"] = "invalid_meter_id"
            else:
                await self.async_set_unique_id(meter)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"ČEZ PND ({meter})",
                    data={CONF_BRIDGE_URL:url, CONF_ELECTROMETER_ID:meter}
                )
        schema = vol.Schema({
            vol.Required(CONF_BRIDGE_URL, default="http://cez-pnd-bridge:8099"): str,
            vol.Required(CONF_ELECTROMETER_ID, default="3000017121"): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CezPndOptionsFlow(config_entry)

class CezPndOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)):
                vol.All(int, vol.Range(min=15, max=180))
        }))
