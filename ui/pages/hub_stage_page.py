from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import pyqtgraph as pg


class HubStagePage(QWidget):
    finish_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.lbl_hub_status = QLabel("AGUARDANDO COMANDO DO HUB...")
        self.lbl_recording_indicator = QLabel("● GRAVANDO NO DISCO")

        self.btn_finish = QPushButton("Finalizar Sessão Geral")

        self.ecg_widget = pg.PlotWidget(
            title="ECG Bruto em Tempo Real - Monitoramento Remoto"
        )
        self.ecg_curve = None

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout()

        left_panel = QVBoxLayout()

        left_panel.addWidget(QLabel("<b>ETAPA 2: Controle via Hub</b>"))

        self.lbl_hub_status.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #475569;
            padding: 8px;
            background-color: #e2e8f0;
            border-radius: 4px;
        """)
        left_panel.addWidget(self.lbl_hub_status)

        self.lbl_recording_indicator.setStyleSheet(
            "color: #ef4444; font-weight: bold; font-size: 14px;"
        )
        self.lbl_recording_indicator.setVisible(False)
        left_panel.addWidget(self.lbl_recording_indicator)

        self.btn_finish.setStyleSheet(
            "background-color: #1e3a8a; color: white; margin-top: 20px;"
        )
        self.btn_finish.clicked.connect(self.finish_requested.emit)
        left_panel.addWidget(self.btn_finish)

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

    def set_recording_started(self):
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

    def set_recording_stopped(self):
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

    def reset_status(self):
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

    def update_plot(self, values):
        self.ecg_curve.setData(values)