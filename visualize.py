import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

PATIENT_DIR = Path(
    "/home/mendes/Desktop/bianca/polarh10_driver/data_captures/"
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33"
)

PLOTS_DIR = PATIENT_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

FS_ECG = 130.0  # Hz
HRV_SMOOTH_WINDOW = 30


# ==========================================================
# ARQUIVOS ECG
# ==========================================================

ECG_REPOUSO = PATIENT_DIR / (
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33_"
    "Etapa_Fixa_5min_20260615_162324_ecg.npy"
)

ECG_SYNC_1 = PATIENT_DIR / (
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33_"
    "Etapa_Sincronizada_Hub_20260615_163316_ecg.npy"
)

ECG_SYNC_2 = PATIENT_DIR / (
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33_"
    "Etapa_Sincronizada_Hub_20260615_163947_ecg.npy"
)


# ==========================================================
# ARQUIVOS HRV
# ==========================================================

HRV_REPOUSO = PATIENT_DIR / (
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33_"
    "Etapa_Fixa_5min_20260615_162324_hrv.npy"
)

HRV_SYNC_1 = PATIENT_DIR / (
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33_"
    "Etapa_Sincronizada_Hub_20260615_163316_hrv.npy"
)

HRV_SYNC_2 = PATIENT_DIR / (
    "Nicolas_Christian_de_Souza_Dunhan_9D25FE33_"
    "Etapa_Sincronizada_Hub_20260615_163947_hrv.npy"
)


# ==========================================================
# FUNÇÕES
# ==========================================================

def load_ecg(path, fs=130.0):
    data = np.load(path)

    ecg = data[:, 1]
    time = np.arange(len(ecg)) / fs

    return time, ecg


def load_hrv(path):
    data = np.load(path)

    timestamps = data[:, 0]
    rr = data[:, 1]

    time = timestamps - timestamps[0]

    return time, rr


def save_pdf(fig, filename):
    output_path = PLOTS_DIR / filename
    fig.savefig(output_path, format="pdf", bbox_inches="tight")
    print(f"Salvo em: {output_path}")


# ==========================================================
# CARREGAMENTO ECG
# ==========================================================

ecg_data = {
    "Repouso 5 min": {
        "path": ECG_REPOUSO,
        "color": "green",
    },
    "Sincronizada 1": {
        "path": ECG_SYNC_1,
        "color": "blue",
    },
    "Sincronizada 2": {
        "path": ECG_SYNC_2,
        "color": "red",
    },
}

for name, item in ecg_data.items():
    t, ecg = load_ecg(item["path"], FS_ECG)
    item["time"] = t
    item["ecg"] = ecg

    print(f"{name}: {len(ecg)} amostras | duração: {t[-1]:.2f} s")


# ==========================================================
# 1) ECG BRUTO SOBREPOSTO
# ==========================================================

fig = plt.figure(figsize=(18, 6))

for name, item in ecg_data.items():
    plt.plot(
        item["time"],
        item["ecg"],
        color=item["color"],
        linewidth=0.8,
        alpha=0.8,
        label=name,
    )

plt.title("ECG bruto sobreposto")
plt.xlabel("Tempo (s)")
plt.ylabel("Amplitude ECG")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend()

plt.tight_layout()
save_pdf(fig, "ecg_bruto_sobreposto.pdf")
plt.close(fig)


# ==========================================================
# 2) ECG EM 3 SUBFIGURAS COM MESMA ESCALA
# ==========================================================

max_time = max(item["time"][-1] for item in ecg_data.values())

all_ecg_values = np.concatenate([
    item["ecg"] for item in ecg_data.values()
])

y_min = np.min(all_ecg_values)
y_max = np.max(all_ecg_values)

margin = 0.05 * (y_max - y_min)
y_min -= margin
y_max += margin

fig, axes = plt.subplots(
    3,
    1,
    figsize=(18, 10),
    sharex=True,
    sharey=True,
)

for ax, (name, item) in zip(axes, ecg_data.items()):
    ax.plot(
        item["time"],
        item["ecg"],
        color=item["color"],
        linewidth=0.8,
        label=name,
    )

    ax.set_title(name)
    ax.set_ylabel("Amplitude ECG")
    ax.set_xlim(0, max_time)
    ax.set_ylim(y_min, y_max)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")

axes[-1].set_xlabel("Tempo (s)")

fig.suptitle("ECG bruto por etapa - mesma escala temporal e mesma escala de amplitude")
plt.tight_layout()
save_pdf(fig, "ecg_bruto_3_subfiguras_mesma_escala.pdf")
plt.close(fig)


# ==========================================================
# CARREGAMENTO HRV
# ==========================================================

hrv_data = {
    "Repouso 5 min": {
        "path": HRV_REPOUSO,
        "color": "green",
    },
    "Sincronizada 1": {
        "path": HRV_SYNC_1,
        "color": "blue",
    },
    "Sincronizada 2": {
        "path": HRV_SYNC_2,
        "color": "red",
    },
}

for name, item in hrv_data.items():
    t, rr = load_hrv(item["path"])

    rr_filt = uniform_filter1d(rr, size=HRV_SMOOTH_WINDOW)

    item["time"] = t
    item["rr"] = rr
    item["rr_filt"] = rr_filt

    print(f"{name}: {len(rr)} RR intervals | duração: {t[-1]:.2f} s")


# ==========================================================
# 3) HRV SOBREPOSTO COM CURVAS FILTRADAS
# ==========================================================

fig = plt.figure(figsize=(18, 8))

for name, item in hrv_data.items():
    plt.plot(
        item["time"],
        item["rr"],
        color=item["color"],
        alpha=0.18,
        linewidth=1,
    )

for name, item in hrv_data.items():
    plt.plot(
        item["time"],
        item["rr_filt"],
        color=item["color"],
        linewidth=3,
        label=f"{name} filtrado",
    )

plt.title("HRV sobreposto - RR intervals suavizados")
plt.xlabel("Tempo (s)")
plt.ylabel("RR Interval (ms)")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend()

plt.tight_layout()
save_pdf(fig, "hrv_sobreposto_filtrado.pdf")
plt.close(fig)


print("\nFinalizado.")
print(f"Gráficos salvos em: {PLOTS_DIR}")