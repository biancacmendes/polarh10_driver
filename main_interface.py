import asyncio
import sys
from datetime import datetime
import os
import uuid
import logging
import numpy as np

from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QProgressBar,
)
import pyqtgraph as pg

from config.data_loader import load_config
from core.polar_client import PolarClient


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

CONFIG_PATH = "config/config.yaml"
DATA_ROOT_FOLDER = "data_captures"

# Corrigido: 5 minutos
CAPTURE_DURATION_SECONDS = 300


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
                from core.websocket_gateway_dashboard import WebSocketGatewayDashboard as Gateway
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

        except Exception as e:
            if not self.is_cancelled:
                logging.error("Falha na inicialização do motor assíncrono: %s", e)
                self.status_updated.emit(f"Erro Crítico: {str(e)}", 0)

    async def _check_hub_status(self):
        last_state = False

        while not self.is_cancelled:
            await asyncio.sleep(0.1)

            if not self.gateway:
                continue

            current_state = getattr(self.gateway, "is_recording", None)

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

        except Exception as e:
            logging.warning("Erro ao limpar conexões: %s", e)

        finally:
            tasks = [
                task for task in asyncio.all_tasks(self.loop)
                if task is not asyncio.current_task(self.loop)
            ]

            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)
            self.loop.stop()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("BioSignal Capture Platform - Integrated")
        self.resize(1100, 750)

        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #2d3748; }
            QLabel { color: #2d3748; }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: #ffffff;
            }
            QPushButton {
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
        """)

        self.is_recording_fixed = False
        self.is_recording_hub = False
        self.timer_counter = 0
        self.countdown_timer = None

        self.save_ecg_buffer = []
        self.save_hrv_buffer = []

        self.ecg_plot_buffer = []
        self.max_plot_points = 300

        self.current_id = ""
        self.participant_folder = ""
        self.file_prefix = ""

        self.worker = None

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_page_loading()
        self.create_page_form()
        self.create_page_stage_fixed()
        self.create_page_stage_hub()

        self.stacked_widget.setCurrentIndex(0)

        self.start_backend_engine()

    def start_backend_engine(self):
        self.btn_cancel_search.setEnabled(True)

        self.worker = CoreAsyncWorker()
        self.worker.status_updated.connect(self.update_loading_status)
        self.worker.data_emitted.connect(self.process_live_stream)
        self.worker.hub_command.connect(self.handle_hub_remote_trigger)
        self.worker.engine_ready.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.worker.search_stopped.connect(self.handle_post_cancellation)
        self.worker.start()

    def create_page_loading(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        title = QLabel("Iniciando Plataforma...")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e3a8a;")

        self.lbl_loading_status = QLabel("Preparando ambiente assíncrono...")
        self.lbl_loading_status.setStyleSheet("color: #475569; font-size: 14px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(400)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(5)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                background-color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                width: 10px;
            }
        """)

        self.btn_cancel_search = QPushButton("Cancelar Busca")
        self.btn_cancel_search.setFixedWidth(180)
        self.btn_cancel_search.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.btn_cancel_search.clicked.connect(self.abort_loading_pipeline)

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_loading_status, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.btn_cancel_search, alignment=Qt.AlignmentFlag.AlignCenter)

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    def update_loading_status(self, message, percentage):
        self.lbl_loading_status.setText(message)
        self.progress_bar.setValue(percentage)

    def abort_loading_pipeline(self):
        self.btn_cancel_search.setEnabled(False)
        self.lbl_loading_status.setText("Cancelando operações e fechando canais...")

        if self.worker:
            self.worker.cancel_operation()

    def handle_post_cancellation(self):
        if self.stacked_widget.currentIndex() == 0:
            self.lbl_loading_status.setText("Busca encerrada.")
            QMessageBox.information(
                self,
                "Cancelado",
                "A busca pelo dispositivo e a inicialização dos gateways foram interrompidas."
            )

    def create_page_form(self):
        page = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_group = QGroupBox("Identificação do Participante e Triagem")
        form_group.setFixedWidth(480)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(20, 20, 20, 20)

        self.input_name = QLineEdit()
        self.input_age = QLineEdit()

        self.input_gender = QComboBox()
        self.input_gender.addItems(["Não Informado", "Masculino", "Feminino"])

        self.input_caffeine = QComboBox()
        self.input_caffeine.addItems(["Não", "Sim"])

        self.input_sleep = QLineEdit()
        self.input_obs = QLineEdit()

        form_layout.addRow("Nome Completo:", self.input_name)
        form_layout.addRow("Idade:", self.input_age)
        form_layout.addRow("Gênero:", self.input_gender)
        form_layout.addRow("Cafeína (< 6h):", self.input_caffeine)
        form_layout.addRow("Horas de Sono:", self.input_sleep)
        form_layout.addRow("Observações:", self.input_obs)

        form_group.setLayout(form_layout)

        btn_next = QPushButton("Avançar para Etapa de 5 Minutos")
        btn_next.setStyleSheet("background-color: #2563eb; color: white; padding: 10px 20px;")
        btn_next.clicked.connect(self.validate_and_go_fixed)

        main_layout.addWidget(form_group)
        main_layout.addWidget(btn_next, alignment=Qt.AlignmentFlag.AlignCenter)

        page.setLayout(main_layout)
        self.stacked_widget.addWidget(page)

    def validate_and_go_fixed(self):
        if not self.input_name.text().strip():
            QMessageBox.warning(self, "Aviso", "Por favor, insira o nome do participante.")
            return

        self.current_id = str(uuid.uuid4())[:8].upper()
        self.stacked_widget.setCurrentIndex(2)

    def create_page_stage_fixed(self):
        page = QWidget()
        layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("<b>ETAPA 1: Gravação Estática - 5 minutos</b>"))

        self.lbl_timer_fixed = QLabel("05:00")
        self.lbl_timer_fixed.setStyleSheet("font-size: 32px; font-weight: bold; color: #1e3a8a;")
        left_panel.addWidget(self.lbl_timer_fixed)

        self.btn_start_fixed = QPushButton("Iniciar 5 Minutos")
        self.btn_start_fixed.setStyleSheet("background-color: #10b981; color: white; padding: 10px;")
        self.btn_start_fixed.clicked.connect(self.start_fixed_recording)
        left_panel.addWidget(self.btn_start_fixed)

        btn_skip = QPushButton("Pular esta etapa ➔")
        btn_skip.setStyleSheet("background-color: #64748b; color: white;")
        btn_skip.clicked.connect(self.go_to_hub_stage)
        left_panel.addWidget(btn_skip)

        left_panel.addStretch()

        self.ecg_widget_fixed = pg.PlotWidget(title="ECG Bruto em Tempo Real")
        self.ecg_widget_fixed.setBackground("#ffffff")
        self.ecg_curve_fixed = self.ecg_widget_fixed.plot(
            pen=pg.mkPen("#ef4444", width=1.5)
        )

        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setFixedWidth(260)

        layout.addWidget(left_container)
        layout.addWidget(self.ecg_widget_fixed)

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    def start_fixed_recording(self):
        if self.is_recording_fixed:
            return

        self.is_recording_fixed = True
        self.btn_start_fixed.setEnabled(False)

        self.prepare_storage_paths("Etapa_Fixa_5min")

        self.timer_counter = CAPTURE_DURATION_SECONDS
        self.lbl_timer_fixed.setText("05:00")

        if self.countdown_timer:
            self.countdown_timer.stop()
            self.countdown_timer.deleteLater()

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.handle_fixed_countdown)
        self.countdown_timer.start(1000)

    def handle_fixed_countdown(self):
        if self.timer_counter > 0:
            self.timer_counter -= 1

            minutes = self.timer_counter // 60
            seconds = self.timer_counter % 60

            self.lbl_timer_fixed.setText(f"{minutes:02d}:{seconds:02d}")
            return

        self.stop_fixed_recording(auto_advance=True)

    def stop_fixed_recording(self, auto_advance=False):
        if self.countdown_timer:
            self.countdown_timer.stop()
            self.countdown_timer.deleteLater()
            self.countdown_timer = None

        if self.is_recording_fixed:
            self.is_recording_fixed = False
            self.finalize_npy_save()

        self.lbl_timer_fixed.setText("05:00")
        self.btn_start_fixed.setEnabled(True)

        if auto_advance:
            QMessageBox.information(
                self,
                "Concluído",
                "Gravação estática de 5 minutos finalizada!"
            )
            self.go_to_hub_stage()

    def go_to_hub_stage(self):
        if self.is_recording_fixed:
            self.stop_fixed_recording(auto_advance=False)

        # Importante:
        # Aqui NÃO chamamos:
        # - self.worker.cancel_operation()
        # - gateway.stop()
        # - polar.disconnect()
        #
        # Assim o WebSocket continua ativo para a etapa controlada pelo Hub.
        self.stacked_widget.setCurrentIndex(3)

    def create_page_stage_hub(self):
        page = QWidget()
        layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("<b>ETAPA 2: Controle via Hub</b>"))

        self.lbl_hub_status = QLabel("AGUARDANDO COMANDO DO HUB...")
        self.lbl_hub_status.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #475569;
            padding: 8px;
            background-color: #e2e8f0;
            border-radius: 4px;
        """)
        left_panel.addWidget(self.lbl_hub_status)

        self.lbl_recording_indicator = QLabel("● GRAVANDO NO DISCO")
        self.lbl_recording_indicator.setStyleSheet(
            "color: #ef4444; font-weight: bold; font-size: 14px;"
        )
        self.lbl_recording_indicator.setVisible(False)
        left_panel.addWidget(self.lbl_recording_indicator)

        btn_finish = QPushButton("Finalizar Sessão Geral")
        btn_finish.setStyleSheet("background-color: #1e3a8a; color: white; margin-top: 20px;")
        btn_finish.clicked.connect(self.close_entire_session)
        left_panel.addWidget(btn_finish)

        left_panel.addStretch()

        self.ecg_widget_hub = pg.PlotWidget(
            title="ECG Bruto em Tempo Real - Monitoramento Remoto"
        )
        self.ecg_widget_hub.setBackground("#ffffff")
        self.ecg_curve_hub = self.ecg_widget_hub.plot(
            pen=pg.mkPen("#ef4444", width=1.5)
        )

        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setFixedWidth(260)

        layout.addWidget(left_container)
        layout.addWidget(self.ecg_widget_hub)

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    def handle_hub_remote_trigger(self, command):
        if command == "START" and not self.is_recording_hub:
            self.is_recording_hub = True

            self.lbl_hub_status.setText("GRAVAÇÃO INICIADA PELO HUB")
            self.lbl_hub_status.setStyleSheet("""
                font-size: 12px;
                font-weight: bold;
                color: white;
                padding: 8px;
                background-color: #b91c1c;
                border-radius: 4px;
            """)
            self.lbl_recording_indicator.setVisible(True)

            self.prepare_storage_paths("Etapa_Sincronizada_Hub")

        elif command == "STOP" and self.is_recording_hub:
            self.is_recording_hub = False

            self.lbl_hub_status.setText("GRAVAÇÃO FINALIZADA PELO HUB")
            self.lbl_hub_status.setStyleSheet("""
                font-size: 12px;
                font-weight: bold;
                color: white;
                padding: 8px;
                background-color: #15803d;
                border-radius: 4px;
            """)
            self.lbl_recording_indicator.setVisible(False)

            self.finalize_npy_save()

    def prepare_storage_paths(self, stage_name):
        name_clean = self.input_name.text().strip().replace(" ", "_")

        if not name_clean:
            name_clean = "Participante"

        folder_identity = f"{name_clean}_{self.current_id}"

        self.participant_folder = os.path.join(DATA_ROOT_FOLDER, folder_identity)
        os.makedirs(self.participant_folder, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_prefix = f"{folder_identity}_{stage_name}_{timestamp_str}"

        self.save_ecg_buffer.clear()
        self.save_hrv_buffer.clear()

    def process_live_stream(self, data):
        samples = data.get("samples", [])
        metrics = data.get("metrics", {})
        ts = data.get("timestamp", datetime.now().timestamp())

        for val in samples:
            self.ecg_plot_buffer.append(val)

            if self.is_recording_fixed or self.is_recording_hub:
                self.save_ecg_buffer.append([ts, val])

        if len(self.ecg_plot_buffer) > self.max_plot_points:
            self.ecg_plot_buffer = self.ecg_plot_buffer[-self.max_plot_points:]

        current_idx = self.stacked_widget.currentIndex()

        if current_idx == 2:
            self.ecg_curve_fixed.setData(self.ecg_plot_buffer)
        elif current_idx == 3:
            self.ecg_curve_hub.setData(self.ecg_plot_buffer)

        if metrics and (self.is_recording_fixed or self.is_recording_hub):
            rr_val = metrics.get("rr")

            if rr_val is not None:
                self.save_hrv_buffer.append([
                    ts,
                    float(rr_val),
                    metrics.get("hr", 0)
                ])

    def finalize_npy_save(self):
        if not self.participant_folder or not self.file_prefix:
            return

        if self.save_ecg_buffer:
            ecg_array = np.array(self.save_ecg_buffer, dtype=np.float64)
            np.save(
                os.path.join(self.participant_folder, f"{self.file_prefix}_ecg.npy"),
                ecg_array
            )

        if self.save_hrv_buffer:
            hrv_array = np.array(self.save_hrv_buffer, dtype=np.float64)
            np.save(
                os.path.join(self.participant_folder, f"{self.file_prefix}_hrv.npy"),
                hrv_array
            )

        self.save_ecg_buffer.clear()
        self.save_hrv_buffer.clear()

    def close_entire_session(self):
        if self.is_recording_fixed:
            self.stop_fixed_recording(auto_advance=False)

        if self.is_recording_hub:
            self.handle_hub_remote_trigger("STOP")

        self.input_name.clear()
        self.input_age.clear()
        self.input_sleep.clear()
        self.input_obs.clear()

        self.lbl_hub_status.setText("AGUARDANDO COMANDO DO HUB...")
        self.lbl_hub_status.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #475569;
            padding: 8px;
            background-color: #e2e8f0;
            border-radius: 4px;
        """)
        self.lbl_recording_indicator.setVisible(False)

        self.stacked_widget.setCurrentIndex(1)

    def closeEvent(self, event):
        if self.is_recording_fixed:
            self.stop_fixed_recording(auto_advance=False)

        if self.is_recording_hub:
            self.handle_hub_remote_trigger("STOP")

        if self.worker:
            self.worker.cancel_operation()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())