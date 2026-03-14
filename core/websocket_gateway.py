import asyncio
import logging

from fastapi import FastAPI, WebSocket
import uvicorn


class WebSocketGateway:

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