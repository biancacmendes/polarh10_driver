import asyncio
import logging
import time

from bleak import BleakScanner, BleakClient
from bleakheart import PolarMeasurementData

from core.signal_processor import SignalProcessor

# Configuration constants
PACKET_TYPE_ECG = "ecg"


class PolarClient:
    """Client responsible for connecting to a Polar device using bleakheart and managing queues."""

    def __init__(self, config):
        self.config = config
        
        try:
            self.device_address = config.get("bluetooth", "device_address")
        except Exception:
            self.device_address = config.get("device_address")

        self.seq = 0
        self.queue = asyncio.Queue()
        self.device = None
        self.client = None
        self.pmd = None
        self._consumer_task = None

        # State buffers required by the web gateways and dashboard
        self.latest_ecg = None
        self.latest_acc = None
        self.latest_hr = None

        self.ecg_buffer = []
        self.acc_buffer = []
        self.hr_buffer = []

        self.processor = SignalProcessor(config)

    async def connect(self):
        """Resolve the Polar hardware address using robust active scanning with retries."""
        logging.info("Preparing Bluetooth adapter cache...")
        try:
            await BleakScanner.discover(timeout=1.0)
        except Exception:
            pass

        max_retries = 3
        retry_delay = 2.0
        device = None

        for attempt in range(1, max_retries + 1):
            logging.info(
                "Scanning specifically for Polar device: %s (Attempt %d/%d)", 
                self.device_address, attempt, max_retries
            )
            
            device = await BleakScanner.find_device_by_address(self.device_address, timeout=7.0)
            
            if device is not None:
                break
                
            if attempt < max_retries:
                logging.warning("Device not found on this scan. Shaking D-Bus adapter and retrying...")
                await asyncio.sleep(retry_delay)

        if device is None:
            raise RuntimeError(
                f"Polar device not found at address {self.device_address} after {max_retries} attempts."
            )

        self.device = device
        logging.info("Polar device hardware resolved: %s", device.address)

    async def _consume_bleakheart_queue(self, bh_queue):
        """Internal task to process incoming bleakheart queue data and feed the main architecture."""
        loop = asyncio.get_running_loop()
        
        while True:
            try:
                frame = await bh_queue.get()
                
                # Sinalizador de parada do cliente BLE
                if frame[0] == "QUIT":
                    logging.info("Internal bleakheart queue consumer received QUIT signal.")
                    break
                
                # Identifica se o bloco recebido é de dados de ECG
                if frame[0] == "ECG":
                    # Estrutura do frame: ('ECG', tstamp, [samples])
                    samples = frame[2]
                    if not samples:
                        continue

                    # Alimenta os históricos que o gateway/dashboard buscam por fora
                    self.latest_ecg = samples
                    self.ecg_buffer.append(samples)

                    samples_list = list(samples)
                    self.seq += 1

                    packet = {
                        "type": PACKET_TYPE_ECG,
                        "seq": self.seq,
                        "timestamp": time.time(),
                        "samples": samples_list,
                    }

                    # Envia os dados para a sua pipeline analítica
                    metrics_results = self.processor.process(samples_list)

                    if metrics_results:
                        packet["metrics"] = metrics_results[-1]
                        if isinstance(metrics_results[-1], dict) and "hr" in metrics_results[-1]:
                            self.latest_hr = metrics_results[-1]["hr"]
                            self.hr_buffer.append(metrics_results[-1]["hr"])

                    # Enfileira o pacote formatado para o seu WebSocketGateway consumir
                    loop.call_soon_threadsafe(self.queue.put_nowait, packet)
                    
            except Exception as e:
                logging.error("Error inside bleakheart pipeline consumer: %s", e)

    async def start_stream(self):
        """Establish direct connection and launch streaming via PolarMeasurementData container."""
        logging.info("Opening raw BleakClient pipeline connection...")
        
        # Usamos o cliente explícito para manter a conexão aberta sem cair do escopo do context manager
        self.client = BleakClient(self.device)
        await self.client.connect()
        logging.info("Connection established successfully with the device hardware.")

        # Criamos a fila que a classe do bleakheart exige para depositar as tuplas
        bleakheart_queue = asyncio.Queue()

        # Instancia o driver injetando a nossa conexão ativa
        self.pmd = PolarMeasurementData(self.client, ecg_queue=bleakheart_queue)

        logging.info("Requesting available configuration profiles from the firmware...")
        try:
            settings = await self.pmd.available_settings("ECG")
            logging.info("ECG Hardware Settings Available: %s", settings)
        except Exception:
            pass

        # Dispara o worker assíncrono interno para esvaziar a fila da lib e alimentar o seu SignalProcessor
        self._consumer_task = asyncio.create_task(self._consume_bleakheart_queue(bleakheart_queue))

        logging.info("Activating ECG stream pipeline on the Polar microprocessor...")
        err_code, err_msg, _ = await self.pmd.start_streaming("ECG")
        
        if err_code != 0:
            raise RuntimeError(f"PMD returned streaming registration error: {err_msg}")

        logging.info("All telemetry streams are fully active and delivering data.")

    async def get_packet(self):
        """Retrieve next available packet from the processing queue."""
        return await self.queue.get()

    async def disconnect(self):
        """Cleanly close the session and release system sockets."""
        if self.pmd is not None and self.client is not None and self.client.is_connected:
            try:
                await self.pmd.stop_streaming("ECG")
            except Exception:
                pass
        
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None
            logging.info("Disconnected cleanly from Polar hardware session.")
            
        self.pmd = None