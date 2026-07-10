import asyncio
import logging

from PyQt6.QtCore import QThread, pyqtSignal

from app.constants import CONFIG_PATH
from config.data_loader import load_config
from core.polar_client import PolarClient


class CoreAsyncWorker(QThread):
    status_updated = pyqtSignal(str, int)
    data_emitted = pyqtSignal(dict)
    hub_command = pyqtSignal(str)
    engine_ready = pyqtSignal()
    search_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.loop = None
        self.polar = None
        self.gateway = None
        self.is_cancelled = False

    def run(self):
        self.is_cancelled = False
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._lifecycle())

        except asyncio.CancelledError:
            logging.info("Rotina assíncrona abortada pelo usuário.")

        finally:
            self.search_stopped.emit()

    async def _lifecycle(self):
        try:
            if self.is_cancelled:
                return

            self.status_updated.emit("Carregando arquivos de configuração...", 15)

            config = load_config(CONFIG_PATH)

            await asyncio.sleep(0.1)

            if self.is_cancelled:
                return

            self.status_updated.emit("Buscando sensor Polar H10 via Bluetooth...", 40)

            self.polar = PolarClient(config)

            await self.polar.connect()

            if self.is_cancelled:
                return

            self.status_updated.emit("Ativando canais de transmissão internos...", 65)

            await self.polar.start_stream()

            if self.is_cancelled:
                return

            self.status_updated.emit("Inicializando portas do WebSocket Gateway...", 85)

            try:
                visualization_enabled = config.get("visualization", "enabled")

            except Exception:
                visualization_enabled = False

            if visualization_enabled:
                from core.websocket_gateway_dashboard import (
                    WebSocketGatewayDashboard as Gateway,
                )
            else:
                from core.websocket_gateway import WebSocketGateway as Gateway

            self.gateway = Gateway(config, self.polar)

            asyncio.create_task(self.gateway.start())

            await asyncio.sleep(0.5)

            if self.is_cancelled:
                return

            self.status_updated.emit("Todos os sistemas online!", 100)

            await asyncio.sleep(0.2)

            self.engine_ready.emit()

            asyncio.create_task(self._check_hub_status())

            while not self.is_cancelled:
                packet = await self.polar.queue.get()

                self.data_emitted.emit(packet)

                self.polar.queue.task_done()

        except Exception as error:
            if not self.is_cancelled:
                logging.error("Falha na inicialização do motor assíncrono: %s", error)
                self.status_updated.emit(f"Erro Crítico: {str(error)}", 0)

    async def _check_hub_status(self):
        last_state = False

        while not self.is_cancelled:
            await asyncio.sleep(0.1)

            if not self.gateway:
                continue

            current_state = getattr(self.gateway, "recording_enabled", None)

            if current_state is None and self.polar:
                current_state = getattr(self.polar, "is_recording", False)

            current_state = bool(current_state)

            if current_state != last_state:
                last_state = current_state

                command_str = "START" if current_state else "STOP"

                self.hub_command.emit(command_str)

    def cancel_operation(self):
        self.is_cancelled = True

        if self.loop and self.loop.is_running():
            self.loop.create_task(self._shutdown())

    async def _shutdown(self):
        try:
            if self.gateway:
                await self.gateway.stop()

            if self.polar:
                await self.polar.disconnect()

        except Exception as error:
            logging.warning("Erro ao limpar conexões: %s", error)

        finally:
            tasks = [
                task
                for task in asyncio.all_tasks(self.loop)
                if task is not asyncio.current_task(self.loop)
            ]

            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

            self.loop.stop()