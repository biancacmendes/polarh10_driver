import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import neurokit2 as nk
from pathlib import Path

# CONFIGURAÇÃO DE CAMINHO DINÂMICA
BASE_DIR = Path(os.getcwd())
OUTPUT_DIR = os.path.join(BASE_DIR, "plots_hrv_neurokit")
TABLE_DIR = os.path.join(BASE_DIR, "tables_hrv_neurokit")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TABLE_DIR, exist_ok=True)

FS_ECG = 65.2133  

# Mapeamento estrito para os rótulos acadêmicos das legendas
CONFIG_ETAPAS = {
    "fixa": {"file": "Fixed_Stage", "label": "Fixed Stage"},
    "hub1": {"file": "Synchronized_Hub_1", "label": "Stage 1 (Hub 1)"},
    "hub2": {"file": "Synchronized_Hub_2", "label": "Stage 2 (Hub 2)"}
}

linhas_summary_tabela = []

def configurar_estilo_academico():
    plt.rcParams.update({
        "font.size": 12,
        "font.family": "serif",
        "axes.titlesize": 0,  
        "axes.labelsize": 12,
        "legend.fontsize": 10
    })

def salvar_plot_nativo_nk(metrica_nome, id_paciente, etapa_chave):
    """Captura a figura do NeuroKit, remove títulos internos e injeta a legenda acadêmica unificada"""
    fig = plt.gcf()
    fig.set_size_inches(6.5, 4.2)
    
    label_experimento = f"ID: {id_paciente} | {CONFIG_ETAPAS[etapa_chave]['label']}"
    
    for ax in fig.get_axes():
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, linestyle="--", alpha=0.5)
        
        if hasattr(ax, 'get_title'):
            ax.set_title("") 
            
        # Adiciona a legenda customizada com ID e Stage no canto superior direito de cada subplot
        ax.legend([label_experimento], loc="upper right", frameon=True, facecolor="white", edgecolor="none")
            
    plt.tight_layout()
    
    nome_base = f"{metrica_nome}_{id_paciente}_{CONFIG_ETAPAS[etapa_chave]['file']}"
    plt.savefig(os.path.join(OUTPUT_DIR, f"{nome_base}.pdf"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(OUTPUT_DIR, f"{nome_base}.png"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] Saved NeuroKit plot with academic legend: {nome_base}")

def processar_paciente(pasta_paciente):
    id_paciente = pasta_paciente.name.split("_")[-1]
    arquivos_ecg = sorted(list(pasta_paciente.glob("*_ecg.npy")))
    
    print(f"\nProcessing directory: {pasta_paciente.name} ({len(arquivos_ecg)} files)")
    if not arquivos_ecg: 
        return

    for i, caminho_arquivo in enumerate(arquivos_ecg[:3]):
        try:
            dados = np.load(caminho_arquivo)
            ecg_bruto = dados[:, 1]
            
            limite_inf = np.percentile(ecg_bruto, 0.5)
            limite_sup = np.percentile(ecg_bruto, 99.5)
            ecg_limpo = np.clip(ecg_bruto, limite_inf, limite_sup)
            
            ecg_sinal_clean = nk.ecg_clean(ecg_limpo, sampling_rate=FS_ECG, method="neurokit")
            _, info_picos = nk.ecg_peaks(ecg_sinal_clean, sampling_rate=FS_ECG, method="pantompkins")
            
            picos_r = info_picos["ECG_R_Peaks"]
            if len(picos_r) < 15:
                print(f"   [WARN] Poucos picos detectados em {caminho_arquivo.name}")
                continue
                
            etapa_chave = "fixa" if "Etapa_Fixa" in caminho_arquivo.name else ("hub1" if i == 1 else "hub2")
            
            configurar_estilo_academico()
            
            # Domínio do Tempo com injeção de legenda
            nk.hrv_time(info_picos, sampling_rate=FS_ECG, show=True)
            salvar_plot_nativo_nk("hrv_time", id_paciente, etapa_chave)
            
            # Domínio da Frequência com injeção de legenda
            nk.hrv_frequency(info_picos, sampling_rate=FS_ECG, show=True, normalize=True)
            salvar_plot_nativo_nk("hrv_freq", id_paciente, etapa_chave)
            
            # Métodos Não Lineares com injeção de legenda
            nk.hrv_nonlinear(info_picos, sampling_rate=FS_ECG, show=True)
            salvar_plot_nativo_nk("hrv_nonlinear", id_paciente, etapa_chave)
            
            # Resumo Completo com injeção de legenda
            hrv_indices = nk.hrv(info_picos, sampling_rate=FS_ECG, show=True)
            salvar_plot_nativo_nk("hrv_summary", id_paciente, etapa_chave)
            
            linhas_summary_tabela.append({
                "patient_id": id_paciente,
                "stage": etapa_chave,
                "HR_mean": float(hrv_indices["HRV_MeanNN"].values[0]),
                "SDNN": float(hrv_indices["HRV_SDNN"].values[0]),
                "RMSSD": float(hrv_indices["HRV_RMSSD"].values[0]),
                "LF": float(hrv_indices["HRV_LF"].values[0]),
                "HF": float(hrv_indices["HRV_HF"].values[0]),
                "LFHF": float(hrv_indices["HRV_LFHF"].values[0]),
                "SD1": float(hrv_indices["HRV_SD1"].values[0]),
                "SD2": float(hrv_indices["HRV_SD2"].values[0])
            })
            
        except Exception as e:
            print(f"   [ERROR] No arquivo {caminho_arquivo.name}: {e}")

def gerar_tabela_summary():
    if linhas_summary_tabela:
        print("\n=== GENERATING CONSOLIDATED METRICS TABLE ===")
        df_raw = pd.DataFrame(linhas_summary_tabela)
        
        summary_final = df_raw.groupby("stage").agg({
            "HR_mean": ["mean", "std"],
            "SDNN": ["mean", "std"],
            "RMSSD": ["mean", "std"],
            "LF": ["mean", "std"],
            "HF": ["mean", "std"],
            "LFHF": ["mean", "std"],
            "SD1": ["mean", "std"],
            "SD2": ["mean", "std"]
        }).reset_index()
        
        summary_final.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in summary_final.columns]
        
        path = os.path.join(TABLE_DIR, "summary_neurokit_metrics.csv")
        summary_final.to_csv(path, index=False)
        print(f"[OK] Saved table: {path}")
        print("\n=== FINAL PROTOCOL SUMMARY ===")
        print(summary_final.round(4).to_string(index=False))

def main():
    print("Starting automated directory scan using NeuroKit2 engine...")
    pastas_analisadas = 0

    for subpasta in sorted(BASE_DIR.iterdir()):
        partes_nome = subpasta.name.split("_")
        if subpasta.is_dir() and len(partes_nome) > 1 and len(partes_nome[-1]) == 8:
            processar_paciente(subpasta)
            pastas_analisadas += 1

    if pastas_analisadas == 0:
        print("\n[ERROR] No valid patient data folders detected. Check folder names.")
    else:
        print(f"\nScan completed. Total folders processed: {pastas_analisadas}")
        gerar_tabela_summary()

if __name__ == "__main__":
    main()