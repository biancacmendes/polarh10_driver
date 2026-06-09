import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn


LOG_CLIENT_CONNECTED = "Client connected"
LOG_CLIENT_DISCONNECTED = "Client disconnected"

DEFAULT_BROADCAST_INTERVAL_SEC = 1
DEFAULT_CONTROL_PATH = "/control"
DEFAULT_OUTPUT_DIR = "recordings"

GENERIC_EXCEPTION = Exception


class WebSocketGateway:
    """WebSocket gateway for ECG streaming and recording control."""

    def __init__(self, config, data_source):
        self.config = config
        self.data_source = data_source

        self.host = config.get("gateway", "host")
        self.port = int(config.get("gateway", "port"))
        self.path = config.get("gateway", "websocket_path")

        self.control_path = DEFAULT_CONTROL_PATH
        self.output_dir = Path(DEFAULT_OUTPUT_DIR)

        self.app = FastAPI()
        self.clients = []

        self.recording_enabled = False
        self.recording_run_id = None
        self.recording_label = None
        self.recording_started_at = None
        self.recording_samples = []
        self.recording_packets = []

        self._configure_routes()

    def _configure_routes(self):
        @self.app.websocket(self.path)
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            self.clients.append(ws)

            print(f"[stream] Driver conectado de {ws.client}")
            logging.info(LOG_CLIENT_CONNECTED)

            try:
                while True:
                    await asyncio.sleep(DEFAULT_BROADCAST_INTERVAL_SEC)

            except WebSocketDisconnect:
                pass

            except GENERIC_EXCEPTION:
                pass

            finally:
                if ws in self.clients:
                    self.clients.remove(ws)

                print(f"[stream] Driver desconectado de {ws.client}")
                logging.info(LOG_CLIENT_DISCONNECTED)

        @self.app.websocket(self.control_path)
        async def control_endpoint(ws: WebSocket):
            await ws.accept()

            print(f"[control] Cliente conectado de {ws.client}")
            logging.info("Control client connected")

            try:
                while True:
                    command = await ws.receive_json()
                    print(f"[control] Received: {command}")

                    response = await self.handle_control_command(command)
                    await ws.send_json(response)

            except WebSocketDisconnect:
                pass

            except GENERIC_EXCEPTION as exc:
                print(f"[control] Erro no cliente {ws.client}: {exc}")

            finally:
                print(f"[control] Cliente desconectado de {ws.client}")
                logging.info("Control client disconnected")

    async def handle_control_command(self, command):
        if command.get("type") != "recording":
            return {
                "ok": False,
                "error": "unsupported_type",
                "received": command,
            }

        action = command.get("action")

        if action == "start":
            self.start_recording(
                run_id=command.get("runId"),
                label=command.get("label"),
            )

            return {
                "ok": True,
                "type": "recording",
                "action": "start",
                "runId": self.recording_run_id,
                "recording": self.recording_enabled,
            }

        if action == "stop":
            metadata = self.stop_recording(
                reason=command.get("reason"),
            )

            return {
                "ok": True,
                "type": "recording",
                "action": "stop",
                "recording": self.recording_enabled,
                "metadata": metadata,
            }

        return {
            "ok": False,
            "error": "unsupported_action",
            "action": action,
        }

    def start_recording(self, run_id=None, label=None):
        self.recording_enabled = True
        self.recording_run_id = run_id or f"manual-{self.timestamp_for_filename()}"
        self.recording_label = label
        self.recording_started_at = datetime.now().isoformat()
        self.recording_samples = []
        self.recording_packets = []

        print("\n" + "=" * 72)
        print("[control] RECORDING STARTED")
        print(f"[control] runId     : {self.recording_run_id}")
        print(f"[control] label     : {self.recording_label}")
        print(f"[control] startedAt : {self.recording_started_at}")
        print("=" * 72 + "\n")

    def stop_recording(self, reason=None):
        if not self.recording_enabled:
            print("[control] STOP ignored: recording was not active")
            return None

        self.recording_enabled = False
        finished_at = datetime.now().isoformat()

        self.output_dir.mkdir(parents=True, exist_ok=True)

        run_id_safe = self.safe_name(self.recording_run_id)
        ts = self.timestamp_for_filename()
        file_id = f"{run_id_safe}_{ts}"

        ecg_path = self.output_dir / f"ecg_raw_{file_id}.npy"
        packets_path = self.output_dir / f"packets_{file_id}.npy"
        metadata_path = self.output_dir / f"metadata_{file_id}.json"

        ecg_array = np.asarray(self.recording_samples, dtype=np.float32)
        packets_array = np.asarray(self.recording_packets, dtype=object)

        np.save(ecg_path, ecg_array)
        np.save(packets_path, packets_array, allow_pickle=True)

        metadata = {
            "fileId": file_id,
            "runId": self.recording_run_id,
            "label": self.recording_label,
            "reason": reason,
            "startedAt": self.recording_started_at,
            "finishedAt": finished_at,
            "numSamples": int(ecg_array.size),
            "numPackets": int(len(self.recording_packets)),
            "sampleRateHz": self.safe_config_get("ecg", "sample_rate_hz"),
            "ecgFile": str(ecg_path),
            "packetsFile": str(packets_path),
            "metadataFile": str(metadata_path),
        }

        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print("\n" + "=" * 72)
        print("[control] RECORDING STOPPED")
        print(f"[control] fileId    : {file_id}")
        print(f"[control] runId     : {self.recording_run_id}")
        print(f"[control] label     : {self.recording_label}")
        print(f"[control] startedAt : {self.recording_started_at}")
        print(f"[control] finishedAt: {finished_at}")
        print(f"[control] samples   : {int(ecg_array.size)}")
        print(f"[control] packets   : {int(len(self.recording_packets))}")
        print(f"[control] ECG       : {ecg_path}")
        print(f"[control] packets   : {packets_path}")
        print(f"[control] metadata  : {metadata_path}")
        print("=" * 72 + "\n")

        self.recording_run_id = None
        self.recording_label = None
        self.recording_started_at = None
        self.recording_samples = []
        self.recording_packets = []

        return metadata

    def capture_packet_if_recording(self, packet):
        if not self.recording_enabled:
            return

        samples = packet.get("samples") or []

        if isinstance(samples, list):
            self.recording_samples.extend(samples)

        self.recording_packets.append(packet)

    async def broadcast(self, data):
        for client in list(self.clients):
            try:
                await client.send_json(data)

            except GENERIC_EXCEPTION:
                if client in self.clients:
                    self.clients.remove(client)

    async def data_loop(self):
        while True:
            packet = await self.data_source.get_packet()

            self.capture_packet_if_recording(packet)

            await self.broadcast(packet)

    async def start(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("Iniciando driver Polar H10:")
        print(f"  stream : ws://{self.host}:{self.port}{self.path}")
        print(f"  control: ws://{self.host}:{self.port}{self.control_path}")
        print(f"  output : {self.output_dir.resolve()}")

        logging.info(f"Starting WebSocket server {self.host}:{self.port}")
        logging.info(f"Stream endpoint: ws://{self.host}:{self.port}{self.path}")
        logging.info(f"Control endpoint: ws://{self.host}:{self.port}{self.control_path}")

        asyncio.create_task(self.data_loop())

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
        )

        server = uvicorn.Server(config)

        await server.serve()

    def safe_config_get(self, section, key):
        try:
            return self.config.get(section, key)
        except Exception:
            return None

    @staticmethod
    def timestamp_for_filename():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def safe_name(value):
        if not value:
            return "no_run_id"

        return "".join(
            char if char.isalnum() or char in ("-", "_") else "_"
            for char in str(value)
        )