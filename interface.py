import asyncio
import csv
from datetime import datetime
import json
import os
import sys
import threading
import uuid
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
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
)
import pyqtgraph as pg
import websockets

# --- CONFIGURAÇÕES DO SISTEMA ---
WEBSOCKET_URL = "ws://localhost:8765/stream"
DATA_ROOT_FOLDER = "data_captures"
CAPTURE_DURATION_SECONDS = 600  # 10 minutos


class WebSocketWorker(QObject):
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.is_running = False
        self.loop = None

    def start_collection(self):
        self.is_running = True
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._listen())

    async def _listen(self):
        try:
            async with websockets.connect(self.url) as ws:
                self.connection_status.emit(True)
                while self.is_running:
                    try:
                        message = await ws.recv()
                        data = json.loads(message)
                        self.data_received.emit(data)
                    except websockets.exceptions.ConnectionClosed:
                        self.connection_status.emit(False)
                        break
        except Exception as e:
            print(f"Erro de conexão: {e}")
            self.connection_status.emit(False)

    def stop_collection(self):
        self.is_running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BioSignal Capture Platform")
        self.resize(1020, 720)

        # Configuração do Tema Light Global
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
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3b82f6; }
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #e2e8f0; 
                border-radius: 6px; 
                margin-top: 12px; 
                padding-top: 16px;
                background-color: #ffffff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QPushButton { 
                border-radius: 4px; 
                font-weight: bold; 
                padding: 8px 16px; 
            }
        """)

        self.worker = None
        self.is_recording = False
        self.timer_counter = 0
        self.qt_timer = None

        # Estado dos arquivos e identificadores
        self.ecg_file = None
        self.hrv_file = None
        self.ecg_writer = None
        self.hrv_writer = None
        self.participant_folder = ""
        self.file_prefix = ""
        self.current_id = ""
        
        # Buffers dos gráficos
        self.ecg_data_buffer = []
        self.hrv_data_buffer = []
        self.max_plot_points = 300

        # Gerenciador de telas empilhadas
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_page_welcome()
        self.create_page_form()
        self.create_page_dashboard()

        # Inicia na tela de capa
        self.stacked_widget.setCurrentIndex(0)

    # --- TELA 1: CAPA ---
    def create_page_welcome(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("BioSignal Capture Platform")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e3a8a;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Módulo de Aquisição de ECG & Variabilidade da Frequência Cardíaca (HRV)")
        subtitle.setStyleSheet("font-size: 14px; color: #64748b;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_next = QPushButton("Avançar para Identificação")
        btn_next.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; font-size: 14px; padding: 12px 24px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_next.setFixedWidth(240)
        btn_next.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(btn_next, alignment=Qt.AlignmentFlag.AlignCenter)
        
        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    # --- TELA 2: FORMULÁRIO ---
    def create_page_form(self):
        page = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_group = QGroupBox("Identificação do Participante e Triagem")
        form_group.setFixedWidth(480)
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setContentsMargins(20, 20, 20, 20)

        self.input_name = QLineEdit()
        self.input_age = QLineEdit()
        self.input_gender = QComboBox()
        self.input_gender.addItems(["Não Informado", "Masculino", "Feminino"])

        self.input_caffeine = QComboBox()
        self.input_caffeine.addItems(["Não", "Sim"])

        self.input_sleep = QLineEdit()
        self.input_sleep.setPlaceholderText("Ex: 7h ou Regular")

        self.input_obs = QLineEdit()
        self.input_obs.setPlaceholderText("Anotações ou condições clínicas")

        form_layout.addRow("Nome Completo:", self.input_name)
        form_layout.addRow("Idade:", self.input_age)
        form_layout.addRow("Gênero:", self.input_gender)
        form_layout.addRow("Cafeína (< 6h):", self.input_caffeine)
        form_layout.addRow("Horas de Sono:", self.input_sleep)
        form_layout.addRow("Observações:", self.input_obs)
        form_group.setLayout(form_layout)

        # Botões de Navegação
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        btn_back = QPushButton("Voltar")
        btn_back.setStyleSheet("""
            QPushButton { background-color: #e2e8f0; color: #475569; }
            QPushButton:hover { background-color: #cbd5e1; }
        """)
        btn_back.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        btn_next = QPushButton("Avançar para Dashboard")
        btn_next.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_next.clicked.connect(self.validate_and_go_to_dashboard)

        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(btn_next)

        main_layout.addWidget(form_group)
        main_layout.addSpacing(10)
        main_layout.addLayout(btn_layout)

        page.setLayout(main_layout)
        self.stacked_widget.addWidget(page)

    def validate_and_go_to_dashboard(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Aviso", "Por favor, insira o nome do participante antes de prosseguir.")
            return
        
        # Gera o ID único de 8 caracteres para esta sessão do participante
        self.current_id = str(uuid.uuid4())[:8].upper()
        
        # Atualiza o painel de resumo estático na dashboard antes de mudar de tela
        self.lbl_summary_name.setText(f"Paciente: {name} (ID: {self.current_id})")
        self.lbl_summary_meta.setText(
            f"Idade: {self.input_age.text().strip()} | "
            f"Cafeína (<6h): {self.input_caffeine.currentText()} | "
            f"Sono: {self.input_sleep.text().strip()}"
        )
        self.stacked_widget.setCurrentIndex(2)

    # --- TELA 3: DASHBOARD ---
    def create_page_dashboard(self):
        page = QWidget()
        main_layout = QHBoxLayout()

        # Painel Lateral Esquerdo: Cronômetro e Informações Atuais
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # Caixa do Cronômetro
        timer_group = QGroupBox("Tempo de Sessão")
        timer_layout = QVBoxLayout()
        timer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer = QLabel("10:00")
        self.lbl_timer.setStyleSheet("font-size: 36px; font-weight: bold; color: #1e3a8a; padding: 10px;")
        timer_layout.addWidget(self.lbl_timer)
        timer_group.setLayout(timer_layout)
        left_panel.addWidget(timer_group)

        # Caixa de Resumo do Paciente Atual (Visão fixa na Dashboard)
        info_group = QGroupBox("Sessão Atual")
        info_layout = QVBoxLayout()
        self.lbl_summary_name = QLabel("Paciente: -")
        self.lbl_summary_name.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.lbl_summary_meta = QLabel("Idade: - | Cafeína: - | Sono: -")
        self.lbl_summary_meta.setStyleSheet("color: #475569; font-size: 12px;")
        
        info_layout.addWidget(self.lbl_summary_name)
        info_layout.addWidget(self.lbl_summary_meta)
        info_group.setLayout(info_layout)
        left_panel.addWidget(info_group)

        # Botões de Ação
        self.btn_action = QPushButton("Iniciar Gravação")
        self.btn_action.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-size: 14px; padding: 12px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_action.clicked.connect(self.toggle_recording)
        left_panel.addWidget(self.btn_action)

        self.btn_abort = QPushButton("Voltar / Trocar Paciente")
        self.btn_abort.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; padding: 8px; }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_abort.clicked.connect(self.abort_or_go_back)
        left_panel.addWidget(self.btn_abort)

        left_panel.addStretch()

        # Painel Direito: Gráficos com Light Theme
        right_panel = QVBoxLayout()
        
        # Gráfico ECG
        self.ecg_plot_widget = pg.PlotWidget(title="Eletrocardiograma Bruto (ECG)")
        self.ecg_plot_widget.setBackground("#ffffff")
        self.ecg_plot_widget.showGrid(x=True, y=True, alpha=1.0)
        self.ecg_plot_widget.getAxis('bottom').setPen('#475569')
        self.ecg_plot_widget.getAxis('left').setPen('#475569')
        self.ecg_plot_widget.getAxis('bottom').setTextPen('#475569')
        self.ecg_plot_widget.getAxis('left').setTextPen('#475569')
        self.ecg_plot_curve = self.ecg_plot_widget.plot(pen=pg.mkPen("#ef4444", width=1.5))
        right_panel.addWidget(self.ecg_plot_widget)

        # Gráfico HRV
        self.hrv_plot_widget = pg.PlotWidget(title="Série Temporal de Intervalos RR (Tacograma)")
        self.hrv_plot_widget.setBackground("#ffffff")
        self.hrv_plot_widget.showGrid(x=True, y=True, alpha=1.0)
        self.hrv_plot_widget.getAxis('bottom').setPen('#475569')
        self.hrv_plot_widget.getAxis('left').setPen('#475569')
        self.hrv_plot_widget.getAxis('bottom').setTextPen('#475569')
        self.hrv_plot_widget.getAxis('left').setTextPen('#475569')
        self.hrv_plot_curve = self.hrv_plot_widget.plot(
            pen=pg.mkPen("#2563eb", width=1.5), symbol="o", symbolSize=5, symbolBrush="#2563eb"
        )
        right_panel.addWidget(self.hrv_plot_widget)

        # Junção estrutural dos containers
        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setFixedWidth(280)

        right_container = QWidget()
        right_container.setLayout(right_panel)

        main_layout.addWidget(left_container)
        main_layout.addWidget(right_container)

        page.setLayout(main_layout)
        self.stacked_widget.addWidget(page)

    def toggle_recording(self):
        if not self.is_recording:
            self.start_experiment()
        else:
            self.stop_experiment(completed=False)

    def start_experiment(self):
        name_clean = self.input_name.text().strip().replace(" ", "_")
        
        # Nova notação de pasta de alto nível: Nome_ID
        folder_identity = f"{name_clean}_{self.current_id}"
        self.participant_folder = os.path.join(DATA_ROOT_FOLDER, folder_identity)
        os.makedirs(self.participant_folder, exist_ok=True)
        
        # Prefixo temporal nos arquivos internos da pasta do indivíduo
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_prefix = f"{folder_identity}_{timestamp_str}"

        self.setup_csv_files()

        self.is_recording = True
        self.btn_action.setText("Interromper Captura")
        self.btn_action.setStyleSheet("""
            QPushButton { background-color: #ea580c; color: white; font-size: 14px; padding: 12px; }
            QPushButton:hover { background-color: #c2410c; }
        """)
        self.btn_abort.setEnabled(False)

        self.timer_counter = CAPTURE_DURATION_SECONDS
        self.update_timer_label()
        self.qt_timer = self.startTimer(1000)

        self.worker = WebSocketWorker(WEBSOCKET_URL)
        self.worker.data_received.connect(self.process_incoming_data)
        self.worker.start_collection()

    def setup_csv_files(self):
        ecg_path = os.path.join(self.participant_folder, f"{self.file_prefix}_raw_ecg.csv")
        hrv_path = os.path.join(self.participant_folder, f"{self.file_prefix}_metrics_hrv.csv")
        metadata_path = os.path.join(self.participant_folder, f"{self.file_prefix}_metadata.txt")

        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(f"Sessão ID: {self.current_id}\n")
            f.write(f"Data/Hora de Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Nome: {self.input_name.text().strip()}\n")
            f.write(f"Idade: {self.input_age.text().strip()}\n")
            f.write(f"Gênero: {self.input_gender.currentText()}\n")
            f.write(f"Uso de Cafeína (<6h): {self.input_caffeine.currentText()}\n")
            f.write(f"Horas de Sono: {self.input_sleep.text().strip()}\n")
            f.write(f"Observações: {self.input_obs.text().strip()}\n")

        self.ecg_file = open(ecg_path, "w", newline="", encoding="utf-8")
        self.ecg_writer = csv.writer(self.ecg_file)
        self.ecg_writer.writerow(["timestamp", "seq", "sample_index", "ecg_value"])

        self.hrv_file = open(hrv_path, "w", newline="", encoding="utf-8")
        self.hrv_writer = csv.writer(self.hrv_file)
        self.hrv_writer.writerow(["timestamp", "seq", "rr", "hr", "rmssd", "sdnn", "pnn50", "lf_hf"])

    def process_incoming_data(self, data):
        ts = datetime.now().timestamp()
        seq = data.get("seq", 0)
        samples = data.get("samples", [])
        metrics = data.get("metrics", {})

        for i, val in enumerate(samples):
            if self.ecg_writer:
                self.ecg_writer.writerow([ts, seq, i, val])
            self.ecg_data_buffer.append(val)

        if len(self.ecg_data_buffer) > self.max_plot_points:
            self.ecg_data_buffer = self.ecg_data_buffer[-self.max_plot_points:]
        self.ecg_plot_curve.setData(self.ecg_data_buffer)

        if metrics:
            rr_val = metrics.get("rr")
            if self.hrv_writer:
                self.hrv_writer.writerow([
                    ts, seq, rr_val, metrics.get("hr"), metrics.get("rmssd"),
                    metrics.get("sdnn"), metrics.get("pnn50"), metrics.get("lf_hf")
                ])

            if rr_val is not None:
                self.hrv_data_buffer.append(float(rr_val))
                if len(self.hrv_data_buffer) > 50:
                    self.hrv_data_buffer.pop(0)
                self.hrv_plot_curve.setData(self.hrv_data_buffer)

    def timerEvent(self, event):
        if self.timer_counter > 0:
            self.timer_counter -= 1
            self.update_timer_label()
        else:
            self.killTimer(self.qt_timer)
            self.stop_experiment(completed=True)

    def update_timer_label(self):
        minutes = self.timer_counter // 60
        seconds = self.timer_counter % 60
        self.lbl_timer.setText(f"{minutes:02d}:{seconds:02d}")

    def stop_experiment(self, completed=True):
        self.is_recording = False
        if self.worker:
            self.worker.stop_collection()

        if hasattr(self, "qt_timer") and self.qt_timer:
            try:
                self.killTimer(self.qt_timer)
            except RuntimeError:
                pass

        if self.ecg_file:
            self.ecg_file.flush()
            self.ecg_file.close()
            self.ecg_file = None
        if self.hrv_file:
            self.hrv_file.flush()
            self.hrv_file.close()
            self.hrv_file = None

        self.btn_action.setText("Iniciar Gravação")
        self.btn_action.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-size: 14px; padding: 12px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_abort.setEnabled(True)
        self.lbl_timer.setText("10:00")

        self.ecg_data_buffer.clear()
        self.hrv_data_buffer.clear()

        if completed:
            QMessageBox.information(
                self, "Sucesso", 
                f"Sessão concluída com sucesso!\nDados salvos em: {self.participant_folder}"
            )
            self.input_name.clear()
            self.input_age.clear()
            self.input_obs.clear()
            self.stacked_widget.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Interrompido", "A captação foi cancelada. Os arquivos parciais de dados foram fechados com segurança.")

    def abort_or_go_back(self):
        if self.is_recording:
            return
        self.stacked_widget.setCurrentIndex(1)

    def closeEvent(self, event):
        if self.is_recording:
            self.stop_experiment(completed=False)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
