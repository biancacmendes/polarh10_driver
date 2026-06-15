from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ParticipantPage(QWidget):
    next_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.input_name = QLineEdit()
        self.input_age = QLineEdit()
        self.input_gender = QComboBox()
        self.input_caffeine = QComboBox()
        self.input_sleep = QLineEdit()
        self.input_obs = QLineEdit()

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_group = QGroupBox("Identificação do Participante e Triagem")
        form_group.setFixedWidth(480)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(20, 20, 20, 20)

        self.input_gender.addItems(["Não Informado", "Masculino", "Feminino"])
        self.input_caffeine.addItems(["Não", "Sim"])

        form_layout.addRow("Nome Completo:", self.input_name)
        form_layout.addRow("Idade:", self.input_age)
        form_layout.addRow("Gênero:", self.input_gender)
        form_layout.addRow("Cafeína (< 6h):", self.input_caffeine)
        form_layout.addRow("Horas de Sono:", self.input_sleep)
        form_layout.addRow("Observações:", self.input_obs)

        form_group.setLayout(form_layout)

        btn_next = QPushButton("Avançar para Etapa de 5 Minutos")
        btn_next.setStyleSheet("background-color: #2563eb; color: white; padding: 10px 20px;")
        btn_next.clicked.connect(self.next_requested.emit)

        main_layout.addWidget(form_group)
        main_layout.addWidget(btn_next, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)

    def get_participant_name(self):
        return self.input_name.text().strip()

    def clear_fields(self):
        self.input_name.clear()
        self.input_age.clear()
        self.input_sleep.clear()
        self.input_obs.clear()

        self.input_gender.setCurrentIndex(0)
        self.input_caffeine.setCurrentIndex(0)