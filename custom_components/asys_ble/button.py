"""Support for BMS_BLE binary sensors."""

from collections.abc import Callable

from custom_components.bms_ble.plugins.basebms import BMSmode, BMSsample
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
    ButtonDeviceClass,
)


from homeassistant.const import ATTR_BATTERY_CHARGING, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BTBmsConfigEntry
from .const import ATTR_PROBLEM, DOMAIN
from .coordinator import BTBmsCoordinator
from .const import (
    DOMAIN,
    LOGGER,
)


PARALLEL_UPDATES = 0


class BmsButtonEntityDescription(ButtonEntityDescription, frozen_or_thawed=True):
    """Describes BMS sensor entity."""

    attr_fn: Callable[[BMSsample], dict[str, int | str]] | None = None


BUTTON_TYPES: list[BmsButtonEntityDescription] = [
    BmsButtonEntityDescription(
        key="filtration_hors_gel_state",
        name="paring useless",
        icon = "mdi:snowflake-alert",
        device_class=BinarySensorDeviceClass.RUNNING,
        attr_fn=lambda data: (
            {"filtration_hors_gel_state": data.get("filtration_hors_gel_state", False)}
            if "filtration_hors_gel_state" in data
            else {}
        ),
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


class BMSButtonEntity(CoordinatorEntity[BTBmsCoordinator], ButtonEntity):  # type: ignore[reportIncompatibleMethodOverride]
    """The generic BMS binary sensor implementation."""

    entity_description: BmsButtonEntityDescription

    def __init__(
        self,
        bms: BTBmsCoordinator,
        descr: BmsButtonEntityDescription,
        unique_id: str,
    ) -> None:
        """Intialize BMS binary sensor."""
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self._attr_has_entity_name = True
        self.entity_description: BmsBinaryEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    # def press(self) -> None:
    #     LOGGER.debug("button press")
    #     self.coordinator.associate()
    #     pass

    async def async_press(self) -> None:
        LOGGER.debug("button press")
        return await self.coordinator.associate()

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Handle updated data from the coordinator."""
        return bool(self.coordinator.data.get(self.entity_description.key))

    @property
    def extra_state_attributes(self) -> dict[str, int | str] | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Return entity specific state attributes, e.g. cell voltages."""
        return (
            fn(self.coordinator.data)
            if (fn := self.entity_description.attr_fn)
            else None
        )
