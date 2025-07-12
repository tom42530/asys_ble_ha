from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN




class AsysBleOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Enregistre les nouvelles options
            result = self.async_create_entry(title="", data=user_input)

            # Rechargement du config_entry avec les nouvelles options
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return result

        current = self.config_entry.options.get("scan_interval", 30)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("scan_interval", default=current): int,
            }),
        )