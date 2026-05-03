"""Support for asys_BLE binary sensors."""

from typing import Any

from homeassistant.components.light import (
    LightEntityDescription,
    LightEntity, ColorMode

)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BTBmsConfigEntry
from .const import (
    DOMAIN,
    LOGGER,
)
from .coordinator import BTBmsCoordinator

PARALLEL_UPDATES = 0


class AsicLightEntityDescription(LightEntityDescription):
    pass


LIGHT_TYPES: list[AsicLightEntityDescription] = [
    AsicLightEntityDescription(
        key="light_state",
        name="lumière",
    ),
]


async def async_setup_entry(
        _hass: HomeAssistant,
        config_entry: BTBmsConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in Home Assistant."""

    bms: BTBmsCoordinator = config_entry.runtime_data
    async_add_entities([
        AsicLightEntity(bms, descr, format_mac(config_entry.unique_id))
        for descr in LIGHT_TYPES
    ])



class AsicLightEntity(CoordinatorEntity[BTBmsCoordinator],
                      LightEntity):  # type: ignore[reportIncompatibleMethodOverride]
    """The generic BMS binary sensor implementation."""

    entity_description: AsicLightEntityDescription

    def __init__(
            self,
            bms: BTBmsCoordinator,
            descr: AsicLightEntityDescription,
            unique_id: str,
    ) -> None:
        """Intialize BMS binary sensor."""
        super().__init__(bms)

        self.entity_description = descr
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self._attr_has_entity_name = True
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_icon = "mdi:lightbulb"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return not self.coordinator.data.get("pairing_state", True)

    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on."""
        light_state = self.coordinator.data.get(self.entity_description.key, False)
        LOGGER.debug("light is on: %s", light_state)
        return bool(light_state)

    @property
    def color_mode(self) -> ColorMode | None:
        """Return the current color mode."""
        if self.is_on:
            return ColorMode.ONOFF
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        LOGGER.debug("light turn on")
        await self.coordinator._device.turn_on_off_light(True)
        self.coordinator.data["light_state"] = True
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        LOGGER.debug("light turn off")
        await self.coordinator._device.turn_on_off_light(False)
        self.coordinator.data["light_state"] = False
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()