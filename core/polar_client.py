import asyncio
import logging
import time

from bleak import BleakScanner
from polar_python import PolarDevice, MeasurementSettings, SettingType, ECGData


class PolarClient:

    def __init__(self, config):
        self.config = config
        self.device_address = config.get("bluetooth", "device_address")
        self.seq = 0
        self.queue = asyncio.Queue()

    async def connect(self):
        logging.info("Searching Polar device...")
        device = await BleakScanner.find_device_by_address(self.device_address)
        if device is None:
            raise RuntimeError("Polar device not found")
        self.device = device
        logging.info("Polar device resolved")

    async def start_stream(self):
        logging.info("Starting ECG stream")

        loop = asyncio.get_running_loop()

        def data_callback(data):
            if not isinstance(data, ECGData):
                return

            samples = None
            for k in ("samples", "values", "ecg", "data"):
                if hasattr(data, k):
                    samples = getattr(data, k)
                    break

            if samples is None:
                return

            self.seq += 1

            packet = {
                "type": "ecg",
                "seq": self.seq,
                "timestamp": time.time(),
                "samples": list(samples)
            }

            loop.call_soon_threadsafe(self.queue.put_nowait, packet)

        self.polar = PolarDevice(self.device, data_callback)

        await self.polar.__aenter__()

        settings = MeasurementSettings(
            measurement_type="ECG",
            settings=[
                SettingType(type="SAMPLE_RATE", values=[130]),
                SettingType(type="RESOLUTION", values=[14]),
            ],
        )

        await self.polar.start_stream(settings)

    async def get_packet(self):
        return await self.queue.get()