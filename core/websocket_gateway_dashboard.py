import asyncio
import logging

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn


VIS_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Polar H10 ECG</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body>

<h2>Polar H10 ECG Stream</h2>

<canvas id="chart" width="1000" height="400"></canvas>

<script>

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

ws.onmessage = function(event) {

    const packet = JSON.parse(event.data);

    if(packet.type !== "ecg")
        return;

    packet.samples.forEach(v => {

        chart.data.labels.push("");
        chart.data.datasets[0].data.push(v);

        if(chart.data.datasets[0].data.length > 800){
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

    });

    chart.update();
};

</script>

</body>
</html>
"""


class WebSocketGatewayDashboard:

    def __init__(self, config, data_source):

        self.config = config
        self.data_source = data_source

        self.host = config.get("gateway", "host")
        self.port = config.get("gateway", "port")
        self.path = config.get("gateway", "websocket_path")

        self.app = FastAPI()
        self.clients = []

        self._configure_routes()

    def _configure_routes(self):

        @self.app.get("/")
        async def dashboard():
            return HTMLResponse(VIS_PAGE)

        @self.app.websocket(self.path)
        async def websocket_endpoint(ws: WebSocket):

            await ws.accept()
            self.clients.append(ws)

            logging.info("Client connected")

            try:
                while True:
                    await asyncio.sleep(1)

            except Exception:
                self.clients.remove(ws)

    async def broadcast(self, data):

        for client in list(self.clients):

            try:
                await client.send_json(data)

            except Exception:
                self.clients.remove(client)

    async def data_loop(self):

        while True:

            packet = await self.data_source.get_packet()

            await self.broadcast(packet)

    async def start(self):

        logging.info(f"Starting WebSocket server {self.host}:{self.port}")

        asyncio.create_task(self.data_loop())

        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)

        await server.serve()