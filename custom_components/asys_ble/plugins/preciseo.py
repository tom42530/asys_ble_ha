"""Module to support Daly Smart BMS."""

from collections.abc import Callable
from typing import Any, Final

from Crypto.Cipher import AES
from bleak import BleakError
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.uuids import normalize_uuid_str
import asyncio

from .basebms import AdvertisementPattern, BaseBMS, BMSsample, BMSvalue, crc_modbus


class BMS(BaseBMS):
    """Daly Smart BMS class implementation."""

    encrypt_key_barray = bytearray([
        0x00, 0x00, 0x00, 0x00

    ])


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
        ("problem_code", 116 + HEAD_LEN, 8, lambda x: x % 2**64),
    ]

    def __init__(self, ble_device: BLEDevice, reconnect: bool = False) -> None:
        """Intialize private BMS members."""
        super().__init__(__name__, ble_device, reconnect)

    @staticmethod
    def matcher_dict_list() -> list[AdvertisementPattern]:
        """Provide BluetoothMatcher definition."""
        #LOGGER.debug("tomtom device detected:")
   
        return [
            {
                "service_uuid": "3bef0800-f30a-df90-4a4c-74b6eb69184f",
                "connectable": True,

            }
        ]

    @staticmethod
    def device_info() -> dict[str, str]:
        """Return device information for the Asys system."""
        return {"manufacturer": "ASYS", "model": "ASYSPRECISEO","hw_version":"P00021C-I","sw_version":"I1.05 M0.19","serial_number":"19320001"}

    @staticmethod
    def uuid_services() -> list[str]:
        """Return list of 128-bit UUIDs of services required by BMS."""
        return [normalize_uuid_str("fff0")]

    @staticmethod
    def uuid_rx() -> str:
        """Return 16-bit UUID of characteristic that provides notification/read property."""
        return "3BEF010D-F30A-DF90-4A4C-74B6EB69184F"

    @staticmethod
    def uuid_tx() -> str:
        """Return 16-bit UUID of characteristic that provides write property."""
        return "fff2"

    @staticmethod
    def _calc_values() -> frozenset[BMSvalue]:
        return frozenset(
            {
                "cycle_capacity",
                "power",
                "battery_charging",
                "runtime",
                "temperature",
            }
        )


    #def _notification_handler_control(
    #    self, _sender: BleakGATTCharacteristic, data: bytearray
    #) -> None:
    #    self._log.debug("RX BLE data_control: %s", data)
    #    self._data_control = data


    def _notification_handler(
        self, _sender: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        self._log.debug("RX BLE data: %s", data.hex())
        self._data = data
        self._data_event.set()

    @staticmethod
    def _cell_voltages(data: bytearray, cells: int) -> list[float]:
        return [
            int.from_bytes(
                data[BMS.HEAD_LEN + 2 * idx : BMS.HEAD_LEN + 2 * idx + 2],
                byteorder="big",
                signed=True,
            )
            / 1000
            for idx in range(cells)
        ]

    @staticmethod
    def _temp_sensors(data: bytearray, sensors: int, offs: int) -> list[float]:
        return [
            float(
                int.from_bytes(data[idx : idx + 2], byteorder="big", signed=True) - 40
            )
            for idx in range(offs, offs + sensors * 2, 2)
        ]



    async def _async_update(self) -> BMSsample:
        """Update battery status information."""
        data: BMSsample = {}
        self._log.debug(f"waiting status notify")
        try:
            result = await asyncio.wait_for(self._data_event.wait(), timeout=5)
            #print(result)
        except asyncio.TimeoutError:
            self._log.debug("timeout during waiting event")
        #await self._data_event.wait()
        self._log.debug("status notify recived")

        #self._data = await self._client.read_gatt_char("3BEF0201-F30A-DF90-4A4C-74B6EB69184F")
        #await self._client.read_gatt_char("3BEF0201-F30A-DF90-4A4C-74B6EB69184F")

        if len(self._data) >= 17:
            self._data_event.clear()
            data["water_temperature"] = self._data[14]
            data["air_temperature"] = self._data[16]
            data["current"] = self._data[12]/10
            data["cycles"]  = int.from_bytes(self._data[8:12], byteorder='little',signed=False)#(self._data[11] << 24) +(self._data[10] << 16)+(self._data[9] << 8) +self._data[8] #(x[11] << 24) + (x[10] << 16) +(x[9] << 8) + x[8];
            data["runtime"] = int.from_bytes(self._data[4:8], byteorder='little',signed=False)#runtime
            data["filtration_hors_gel_state"] = bool(self._data[0])
            data["filtration_24_24_state"] = bool(self._data[1])
            data["filtration_state"] = bool(self._data[2])
            data["surcharge_protection_state"] = bool(self._data[3])
            data["pairing_state"] = True
        else:
            self._log.error("data empty")
        #test
        # list_service = await self._client.get_services()
        # for service in list_service:
        #     self._log.info(f"🔧 Service: {service.uuid}")
        #
        #     for char in service.characteristics:
        #         self._log.info(f"  📗 Characteristic: {char.uuid} (propriétés: {char.properties})")

        try:
            model_name = await self._client.read_gatt_char("00002a24-0000-1000-8000-00805f9b34fb")
            self._log.info(f"model name: {model_name.decode('utf-8')}")
            serial_number = await self._client.read_gatt_char("00002a25-0000-1000-8000-00805f9b34fb")
            self._log.info(f"serial_number: {serial_number.decode('utf-8')}")
            firmware_version = await self._client.read_gatt_char("00002a26-0000-1000-8000-00805f9b34fb")
            self._log.info(f"firmware_version: {firmware_version.decode('utf-8')}")
            hardware_version = await self._client.read_gatt_char("00002a27-0000-1000-8000-00805f9b34fb")
            self._log.info(f"hardware_version: {hardware_version.decode('utf-8')}")

            #NEED AUTH
            #time_date_time = await self._client.read_gatt_char("00002a08-0000-1000-8000-00805f9b34fb")
            #self._log.info(f"date_time: {time_date_time.decode('utf-8')}")
            #time_day = await self._client.read_gatt_char("00002a09-0000-1000-8000-00805f9b34fb")
            #self._log.info(f"day: {time_day.decode('utf-8')}")
            #char_installation = await self._client.read_gatt_char("e21d0101-ae5f-11eb-8529-0242ac130003")
            #self._log.info(f"char_installation: {char_installation.decode('utf-8')}")
            #char_parametrage_main = await self._client.read_gatt_char("e21d0102-ae5f-11eb-8529-0242ac130003")
            #self._log.info(f"char_parametrage_main: {char_parametrage_main.decode('utf-8')}")
            #char_parametrage_hecl = await self._client.read_gatt_char("e21d0103-ae5f-11eb-8529-0242ac130003")
            #self._log.info(f"char_parametrage_hecl: {char_installation.decode('utf-8')}")

            manufacturer = await self._client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu: {manufacturer.decode('utf-8')}")
            inconnu1 = await self._client.read_gatt_char("00002a01-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu1: {inconnu1}")
            inconnu2 = await self._client.read_gatt_char("00002a04-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu2: {inconnu2}")
            #fin test
        except BleakError as e:
            self._log.error(f"error during test{e}")
        try:
            control_value = await self._client.read_gatt_char("3BEF010C-F30A-DF90-4A4C-74B6EB69184F")
            self._log.debug(f"read control {control_value.hex()}")
            data["light_state"] = control_value[2] != 0
            data["pairing_state"] = False


            time_date_time = await self._client.read_gatt_char("00002a08-0000-1000-8000-00805f9b34fb")
            self._log.info(f"date_time: {time_date_time.decode('utf-8')}")
            time_day = await self._client.read_gatt_char("00002a09-0000-1000-8000-00805f9b34fb")
            self._log.info(f"day: {time_day.decode('utf-8')}")
            char_installation = await self._client.read_gatt_char("3BEF0101-F30A-DF90-4A4C-74B6EB69184F")
            self._log.info(f"char_installation: {char_installation.hex()}")
            char_parametrage_main = await self._client.read_gatt_char("3BEF0102-F30A-DF90-4A4C-74B6EB69184F")
            self._log.info(f"char_parametrage_main: {char_parametrage_main.hex()}")
            char_parametrage_hppe = await self._client.read_gatt_char("3BEF0103-F30A-DF90-4A4C-74B6EB69184F")
            self._log.info(f"char_parametrage_hecl: {char_parametrage_hppe.hex()}")
        except BleakError as e:
            data["pairing_state"] = True
            self._log.error(f"read control error trying associate{e}")
            await self._associate_asic()



        return data

    async def turn_on_off_light(self,light_state: bool = False) -> None:
        control_value = await self._client.read_gatt_char("E21D0104-AE5F-11EB-8529-0242AC130003")
        self._log.debug(f"read control {control_value}")
        control_value[2] = 1 if light_state else 0
        await self._client.write_gatt_char("E21D0104-AE5F-11EB-8529-0242AC130003",control_value)
        #data["light_state"] = control_value[2] != 0
        return


    async def _associate_asic(self) -> None:

        random_key = await self.client.read_gatt_char("3BEF0201-F30A-DF90-4A4C-74B6EB69184F")
        self._log.debug(f"random key {random_key.hex()}")

        shared_key = await  self.client.read_gatt_char("3BEF0202-F30A-DF90-4A4C-74B6EB69184F")
        self._log.debug(f"shared key {shared_key.hex()}")
        if all(b == 0 for b in shared_key):
            self._log.debug("asic not in pairing mode")
            if not all(b == 0 for b in self.encrypt_key_barray):
                self._log.error("trying auth with previous hash")
                write_encrypt_response = await  self.client.write_gatt_char("3BEF0203-F30A-DF90-4A4C-74B6EB69184F",
                                                                        self.encrypt_key_barray, True)
            return

        secret = bytearray([
            0x11, 0x41, 0xa8, 0x05,
            0x37, 0x44, 0x4a, 0x6a,
            0x85, 0x88, 0x8d, 0x84,
            0x11, 0x5f, 0x28, 0x11
        ])


        #shared = bytearray([
        #    0xe1,0x11,0x3a,0xcf,0x80,0x6e,0x36,0x02
        #])
        #random =  bytearray([
        #    0xe6,0xbe, 0xe1,0x27,0x27,0x7f,0x73,0xdd
        #])
        shared_key.reverse()
        random_key.reverse()

        cipher = AES.new(secret,AES.MODE_ECB)
        #encrypt_key = cipher.encrypt(shared + random)
        encrypt_key = cipher.encrypt(shared_key+random_key)
        self.encrypt_key_barray = bytearray(encrypt_key)
        self.encrypt_key_barray.reverse()

        self._log.debug(f"encrypt key {self.encrypt_key_barray.hex()}")

        write_encrypt_response = await  self.client.write_gatt_char("3BEF0203-F30A-DF90-4A4C-74B6EB69184F",self.encrypt_key_barray,True)

        #self._log.debug(f"encrypt key {write_encrypt_response.hex()}")