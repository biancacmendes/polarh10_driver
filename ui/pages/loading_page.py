from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class LoadingPage(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.lbl_loading_status = QLabel("Preparando ambiente assíncrono...")

        self.progress_bar = QProgressBar()

        self.btn_cancel_search = QPushButton("Cancelar Busca")

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        title = QLabel("Iniciando Plataforma...")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e3a8a;")

        self.lbl_loading_status.setStyleSheet("color: #475569; font-size: 14px;")

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
        self.btn_cancel_search.clicked.connect(self.cancel_requested.emit)

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_loading_status, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.btn_cancel_search, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def update_status(self, message, percentage):
        self.lbl_loading_status.setText(message)
        self.progress_bar.setValue(percentage)

    def set_cancel_enabled(self, enabled):
        self.btn_cancel_search.setEnabled(enabled)

    def set_status_text(self, message):
        self.lbl_loading_status.setText(message)