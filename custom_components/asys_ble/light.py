"""Support for asys_BLE binary sensors."""

from typing import Any

from homeassistant.components.light import (
    LightEntityDescription,
    LightEntity

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
    for descr in LIGHT_TYPES:
        async_add_entities(
            [AsicLightEntity(bms, descr, format_mac(config_entry.unique_id))]
        )


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
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self._attr_has_entity_name = True
        self.entity_description: AsicLightEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    @property
    def available(self) -> bool:
        return not self.coordinator.data.get('pairing_state', True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        LOGGER.debug("light turn on")
        await self.coordinator._device.turn_on_off_light(True)
        self.coordinator.data["light_state"] = True
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()
        return

    async def async_turn_off(self, **kwargs: Any) -> None:
        LOGGER.debug("light turn off")
        await self.coordinator._device.turn_on_off_light(False)
        self.coordinator.data["light_state"] = False
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()
        return

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Handle updated data from the coordinator."""
        LOGGER.debug(
            f"light is on : {bool(self.coordinator.data.get('light_state'))}   {self.coordinator.data.get('light_state', False)}")
        return bool(self.coordinator.data.get(self.entity_description.key, False))
