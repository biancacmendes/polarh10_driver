from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class HubBootPage(QWidget):
    start_hub_requested = pyqtSignal()
    continue_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.lbl_status = QLabel(
            "Cinta Polar H10 conectada com sucesso.\n"
            "Agora você pode subir o Biofeedback Hub."
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(420)
        self.progress_bar.setVisible(False)

        self.btn_start_hub = QPushButton("Subir Biofeedback Hub")
        self.btn_continue = QPushButton("Continuar para Cadastro do Participante")
        self.btn_continue.setEnabled(False)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("Sistema Polar Online")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #1e3a8a;"
        )

        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 15px; color: #475569;")

        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                background-color: #ffffff;
            }

            QProgressBar::chunk {
                background-color: #10b981;
                width: 10px;
            }
        """)

        self.btn_start_hub.setFixedWidth(280)
        self.btn_start_hub.setStyleSheet(
            "background-color: #10b981; color: white; padding: 12px;"
        )
        self.btn_start_hub.clicked.connect(self.start_hub_requested.emit)

        self.btn_continue.setFixedWidth(320)
        self.btn_continue.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 12px;"
        )
        self.btn_continue.clicked.connect(self.continue_requested.emit)

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.btn_start_hub, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.btn_continue, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def set_loading(self, message, percentage):
        self.lbl_status.setText(message)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percentage)
        self.btn_start_hub.setEnabled(False)
        self.btn_continue.setEnabled(False)

    def set_started(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(100)

        self.lbl_status.setText(
            "Biofeedback Hub iniciado com sucesso.\n"
            "Dashboard disponível em:\n"
            "http://127.0.0.1:5173"
        )

        self.btn_start_hub.setEnabled(False)
        self.btn_start_hub.setText("Hub iniciado")
        self.btn_continue.setEnabled(True)

    def set_error(self, message):
        self.progress_bar.setVisible(False)

        self.lbl_status.setText(
            "Erro ao iniciar o Biofeedback Hub.\n"
            f"{message}"
        )

        self.btn_start_hub.setEnabled(True)
        self.btn_continue.setEnabled(False)