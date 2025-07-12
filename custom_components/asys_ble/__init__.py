"""The BLE Battery Management System integration."""

from types import ModuleType
from typing import Final

from bleak.backends.device import BLEDevice

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.importlib import async_import_module
from homeassistant.helpers.storage import Store

from .const import DOMAIN, LOGGER
from .coordinator import BTBmsCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.BUTTON, Platform.LIGHT,Platform.SELECT]

type BTBmsConfigEntry = ConfigEntry[BTBmsCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BTBmsConfigEntry) -> bool:
    """Set up BT Battery Management System from a config entry."""
    LOGGER.debug("Setup of %s", repr(entry))

    if entry.unique_id is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="missing_unique_id",
        )

    # migrate old entries
    migrate_sensor_entities(hass, entry)

    ble_device: Final[BLEDevice | None] = async_ble_device_from_address(
        hass, entry.unique_id, True
    )

    if ble_device is None:
        LOGGER.debug("Failed to discover device %s via Bluetooth", entry.unique_id)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "MAC": entry.unique_id,
            },
        )

    plugin: ModuleType = await async_import_module(hass, entry.data["type"])

    store = Store(hass, 1, f"bms_{entry.entry_id}")
    bms_instance = plugin.BMS(ble_device, store)
    coordinator = BTBmsCoordinator(hass, ble_device, bms_instance, entry)


    # Query the device the first time, initialise coordinator.data
    await coordinator.async_config_entry_first_refresh()

    # Insert the coordinator in the global registry
    hass.data.setdefault(DOMAIN, {})
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BTBmsConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: Final[bool] = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    LOGGER.debug("Unloaded config entry: %s, ok? %s!", entry.unique_id, str(unload_ok))

    return unload_ok





def migrate_sensor_entities(
    hass: HomeAssistant,
    config_entry: BTBmsConfigEntry,
) -> None:
    """Migrate old unique_ids with wrong format (name) to new format (MAC address) if needed."""
    ent_reg: Final[er.EntityRegistry] = er.async_get(hass)
    entities: Final[er.EntityRegistryItems] = ent_reg.entities

    for entry in entities.get_entries_for_config_entry_id(config_entry.entry_id):
        if entry.unique_id.startswith(f"{DOMAIN}-"):
            continue
        new_unique_id: str = (
            f"{DOMAIN}-{format_mac(config_entry.unique_id)}-{entry.unique_id.split('-')[-1]}"
        )
        LOGGER.debug(
            "migrating %s with old unique_id '%s' to new '%s'",
            entry.entity_id,
            entry.unique_id,
            new_unique_id,
        )
        ent_reg.async_update_entity(entry.entity_id, new_unique_id=new_unique_id)
