from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import pyqtgraph as pg


class FixedStagePage(QWidget):
    start_requested = pyqtSignal()
    skip_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.lbl_timer = QLabel("05:00")

        self.btn_start = QPushButton("Iniciar 5 Minutos")
        self.btn_skip = QPushButton("Pular esta etapa ➔")

        self.ecg_widget = pg.PlotWidget(title="ECG Bruto em Tempo Real")
        self.ecg_curve = None

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout()

        left_panel = QVBoxLayout()

        left_panel.addWidget(QLabel("<b>ETAPA 1: Gravação Estática - 5 minutos</b>"))

        self.lbl_timer.setStyleSheet(
            "font-size: 32px; font-weight: bold; color: #1e3a8a;"
        )
        left_panel.addWidget(self.lbl_timer)

        self.btn_start.setStyleSheet("background-color: #10b981; color: white; padding: 10px;")
        self.btn_start.clicked.connect(self.start_requested.emit)
        left_panel.addWidget(self.btn_start)

        self.btn_skip.setStyleSheet("background-color: #64748b; color: white;")
        self.btn_skip.clicked.connect(self.skip_requested.emit)
        left_panel.addWidget(self.btn_skip)

        left_panel.addStretch()

        self.ecg_widget.setBackground("#ffffff")
        self.ecg_curve = self.ecg_widget.plot(
            pen=pg.mkPen("#ef4444", width=1.5)
        )

        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setFixedWidth(260)

        layout.addWidget(left_container)
        layout.addWidget(self.ecg_widget)

        self.setLayout(layout)

    def set_timer_text(self, text):
        self.lbl_timer.setText(text)

    def set_start_enabled(self, enabled):
        self.btn_start.setEnabled(enabled)

    def update_plot(self, values):
        self.ecg_curve.setData(values)