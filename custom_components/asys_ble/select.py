"""Support for asys_BLE binary sensors."""

from collections.abc import Callable

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.asys_ble.plugins.basebms import BMSsample
from . import BTBmsConfigEntry
from .const import (
    DOMAIN,
)
from .coordinator import BTBmsCoordinator

PARALLEL_UPDATES = 0

OPTIONS = ["mode_eco", "mode_normal", "mode_performance"]

class AsysSelectEntityDescription(SelectEntityDescription):
    """Describes BMS sensor entity."""

    attr_fn: Callable[[BMSsample], dict[str, int | str]] | None = None


SELECT_TYPES: list[AsysSelectEntityDescription] = [
    AsysSelectEntityDescription(
        key="select_tom",
        name="lumière",
        options=OPTIONS,

    ),
]


async def async_setup_entry(
        _hass: HomeAssistant,
        config_entry: BTBmsConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in Home Assistant."""

    bms: BTBmsCoordinator = config_entry.runtime_data
    for descr in SELECT_TYPES:
        async_add_entities(
            [AsysSelectEntity(bms, descr, format_mac(config_entry.unique_id))]
        )


class AsysSelectEntity(CoordinatorEntity[BTBmsCoordinator],
                       SelectEntity):  # type: ignore[reportIncompatibleMethodOverride]
    """The generic BMS binary sensor implementation."""

    entity_description: AsysSelectEntityDescription

    def __init__(
            self,
            bms: BTBmsCoordinator,
            descr: AsysSelectEntityDescription,
            unique_id: str,
    ) -> None:
        """Intialize BMS binary sensor."""
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self._attr_current_option = "mode_eco"
        self._attr_has_entity_name = True
        self.entity_description: AsysSelectEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    @property
    def available(self) -> bool:
        return super().available

    async def async_update(self) -> None:
        self._attr_current_option = "mode_eco"
        #return await super().async_update()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option


    @property
    def options(self) -> list[str]:
        return self.entity_description.options

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option