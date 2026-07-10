import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn


LOG_CLIENT_CONNECTED = "Client connected"
LOG_CLIENT_DISCONNECTED = "Client disconnected"

KEEP_ALIVE_INTERVAL_SEC = 1
CONTROL_PATH = "/control"
OUTPUT_DIR = "recordings"


VIS_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Polar H10 Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body{
    font-family: Arial;
}

#metrics{
    margin-bottom:20px;
}

.metric{
    display:inline-block;
    margin-right:30px;
    font-size:18px;
}
</style>

</head>

<body>

<h2>Polar H10 Physiological Monitor</h2>

<div id="metrics">

<div class="metric">HR: <span id="hr">--</span></div>
<div class="metric">RR: <span id="rr">--</span></div>
<div class="metric">RMSSD: <span id="rmssd">--</span></div>
<div class="metric">SDNN: <span id="sdnn">--</span></div>
<div class="metric">pNN50: <span id="pnn50">--</span></div>
<div class="metric">LF/HF: <span id="lfhf">--</span></div>

</div>

<canvas id="chart" width="1000" height="400"></canvas>

<script>

const MAX_POINTS = 800;

const ctx = document.getElementById('chart').getContext('2d');

const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'ECG',
            data: [],
            borderWidth: 1,
            pointRadius: 0
        }]
    },
    options: {
        animation: false,
        scales: {
            x: { display: false }
        }
    }
});

const ws = new WebSocket("ws://" + location.host + "/stream");

ws.onmessage = function(event){

    const packet = JSON.parse(event.data);

    if(packet.type !== "ecg")
        return;

    if(packet.samples){

        packet.samples.forEach(v => {

            chart.data.labels.push("");
            chart.data.datasets[0].data.push(v);

            if(chart.data.datasets[0].data.length > MAX_POINTS){
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }

        });

        chart.update();
    }

    if(packet.metrics){

        if(packet.metrics.hr !== undefined)
            document.getElementById("hr").innerText = packet.metrics.hr.toFixed(1);

        if(packet.metrics.rr !== undefined)
            document.getElementById("rr").innerText = packet.metrics.rr.toFixed(3);

        if(packet.metrics.rmssd !== undefined)
            document.getElementById("rmssd").innerText = packet.metrics.rmssd.toFixed(2);

        if(packet.metrics.sdnn !== undefined)
            document.getElementById("sdnn").innerText = packet.metrics.sdnn.toFixed(2);

        if(packet.metrics.pnn50 !== undefined)
            document.getElementById("pnn50").innerText = packet.metrics.pnn50.toFixed(2);

        if(packet.metrics.lf_hf !== undefined)
            document.getElementById("lfhf").innerText = packet.metrics.lf_hf.toFixed(2);
    }

};

</script>

</body>
</html>
"""


class WebSocketGatewayDashboard:
    """WebSocket gateway with embedded dashboard, ECG stream and recording control."""

    def __init__(self, config, data_source):
        self.config = config
        self.data_source = data_source

        self.host = config.get("gateway", "host")
        self.port = int(config.get("gateway", "port"))
        self.path = config.get("gateway", "websocket_path")

        self.app = FastAPI()
        self.clients = []

        self.output_dir = Path(OUTPUT_DIR)

        self.recording_enabled = False
        self.recording_run_id = None
        self.recording_label = None
        self.recording_started_at = None
        self.recording_samples = []
        self.recording_packets = []

        self._configure_routes()

    def _configure_routes(self):

        @self.app.get("/")
        async def dashboard():
            return HTMLResponse(VIS_PAGE)

        @self.app.websocket(self.path)
        async def websocket_endpoint(ws: WebSocket):

            await ws.accept()
            self.clients.append(ws)

            logging.info(LOG_CLIENT_CONNECTED)

            try:
                while True:
                    await asyncio.sleep(KEEP_ALIVE_INTERVAL_SEC)

            except Exception:
                if ws in self.clients:
                    self.clients.remove(ws)

                logging.info(LOG_CLIENT_DISCONNECTED)

        @self.app.websocket(CONTROL_PATH)
        async def control_endpoint(ws: WebSocket):
            await ws.accept()
            logging.info("Control client connected")

            try:
                while True:
                    command = await ws.receive_json()
                    response = await self.handle_control_command(command)
                    await ws.send_json(response)

            except Exception:
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

        file_id = f"{self.safe_name(self.recording_run_id)}_{self.timestamp_for_filename()}"

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

            except Exception:
                if client in self.clients:
                    self.clients.remove(client)

    async def data_loop(self):

        while True:
            packet = await self.data_source.get_packet()

            self.capture_packet_if_recording(packet)

            await self.broadcast(packet)

    async def start(self):

        logging.info(f"Starting WebSocket server {self.host}:{self.port}")
        logging.info(f"Dashboard endpoint: http://{self.host}:{self.port}/")
        logging.info(f"Stream endpoint: ws://{self.host}:{self.port}{self.path}")
        logging.info(f"Control endpoint: ws://{self.host}:{self.port}{CONTROL_PATH}")

        asyncio.create_task(self.data_loop())

        config = uvicorn.Config(self.app, host=self.host, port=self.port)
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