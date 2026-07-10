import numpy as np
import matplotlib.pyplot as plt
import neurokit2 as nk
from pathlib import Path

# Configurações básicas
BASE_DIR = Path.home() / "Desktop" / "bianca" / "polarh10_driver" / "data_captures"
FS = 65.2133  # Frequência de amostragem real calculada

# Criação das pastas de saída para os plots
OUTPUT_PT = BASE_DIR / "plots_pt"
OUTPUT_EN = BASE_DIR / "plots_en"
OUTPUT_PT.mkdir(exist_ok=True)
OUTPUT_EN.mkdir(exist_ok=True)

# Cores para o design clássico de papel de ECG
ECG_RED = "#d62728"
GRID_MAJOR = "#fbc4c4"
GRID_MINOR = "#ffe4e4"

def processar_e_plotar(pasta_paciente):
    # Extrai apenas o ID final do paciente (ex: DDA59F3E) para anonimato
    id_paciente = pasta_paciente.name.split("_")[-1]
    
    arquivos_ecg = sorted(list(pasta_paciente.glob("*_ecg.npy")))
    if not arquivos_ecg:
        return

    num_arquivos = min(len(arquivos_ecg), 3)

    # Dicionários de tradução para os labels e títulos
    textos = {
        "pt": {
            "titulo": f"Comparativo de ECG e SDNN - Paciente ID: {id_paciente}",
            "eixo_x": "Tempo (minutos)",
            "eixo_y": "Amplitude",
            "fixa": "Etapa Fixa 5min",
            "sinc": "Sincronizada Hub"
        },
        "en": {
            "titulo": f"ECG and SDNN Comparison - Patient ID: {id_paciente}",
            "eixo_x": "Time (minutes)",
            "eixo_y": "Amplitude",
            "fixa": "Fixed Stage 5min",
            "sinc": "Synchronized Hub"
        }
    }

    # Loop para gerar o gráfico em ambos os idiomas
    for idioma, lang_dict in textos.items():
        fig, axes = plt.subplots(num_arquivos, 1, figsize=(13, 9), sharex=True, sharey=True)
        fig.suptitle(lang_dict["titulo"], fontsize=14, fontweight="bold", color="#333333")
        
        if num_arquivos == 1:
            axes = [axes]

        for i in range(num_arquivos):
            caminho_arquivo = arquivos_ecg[i]
            nome_arquivo = caminho_arquivo.name
            
            # Identificação da etapa para a legenda
            if "Etapa_Fixa" in nome_arquivo:
                label_etapa = lang_dict["fixa"]
            elif "Etapa_Sincronizada_Hub" in nome_arquivo:
                timestamp = nome_arquivo.split("_")[-2]
                label_etapa = f"{lang_dict['sinc']} ({timestamp[:2]}:{timestamp[2:4]})"
            else:
                label_etapa = "ECG"

            try:
                dados_completos = np.load(caminho_arquivo)
                ecg_bruto = dados_completos[:, 1]
                
                # --- REMOÇÃO DE OUTLIERS POR PERCENTIL (Técnica que funcionou melhor) ---
                limite_inferior = np.percentile(ecg_bruto, 0.5)
                limite_superior = np.percentile(ecg_bruto, 99.5)
                ecg_limpo_outliers = np.clip(ecg_bruto, limite_inferior, limite_superior)
                
                # Pipeline de Pré-processamento e extração do NeuroKit2
                ecg_filtrado = nk.ecg_clean(ecg_limpo_outliers, sampling_rate=FS, method="neurokit")
                _, info = nk.ecg_peaks(ecg_filtrado, sampling_rate=FS, method="pantompkins")
                
                # Cálculo estatístico do SDNN (Task Force padrão-ouro)
                hrv_indices = nk.hrv_time(info, sampling_rate=FS)
                sdnn = hrv_indices["HRV_SDNN"].values[0]
                
                tempo_minutos = np.arange(len(ecg_filtrado)) / (FS * 60.0)
                
                ax = axes[i]
                ax.plot(tempo_minutos, ecg_filtrado, label=f"{label_etapa}\nSDNN: {sdnn:.2f} ms", color=ECG_RED, linewidth=0.9)
                
                # Estilização do Grid Clássico de Papel de ECG (Milimetrado)
                ax.set_facecolor("#ffffff")
                ax.grid(True, which="major", color=GRID_MAJOR, linestyle="-", linewidth=0.8)
                ax.grid(True, which="minor", color=GRID_MINOR, linestyle="-", linewidth=0.4)
                ax.minorticks_on()
                
                ax.set_ylabel(lang_dict["eixo_y"], color="#333333")
                ax.legend(loc="upper right", fontsize=9, framealpha=0.9, facecolor="#ffffff", edgecolor=GRID_MAJOR)
                
            except Exception as e:
                print(f"Erro no arquivo {nome_arquivo}: {e}")
                axes[i].text(0.5, 0.5, f"Error processing file:\n{e}", ha='center', va='center', transform=axes[i].transAxes, color='red')

        axes[-1].set_xlabel(lang_dict["eixo_x"], color="#333333")
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Salva o arquivo na respectiva pasta de idioma utilizando o ID anônimo
        if idioma == "pt":
            plt.savefig(OUTPUT_PT / f"ecg_sdnn_paciente_{id_paciente}.png", dpi=300)
        else:
            plt.savefig(OUTPUT_EN / f"ecg_sdnn_patient_{id_paciente}.png", dpi=300)
            
        plt.close()

# Varredura automática por todas as pastas de pacientes dentro do diretório base
print("Iniciando o processamento em lote de todos os pacientes com a tecnica de percentil...")
pastas_processadas = 0

for subpasta in sorted(BASE_DIR.iterdir()):
    if subpasta.is_dir() and subpasta.name not in ["plots", "plots_pt", "plots_en", ".venv"]:
        print(f"\nProcessando estrutura do diretório: {subpasta.name}")
        processar_e_plotar(subpasta)
        pastas_processadas += 1

print(f"\nConcluído! {pastas_processadas} pastas de pacientes foram processadas.")
print(f"Plots salvos em:\n -> {OUTPUT_PT}\n -> {OUTPUT_EN}")