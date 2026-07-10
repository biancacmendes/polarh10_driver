import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks
from pathlib import Path

BASE_DIR = Path(os.getcwd())
OUTPUT_DIR = os.path.join(BASE_DIR, "plots_sdnn_academic")
TABLE_DIR = os.path.join(BASE_DIR, "tables_sdnn_academic")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TABLE_DIR, exist_ok=True)

FS = 65.2133  
TAMANHO_JANELA_MIN = 1.0  
PASSO_JANELA_MIN = 0.166  

# Paleta de cores sóbrias baseada exatamente no seu script do BlueROV2
CONFIG_ETAPAS = {
    "fixa": {"label_pt": "Etapa Fixa 5min", "label_en": "Fixed Stage 5min", "color": "#4E79A7", "ls": "-"},
    "hub1": {"label_pt": "Sincronizada Hub 1", "label_en": "Synchronized Hub 1", "color": "#E15759", "ls": "-"},
    "hub2": {"label_pt": "Sincronizada Hub 2", "label_en": "Synchronized Hub 2", "color": "#59A14F", "ls": "-"}
}

dados_globais = {"fixa": [], "hub1": [], "hub2": []}

def save_plot(name):
    plt.savefig(os.path.join(OUTPUT_DIR, f"{name}.pdf"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(OUTPUT_DIR, f"{name}.png"), dpi=300, bbox_inches="tight")
    print(f"[OK] Saved {name}")

def save_table(df, name):
    path = os.path.join(TABLE_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    print(f"[OK] Saved table: {path}")

def butter_bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, data)

def butter_lowpass_filter(data, cutoff, fs, order=2):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    return filtfilt(b, a, data)

def detectar_picos_r(ecg_filtrado, fs):
    sinal_quadrado = ecg_filtrado ** 2
    prominencia_minima = np.mean(sinal_quadrado) + 0.5 * np.std(sinal_quadrado)
    distancia_minima = int(0.3 * fs)
    picos, _ = find_peaks(sinal_quadrado, distance=distancia_minima, prominence=prominencia_minima)
    return picos

def executar_pipeline_sdnn(picos_r, tempos_amostras):
    intervalos_rr = np.diff(picos_r) * (1000.0 / FS)  
    tempos_rr = tempos_amostras[picos_r[:-1]]         
    
    indices_validos = np.where((intervalos_rr >= 300.0) & (intervalos_rr <= 1500.0))[0]
    intervalos_nn = intervalos_rr[indices_validos]
    tempos_nn = tempos_rr[indices_validos]
    
    tempos_janelas = []
    valores_sdnn = []
    
    if len(tempos_nn) == 0:
        return np.array([]), np.array([])
        
    tempo_inicial = tempos_nn[0]
    tempo_final = tempos_nn[-1]
    ponteiro_tempo = tempo_inicial
    
    while ponteiro_tempo + TAMANHO_JANELA_MIN <= tempo_final:
        indices_janela = np.where((tempos_nn >= ponteiro_tempo) & (tempos_nn < ponteiro_tempo + TAMANHO_JANELA_MIN))[0]
        
        if len(indices_janela) > 5:
            nn_trecho = intervalos_nn[indices_janela]
            media_nn = np.mean(nn_trecho)
            diferencas = nn_trecho - media_nn
            quadrados = diferencas ** 2
            variancia = np.sum(quadrados) / (len(nn_trecho) - 1)
            sdnn_final = np.sqrt(variancia)
            
            tempos_janelas.append(ponteiro_tempo + (TAMANHO_JANELA_MIN / 2.0))
            valores_sdnn.append(sdnn_final)
            
        ponteiro_tempo += PASSO_JANELA_MIN
        
    return np.array(tempos_janelas), np.array(valores_sdnn)

def processar_paciente(pasta_paciente):
    id_paciente = pasta_paciente.name.split("_")[-1]
    arquivos_ecg = sorted(list(pasta_paciente.glob("*_ecg.npy")))
    
    print(f"\nProcessing directory: {pasta_paciente.name} ({len(arquivos_ecg)} files)")
    if not arquivos_ecg: 
        return

    textos = {
        "pt": {"x": "Tempo Relativo (min)", "y": "SDNN (ms)"},
        "en": {"x": "Relative Time (min)", "y": "SDNN (ms)"}
    }

    for idioma, lang in textos.items():
        plt.figure(figsize=(6.5, 4.2))
        graficos_gerados = 0
        
        for i, caminho_arquivo in enumerate(arquivos_ecg[:3]):
            try:
                dados = np.load(caminho_arquivo)
                ecg_bruto = dados[:, 1]
                
                limite_inf = np.percentile(ecg_bruto, 0.5)
                limite_sup = np.percentile(ecg_bruto, 99.5)
                ecg_limpo = np.clip(ecg_bruto, limite_inf, limite_sup)
                
                ecg_filtrado = butter_bandpass_filter(ecg_limpo, 0.5, 30.0, FS, order=4)
                tempos_amostras = np.arange(len(ecg_filtrado)) / (FS * 60.0)
                
                picos_r = detectar_picos_r(ecg_filtrado, FS)
                if len(picos_r) < 10:
                    continue
                
                t_sdnn, v_sdnn = executar_pipeline_sdnn(picos_r, tempos_amostras)
                
                if len(v_sdnn) > 0:
                    fs_sdnn = 1.0 / (PASSO_JANELA_MIN * 60.0)
                    v_sdnn_filtrado = butter_lowpass_filter(v_sdnn, cutoff=0.015, fs=fs_sdnn, order=2) if len(v_sdnn) > 6 else v_sdnn
                    
                    t_relativo = t_sdnn - t_sdnn[0]
                    
                    if "Etapa_Fixa" in caminho_arquivo.name:
                        chave = "fixa"
                    else:
                        chave = "hub1" if i == 1 else "hub2"
                    
                    if idioma == "pt":
                        dados_globais[chave].append((t_relativo, v_sdnn_filtrado))
                    
                    label = CONFIG_ETAPAS[chave]["label_pt"] if idioma == "pt" else CONFIG_ETAPAS[chave]["label_en"]
                    
                    plt.plot(
                        t_relativo, v_sdnn_filtrado,
                        label=label,
                        color=CONFIG_ETAPAS[chave]["color"],
                        linestyle=CONFIG_ETAPAS[chave]["ls"],
                        marker="o", markersize=2, alpha=0.85
                    )
                    graficos_gerados += 1
                
            except Exception as e:
                print(f"   [ERROR] File {caminho_arquivo.name}: {e}")

        if graficos_gerados > 0:
            plt.xlabel(lang["x"])
            plt.ylabel(lang["y"])
            plt.gca().spines["top"].set_visible(False)
            plt.gca().spines["right"].set_visible(False)
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend(frameon=True)
            plt.tight_layout()
            
            suffix = "pt" if idioma == "pt" else "en"
            save_plot(f"sdnn_overlaid_{id_paciente}_{suffix}")
            
        plt.close()

def gerar_outputs_consolidados():
    print("\n=== GENERATING CONSOLIDATED ACADEMIC OUTPUTS ===")
    
    tempo_comum = np.arange(0.0, 5.0, PASSO_JANELA_MIN)
    
    textos_media = {
        "pt": {"x": "Tempo Relativo da Etapa (min)", "y": "SDNN Médio (ms)"},
        "en": {"x": "Relative Stage Time (min)", "y": "Mean SDNN (ms)"}
    }
    
    # Geração dos Plots Médios Consolidados (Sem títulos internos para padrão tese)
    for idioma, lang in textos_media.items():
        plt.figure(figsize=(6.5, 4.2))
        linhas_plotadas = 0
        
        for chave in ["fixa", "hub1", "hub2"]:
            listagem = dados_globais[chave]
            if len(listagem) == 0: continue
                
            valores_interpolados = []
            for t_rel, v_filt in listagem:
                v_interp = np.interp(tempo_comum, t_rel, v_filt, left=np.nan, right=np.nan)
                valores_interpolados.append(v_interp)
            
            valores_medios = np.nanmean(valores_interpolados, axis=0)
            mascara = ~np.isnan(valores_medios)
            
            if np.sum(mascara) > 0:
                label = CONFIG_ETAPAS[chave]["label_pt"] if idioma == "pt" else CONFIG_ETAPAS[chave]["label_en"]
                plt.plot(
                    tempo_comum[mascara], valores_medios[mascara],
                    label=label,
                    color=CONFIG_ETAPAS[chave]["color"],
                    linestyle=CONFIG_ETAPAS[chave]["ls"],
                    linewidth=2.0, marker="o", markersize=3
                )
                linhas_plotadas += 1
                
        if linhas_plotadas > 0:
            plt.xlabel(lang["x"])
            plt.ylabel(lang["y"])
            plt.gca().spines["top"].set_visible(False)
            plt.gca().spines["right"].set_visible(False)
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend(frameon=True)
            plt.tight_layout()
            
            save_plot(f"sdnn_global_mean_evolution_{idioma}")
        plt.close()

    # Processamento Estatístico e Salvamento do CSV Summary
    summary_rows = []
    for chave in ["fixa", "hub1", "hub2"]:
        listagem = dados_globais[chave]
        if len(listagem) == 0: continue
            
        todos_valores = []
        for _, v_filt in listagem:
            todos_valores.extend(v_filt)
            
        todos_valores = np.array(todos_valores)
        
        summary_rows.append({
            "stage": chave,
            "n_samples": int(len(todos_valores)),
            "sdnn_mean": float(np.mean(todos_valores)),
            "sdnn_std": float(np.std(todos_valores, ddof=1)) if len(todos_valores) > 1 else 0.0,
            "sdnn_min": float(np.min(todos_valores)),
            "sdnn_max": float(np.max(todos_valores))
        })
        
    summary_df = pd.DataFrame(summary_rows)
    save_table(summary_df, "summary_sdnn_metrics")
    
    print("\n=== SDNN METRICS SUMMARY ===")
    print(summary_df.round(4).to_string(index=False))

def main():
    # Parâmetros globais de tipografia idênticos ao script fornecido
    plt.rcParams.update({
        "font.size": 12,
        "font.family": "serif",
    })

    print("Starting automated directory scan...")
    pastas_analisadas = 0

    for subpasta in sorted(BASE_DIR.iterdir()):
        if subpasta.is_dir() and subpasta.name not in ["plots_pt", "plots_en", ".venv", "__pycache__", "plots_sdnn_academic", "tables_sdnn_academic"]:
            processar_paciente(subpasta)
            pastas_analisadas += 1

    if pastas_analisadas == 0:
        print("\n[ERROR] No valid patient data folders detected.")
    else:
        print(f"\nScan completed. Total folders processed: {pastas_analisadas}")
        gerar_outputs_consolidados()

if __name__ == "__main__":
    main()