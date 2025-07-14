"""Support for asys_BLE binary sensors."""
import asyncio

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BTBmsConfigEntry
from .const import (
    DOMAIN, LOGGER,
)
from .coordinator import BTBmsCoordinator

OPTIONS_FILTRATION_STATE_MODE = ["OFF", "ON", "AUTO"]
OPTIONS_FILTRATION_MODE =["Automatique (Loi d'eau)","Horloge 72h","Horloge Usine 1","Horloge Usine 2","Horloge Usine 3","Horloge Personnalisable Eté","Horloge Personnalisable Hivers"]



class AsysSelectEntityDescription(SelectEntityDescription):
    """Describes BMS sensor entity."""


filtrationStateModeEntityDescription=AsysSelectEntityDescription(
        key="select_filtration_mode_state",
        name="état filtration",
        options=OPTIONS_FILTRATION_STATE_MODE,

    )

filtrationModeEntityDescription=AsysSelectEntityDescription(
        key="select_filtration_mode",
        name="mode filtration",
        options=OPTIONS_FILTRATION_MODE,

    )


async def async_setup_entry(
        _hass: HomeAssistant,
        config_entry: BTBmsConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in Home Assistant."""

    bms: BTBmsCoordinator = config_entry.runtime_data
    async_add_entities(
        [AsysSelectFiltrationModeStateEntity(bms, filtrationStateModeEntityDescription, format_mac(config_entry.unique_id))]
    )
    async_add_entities(
        [AsysSelectFiltrationModeEntity(bms, filtrationModeEntityDescription, format_mac(config_entry.unique_id))]
    )



class AsysSelectFiltrationModeStateEntity(CoordinatorEntity[BTBmsCoordinator],
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
        self._attr_current_option = "nc"
        self._attr_has_entity_name = True
        self.entity_description: AsysSelectEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    @property
    def available(self) -> bool:
        return not self.coordinator.data.get('pairing_state', True)



    async def async_select_option(self, option: str) -> None:
        await self.coordinator._device.set_filtration_mode_state(option)
        if option == 'OFF':
            self.coordinator.data["filtration_mode_state"] = 0
        elif option == 'ON':
            self.coordinator.data["filtration_mode_state"] = 1
        else:
            self.coordinator.data["filtration_mode_state"] = 2
        #update select state sleep 2second and finally update all ohers entities
        self.async_write_ha_state()
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()


    @property
    def options(self) -> list[str]:
        return self.entity_description.options

    @property
    def current_option(self) -> str | None:
        LOGGER.debug(
            f"filtration_mode_state current_option : : {self.coordinator.data.get("filtration_mode_state", 0)}")
        if self.coordinator.data.get("filtration_mode_state", 0) == 0:
            return "OFF"
        elif self.coordinator.data.get("filtration_mode_state", 0) == 1:
            return "ON"
        else:
            return "AUTO"





class AsysSelectFiltrationModeEntity(CoordinatorEntity[BTBmsCoordinator],
                       SelectEntity):  # type: ignore[reportIncompatibleMethodOverride]

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
        self._attr_current_option = "nc"
        self._attr_has_entity_name = True
        self.entity_description: AsysSelectEntityDescription = descr  # type: ignore[reportIncompatibleVariableOverride]
        super().__init__(bms)

    @property
    def available(self) -> bool:
        return not self.coordinator.data.get('pairing_state', True)



    async def async_select_option(self, option: str) -> None:
        try:
            index = OPTIONS_FILTRATION_MODE.index(option)
            await self.coordinator._device.set_filtration_mode(index)
            self.coordinator.data["filtration_mode"] = index
            # update select state sleep 2second and finally update all ohers entities
            self.async_write_ha_state()
            await asyncio.sleep(2)
            await self.coordinator.async_request_refresh()
        except ValueError:
            LOGGER.error(
                f"filtration_mode unable to parse value")



    @property
    def options(self) -> list[str]:
        return self.entity_description.options

    @property
    def current_option(self) -> str | None:
        LOGGER.debug(
            f"filtration_mode current_option : : {self.coordinator.data.get("filtration_mode", 0)}")
        return OPTIONS_FILTRATION_MODE[self.coordinator.data.get("filtration_mode", 0)]
