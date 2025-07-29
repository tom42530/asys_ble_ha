"""Base class defintion for battery management systems (BMS)."""

from datetime import datetime
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Final, TypedDict

from Crypto.Cipher import AES
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.match import ble_device_matches
from homeassistant.helpers.storage import Store
from homeassistant.loader import BluetoothMatcherOptional

from custom_components.asys_ble.const import DEFAULT_UNDERLOAD_PERIOD, DEFAULT_UNDERLOAD_INTENSITY_THRESHOLD


class BMSsample(TypedDict, total=False):
    """Dictionary representing a sample of battery management system (BMS) data."""

    filtration_hors_gel_state: bool
    filtration_24_24_state: bool
    filtration_state: bool
    surcharge_protection_state: bool
    current: float  # [A] (positive: charging)
    water_temperature: int | float  # [°C]
    air_temperature: int | float  # [°C]
    cycles: int  # [#]
    pairing_state: bool
    runtime: int  # [s]
    temp_sensors: int  # [#]
    temp_values: list[int | float]  # [°C]
    light_state: bool
    filtration_mode_state: int
    filtration_mode: int
    manufacturer: str
    model:str
    hw_version: str
    sw_version:str
    serial_number: str
    underload_protection_state: bool


class AdvertisementPattern(TypedDict, total=False):
    """Optional patterns that can match Bleak advertisement data."""

    local_name: str  # name pattern that supports Unix shell-style wildcards
    service_uuid: str  # 128-bit UUID that the device must advertise
    service_data_uuid: str  # service data for the service UUID
    manufacturer_id: int  # required manufacturer ID
    manufacturer_data_start: list[int]  # required starting bytes of manufacturer data
    connectable: bool  # True if active connections to the device are required


class BaseBMS(ABC):
    """Abstract base class for battery management system."""

    CHARACTERISTIC_SYSTEM_SHAREDKEY_UUID = "3BEF0202-F30A-DF90-4A4C-74B6EB69184F"
    CHARACTERISTIC_SYSTEM_ENCRYPTKEY_UUID = "3BEF0203-F30A-DF90-4A4C-74B6EB69184F"
    CHARACTERISTIC_SYSTEM_RANDOMKEY_UUID = "3BEF0201-F30A-DF90-4A4C-74B6EB69184F"



    def __init__(
            self,
            logger_name: str,
            ble_device: BLEDevice,
            store: Store,
            reconnect: bool = False,
    ) -> None:
        """Intialize the BMS.



        Args:
            logger_name (str): name of the logger for the BMS instance (usually file name)
            ble_device (BLEDevice): the Bleak device to connect to
            reconnect (bool): if true, the connection will be closed after each update

        """

        self._ble_device: Final[BLEDevice] = ble_device
        self._reconnect: Final[bool] = reconnect
        self.name: Final[str] = self._ble_device.name or "undefined"
        self._log: Final[logging.Logger] = logging.getLogger(
            f"{logger_name.replace('.plugins', '')}::{self.name}:"
            f"{self._ble_device.address[-5:].replace(':', '')})"
        )
        self._store = store
        self._inv_wr_mode: bool | None = None  # invert write mode (WNR <-> W)

        self._log.debug(
            "initializing %s, BT address: %s", self.device_id(), ble_device.address
        )
        self._client: BleakClient = BleakClient(
            self._ble_device,
            disconnected_callback=self._on_disconnect,
        )
        self._data: bytearray = bytearray()
        # self._data_control: bytearray = bytearray()
        self._data_event: Final[asyncio.Event] = asyncio.Event()
        self.is_pump_underload_protection_enabled = False
        self.underload_intensity_threshold = DEFAULT_UNDERLOAD_INTENSITY_THRESHOLD
        self.underload_period_s = DEFAULT_UNDERLOAD_PERIOD
        self.underload_seen_datetime = None

    @staticmethod
    @abstractmethod
    def matcher_dict_list() -> list[AdvertisementPattern]:
        """Return a list of Bluetooth advertisement matchers."""

    @staticmethod
    @abstractmethod
    def device_info() -> dict[str, str]:
        """Return a dictionary of device information.

        keys: manufacturer, model
        """

    @classmethod
    def device_id(cls) -> str:
        """Return device information as string."""
        return " ".join(cls.device_info().values())

    @classmethod
    def supported(cls, discovery_info: BluetoothServiceInfoBleak) -> bool:
        """Return true if service_info matches BMS type."""
        # if "e21d0100-ae5f-11eb-8529-0242ac130003" in discovery_info.service_uuids:
        #    return True
        # logging.debug("BMS already connected %s",discovery_info.service_uuids)
        for matcher_dict in cls.matcher_dict_list():
            if ble_device_matches(
                    BluetoothMatcherOptional(**matcher_dict), discovery_info
            ):
                return True
        return False


    def set_pump_underload_settings(self,is_pump_underload_protection_enabled: bool,underload_intensity_threshold: int,underload_period_s: int) -> None:
        self._log.debug(f"set_pump_underload_settings {is_pump_underload_protection_enabled} {underload_intensity_threshold} {underload_period_s}")
        self.is_pump_underload_protection_enabled = is_pump_underload_protection_enabled
        self.underload_intensity_threshold = underload_intensity_threshold
        self.underload_period_s = underload_period_s


    def _on_disconnect(self, _client: BleakClient) -> None:
        """Disconnect callback function."""

        self._log.debug("disconnected from BMS")

    async def _init_connection(self) -> None:
        # reset any stale data from BMS
        self._data.clear()
        self._data_event.clear()


    async def _connect(self) -> None:
        """Connect to the BMS ."""

        if self._client.is_connected:
            self._log.debug("BMS already connected")
            return

        self._log.debug("connecting BMS")
        self._client = await establish_connection(
            client_class=BleakClient,
            device=self._ble_device,
            name=self._ble_device.address,
            disconnected_callback=self._on_disconnect,
        )

        try:
            await self._init_connection()
        except Exception as err:
            self._log.info(
                "failed to initialize BMS connection (%s)", type(err).__name__
            )
            await self.disconnect()
            raise



    async def disconnect(self, reset: bool = False) -> None:
        """Disconnect the BMS, includes stoping notifications."""

        if self._client.is_connected:
            self._log.debug("disconnecting BMS")
            try:
                self._data_event.clear()
                if reset:
                    self._inv_wr_mode = None  # reset write mode
                await self._client.disconnect()
            except BleakError:
                self._log.warning("disconnect failed!")

    async def _wait_event(self) -> None:
        """Wait for data event and clear it."""
        await self._data_event.wait()
        self._data_event.clear()

    @abstractmethod
    async def _async_update(self) -> BMSsample:
        """Return a dictionary of BMS values (keys need to come from the SENSOR_TYPES list)."""

    async def async_update(self) -> BMSsample:
        """Retrieve updated values from the BMS using method of the subclass.

        Args:
            raw (bool): if true, the raw data from the BMS is returned without
                any calculations or missing values added

        Returns:
            BMSsample: dictionary with BMS values

        """
        await self._connect()

        data: BMSsample = await self._async_update()

        if self._reconnect:
            # disconnect after data update to force reconnect next time (slow!)
            await self.disconnect()

        return data

    @property
    def client(self):
        return self._client


    def set_underload_state(self,data: BMSsample):
        if self.is_pump_underload_protection_enabled:
            data["underload_protection_state"] = False
            if data["filtration_state"] and data["current"] < self.underload_intensity_threshold:
                if self.underload_seen_datetime is None:
                    self.underload_seen_datetime = datetime.now()
                elif abs(datetime.now() - self.underload_seen_datetime).total_seconds() > self.underload_period_s:
                    self._log.error(f"alert")
                    data["underload_protection_state"] = True
            else:
                self.underload_seen_datetime = None
        else:
            self.underload_seen_datetime = None

    async def _associate_asic(self) -> None:

        random_key = await self.client.read_gatt_char(self.CHARACTERISTIC_SYSTEM_RANDOMKEY_UUID)
        self._log.debug(f"random key {random_key.hex()}")

        shared_key = await  self.client.read_gatt_char(self.CHARACTERISTIC_SYSTEM_SHAREDKEY_UUID)
        self._log.debug(f"shared key {shared_key.hex()}")
        if all(b == 0 for b in shared_key):
            self._log.debug("asic not in pairing mode")
            saved_data = await self._store.async_load()
            if saved_data:
                decoded_data = saved_data.get("last_data")
                if decoded_data:
                    original_bytes = bytearray(bytes.fromhex(decoded_data))
                    if all(b == 0 for b in original_bytes):
                        self._log.error("No shared key saved in storage. Abort.")
                        return
                    else:
                        shared_key = original_bytes
                else:
                    self._log.error("No 'last_data' found in storage. Abort.")
                    return
            else:
                self._log.error("No saved data found in storage. Abort.")
                return

        decoded_shared_key = shared_key.hex()
        self._log.debug(f"save shared key to store {decoded_shared_key}")
        await self._store.async_save({"last_data": decoded_shared_key})

        secret = bytearray([
            0x11, 0x41, 0xa8, 0x05,
            0x37, 0x44, 0x4a, 0x6a,
            0x85, 0x88, 0x8d, 0x84,
            0x11, 0x5f, 0x28, 0x11
        ])

        shared_key.reverse()
        random_key.reverse()

        cipher = AES.new(secret, AES.MODE_ECB)
        encrypt_key = cipher.encrypt(shared_key + random_key)
        self.encrypt_key_barray = bytearray(encrypt_key)
        self.encrypt_key_barray.reverse()

        self._log.debug(f"encrypt key {self.encrypt_key_barray.hex()}")

        await  self.client.write_gatt_char(self.CHARACTERISTIC_SYSTEM_ENCRYPTKEY_UUID, self.encrypt_key_barray, True)


