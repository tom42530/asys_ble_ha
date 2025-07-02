"""Base class defintion for battery management systems (BMS)."""

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from enum import IntEnum
import logging
from statistics import fmean
from typing import Any, Final, Literal, TypedDict

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BLEAK_TRANSIENT_BACKOFF_TIME, establish_connection

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.match import ble_device_matches
from homeassistant.loader import BluetoothMatcherOptional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad,unpad


type BMSvalue = Literal[
    "battery_charging",
    "battery_mode",
    "battery_level",
    "current",
    "power",
    "water_temperature",
    "voltage",
    "cycles",
    "cycle_capacity",
    "cycle_charge",
    "delta_voltage",
    "problem",
    "runtime",
    "balance_current",
    "cell_count",
    "cell_voltages",
    "design_capacity",
    "pack_count",
    "temp_sensors",
    "temp_values",
    "problem_code",
]

type BMSpackvalue = Literal[
    "pack_voltages",
    "pack_currents",
    "pack_battery_levels",
    "pack_cycles",
]


class BMSmode(IntEnum):
    """Enumeration of BMS modes."""

    UNKNOWN = -1
    BULK = 0x00
    ABSORPTION = 0x01
    FLOAT = 0x02

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

    MAX_RETRY: Final[int] = 3  # max number of retries for data requests
    _MAX_TIMEOUT_FACTOR: Final[int] = 8  # limit timout increase to 8x
    TIMEOUT: Final[float] = BLEAK_TRANSIENT_BACKOFF_TIME * _MAX_TIMEOUT_FACTOR
    _MAX_CELL_VOLT: Final[float] = 5.906  # max cell potential
    _HRS_TO_SECS: Final[int] = 60 * 60  # seconds in an hour

    def __init__(
        self,
        logger_name: str,
        ble_device: BLEDevice,
        reconnect: bool = False,
    ) -> None:
        """Intialize the BMS.

        notification_handler: the callback function used for notifications from 'uuid_rx()'
            characteristic. Not defined as abstract in this base class, as it can be both,
            a normal or async function

        Args:
            logger_name (str): name of the logger for the BMS instance (usually file name)
            ble_device (BLEDevice): the Bleak device to connect to
            reconnect (bool): if true, the connection will be closed after each update

        """
        assert (
            getattr(self, "_notification_handler", None) is not None
        ), "BMS class must define _notification_handler method"
        self._ble_device: Final[BLEDevice] = ble_device
        self._reconnect: Final[bool] = reconnect
        self.name: Final[str] = self._ble_device.name or "undefined"
        self._log: Final[logging.Logger] = logging.getLogger(
            f"{logger_name.replace('.plugins', '')}::{self.name}:"
            f"{self._ble_device.address[-5:].replace(':','')})"
        )
        self._inv_wr_mode: bool | None = None  # invert write mode (WNR <-> W)

        self._log.debug(
            "initializing %s, BT address: %s", self.device_id(), ble_device.address
        )
        self._client: BleakClient = BleakClient(
            self._ble_device,
            disconnected_callback=self._on_disconnect,
            services=[*self.uuid_services()],
        )
        self._data: bytearray = bytearray()
        #self._data_control: bytearray = bytearray()
        self._data_event: Final[asyncio.Event] = asyncio.Event()

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
        #if "e21d0100-ae5f-11eb-8529-0242ac130003" in discovery_info.service_uuids:
        #    return True
        #logging.debug("BMS already connected %s",discovery_info.service_uuids)
        for matcher_dict in cls.matcher_dict_list():
            if ble_device_matches(
                BluetoothMatcherOptional(**matcher_dict), discovery_info
            ):
                return True
        return False

    @staticmethod
    @abstractmethod
    def uuid_services() -> list[str]:
        """Return list of 128-bit UUIDs of services required by BMS."""

    @staticmethod
    @abstractmethod
    def uuid_rx() -> str:
        """Return 16-bit UUID of characteristic that provides notification/read property."""

    @staticmethod
    @abstractmethod
    def uuid_tx() -> str:
        """Return 16-bit UUID of characteristic that provides write property."""

    @staticmethod
    def _calc_values() -> frozenset[BMSvalue]:
        """Return values that the BMS cannot provide and need to be calculated.

        See _add_missing_values() function for the required input to actually do so.
        """
        return frozenset()

    @staticmethod
    def _add_missing_values(data: BMSsample, values: frozenset[BMSvalue]) -> None:
        return



    def _on_disconnect(self, _client: BleakClient) -> None:
        """Disconnect callback function."""

        self._log.debug("disconnected from BMS")

    async def _init_connection(self) -> None:
        # reset any stale data from BMS
        self._data.clear()
        self._data_event.clear()

        await self._client.start_notify(
            self.uuid_rx(), getattr(self, "_notification_handler")
        )
        #await self._client.start_notify(
        #    "E21D0104-AE5F-11EB-8529-0242AC130003", getattr(self, "_notification_handler_control")
        #)

    async def _connect(self) -> None:
        """Connect to the BMS and setup notification if not connected."""

        if self._client.is_connected:
            self._log.debug("BMS already connected")
            return

        self._log.debug("connecting BMS")
        self._client = await establish_connection(
            client_class=BleakClient,
            device=self._ble_device,
            name=self._ble_device.address,
            disconnected_callback=self._on_disconnect,
            services=[*self.uuid_services()],
        )

        try:
            await self._init_connection()
        except Exception as err:
            self._log.info(
                "failed to initialize BMS connection (%s)", type(err).__name__
            )
            await self.disconnect()
            raise

    def _wr_response(self, char: int | str) -> bool:
        char_tx: Final[BleakGATTCharacteristic | None] = (
            self._client.services.get_characteristic(char)
        )
        return bool(char_tx and "write" in getattr(char_tx, "properties", []))

    async def _send_msg(
        self,
        data: bytes,
        max_size: int,
        char: int | str,
        attempt: int,
        inv_wr_mode: bool = False,
    ) -> None:
        """Send message to the bms in chunks if needed."""
        chunk_size: Final[int] = max_size or len(data)

        for i in range(0, len(data), chunk_size):
            chunk: bytes = data[i : i + chunk_size]
            self._log.debug(
                "TX BLE req #%i (%s%s%s): %s",
                attempt + 1,
                "!" if inv_wr_mode else "",
                "W" if self._wr_response(char) else "WNR",
                "." if self._inv_wr_mode is not None else "",
                chunk.hex(" "),
            )
            await self._client.write_gatt_char(
                char,
                chunk,
                response=(self._wr_response(char) != inv_wr_mode),
            )

    async def _await_reply(
        self,
        data: bytes,
        char: int | str | None = None,
        wait_for_notify: bool = True,
        max_size: int = 0,
    ) -> None:
        """Send data to the BMS and wait for valid reply notification."""

        for inv_wr_mode in (
            [False, True] if self._inv_wr_mode is None else [self._inv_wr_mode]
        ):
            try:
                for attempt in range(BaseBMS.MAX_RETRY):
                    self._data_event.clear()  # clear event before requesting new data
                    await self._send_msg(
                        data, max_size, char or self.uuid_tx(), attempt, inv_wr_mode
                    )
                    try:
                        if wait_for_notify:
                            await asyncio.wait_for(
                                self._wait_event(),
                                BLEAK_TRANSIENT_BACKOFF_TIME
                                * min(2**attempt, BaseBMS._MAX_TIMEOUT_FACTOR),
                            )
                    except TimeoutError:
                        self._log.debug("TX BLE request timed out.")
                        continue  # retry sending data

                    self._inv_wr_mode = inv_wr_mode
                    return  # leave loop if no exception
            except BleakError as exc:
                # reconnect on communication errors
                self._log.warning(
                    "TX BLE request error, retrying connection (%s)", type(exc).__name__
                )
                await self.disconnect()
                await self._connect()
        raise TimeoutError

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



    async def associate(self) -> None:
        if not self.client.is_connected:
            await self.client.connect()
        random_key = await self.client.read_gatt_char("3BEF0201-F30A-DF90-4A4C-74B6EB69184F")
        self._log.debug(f"random key {random_key.hex()}")

        shared_key = await  self.client.read_gatt_char("3BEF0202-F30A-DF90-4A4C-74B6EB69184F")
        self._log.debug(f"shared key {shared_key.hex()}")
        if all(b == 0 for b in shared_key):
            self._log.debug("asic not in pairing mode")
            #return

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
        encrypt_key_barray = bytearray(encrypt_key)
        encrypt_key_barray.reverse()

        self._log.debug(f"encrypt key {encrypt_key_barray.hex()}")

        write_encrypt_response = await  self.client.write_gatt_char("3BEF0203-F30A-DF90-4A4C-74B6EB69184F",encrypt_key_barray,True)

        #self._log.debug(f"encrypt key {write_encrypt_response.hex()}")

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
        self._add_missing_values(data, self._calc_values())

        if self._reconnect:
            # disconnect after data update to force reconnect next time (slow!)
            await self.disconnect()

        return data

    @property
    def client(self):
        return self._client


def crc_modbus(data: bytearray) -> int:
    """Calculate CRC-16-CCITT MODBUS."""
    crc: int = 0xFFFF
    for i in data:
        crc ^= i & 0xFF
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc % 2 else (crc >> 1)
    return crc & 0xFFFF


def lrc_modbus(data: bytearray) -> int:
    """Calculate MODBUS LRC."""
    return ((sum(data) ^ 0xFFFF) + 1) & 0xFFFF


def crc_xmodem(data: bytearray) -> int:
    """Calculate CRC-16-CCITT XMODEM."""
    crc: int = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else (crc << 1)
    return crc & 0xFFFF


def crc8(data: bytearray) -> int:
    """Calculate CRC-8/MAXIM-DOW."""
    crc: int = 0x00  # Initialwert für CRC

    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8C if crc & 0x1 else crc >> 1

    return crc & 0xFF


def crc_sum(frame: bytearray, size: int = 1) -> int:
    """Calculate the checksum of a frame using a specified size.

    size : int, optional
        The size of the checksum in bytes (default is 1).
    """
    return sum(frame) & ((1 << (8 * size)) - 1)
