"""Support for asys_BLE binary sensors."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription, ButtonDeviceClass,
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


class AsicButtonEntityDescription(ButtonEntityDescription):
    pass


BUTTON_TYPES: list[AsicButtonEntityDescription] = [
    AsicButtonEntityDescription(
        key="bt_light_color",
        name="Change light color",
        icon="mdi:lightbulb",
        device_class=ButtonDeviceClass.UPDATE,

    ),
]


async def async_setup_entry(
        _hass: HomeAssistant,
        config_entry: BTBmsConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in Home Assistant."""

    bms: BTBmsCoordinator = config_entry.runtime_data
    for descr in BUTTON_TYPES:
        async_add_entities(
            [BMSButtonEntity(bms, descr, format_mac(config_entry.unique_id))]
        )


class BMSButtonEntity(CoordinatorEntity[BTBmsCoordinator],
                      ButtonEntity):  # type: ignore[reportIncompatibleMethodOverride]

    entity_description: AsicButtonEntityDescription

    def __init__(
            self,
            bms: BTBmsCoordinator,
            descr: AsicButtonEntityDescription,
            unique_id: str,
    ) -> None:
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self._attr_has_entity_name = True
        self.entity_description: AsicButtonEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    async def async_press(self) -> None:
        LOGGER.debug("button press")
        return await self.coordinator._device.change_light_color()

    @property
    def available(self) -> bool:
        return (not self.coordinator.data.get('pairing_state', True)) and self.coordinator.data["light_state"]

    # @property
    # def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
    #     """Handle updated data from the coordinator."""
    #     return bool(self.coordinator.data.get(self.entity_description.key))
