import os
import signal
import subprocess
import time

from PyQt6.QtCore import QThread, pyqtSignal


class HubLauncher:
    def __init__(self):
        self.polar_ws = "ws://localhost:8765/stream"
        self.polar_control_ws = "ws://localhost:8765/control"
        self.hub_ws = "ws://127.0.0.1:8787/ws"

        self.hub_dir = os.path.expanduser("~/Desktop/bianca/hub-ue/apps/hub")
        self.project_dir = os.path.expanduser("~/Desktop/bianca/hub-ue")

        self.processes = []

    def _run_headless(self, command, cwd):
        # Usando bash -c explicitamente para garantir a execução correta do source e encadeamento
        process = subprocess.Popen(
            ["/bin/bash", "-c", command],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        self.processes.append(process)
        return process

    def start_hub(self):
        # Encadeando com && garante que o segundo comando só roda se o ambiente ativar
        command = "source .venv/bin/activate && biofeedback-hub"
        return self._run_headless(command, self.hub_dir)

    def start_polar_bridge(self):
        # Construção da string em uma única linha limpa para evitar problemas de quebra de escopo
        command = (
            f"source .venv/bin/activate && biofeedback-polarh10 "
            f"--polar-ws '{self.polar_ws}' "
            f"--polar-control-ws '{self.polar_control_ws}' "
            f"--hub-ws '{self.hub_ws}'"
        )
        return self._run_headless(command, self.hub_dir)

    def start_dashboard(self):
        command = "npm run dev:dashboard"
        return self._run_headless(command, self.project_dir)

    def stop_all(self):
        for process in self.processes:
            if process.poll() is None:
                try:
                    os.killpg(
                        os.getpgid(process.pid),
                        signal.SIGTERM,
                    )
                except ProcessLookupError:
                    pass

        self.processes.clear()


class HubLauncherWorker(QThread):
    status_updated = pyqtSignal(str, int)
    finished_successfully = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, hub_launcher, delay_seconds=10):
        super().__init__()
        self.hub_launcher = hub_launcher
        self.delay_seconds = delay_seconds

    def run(self):
        try:
            self.status_updated.emit(
                "Iniciando Biofeedback Hub em modo headless...",
                10,
            )
            self.hub_launcher.start_hub()
            time.sleep(self.delay_seconds)

            self.status_updated.emit(
                "Iniciando ponte Polar H10 → Hub...",
                45,
            )
            self.hub_launcher.start_polar_bridge()
            time.sleep(self.delay_seconds)

            self.status_updated.emit(
                "Iniciando dashboard...",
                75,
            )
            self.hub_launcher.start_dashboard()
            time.sleep(2)

            self.status_updated.emit(
                "Biofeedback Hub iniciado com sucesso.",
                100,
            )
            self.finished_successfully.emit()

        except Exception as error:
            self.failed.emit(str(error))