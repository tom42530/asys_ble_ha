from datetime import datetime
from typing import Final

from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak.uuids import normalize_uuid_str
from homeassistant.helpers.storage import Store

from .basebms import AdvertisementPattern, BaseBMS, BMSsample


class BMS(BaseBMS):
    CHARACTERISTIC_PRECISEOB_STATUS_UUID = "E21D0105-AE5F-11EB-8529-0242AC130003"
    CHARACTERISTIC_PRECISEOB_CONTROL_UUID = "E21D0104-AE5F-11EB-8529-0242AC130003"




    def __init__(self, ble_device: BLEDevice, store: Store, reconnect: bool = False) -> None:
        """Intialize private BMS members."""
        super().__init__(__name__, ble_device, store, reconnect)

    @staticmethod
    def matcher_dict_list() -> list[AdvertisementPattern]:
        """Provide BluetoothMatcher definition."""
        # LOGGER.debug("tomtom device detected:")

        return [
            {
                "service_uuid": "3bef0200-f30a-df90-4a4c-74b6eb69184f",
                "connectable": True,
            }
        ]

    @staticmethod
    def device_info() -> dict[str, str]:
        """Return device information for the Asys system."""
        return {}









    async def _async_update(self) -> BMSsample:
        """Update battery status information."""
        data: BMSsample = {}


        try:
            await self._associate_asic()
            control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID)
            self._log.debug(f"read control {control_value.hex()}")
            data["light_state"] = control_value[2] != 0
            data["filtration_mode_state"] = control_value[1]
            data["filtration_mode"] = control_value[0]

            status_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_STATUS_UUID)
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



            self.set_underload_state(data)


            time_date_time = await self._client.read_gatt_char("00002a08-0000-1000-8000-00805f9b34fb")
            self._log.info(f"date_time: {time_date_time.decode('utf-8')}")
            time_day = await self._client.read_gatt_char("00002a09-0000-1000-8000-00805f9b34fb")
            self._log.info(f"day: {time_day.decode('utf-8')}")
            char_installation = await self._client.read_gatt_char("e21d0101-ae5f-11eb-8529-0242ac130003")
            self._log.info(f"char_installation: {char_installation.hex()}")
            char_parametrage_main = await self._client.read_gatt_char("e21d0102-ae5f-11eb-8529-0242ac130003")
            self._log.info(f"char_parametrage_main: {char_parametrage_main.hex()}")
            char_parametrage_hecl = await self._client.read_gatt_char("e21d0103-ae5f-11eb-8529-0242ac130003")
            self._log.info(f"char_parametrage_hecl: {char_parametrage_hecl.hex()}")
        except BleakError as e:
            data["pairing_state"] = True
            self._log.error(f"read control error trying associate{e}")



        # test
        # list_service = await self._client.get_services()
        # for service in list_service:
        #     self._log.info(f"🔧 Service: {service.uuid}")
        #
        #     for char in service.characteristics:
        #         self._log.info(f"  📗 Characteristic: {char.uuid} (propriétés: {char.properties})")

        try:
            model_name = await self._client.read_gatt_char("00002a24-0000-1000-8000-00805f9b34fb")
            self._log.info(f"model name: {model_name.decode('utf-8')}")
            data["model"]=model_name.decode('utf-8')
            serial_number = await self._client.read_gatt_char("00002a25-0000-1000-8000-00805f9b34fb")
            self._log.info(f"serial_number: {serial_number.decode('utf-8')}")
            data["serial_number"] = serial_number.decode('utf-8')
            firmware_version = await self._client.read_gatt_char("00002a26-0000-1000-8000-00805f9b34fb")
            self._log.info(f"firmware_version: {firmware_version.decode('utf-8')}")
            data["sw_version"] = firmware_version.decode('utf-8')
            hardware_version = await self._client.read_gatt_char("00002a27-0000-1000-8000-00805f9b34fb")
            self._log.info(f"hardware_version: {hardware_version.decode('utf-8')}")
            data["hw_version"] = hardware_version.decode('utf-8')

            # NEED AUTH
            # time_date_time = await self._client.read_gatt_char("00002a08-0000-1000-8000-00805f9b34fb")
            # self._log.info(f"date_time: {time_date_time.decode('utf-8')}")
            # time_day = await self._client.read_gatt_char("00002a09-0000-1000-8000-00805f9b34fb")
            # self._log.info(f"day: {time_day.decode('utf-8')}")
            # char_installation = await self._client.read_gatt_char("e21d0101-ae5f-11eb-8529-0242ac130003")
            # self._log.info(f"char_installation: {char_installation.decode('utf-8')}")
            # char_parametrage_main = await self._client.read_gatt_char("e21d0102-ae5f-11eb-8529-0242ac130003")
            # self._log.info(f"char_parametrage_main: {char_parametrage_main.decode('utf-8')}")
            # char_parametrage_hecl = await self._client.read_gatt_char("e21d0103-ae5f-11eb-8529-0242ac130003")
            # self._log.info(f"char_parametrage_hecl: {char_installation.decode('utf-8')}")

            manufacturer = await self._client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
            self._log.info(f"manufacturer: {manufacturer.decode('utf-8')}")
            data["manufacturer"] = manufacturer.decode('utf-8')

            inconnu1 = await self._client.read_gatt_char("00002a01-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu1: {inconnu1}")
            inconnu2 = await self._client.read_gatt_char("00002a04-0000-1000-8000-00805f9b34fb")
            self._log.info(f"inconnu2: {inconnu2}")
            # fin test
        except BleakError as e:
            self._log.error(f"error during test{e}")


        return data

    async def turn_on_off_light(self, light_state: bool = False) -> None:
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        control_value[2] = 1 if light_state else 0
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID, control_value)
        # data["light_state"] = control_value[2] != 0
        return

    async def change_light_color(self) -> None:
        self._log.debug("Changing light color")
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        control_value[3] = 1
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID, control_value)
        return

    async def set_filtration_mode_state(self,option: str) -> None:
        self._log.debug(f"Set filtration mode state to {option}")
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        if option == 'OFF':
            control_value[1] = 0
        elif option == 'ON':
            control_value[1] = 1
        else :
            control_value[1] = 2
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID, control_value)
        return

    async def set_filtration_mode(self,option: int) -> None:
        self._log.debug(f"Set filtration mode to {option}")
        control_value = await self._client.read_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID)
        self._log.debug(f"read control {control_value}")
        control_value[0] = option
        await self._client.write_gatt_char(BMS.CHARACTERISTIC_PRECISEOB_CONTROL_UUID, control_value)
        return
