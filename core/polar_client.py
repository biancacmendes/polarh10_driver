import asyncio
import logging
import time

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from polar_python import PolarDevice, MeasurementSettings, SettingType, ECGData, HRData
from polar_python import constants as polar_constants

from core.signal_processor import SignalProcessor


# Logging messages
LOG_SEARCHING_DEVICE = "Searching Polar device..."
LOG_DEVICE_RESOLVED = "Polar device resolved"
LOG_STARTING_STREAM = "Starting ECG stream"

# Packet configuration
PACKET_TYPE_ECG = "ecg"
PACKET_TYPE_HEART_RATE = "heart_rate"

# ECG data attribute candidates (library-dependent variability)
ECG_SAMPLE_KEYS = ("samples", "values", "ecg", "data")

# Measurement configuration
MEASUREMENT_TYPE_ECG = "ECG"
SETTING_SAMPLE_RATE = "SAMPLE_RATE"
SETTING_RESOLUTION = "RESOLUTION"
ERROR_INSUFFICIENT_AUTHENTICATION = "Insufficient Authentication"


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class PolarClient:
    """Client responsible for connecting to a Polar device and streaming ECG data."""

    def __init__(self, config):
        """
        Initialize client with configuration.

        Parameters
        ----------
        config : ConfigParser or similar
            Configuration source containing Bluetooth and ECG parameters.
        """
        self.config = config
        self.device_address = config.get("bluetooth", "device_address")
        self.pair = _as_bool(config.get("bluetooth", "pair", default=True))
        self.scan_timeout = config.get("bluetooth", "scan_timeout", default=10)
        self.connect_timeout = config.get("bluetooth", "connect_timeout", default=45)
        self.direct_address_fallback = _as_bool(
            config.get("bluetooth", "direct_address_fallback", default=True)
        )
        self.reset_pairing_on_start = _as_bool(
            config.get("bluetooth", "reset_pairing_on_start", default=True)
        )
        self.unpair_on_close = _as_bool(
            config.get("bluetooth", "unpair_on_close", default=True)
        )
        self.prefer_direct_heart_rate = _as_bool(
            config.get("bluetooth", "prefer_direct_heart_rate", default=True)
        )
        self.device_name = config.get("bluetooth", "device_name", default="Polar H10")
        self.prefer_heart_rate = _as_bool(config.get("stream", "prefer_heart_rate", default=True))
        self._pairing_reset_done = False

        self.seq = 0
        self.queue = asyncio.Queue()
        self.stream_kind = None
        self.loop = None
        self.last_packet_at = None
        self.sample_watchdog_task = None
        self.no_sample_recoveries = 0

        self.processor = SignalProcessor(config)

    async def connect(self):
        """
        Resolve the Polar device using its Bluetooth address.

        Raises
        ------
        RuntimeError
            If the device cannot be found.
        """
        logging.info(LOG_SEARCHING_DEVICE)

        if self.reset_pairing_on_start and not self._pairing_reset_done:
            await self._unpair_windows_device("startup")
            self._pairing_reset_done = True
            await asyncio.sleep(1.0)

        self.device = await self._resolve_device()

        logging.info(LOG_DEVICE_RESOLVED)

    async def start_stream(self):
        """
        Start ECG streaming and enqueue processed packets asynchronously.
        """
        logging.info(LOG_STARTING_STREAM)

        loop = asyncio.get_running_loop()
        self.loop = loop

        def data_callback(data):
            """
            Callback executed on incoming BLE data.

            Filters ECG data, extracts samples, processes metrics,
            and pushes structured packets into the async queue.
            """

            # Ensure data type is ECG
            if not isinstance(data, ECGData):
                return

            samples = None

            # Handle variability across Polar SDK versions
            for key in ECG_SAMPLE_KEYS:
                if hasattr(data, key):
                    samples = getattr(data, key)
                    break

            if samples is None:
                return

            samples = list(samples)

            self.seq += 1
            self.last_packet_at = time.time()

            packet = {
                "type": PACKET_TYPE_ECG,
                "seq": self.seq,
                "timestamp": time.time(),
                "samples": samples,
            }

            # Process signal and attach latest metrics if available
            metrics_results = self.processor.process(samples)

            if metrics_results:
                packet["metrics"] = metrics_results[-1]

            # Thread-safe enqueue into asyncio loop
            loop.call_soon_threadsafe(self.queue.put_nowait, packet)

        def heartrate_callback(data):
            """Callback executed on standard Bluetooth heart-rate packets."""
            if not isinstance(data, HRData):
                return

            rr_intervals_ms = [
                float(value)
                for value in getattr(data, "rr_intervals", [])
                if isinstance(value, (int, float))
            ]

            self._enqueue_heart_rate_packet(float(data.heartrate), rr_intervals_ms)

        self.polar = PolarDevice(self.device, data_callback, heartrate_callback)
        self.polar.client = self._new_client()

        if self.prefer_heart_rate:
            logging.info("Starting Polar H10 heart-rate stream before ECG/PMD.")
            await self._start_heartrate_fallback()
            logging.info("Polar H10 heart-rate stream started.")
            return

        await self._connect_polar_device()

        if self.stream_kind == PACKET_TYPE_HEART_RATE:
            logging.info("Polar H10 heart-rate stream started.")
            return

        # Configure ECG stream parameters
        settings = MeasurementSettings(
            measurement_type=MEASUREMENT_TYPE_ECG,
            settings=[
                SettingType(
                    type=SETTING_SAMPLE_RATE,
                    values=[self.config.get("ecg", "sample_rate_hz")],
                ),
                SettingType(
                    type=SETTING_RESOLUTION,
                    values=[self.config.get("ecg", "resolution_bits")],
                ),
            ],
        )

        await self.polar.start_stream(settings)
        self.stream_kind = PACKET_TYPE_ECG

    async def _connect_polar_device(self):
        """
        Connect to the Polar device and start PMD notifications.

        Windows sometimes fails when pairing is requested during BleakClient.connect().
        We first connect normally, then pair only if the PMD control/data
        characteristics require authentication.
        """
        await self.polar.client.connect()

        try:
            await self._start_pmd_notifications()
        except Exception as exc:
            if self.pair and ERROR_INSUFFICIENT_AUTHENTICATION in str(exc):
                logging.info(
                    "Polar device requires authentication; pairing and retrying PMD notifications"
                )
                try:
                    await self._stop_pmd_notifications()
                    await self.polar.client.pair()
                    await self._start_pmd_notifications()
                    self.stream_kind = PACKET_TYPE_ECG
                    return
                except Exception as pair_exc:
                    logging.warning(
                        "Polar H10 PMD pairing failed; falling back to heart-rate service: %s",
                        pair_exc,
                    )
                    await self._start_heartrate_fallback()
                    return

            await self.polar.client.disconnect()
            raise

        self.stream_kind = PACKET_TYPE_ECG

    async def _start_heartrate_fallback(self):
        logging.info("Starting clean Polar H10 heart-rate connection.")
        last_error = None

        for attempt in range(2):
            await self._stop_pmd_notifications()
            await self._safe_disconnect()
            await asyncio.sleep(1.0 + attempt)

            self.device = await self._resolve_heart_rate_device()

            self.polar.client = self._new_client()
            try:
                await self.polar.client.connect()
                await self.polar.client.start_notify(
                    polar_constants.HEART_RATE_CHAR_UUID,
                    self._handle_heartrate_measurement_raw,
                )
                self.stream_kind = PACKET_TYPE_HEART_RATE
                self._start_sample_watchdog()
                return
            except Exception as exc:
                last_error = exc
                logging.warning(
                    "Polar H10 heart-rate fallback attempt %s failed: %s",
                    attempt + 1,
                    exc,
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("Polar H10 heart-rate fallback failed")

    def _handle_heartrate_measurement_raw(self, sender, data):
        try:
            heartrate, rr_intervals_ms = self._parse_heartrate_measurement(data)
        except Exception as exc:
            logging.warning("Failed to parse Polar H10 heart-rate payload: %s", exc)
            return

        self._enqueue_heart_rate_packet(heartrate, rr_intervals_ms)

    def _parse_heartrate_measurement(self, data):
        if len(data) < 2:
            raise ValueError("heart-rate payload is too short")

        flags = data[0]
        index = 1

        if flags & 0x01:
            if len(data) < index + 2:
                raise ValueError("heart-rate uint16 payload is incomplete")
            heartrate = float(int.from_bytes(data[index:index + 2], byteorder="little", signed=False))
            index += 2
        else:
            heartrate = float(data[index])
            index += 1

        if flags & 0x08:
            index += 2

        rr_intervals_ms = []
        if flags & 0x10:
            while index + 1 < len(data):
                rr_intervals_ms.append(
                    int.from_bytes(data[index:index + 2], byteorder="little", signed=False)
                    / 1024.0
                    * 1000.0
                )
                index += 2

        return heartrate, rr_intervals_ms

    def _enqueue_heart_rate_packet(self, heartrate, rr_intervals_ms):
        self.seq += 1
        self.last_packet_at = time.time()
        self.no_sample_recoveries = 0

        metrics = {
            "hr": float(heartrate),
        }

        if rr_intervals_ms:
            latest_rr_ms = rr_intervals_ms[-1]
            metrics["rr"] = latest_rr_ms / 1000.0
            metrics["rrMs"] = latest_rr_ms

            for rr_ms in rr_intervals_ms:
                self.processor.metrics.update_rr(rr_ms / 1000.0)

            computed = self.processor.metrics.compute()
            if computed:
                metrics.update(computed)

        packet = {
            "type": PACKET_TYPE_HEART_RATE,
            "seq": self.seq,
            "timestamp": self.last_packet_at,
            "metrics": metrics,
            "ibiMs": rr_intervals_ms,
        }

        if self.seq == 1 or self.seq % 10 == 0:
            logging.info(
                "Polar H10 heart-rate packet received: bpm=%s rr_count=%s",
                round(float(heartrate), 2),
                len(rr_intervals_ms),
            )

        if self.loop is None:
            self.queue.put_nowait(packet)
            return

        self.loop.call_soon_threadsafe(self.queue.put_nowait, packet)

    def _start_sample_watchdog(self):
        if self.sample_watchdog_task is None or self.sample_watchdog_task.done():
            self.sample_watchdog_task = asyncio.create_task(self._sample_watchdog())

    async def _sample_watchdog(self):
        while self.stream_kind == PACKET_TYPE_HEART_RATE:
            await asyncio.sleep(10)
            if self.last_packet_at is None or time.time() - self.last_packet_at > 10:
                logging.warning(
                    "Polar H10 heart-rate stream is connected but no samples arrived yet. "
                    "Recovering the heart-rate stream. Wear the strap, moisten the electrodes, "
                    "and make sure no other app is using it."
                )
                try:
                    await self._recover_stalled_heartrate_stream()
                except Exception as exc:
                    logging.warning("Polar H10 heart-rate watchdog recovery failed: %s", exc)

    async def _recover_stalled_heartrate_stream(self):
        self.no_sample_recoveries += 1

        if self.no_sample_recoveries == 1:
            await self._refresh_heartrate_subscription()
            return

        if self.no_sample_recoveries >= 3:
            await self._safe_disconnect()
            await self._unpair_windows_device("stalled heart-rate stream")
            await asyncio.sleep(1.0)

        logging.info(
            "Reconnecting Polar H10 heart-rate stream after %s stalled checks.",
            self.no_sample_recoveries,
        )
        await self._start_heartrate_fallback()

    async def _refresh_heartrate_subscription(self):
        try:
            await self.polar.client.stop_notify(polar_constants.HEART_RATE_CHAR_UUID)
        except Exception:
            pass

        try:
            await self.polar.client.start_notify(
                polar_constants.HEART_RATE_CHAR_UUID,
                self._handle_heartrate_measurement_raw,
            )
            logging.info("Polar H10 heart-rate subscription refreshed.")
            return
        except Exception as exc:
            logging.warning("Polar H10 heart-rate refresh failed; reconnecting: %s", exc)

        await self._safe_disconnect()
        await asyncio.sleep(1.0)
        self.device = await self._resolve_heart_rate_device()
        self.polar.client = self._new_client()
        await self.polar.client.connect()
        await self.polar.client.start_notify(
            polar_constants.HEART_RATE_CHAR_UUID,
            self._handle_heartrate_measurement_raw,
        )
        logging.info("Polar H10 heart-rate subscription reconnected.")

    def _new_client(self):
        return BleakClient(
            self.device,
            timeout=float(self.connect_timeout),
            winrt={"use_cached_services": False},
        )

    async def _resolve_device(self):
        device = await BleakScanner.find_device_by_address(
            self.device_address,
            timeout=float(self.scan_timeout),
        )
        if device is not None:
            return device

        if self.direct_address_fallback:
            logging.warning(
                "Polar H10 was not found during BLE scan; trying direct Windows GATT address fallback."
            )
            return BLEDevice(self.device_address, self.device_name, None)

        raise RuntimeError("Polar device not found")

    async def _resolve_heart_rate_device(self):
        if self.prefer_direct_heart_rate and self.direct_address_fallback:
            logging.info("Using direct Windows GATT address for Polar H10 heart-rate stream.")
            return BLEDevice(self.device_address, self.device_name, None)

        return await self._resolve_device()

    async def _safe_disconnect(self):
        if not hasattr(self, "polar"):
            return
        try:
            await self.polar.client.disconnect()
        except Exception:
            pass

    async def close(self, unpair=None):
        self.stream_kind = None
        if self.sample_watchdog_task is not None:
            self.sample_watchdog_task.cancel()
            try:
                await self.sample_watchdog_task
            except asyncio.CancelledError:
                pass
            self.sample_watchdog_task = None

        if hasattr(self, "polar"):
            try:
                await self._stop_pmd_notifications()
            except Exception:
                pass
            try:
                await self.polar.client.stop_notify(polar_constants.HEART_RATE_CHAR_UUID)
            except Exception:
                pass
            await self._safe_disconnect()

        should_unpair = self.unpair_on_close if unpair is None else unpair
        if should_unpair:
            await self._unpair_windows_device("shutdown")

    async def _unpair_windows_device(self, reason):
        try:
            client = BleakClient(
                self.device_address,
                timeout=float(self.connect_timeout),
                winrt={"use_cached_services": True},
            )
            await client.unpair()
            logging.info("Polar H10 Windows Bluetooth pairing cleared on %s.", reason)
        except Exception as exc:
            logging.info("Polar H10 Windows Bluetooth pairing clear skipped on %s: %s", reason, exc)

    async def _start_pmd_notifications(self):
        await self.polar.client.start_notify(
            polar_constants.PMD_CONTROL_POINT_UUID,
            self.polar._handle_pmd_control,
        )
        await self.polar.client.start_notify(
            polar_constants.PMD_DATA_UUID,
            self.polar._handle_pmd_data,
        )

    async def _stop_pmd_notifications(self):
        for characteristic in (
            polar_constants.PMD_CONTROL_POINT_UUID,
            polar_constants.PMD_DATA_UUID,
        ):
            try:
                await self.polar.client.stop_notify(characteristic)
            except Exception:
                pass

    async def get_packet(self):
        """
        Retrieve next available packet from the processing queue.

        Returns
        -------
        dict
            Structured ECG packet with optional HRV metrics.
        """
        return await self.queue.get()
