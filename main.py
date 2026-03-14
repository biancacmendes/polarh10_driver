import asyncio
import logging

from config.data_loader import load_config
from core.polar_client import PolarClient

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)


async def main():

    config = load_config("config/config.yaml")

    polar = PolarClient(config)

    await polar.connect()
    await polar.start_stream()

    try:
        visualization_enabled = config.get("visualization", "enabled")
    except Exception:
        visualization_enabled = False

    if visualization_enabled:
        from core.websocket_gateway_dashboard import WebSocketGatewayDashboard as Gateway
        logging.info("Visualization dashboard enabled")
    else:
        from core.websocket_gateway import WebSocketGateway as Gateway
        logging.info("Running standard WebSocket gateway")

    gateway = Gateway(config, polar)

    await gateway.start()


if __name__ == "__main__":
    asyncio.run(main())