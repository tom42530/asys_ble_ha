"""Module to support Daly Smart BMS."""
import time
from collections.abc import Callable
from typing import Any, Final

from Crypto.Cipher import AES
from bleak import BleakError
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.uuids import normalize_uuid_str
import asyncio

from homeassistant.helpers.storage import Store

from .basebms import AdvertisementPattern, BaseBMS, BMSsample, BMSvalue, crc_modbus


class BMS(BaseBMS):
    """Daly Smart BMS class implementation."""

    CHARACTERISTIC_PRECISEO_STATUS_UUID = "3BEF010D-F30A-DF90-4A4C-74B6EB69184F"
    CHARACTERISTIC_PRECISEO_CONTROL_UUID = "3BEF010C-F30A-DF90-4A4C-74B6EB69184F"

    HEAD_READ: Final[bytes] = b"\xd2\x03"
    CMD_INFO: Final[bytes] = b"\x00\x00\x00\x3e\xd7\xb9"
    MOS_INFO: Final[bytes] = b"\x00\x3e\x00\x09\xf7\xa3"
    HEAD_LEN: Final[int] = 3
    CRC_LEN: Final[int] = 2
    MAX_CELLS: Final[int] = 32
    MAX_TEMP: Final[int] = 8
    INFO_LEN: Final[int] = 84 + HEAD_LEN + CRC_LEN + MAX_CELLS + MAX_TEMP
    MOS_TEMP_POS: Final[int] = HEAD_LEN + 8
    MOS_NOT_AVAILABLE: Final[tuple[str]] = ("DL-FB4C2E0",)
    _FIELDS: Final[list[tuple[BMSvalue, int, int, Callable[[int], Any]]]] = [
        ("voltage", 80 + HEAD_LEN, 2, lambda x: float(x / 10)),
        ("current", 82 + HEAD_LEN, 2, lambda x: float((x - 30000) / 10)),
        ("battery_level", 84 + HEAD_LEN, 2, lambda x: float(x / 10)),
        ("cycle_charge", 96 + HEAD_LEN, 2, lambda x: float(x / 10)),
        ("cell_count", 98 + HEAD_LEN, 2, lambda x: min(x, BMS.MAX_CELLS)),
        ("temp_sensors", 100 + HEAD_LEN, 2, lambda x: min(x, BMS.MAX_TEMP)),
        ("cycles", 102 + HEAD_LEN, 2, lambda x: x),
        ("delta_voltage", 112 + HEAD_LEN, 2, lambda x: float(x / 1000)),
        ("problem_code", 116 + HEAD_LEN, 8, lambda x: x % 2 ** 64),
    ]

    def __init__(self, ble_device: BLEDevice, store: Store, reconnect: bool = False) -> None:
        """Intialize private BMS members."""
        super().__init__(__name__, ble_device, store, reconnect)

    @staticmethod
    def matcher_dict_list() -> list[AdvertisementPattern]:
        """Provide BluetoothMatcher definition."""
        # LOGGER.debug("tomtom device detected:")

        return [
            {
                "service_uuid": "3bef0800-f30a-df90-4a4c-74b6eb69184f",
                "connectable": True,

            }
        ]

    @staticmethod
    def device_info() -> dict[str, str]:
        """Return device information for the Asys system."""
        return {}

    @staticmethod
    def uuid_services() -> list[str]:
        """Return list of 128-bit UUIDs of services required by BMS."""
        return [normalize_uuid_str("fff0")]

    @staticmethod
    def uuid_rx() -> str:
        """Return 16-bit UUID of characteristic that provides notification/read property."""
        return BMS.CHARACTERISTIC_PRECISEO_STATUS_UUID

    @staticmethod
    def uuid_tx() -> str:
        """Return 16-bit UUID of characteristic that provides write property."""
        return "fff2"








    async def _async_update(self) -> BMSsample:
        """Update battery status information."""
        data: BMSsample = {}

        try:
            await self._associate_asic()
            control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID)
            self._log.debug(f"read control {control_value.hex()}")
            data["light_state"] = control_value[2] != 0
            data["filtration_mode_state"] = control_value[1]

            status_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEO_STATUS_UUID)
            data["water_temperature"] = status_value[14]
            data["air_temperature"] = status_value[16]
            data["current"] = status_value[12] / 10
            data["cycles"] = int.from_bytes(status_value[8:12], byteorder='little',
                                            signed=False)  # (self._data[11] << 24) +(self._data[10] << 16)+(self._data[9] << 8) +self._data[8] #(x[11] << 24) + (x[10] << 16) +(x[9] << 8) + x[8];
            data["runtime"] = int.from_bytes(status_value[4:8], byteorder='little', signed=False)  # runtime
            data["filtration_hors_gel_state"] = bool(status_value[0])
            data["filtration_24_24_state"] = bool(status_value[1])
            data["filtration_state"] = bool(status_value[2])
            data["surcharge_protection_state"] = bool(status_value[3])
            data["pairing_state"] = False

            model_name = await self._client.read_gatt_char("00002a24-0000-1000-8000-00805f9b34fb")
            self._log.info(f"model name: {model_name.decode('utf-8')}")
            data["model"]=model_name.decode('utf-8')

            serial_number = await self._client.read_gatt_char("00002a25-0000-1000-8000-00805f9b34fb")
            self._log.info(f"serial_number: {serial_number.decode('utf-8')}")
            data["serial_number"]=serial_number.decode('utf-8')
            firmware_version = await self._client.read_gatt_char("00002a26-0000-1000-8000-00805f9b34fb")
            self._log.info(f"firmware_version: {firmware_version.decode('utf-8')}")
            data["sw_version"]=firmware_version.decode('utf-8')
            hardware_version = await self._client.read_gatt_char("00002a27-0000-1000-8000-00805f9b34fb")
            self._log.info(f"hardware_version: {hardware_version.decode('utf-8')}")
            data["hw_version"]=model_name.decode('utf-8')


            manufacturer = await self._client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
            self._log.info(f"manufacturer: {manufacturer.decode('utf-8')}")
            data["manufacturer"] = manufacturer.decode('utf-8')

            inconnu1 = await self._client.read_gatt_char("00002a01-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu1: {inconnu1}")
            inconnu2 = await self._client.read_gatt_char("00002a04-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu2: {inconnu2}")
        except BleakError as e:
            data["pairing_state"] = True
            self._log.error(f"read control error trying associate{e}")

        return data

    async def turn_on_off_light(self, light_state: bool = False) -> None:
        self._log.debug("Changing light state")
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        control_value[2] = 1 if light_state else 0
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID, control_value)
        return

    async def change_light_color(self) -> None:
        self._log.debug("Changing light color")
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        control_value[3] = 1
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID, control_value)
        return

    async def set_filtration_mode(self,option: str) -> None:
        self._log.debug(f"Set filtration mode to {option}")
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        if option == 'OFF':
            control_value[1] = 0
        elif option == 'ON':
            control_value[1] = 1
        else :
            control_value[1] = 2
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEO_CONTROL_UUID, control_value)
        return