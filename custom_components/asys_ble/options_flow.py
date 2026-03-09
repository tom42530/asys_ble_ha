from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL_S, DEFAULT_UNDERLOAD_INTENSITY_THRESHOLD, DEFAULT_UNDERLOAD_PERIOD


class AsysBleOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self._config_entry = config_entry  # attribut privé pour éviter le conflit

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            result = self.async_create_entry(title="", data=user_input)
            return result

        cur_scan_interval = self._config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL_S)
        cur_pump_underload_protection = self._config_entry.options.get("pump_underload_protection", False)
        cur_underload_intensity_threshold = self._config_entry.options.get("underload_intensity_threshold", DEFAULT_UNDERLOAD_INTENSITY_THRESHOLD)
        cur_underload_period_s = self._config_entry.options.get("underload_period_s", DEFAULT_UNDERLOAD_PERIOD)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("scan_interval", default=cur_scan_interval): int,
                vol.Optional("pump_underload_protection", default=cur_pump_underload_protection): bool,
                vol.Optional("underload_intensity_threshold", default=cur_underload_intensity_threshold): int,
                vol.Optional("underload_period_s", default=cur_underload_period_s): int,
            }),
        )