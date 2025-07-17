"""Platform for sensor integration."""

from collections.abc import Callable
from datetime import datetime
from typing import Final, cast

from custom_components.asys_ble.plugins.basebms import  BMSsample
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription,RestoreEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TEMPERATURE,
    ATTR_VOLTAGE,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BTBmsConfigEntry
from .const import (
    ATTR_CURRENT,
    ATTR_CYCLE_CAP,
    ATTR_CYCLES,
    ATTR_DELTA_VOLTAGE,
    ATTR_LQ,
    ATTR_POWER,
    ATTR_RSSI,
    ATTR_RUNTIME,
    DOMAIN,
    LOGGER,
)
from .coordinator import BTBmsCoordinator

PARALLEL_UPDATES = 0


class BmsEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """Describes BMS sensor entity."""

    value_fn: Callable[[BMSsample], float | int | None]
    attr_fn: Callable[[BMSsample], dict[str, list[int | float]]] | None = None





SENSOR_TYPES: Final[list[BmsEntityDescription]] = [
    BmsEntityDescription(
        key=ATTR_TEMPERATURE,
        translation_key=ATTR_TEMPERATURE,
        name="température eau",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("water_temperature"),
        attr_fn=lambda data: (
            {"temperature_sensors": data.get("temp_values", [])}
            if "temp_values" in data
            else (
                {"temperature_sensors": [data.get("water_temperature", 0.0)]}
                if "water_temperature" in data
                else {}
            )
        ),
    ),
    BmsEntityDescription(
        key=ATTR_TEMPERATURE,
        name = "température air",
        translation_key=ATTR_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("air_temperature"),
        attr_fn=lambda data: (
            {"temperature_sensors": data.get("temp_values", [])}
            if "temp_values" in data
            else (
                {"temperature_sensors": [data.get("air_temperature", 0.0)]}
                if "air_temperature" in data
                else {}
            )
        ),
    ),
    BmsEntityDescription(
        key=ATTR_CURRENT,
        translation_key=ATTR_CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.get("current"),
        attr_fn=lambda data: (
            {"current": [data.get("current", 0.0)]}
            if "current" in data
            else {}
        ),
    ),
    BmsEntityDescription(
        key="pump_power",
        name="consommation pompe",
        translation_key="pump_power",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: None,
    ),
    BmsEntityDescription(
        key=ATTR_CYCLES,
        translation_key=ATTR_CYCLES,
        name="Cycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("cycles"),
    ),
    BmsEntityDescription(
        key=ATTR_RUNTIME,
        translation_key=ATTR_RUNTIME,
        name="Runtime",
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: data.get("runtime"),
    ),
    BmsEntityDescription(
        key=ATTR_RSSI,
        translation_key=ATTR_RSSI,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: None,  # RSSI is handled in a separate class
    ),
    BmsEntityDescription(
        key=ATTR_LQ,
        translation_key=ATTR_LQ,
        name="Link quality",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: None,  # LQ is handled in a separate class
    ),
]


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: BTBmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in Home Assistant."""

    bms: Final[BTBmsCoordinator] = config_entry.runtime_data
    mac: Final[str] = format_mac(config_entry.unique_id)
    for descr in SENSOR_TYPES:
        if descr.key == ATTR_RSSI:
            async_add_entities([RSSISensor(bms, descr, mac)])
            continue
        if descr.key == ATTR_LQ:
            async_add_entities([LQSensor(bms, descr, mac)])
            continue
        if descr.key == "pump_power":
            async_add_entities([AsysEnergySensor(bms, descr, mac)])
            continue
        async_add_entities([BMSSensor(bms, descr, mac)])



class AsysEnergySensor(RestoreEntity,SensorEntity):  # type: ignore[reportIncompatibleMethodOverride]

    _attr_has_entity_name = True
    entity_description: BmsEntityDescription

    def __init__(
        self, bms: BTBmsCoordinator, descr: BmsEntityDescription, unique_id: str
    ) -> None:
        """Intitialize the BMS sensor."""
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}-{descr.name}"
        self._attr_device_info = bms.device_info
        self.entity_description = descr  # type: ignore[reportIncompatibleVariableOverride]
        self._last_update = None
        self._bms: Final[BTBmsCoordinator] = bms
        self._last_state = None
        self._energy_wh = 0.0

    async def async_added_to_hass(self):
        self._last_state= await self.async_get_last_state()
        try:
            self._energy_wh = float(self._last_state.state)
        except ValueError:
            self._energy_wh = 0.0



    async def async_update(self) -> None:

        intensity = self._bms.data.get("current")
        power_w = intensity * 230
        now_time = datetime.now()
        if self._last_update is not None:
            delta = (now_time - self._last_update).total_seconds() / 3600  # en heures
            energy_added = power_w * delta  # P * t = Wh
            self._energy_wh += energy_added
        self._last_update = now_time
        self._attr_native_value = round(self._energy_wh, 2)
        self._attr_available = True
        self.async_write_ha_state()




class BMSSensor(CoordinatorEntity[BTBmsCoordinator], SensorEntity):  # type: ignore[reportIncompatibleMethodOverride]
    """The generic BMS sensor implementation."""

    _attr_has_entity_name = True
    entity_description: BmsEntityDescription

    def __init__(
        self, bms: BTBmsCoordinator, descr: BmsEntityDescription, unique_id: str
    ) -> None:
        """Intitialize the BMS sensor."""
        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}-{descr.name}"
        self._attr_device_info = bms.device_info
        self.entity_description = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    @property
    def extra_state_attributes(self) -> dict[str, list[int | float]] | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Return entity specific state attributes, e.g. cell voltages."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator.data)

        return None

    @property
    def native_value(self) -> int | float | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)


class RSSISensor(SensorEntity):
    """The Bluetooth RSSI sensor."""

    LIMIT: Final[int] = 127  # limit to +/- this range
    _attr_has_entity_name = True
    _attr_native_value = -LIMIT

    def __init__(
        self, bms: BTBmsCoordinator, descr: SensorEntityDescription, unique_id: str
    ) -> None:
        """Intitialize the BMS sensor."""

        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self.entity_description = descr
        self._bms: Final[BTBmsCoordinator] = bms

    async def async_update(self) -> None:
        """Update RSSI sensor value."""

        self._attr_native_value = max(
            min(self._bms.rssi or -self.LIMIT, self.LIMIT), -self.LIMIT
        )
        self._attr_available = self._bms.rssi is not None

        LOGGER.debug("%s: RSSI value: %i dBm", self._bms.name, self._attr_native_value)
        self.async_write_ha_state()


class LQSensor(SensorEntity):
    """The BMS link quality sensor."""

    _attr_has_entity_name = True
    _attr_available = True  # always available
    _attr_native_value = 0

    def __init__(
        self, bms: BTBmsCoordinator, descr: SensorEntityDescription, unique_id: str
    ) -> None:
        """Intitialize the BMS link quality sensor."""

        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{descr.key}"
        self._attr_device_info = bms.device_info
        self.entity_description = descr
        self._bms: Final[BTBmsCoordinator] = bms

    async def async_update(self) -> None:
        """Update BMS link quality sensor value."""

        self._attr_native_value = self._bms.link_quality

        LOGGER.debug("%s: Link quality: %i %%", self._bms.name, self._attr_native_value)
        self.async_write_ha_state()
