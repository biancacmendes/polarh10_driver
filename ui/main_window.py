import logging
import uuid
from datetime import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from app.async_worker import CoreAsyncWorker
from app.constants import (
    CAPTURE_DURATION_SECONDS,
    LOG_FORMAT,
    MAX_PLOT_POINTS,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from app.hub_launcher import HubLauncher, HubLauncherWorker
from app.session_controller import SessionController
from app.storage_manager import StorageManager

from ui.pages.loading_page import LoadingPage
from ui.pages.hub_boot_page import HubBootPage
from ui.pages.participant_page import ParticipantPage
from ui.pages.fixed_stage_page import FixedStagePage
from ui.pages.hub_stage_page import HubStagePage


logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class MainWindow(QMainWindow):
    PAGE_LOADING = 0
    PAGE_HUB_BOOT = 1
    PAGE_FORM = 2
    PAGE_FIXED = 3
    PAGE_HUB = 4

    def __init__(self):
        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self._apply_style()

        self.session = SessionController()
        self.storage = StorageManager()
        self.hub_launcher = HubLauncher()
        self.hub_launcher_worker = None

        self.worker = None

        self.current_id = ""

        self.timer_counter = 0
        self.countdown_timer = None

        self.ecg_plot_buffer = []

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.loading_page = LoadingPage()
        self.hub_boot_page = HubBootPage()
        self.participant_page = ParticipantPage()
        self.fixed_stage_page = FixedStagePage()
        self.hub_stage_page = HubStagePage()

        self._setup_pages()
        self._connect_ui_signals()

        self.stacked_widget.setCurrentIndex(self.PAGE_LOADING)

        self.start_backend_engine()

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }

            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                color: #2d3748;
            }

            QLabel {
                color: #2d3748;
            }

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

    def _setup_pages(self):
        self.stacked_widget.addWidget(self.loading_page)
        self.stacked_widget.addWidget(self.hub_boot_page)
        self.stacked_widget.addWidget(self.participant_page)
        self.stacked_widget.addWidget(self.fixed_stage_page)
        self.stacked_widget.addWidget(self.hub_stage_page)

    def _connect_ui_signals(self):
        self.loading_page.cancel_requested.connect(self.abort_loading_pipeline)

        self.hub_boot_page.start_hub_requested.connect(self.start_hub_stack)
        self.hub_boot_page.continue_requested.connect(
            lambda: self.stacked_widget.setCurrentIndex(self.PAGE_FORM)
        )

        self.participant_page.next_requested.connect(self.validate_and_go_fixed)

        self.fixed_stage_page.start_requested.connect(self.start_fixed_recording)
        self.fixed_stage_page.skip_requested.connect(self.go_to_hub_stage)

        self.hub_stage_page.finish_requested.connect(self.close_entire_session)

    def start_backend_engine(self):
        self.loading_page.set_cancel_enabled(True)

        self.worker = CoreAsyncWorker()

        self.worker.status_updated.connect(self.loading_page.update_status)
        self.worker.data_emitted.connect(self.process_live_stream)
        self.worker.hub_command.connect(self.handle_hub_remote_trigger)
        self.worker.engine_ready.connect(
            lambda: self.stacked_widget.setCurrentIndex(self.PAGE_HUB_BOOT)
        )
        self.worker.search_stopped.connect(self.handle_post_cancellation)

        self.worker.start()

    def start_hub_stack(self):
        self.hub_boot_page.set_loading(
            "Preparando inicialização do Biofeedback Hub...",
            5,
        )

        self.hub_launcher_worker = HubLauncherWorker(
            hub_launcher=self.hub_launcher,
            delay_seconds=10,
        )

        self.hub_launcher_worker.status_updated.connect(
            self.hub_boot_page.set_loading
        )

        self.hub_launcher_worker.finished_successfully.connect(
            self.handle_hub_started
        )

        self.hub_launcher_worker.failed.connect(
            self.handle_hub_start_error
        )

        self.hub_launcher_worker.start()

    def handle_hub_started(self):
        self.hub_boot_page.set_started()

    def handle_hub_start_error(self, error_message):
        self.hub_boot_page.set_error(error_message)

        QMessageBox.critical(
            self,
            "Erro ao iniciar HUB",
            f"Não foi possível iniciar o Biofeedback Hub:\n{error_message}",
        )

    def abort_loading_pipeline(self):
        self.loading_page.set_cancel_enabled(False)
        self.loading_page.set_status_text(
            "Cancelando operações e fechando canais..."
        )

        if self.worker:
            self.worker.cancel_operation()

    def handle_post_cancellation(self):
        if self.stacked_widget.currentIndex() == self.PAGE_LOADING:
            self.loading_page.set_status_text("Busca encerrada.")

            QMessageBox.information(
                self,
                "Cancelado",
                "A busca pelo dispositivo e a inicialização dos gateways foram interrompidas.",
            )

    def validate_and_go_fixed(self):
        participant_name = self.participant_page.get_participant_name()

        if not participant_name:
            QMessageBox.warning(
                self,
                "Aviso",
                "Por favor, insira o nome do participante.",
            )
            return

        self.current_id = str(uuid.uuid4())[:8].upper()

        self.stacked_widget.setCurrentIndex(self.PAGE_FIXED)

    def start_fixed_recording(self):
        if self.session.is_recording_fixed:
            return

        self.session.start_fixed()

        self.fixed_stage_page.set_start_enabled(False)

        participant_name = self.participant_page.get_participant_name()

        self.storage.prepare(
            participant_name=participant_name,
            participant_id=self.current_id,
            stage_name="Etapa_Fixa_5min",
        )

        self.timer_counter = CAPTURE_DURATION_SECONDS

        self.fixed_stage_page.set_timer_text("05:00")

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

            self.fixed_stage_page.set_timer_text(
                f"{minutes:02d}:{seconds:02d}"
            )

            return

        self.stop_fixed_recording(auto_advance=True)

    def stop_fixed_recording(self, auto_advance=False):
        if self.countdown_timer:
            self.countdown_timer.stop()
            self.countdown_timer.deleteLater()
            self.countdown_timer = None

        if self.session.is_recording_fixed:
            self.session.stop_fixed()
            self.storage.save()

        self.fixed_stage_page.set_timer_text("05:00")
        self.fixed_stage_page.set_start_enabled(True)

        if auto_advance:
            QMessageBox.information(
                self,
                "Concluído",
                "Gravação estática de 5 minutos finalizada!",
            )

            self.go_to_hub_stage()

    def go_to_hub_stage(self):
        if self.session.is_recording_fixed:
            self.stop_fixed_recording(auto_advance=False)

        self.stacked_widget.setCurrentIndex(self.PAGE_HUB)

    def handle_hub_remote_trigger(self, command):
        if command == "START" and not self.session.is_recording_hub:
            self.session.start_hub()

            self.hub_stage_page.set_recording_started()

            participant_name = self.participant_page.get_participant_name()

            self.storage.prepare(
                participant_name=participant_name,
                participant_id=self.current_id,
                stage_name="Etapa_Sincronizada_Hub",
            )

        elif command == "STOP" and self.session.is_recording_hub:
            self.session.stop_hub()

            self.hub_stage_page.set_recording_stopped()

            self.storage.save()

    def process_live_stream(self, data):
        samples = data.get("samples", [])
        metrics = data.get("metrics", {})
        timestamp = data.get("timestamp", datetime.now().timestamp())

        for value in samples:
            self.ecg_plot_buffer.append(value)

            if self.session.is_any_recording():
                self.storage.add_ecg(timestamp, value)

        if len(self.ecg_plot_buffer) > MAX_PLOT_POINTS:
            self.ecg_plot_buffer = self.ecg_plot_buffer[-MAX_PLOT_POINTS:]

        current_page = self.stacked_widget.currentIndex()

        if current_page == self.PAGE_FIXED:
            self.fixed_stage_page.update_plot(self.ecg_plot_buffer)

        elif current_page == self.PAGE_HUB:
            self.hub_stage_page.update_plot(self.ecg_plot_buffer)

        if metrics and self.session.is_any_recording():
            rr_value = metrics.get("rr")

            if rr_value is not None:
                self.storage.add_hrv(
                    timestamp=timestamp,
                    rr=float(rr_value),
                    hr=metrics.get("hr", 0),
                )

    def close_entire_session(self):
        if self.session.is_recording_fixed:
            self.stop_fixed_recording(auto_advance=False)

        if self.session.is_recording_hub:
            self.handle_hub_remote_trigger("STOP")

        self.participant_page.clear_fields()

        self.hub_stage_page.reset_status()

        self.stacked_widget.setCurrentIndex(self.PAGE_FORM)

    def closeEvent(self, event):
        if self.session.is_recording_fixed:
            self.stop_fixed_recording(auto_advance=False)

        if self.session.is_recording_hub:
            self.handle_hub_remote_trigger("STOP")

        if self.worker:
            self.worker.cancel_operation()

        if self.hub_launcher:
            self.hub_launcher.stop_all()

        event.accept()