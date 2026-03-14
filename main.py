import asyncio
import logging

from config.data_loader import load_config
from core.polar_client import PolarClient
from core.websocket_gateway import WebSocketGateway

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

async def main():
    config = load_config("config/config.yaml")
    polar = PolarClient(config)
    await polar.connect()
    await polar.start_stream()
    gateway = WebSocketGateway(config, polar)
    await gateway.start()

if __name__ == "__main__":
    asyncio.run(main())