import os
from datetime import datetime

import numpy as np

from app.constants import DATA_ROOT_FOLDER


class StorageManager:
    def __init__(self):
        self.participant_folder = ""
        self.file_prefix = ""

        self.ecg_buffer = []
        self.hrv_buffer = []

    def prepare(self, participant_name, participant_id, stage_name):
        name_clean = participant_name.strip().replace(" ", "_")

        if not name_clean:
            name_clean = "Participante"

        folder_identity = f"{name_clean}_{participant_id}"

        self.participant_folder = os.path.join(
            DATA_ROOT_FOLDER,
            folder_identity,
        )

        os.makedirs(self.participant_folder, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.file_prefix = f"{folder_identity}_{stage_name}_{timestamp_str}"

        self.ecg_buffer.clear()
        self.hrv_buffer.clear()

    def add_ecg(self, timestamp, value):
        self.ecg_buffer.append([timestamp, value])

    def add_hrv(self, timestamp, rr, hr):
        self.hrv_buffer.append([timestamp, float(rr), hr])

    def save(self):
        if not self.participant_folder or not self.file_prefix:
            return

        if self.ecg_buffer:
            ecg_array = np.array(self.ecg_buffer, dtype=np.float64)

            np.save(
                os.path.join(
                    self.participant_folder,
                    f"{self.file_prefix}_ecg.npy",
                ),
                ecg_array,
            )

        if self.hrv_buffer:
            hrv_array = np.array(self.hrv_buffer, dtype=np.float64)

            np.save(
                os.path.join(
                    self.participant_folder,
                    f"{self.file_prefix}_hrv.npy",
                ),
                hrv_array,
            )

        self.ecg_buffer.clear()
        self.hrv_buffer.clear()