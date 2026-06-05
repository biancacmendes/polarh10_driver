import asyncio
import logging

from config.data_loader import load_config
from core.polar_client import PolarClient


# Logging configuration

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
)

# Configuration keys

CONFIG_PATH = "config/config.yaml"

CONFIG_SECTION_VISUALIZATION = "visualization"
CONFIG_KEY_ENABLED = "enabled"


# Logging messages

LOG_VISUALIZATION_ENABLED = "Visualization dashboard enabled"
LOG_STANDARD_GATEWAY = "Running standard WebSocket gateway"
LOG_POLAR_RETRY = "Polar stream is waiting to reconnect"
POLAR_RECONNECT_SECONDS = 3


async def main():
    """
    Application entrypoint.

    Initializes configuration, starts Polar device streaming,
    and launches the appropriate WebSocket gateway (standard or dashboard).

    The gateway selection is controlled via configuration.
    """

    # Load application configuration
    config = load_config(CONFIG_PATH)

    # Initialize Polar device client
    polar = PolarClient(config)

    polar_task = asyncio.create_task(run_polar_stream(polar))

    # Determine whether visualization dashboard should be enabled
    try:
        visualization_enabled = config.get(
            CONFIG_SECTION_VISUALIZATION,
            CONFIG_KEY_ENABLED,
        )
    except Exception:
        # Fallback to disabled if configuration is missing
        visualization_enabled = False

    # Select gateway implementation dynamically
    if visualization_enabled:
        from core.websocket_gateway_dashboard import (
            WebSocketGatewayDashboard as Gateway,
        )
        logging.info(LOG_VISUALIZATION_ENABLED)
    else:
        from core.websocket_gateway import WebSocketGateway as Gateway
        logging.info(LOG_STANDARD_GATEWAY)

    # Initialize and start gateway
    gateway = Gateway(config, polar)
    try:
        await gateway.start()
    finally:
        polar_task.cancel()
        try:
            await polar_task
        except asyncio.CancelledError:
            pass
        await polar.close(unpair=True)


async def run_polar_stream(polar):
    """
    Keep the Bluetooth side alive without blocking the WebSocket gateway.

    The hub bridge connects to the driver's WebSocket immediately. If Windows
    Bluetooth needs time to release or rediscover the strap, this task retries
    in the background instead of preventing the gateway from starting.
    """
    while True:
        try:
            await polar.connect()
            await polar.start_stream()
            logging.info("Polar stream initialized.")
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logging.warning("%s: %s: %r", LOG_POLAR_RETRY, type(exc).__name__, exc)
            await polar.close(unpair=False)
            await asyncio.sleep(POLAR_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
