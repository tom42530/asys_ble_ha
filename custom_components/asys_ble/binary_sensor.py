"""Support for BMS_BLE binary sensors."""

from collections.abc import Callable

from custom_components.bms_ble.plugins.basebms import BMSmode, BMSsample
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import ATTR_BATTERY_CHARGING, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BTBmsConfigEntry
from .const import ATTR_PROBLEM, DOMAIN
from .coordinator import BTBmsCoordinator

PARALLEL_UPDATES = 0


class BmsBinaryEntityDescription(BinarySensorEntityDescription, frozen_or_thawed=True):
    """Describes BMS sensor entity."""

    attr_fn: Callable[[BMSsample], dict[str, int | str]] | None = None


BINARY_SENSOR_TYPES: list[BmsBinaryEntityDescription] = [
    BmsBinaryEntityDescription(
        key="filtration_hors_gel_state",
        name="filtration hors gel",
        icon = "mdi:snowflake-alert",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BmsBinaryEntityDescription(
        key="filtration_24_24_state",
        name="filtration 24/24",
        icon="mdi:air-filter",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BmsBinaryEntityDescription(
        key="filtration_state",
        name="filtration",
        icon="mdi:air-filter",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BmsBinaryEntityDescription(
        key="surcharge_protection_state",
        name="protection surcharge",
        icon="mdi:flash-alert",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BmsBinaryEntityDescription(
        key="pairing_state",
        translation_key="pairing status",
        icon="mdi:bluetooth-connect",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: BTBmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in Home Assistant."""

    bms: BTBmsCoordinator = config_entry.runtime_data
    for descr in BINARY_SENSOR_TYPES:
        async_add_entities(
            [BMSBinarySensor(bms, descr, format_mac(config_entry.unique_id))]
        )


class BMSBinarySensor(CoordinatorEntity[BTBmsCoordinator], BinarySensorEntity):  # type: ignore[reportIncompatibleMethodOverride]
    """The generic BMS binary sensor implementation."""

    entity_description: BmsBinaryEntityDescription

    def __init__(
        self,
        bms: BTBmsCoordinator,
        descr: BmsBinaryEntityDescription,
        unique_id: str,
    ) -> None:
        """Intialize BMS binary sensor."""
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self._attr_has_entity_name = True
        self.entity_description: BmsBinaryEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Handle updated data from the coordinator."""
        return bool(self.coordinator.data.get(self.entity_description.key))


