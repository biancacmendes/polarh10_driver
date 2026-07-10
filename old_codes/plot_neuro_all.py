# import os
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# from scipy.signal import butter, filtfilt, find_peaks
# from pathlib import Path

# # CONFIGURAÇÃO DE CAMINHO DINÂMICA
# BASE_DIR = Path(os.getcwd())
# OUTPUT_DIR = os.path.join(BASE_DIR, "plots_hrv_population_averages")
# TABLE_DIR = os.path.join(BASE_DIR, "tables_hrv_population_averages")

# os.makedirs(OUTPUT_DIR, exist_ok=True)
# os.makedirs(TABLE_DIR, exist_ok=True)

# FS_ECG = 65.2133  
# TAMANHO_JANELA_MIN = 1.0  
# PASSO_JANELA_MIN = 0.166  # Deslocamento a cada 10 segundos

# # Configuração visual baseada na identidade sóbria estabelecida
# CONFIG_ETAPAS = {
#     "fixa": {"label_pt": "Média Etapa Fixa 5min", "label_en": "Mean Fixed Stage 5min", "color": "#4E79A7", "ls": "-"},
#     "hub1": {"label_pt": "Média Sincronizada Hub 1 (Δ%)", "label_en": "Mean Synchronized Hub 1 (Δ%)", "color": "#E15759", "ls": "-"},
#     "hub2": {"label_pt": "Média Sincronizada Hub 2 (Δ%)", "label_en": "Mean Synchronized Hub 2 (Δ%)", "color": "#59A14F", "ls": "-"}
# }

# # Estrutura para acumular os vetores temporais contínuos de cada paciente
# dados_series_temporais = {
#     "HR": {"fixa": [], "hub1": [], "hub2": []},
#     "SDNN": {"fixa": [], "hub1": [], "hub2": []},
#     "RMSSD": {"fixa": [], "hub1": [], "hub2": []}
# }

# # Estrutura para acumular os valores médios globais de cada bloco para os Boxplots
# dados_estaticos_boxplot = {
#     "HR": {"fixa": [], "hub1": [], "hub2": []},
#     "SDNN": {"fixa": [], "hub1": [], "hub2": []},
#     "RMSSD": {"fixa": [], "hub1": [], "hub2": []}
# }

# def save_plot(name):
#     plt.savefig(os.path.join(OUTPUT_DIR, f"{name}.pdf"), dpi=300, bbox_inches="tight")
#     plt.savefig(os.path.join(OUTPUT_DIR, f"{name}.png"), dpi=300, bbox_inches="tight")
#     print(f"[OK] Saved plot: {name}")

# def save_table(df, name):
#     path = os.path.join(TABLE_DIR, f"{name}.csv")
#     df.to_csv(path, index=False)
#     print(f"[OK] Saved table: {path}")

# def butter_bandpass_filter(data, lowcut, highcut, fs, order=4):
#     nyq = 0.5 * fs
#     low = lowcut / nyq
#     high = highcut / nyq
#     b, a = butter(order, [low, high], btype="band")
#     return filtfilt(b, a, data)

# def butter_lowpass_filter(data, cutoff, fs, order=2):
#     nyq = 0.5 * fs
#     normal_cutoff = cutoff / nyq
#     b, a = butter(order, normal_cutoff, btype="low", analog=False)
#     return filtfilt(b, a, data)

# def detectar_picos_r(ecg_filtrado, fs):
#     sinal_quadrado = ecg_filtrado ** 2
#     prominencia_minima = np.mean(sinal_quadrado) + 0.5 * np.std(sinal_quadrado)
#     distancia_minima = int(0.3 * fs)
#     picos, _ = find_peaks(sinal_quadrado, distance=distancia_minima, prominence=prominencia_minima)
#     return picos

# def executar_pipeline_janela_movel(picos_r, tempos_amostras):
#     intervalos_rr = np.diff(picos_r) * (1000.0 / FS_ECG)  
#     tempos_rr = tempos_amostras[picos_r[:-1]]         
    
#     indices_validos = np.where((intervalos_rr >= 300.0) & (intervalos_rr <= 1500.0))[0]
#     intervalos_nn = intervalos_rr[indices_validos]
#     tempos_nn = tempos_rr[indices_validos]
    
#     tempos_janelas = []
#     historico_hr = []
#     historico_sdnn = []
#     historico_rmssd = []
    
#     if len(tempos_nn) == 0:
#         return None
        
#     tempo_inicial = tempos_nn[0]
#     tempo_final = tempos_nn[-1]
#     ponteiro_tempo = tempo_inicial
    
#     while ponteiro_tempo + TAMANHO_JANELA_MIN <= tempo_final:
#         indices_janela = np.where((tempos_nn >= ponteiro_tempo) & (tempos_nn < ponteiro_tempo + TAMANHO_JANELA_MIN))[0]
        
#         if len(indices_janela) > 5:
#             nn_trecho = intervalos_nn[indices_janela]
            
#             media_nn_s = np.mean(nn_trecho) / 1000.0
#             hr_janela = 60.0 / media_nn_s
#             sdnn_janela = np.std(nn_trecho, ddof=1)
#             rmssd_janela = np.sqrt(np.mean(np.diff(nn_trecho) ** 2))
            
#             tempos_janelas.append(ponteiro_tempo + (TAMANHO_JANELA_MIN / 2.0))
#             historico_hr.append(hr_janela)
#             historico_sdnn.append(sdnn_janela)
#             historico_rmssd.append(rmssd_janela)
            
#         ponteiro_tempo += PASSO_JANELA_MIN
        
#     if len(tempos_janelas) == 0:
#         return None
        
#     return {
#         "t": np.array(tempos_janelas),
#         "HR": np.array(historico_hr),
#         "SDNN": np.array(historico_sdnn),
#         "RMSSD": np.array(historico_rmssd)
#     }

# def processar_paciente(pasta_paciente):
#     id_paciente = pasta_paciente.name.split("_")[-1]
#     arquivos_ecg = sorted(list(pasta_paciente.glob("*_ecg.npy")))
    
#     print(f"Processing directory: {pasta_paciente.name} ({len(arquivos_ecg)} files)")
#     if not arquivos_ecg: 
#         return

#     series_paciente = {m: {} for m in ["HR", "SDNN", "RMSSD"]}

#     for i, caminho_arquivo in enumerate(arquivos_ecg[:3]):
#         try:
#             dados = np.load(caminho_arquivo)
#             ecg_bruto = dados[:, 1]
            
#             limite_inf = np.percentile(ecg_bruto, 0.5)
#             limite_sup = np.percentile(ecg_bruto, 99.5)
#             ecg_limpo = np.clip(ecg_bruto, limite_inf, limite_sup)
#             ecg_filtrado = butter_bandpass_filter(ecg_limpo, 0.5, 30.0, FS_ECG, order=4)
            
#             tempos_amostras = np.arange(len(ecg_filtrado)) / (FS_ECG * 60.0)
#             picos_r = detectar_picos_r(ecg_filtrado, FS_ECG)
            
#             if len(picos_r) < 15:
#                 continue
            
#             res_janelas = executar_pipeline_janela_movel(picos_r, tempos_amostras)
#             if res_janelas is None:
#                 continue
                
#             etapa_chave = "fixa" if "Etapa_Fixa" in caminho_arquivo.name else ("hub1" if i == 1 else "hub2")
#             fs_sdnn = 1.0 / (PASSO_JANELA_MIN * 60.0)
            
#             for metrica in ["HR", "SDNN", "RMSSD"]:
#                 v_sinal = res_janelas[metrica]
#                 v_suavizado = butter_lowpass_filter(v_sinal, cutoff=0.015, fs=fs_sdnn, order=2) if len(v_sinal) > 6 else v_sinal
#                 t_relativo = res_janelas["t"] - res_janelas["t"][0]
                
#                 series_paciente[metrica][etapa_chave] = (t_relativo, v_suavizado)
#                 dados_estaticos_boxplot[metrica][etapa_chave].append(np.mean(v_suavizado))
                
#         except Exception as e:
#             print(f"   [ERROR] No arquivo {caminho_arquivo.name}: {e}")

#     tempo_grade_padrao = np.arange(0.0, 5.0, PASSO_JANELA_MIN)
    
#     for metrica in ["HR", "SDNN", "RMSSD"]:
#         if "fixa" in series_paciente[metrica]:
#             t_fixa, v_fixa = series_paciente[metrica]["fixa"]
#             v_fixa_interp = np.interp(tempo_grade_padrao, t_fixa, v_fixa, left=np.nan, right=np.nan)
            
#             dados_series_temporais[metrica]["fixa"].append((tempo_grade_padrao, v_fixa_interp))
            
#             for hub_chave in ["hub1", "hub2"]:
#                 if hub_chave in series_paciente[metrica]:
#                     t_hub, v_hub = series_paciente[metrica][hub_chave]
#                     v_hub_interp = np.interp(tempo_grade_padrao, t_hub, v_hub, left=np.nan, right=np.nan)
                    
#                     v_delta_percentual = ((v_hub_interp - v_fixa_interp) / v_fixa_interp) * 100.0
#                     dados_series_temporais[metrica][hub_chave].append((tempo_grade_padrao, v_delta_percentual))

# def gerar_outputs_consolidados():
#     print("\n=== GENERATING CONSOLIDATED ACADEMIC OUTPUTS ===")
    
#     tempo_comum = np.arange(0.0, 5.0, PASSO_JANELA_MIN)
#     metricas_lista = ["HR", "SDNN", "RMSSD"]
    
#     idiomas = {
#         "pt": {"x": "Tempo Relativo da Etapa (min)", "y_delta": "Variação Média (Δ%)", "x_box": "Etapa Experimental", "y_box": "Variação Global (Δ%)"},
#         "en": {"x": "Relative Stage Time (min)", "y_delta": "Mean Variation (Δ%)", "x_box": "Experimental Stage", "y_box": "Global Variation (Δ%)"}
#     }
    
#     linhas_tabela_summary = []
    
#     for idioma, lang in idiomas.items():
#         for metrica in metricas_lista:
#             # --- CURVAS TEMPORAIS DAS MÉDIAS POPULACIONAIS (Δ%) ---
#             plt.figure(figsize=(6.5, 4.2))
#             linhas_plotadas = 0
            
#             for chave_hub in ["hub1", "hub2"]:
#                 listagem_hub = dados_series_temporais[metrica][chave_hub]
#                 if len(listagem_hub) == 0: 
#                     continue
                    
#                 matriz_deltas = [v for _, v in listagem_hub]
#                 valores_medios_delta = np.nanmean(matriz_deltas, axis=0)
#                 mascara = ~np.isnan(valores_medios_delta)
                
#                 if np.sum(mascara) > 0:
#                     label = CONFIG_ETAPAS[chave_hub]["label_pt"] if idioma == "pt" else CONFIG_ETAPAS[chave_hub]["label_en"]
#                     plt.plot(
#                         tempo_comum[mascara], valores_medios_delta[mascara],
#                         label=label,
#                         color=CONFIG_ETAPAS[chave_hub]["color"],
#                         linestyle=CONFIG_ETAPAS[chave_hub]["ls"],
#                         linewidth=2.0, marker="o", markersize=2, alpha=0.9
#                     )
#                     linhas_plotadas += 1
                    
#             if linhas_plotadas > 0:
#                 plt.axhline(0, color="#7f7f7f", linestyle="--", linewidth=1.0)
#                 plt.xlabel(lang["x"])
#                 plt.ylabel(f"{metrica} - {lang['y_delta']}")
#                 plt.gca().spines["top"].set_visible(False)
#                 plt.gca().spines["right"].set_visible(False)
#                 plt.grid(True, linestyle="--", alpha=0.5)
#                 plt.legend(frameon=True, loc="upper right")
#                 plt.tight_layout()
#                 save_plot(f"population_continuous_mean_{metrica.lower()}_{idioma}")
#             plt.close()

#             # --- BOXPLOTS POPULACIONAIS COM EXTRAÇÃO DE BASELINE (Δ%) ---
#             data_boxplot = []
#             labels_boxplot = []
#             cores_boxplot = []
            
#             fixa_bruto = np.array(dados_estaticos_boxplot[metrica]["fixa"])
            
#             for eth in ["hub1", "hub2"]:
#                 hub_bruto = np.array(dados_estaticos_boxplot[metrica][eth])
                
#                 if len(hub_bruto) == len(fixa_bruto) and len(fixa_bruto) > 0:
#                     delta_percentual_indiv = ((hub_bruto - fixa_bruto) / fixa_bruto) * 100.0
#                     data_boxplot.append(delta_percentual_indiv)
                    
#                     labels_boxplot.append("Hub 1" if eth == "hub1" else "Hub 2")
#                     cores_boxplot.append(CONFIG_ETAPAS[eth]["color"])
                    
#                     if idioma == "pt":
#                         linhas_tabela_summary.append({
#                             "metric": metrica,
#                             "stage": eth,
#                             "delta_mean": float(np.mean(delta_percentual_indiv)),
#                             "delta_std": float(np.std(delta_percentual_indiv, ddof=1)) if len(delta_percentual_indiv) > 1 else 0.0,
#                             "delta_min": float(np.min(delta_percentual_indiv)),
#                             "delta_max": float(np.max(delta_percentual_indiv))
#                         })
            
#             if data_boxplot:
#                 plt.figure(figsize=(5.0, 4.2))
                
#                 bp = plt.boxplot(
#                     data_boxplot,
#                     labels=labels_boxplot,
#                     patch_artist=True,
#                     showmeans=True,
#                 )
                
#                 for patch, color in zip(bp["boxes"], cores_boxplot):
#                     patch.set_facecolor(color)
#                     patch.set_alpha(0.65)
#                     patch.set_edgecolor("#4d4d4d")
                    
#                 for whisker in bp["whiskers"]:
#                     whisker.set(color="#4d4d4d", linestyle="--", linewidth=1.0)
                    
#                 for cap in bp["caps"]:
#                     cap.set(color="#4d4d4d", linewidth=1.0)
                    
#                 for median in bp["medians"]:
#                     median.set(color="black", linewidth=1.5)
                    
#                 for mean_marker in bp["means"]:
#                     mean_marker.set(marker="D", markerfacecolor="white", markeredgecolor="black", markersize=5)

#                 plt.axhline(0, color="#7f7f7f", linestyle="--", linewidth=1.0)
#                 plt.xlabel(lang["x_box"])
#                 plt.ylabel(f"Δ% {metrica} - {lang['y_box']}")
#                 plt.gca().spines["top"].set_visible(False)
#                 plt.gca().spines["right"].set_visible(False)
#                 plt.grid(True, axis="y", linestyle="--", alpha=0.5)
#                 plt.tight_layout()
#                 save_plot(f"population_boxplot_delta_{metrica.lower()}_{idioma}")
#             plt.close()

#     if linhas_tabela_summary:
#         df_summary = pd.DataFrame(linhas_tabela_summary)
#         save_table(df_summary, "summary_population_delta_metrics")
#         print("\n=== POPULATION DELTA METRICS SUMMARY ===")
#         print(df_summary.round(4).to_string(index=False))

# def main():
#     plt.rcParams.update({
#         "font.size": 12,
#         "font.family": "serif",
#     })

#     print("Starting automated directory scan for continuous cohort average lines...")
#     pastas_analisadas = 0

#     diretorios_ignorar = [
#         "plots_hrv_population_averages", "tables_hrv_population_averages",
#         "plots_pt", "plots_en", ".venv", "__pycache__", "plots_sdnn_academic",
#         "tables_sdnn_academic", "plots_hrv_freq_academic", "tables_hrv_freq_academic",
#         "plots_hrv_time_academic", "tables_hrv_time_academic", "plots_hrv_general_analysis",
#         "tables_hrv_general_analysis", "plots_hrv_neurokit", "tables_hrv_neurokit"
#     ]

#     for subpasta in sorted(BASE_DIR.iterdir()):
#         partes_nome = subpasta.name.split("_")
#         if subpasta.is_dir() and subpasta.name not in diretorios_ignorar:
#             if len(partes_nome) > 1 and len(partes_nome[-1]) == 8:
#                 processar_paciente(subpasta)
#                 pastas_analisadas += 1

#     if pastas_analisadas == 0:
#         print("\n[ERROR] No valid patient data folders detected.")
#     else:
#         print(f"Scan completed. Total folders processed: {pastas_analisadas}")
#         gerar_outputs_consolidados()

# if __name__ == "__main__":
#     main()

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.signal import butter, filtfilt, find_peaks
from pathlib import Path


BASE_DIR = Path(os.getcwd())
OUTPUT_DIR = BASE_DIR / "plots_hrv_population_averages"
TABLE_DIR = BASE_DIR / "tables_hrv_population_averages"

OUTPUT_DIR.mkdir(exist_ok=True)
TABLE_DIR.mkdir(exist_ok=True)

FS_ECG = 65.2133
TAMANHO_JANELA_MIN = 1.0
PASSO_JANELA_MIN = 0.166


CONFIG_ETAPAS = {
    "fixa": {
        "label_pt": "Média Etapa Fixa 5min",
        "label_en": "Mean Fixed Stage 5min",
        "color": "#4E79A7",
        "ls": "-",
    },
    "hub1": {
        "label_pt": "Média Sincronizada Hub 1 (Δ%)",
        "label_en": "Mean Synchronized Hub 1 (Δ%)",
        "color": "#E15759",
        "ls": "-",
    },
    "hub2": {
        "label_pt": "Média Sincronizada Hub 2 (Δ%)",
        "label_en": "Mean Synchronized Hub 2 (Δ%)",
        "color": "#59A14F",
        "ls": "-",
    },
}


dados_series_temporais = {
    "HR": {"fixa": [], "hub1": [], "hub2": []},
    "SDNN": {"fixa": [], "hub1": [], "hub2": []},
    "RMSSD": {"fixa": [], "hub1": [], "hub2": []},
}

dados_estaticos_por_paciente = {
    "HR": {},
    "SDNN": {},
    "RMSSD": {},
}


def save_plot(name):
    plt.savefig(OUTPUT_DIR / f"{name}.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    print(f"[OK] Saved plot: {name}")


def save_table(df, name):
    path = TABLE_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] Saved table: {path}")


def validar_tamanho_para_filtro(data, b, a, caminho_arquivo):
    padlen = 3 * max(len(a), len(b))

    if len(data) <= padlen:
        print(
            f"   [SKIP] Arquivo muito curto para filtfilt: "
            f"{caminho_arquivo.name} | Amostras: {len(data)} | padlen: {padlen}"
        )
        return False

    return True


def butter_bandpass_filter(data, lowcut, highcut, fs, order=4, caminho_arquivo=None):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq

    b, a = butter(order, [low, high], btype="band")

    if caminho_arquivo is not None:
        if not validar_tamanho_para_filtro(data, b, a, caminho_arquivo):
            return None

    return filtfilt(b, a, data)


def butter_lowpass_filter(data, cutoff, fs, order=2):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq

    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    padlen = 3 * max(len(a), len(b))

    if len(data) <= padlen:
        return data

    return filtfilt(b, a, data)


def detectar_picos_r(ecg_filtrado, fs):
    sinal_quadrado = ecg_filtrado ** 2

    prominencia_minima = np.mean(sinal_quadrado) + 0.5 * np.std(sinal_quadrado)
    distancia_minima = int(0.3 * fs)

    picos, _ = find_peaks(
        sinal_quadrado,
        distance=distancia_minima,
        prominence=prominencia_minima,
    )

    return picos


def executar_pipeline_janela_movel(picos_r, tempos_amostras):
    intervalos_rr = np.diff(picos_r) * (1000.0 / FS_ECG)
    tempos_rr = tempos_amostras[picos_r[:-1]]

    indices_validos = np.where((intervalos_rr >= 300.0) & (intervalos_rr <= 1500.0))[0]

    intervalos_nn = intervalos_rr[indices_validos]
    tempos_nn = tempos_rr[indices_validos]

    if len(tempos_nn) == 0:
        return None

    tempos_janelas = []
    historico_hr = []
    historico_sdnn = []
    historico_rmssd = []

    tempo_inicial = tempos_nn[0]
    tempo_final = tempos_nn[-1]
    ponteiro_tempo = tempo_inicial

    while ponteiro_tempo + TAMANHO_JANELA_MIN <= tempo_final:
        indices_janela = np.where(
            (tempos_nn >= ponteiro_tempo)
            & (tempos_nn < ponteiro_tempo + TAMANHO_JANELA_MIN)
        )[0]

        if len(indices_janela) > 5:
            nn_trecho = intervalos_nn[indices_janela]

            media_nn_s = np.mean(nn_trecho) / 1000.0
            hr_janela = 60.0 / media_nn_s
            sdnn_janela = np.std(nn_trecho, ddof=1)
            rmssd_janela = np.sqrt(np.mean(np.diff(nn_trecho) ** 2))

            tempos_janelas.append(ponteiro_tempo + TAMANHO_JANELA_MIN / 2.0)
            historico_hr.append(hr_janela)
            historico_sdnn.append(sdnn_janela)
            historico_rmssd.append(rmssd_janela)

        ponteiro_tempo += PASSO_JANELA_MIN

    if len(tempos_janelas) == 0:
        return None

    return {
        "t": np.array(tempos_janelas),
        "HR": np.array(historico_hr),
        "SDNN": np.array(historico_sdnn),
        "RMSSD": np.array(historico_rmssd),
    }


def identificar_etapas(arquivos_ecg):
    arquivos_fixa = [
        arq for arq in arquivos_ecg
        if "Etapa_Fixa" in arq.name
    ]

    arquivos_hub = [
        arq for arq in arquivos_ecg
        if "Etapa_Sincronizada_Hub" in arq.name
    ]

    arquivos_fixa = sorted(arquivos_fixa)
    arquivos_hub = sorted(arquivos_hub)

    mapa = {}

    if len(arquivos_fixa) >= 1:
        mapa[arquivos_fixa[0]] = "fixa"

    if len(arquivos_hub) >= 1:
        mapa[arquivos_hub[0]] = "hub1"

    if len(arquivos_hub) >= 2:
        mapa[arquivos_hub[1]] = "hub2"

    return mapa


def registrar_valor_estatico(id_paciente, metrica, etapa_chave, valor):
    if id_paciente not in dados_estaticos_por_paciente[metrica]:
        dados_estaticos_por_paciente[metrica][id_paciente] = {}

    dados_estaticos_por_paciente[metrica][id_paciente][etapa_chave] = float(valor)


def processar_paciente(pasta_paciente):
    id_paciente = pasta_paciente.name.split("_")[-1]
    arquivos_ecg = sorted(list(pasta_paciente.glob("*_ecg.npy")))

    print(f"Processing directory: {pasta_paciente.name} ({len(arquivos_ecg)} files)")

    if not arquivos_ecg:
        return

    mapa_etapas = identificar_etapas(arquivos_ecg)

    if "fixa" not in mapa_etapas.values():
        print(f"   [SKIP] Paciente sem etapa fixa: {pasta_paciente.name}")
        return

    series_paciente = {
        "HR": {},
        "SDNN": {},
        "RMSSD": {},
    }

    for caminho_arquivo, etapa_chave in mapa_etapas.items():
        try:
            dados = np.load(caminho_arquivo)

            if dados.ndim != 2 or dados.shape[1] < 2:
                print(f"   [SKIP] Formato inválido: {caminho_arquivo.name}")
                continue

            ecg_bruto = dados[:, 1]

            if len(ecg_bruto) < 30:
                print(
                    f"   [SKIP] ECG muito curto: "
                    f"{caminho_arquivo.name} | Amostras: {len(ecg_bruto)}"
                )
                continue

            limite_inf = np.percentile(ecg_bruto, 0.5)
            limite_sup = np.percentile(ecg_bruto, 99.5)
            ecg_limpo = np.clip(ecg_bruto, limite_inf, limite_sup)

            ecg_filtrado = butter_bandpass_filter(
                ecg_limpo,
                0.5,
                30.0,
                FS_ECG,
                order=4,
                caminho_arquivo=caminho_arquivo,
            )

            if ecg_filtrado is None:
                continue

            tempos_amostras = np.arange(len(ecg_filtrado)) / (FS_ECG * 60.0)
            picos_r = detectar_picos_r(ecg_filtrado, FS_ECG)

            if len(picos_r) < 15:
                print(
                    f"   [SKIP] Poucos picos R detectados: "
                    f"{caminho_arquivo.name} | Picos: {len(picos_r)}"
                )
                continue

            res_janelas = executar_pipeline_janela_movel(picos_r, tempos_amostras)

            if res_janelas is None:
                print(f"   [SKIP] Sem janelas HRV válidas: {caminho_arquivo.name}")
                continue

            fs_sdnn = 1.0 / (PASSO_JANELA_MIN * 60.0)

            for metrica in ["HR", "SDNN", "RMSSD"]:
                v_sinal = res_janelas[metrica]

                v_suavizado = butter_lowpass_filter(
                    v_sinal,
                    cutoff=0.015,
                    fs=fs_sdnn,
                    order=2,
                )

                t_relativo = res_janelas["t"] - res_janelas["t"][0]

                series_paciente[metrica][etapa_chave] = (t_relativo, v_suavizado)

                registrar_valor_estatico(
                    id_paciente=id_paciente,
                    metrica=metrica,
                    etapa_chave=etapa_chave,
                    valor=np.nanmean(v_suavizado),
                )

        except Exception as e:
            print(f"   [ERROR] No arquivo {caminho_arquivo.name}: {e}")

    tempo_grade_padrao = np.arange(0.0, 5.0, PASSO_JANELA_MIN)

    for metrica in ["HR", "SDNN", "RMSSD"]:
        if "fixa" not in series_paciente[metrica]:
            continue

        t_fixa, v_fixa = series_paciente[metrica]["fixa"]

        v_fixa_interp = np.interp(
            tempo_grade_padrao,
            t_fixa,
            v_fixa,
            left=np.nan,
            right=np.nan,
        )

        dados_series_temporais[metrica]["fixa"].append(
            {
                "id": id_paciente,
                "t": tempo_grade_padrao,
                "v": v_fixa_interp,
            }
        )

        for hub_chave in ["hub1", "hub2"]:
            if hub_chave not in series_paciente[metrica]:
                continue

            t_hub, v_hub = series_paciente[metrica][hub_chave]

            v_hub_interp = np.interp(
                tempo_grade_padrao,
                t_hub,
                v_hub,
                left=np.nan,
                right=np.nan,
            )

            with np.errstate(divide="ignore", invalid="ignore"):
                v_delta_percentual = ((v_hub_interp - v_fixa_interp) / v_fixa_interp) * 100.0

            dados_series_temporais[metrica][hub_chave].append(
                {
                    "id": id_paciente,
                    "t": tempo_grade_padrao,
                    "v": v_delta_percentual,
                }
            )


def calcular_deltas_boxplot_por_paciente(metrica, etapa_hub):
    deltas = []
    ids_validos = []

    dados_metrica = dados_estaticos_por_paciente[metrica]

    for id_paciente, etapas in sorted(dados_metrica.items()):
        if "fixa" not in etapas:
            continue

        if etapa_hub not in etapas:
            continue

        valor_fixa = etapas["fixa"]
        valor_hub = etapas[etapa_hub]

        if not np.isfinite(valor_fixa) or not np.isfinite(valor_hub):
            continue

        if valor_fixa == 0:
            continue

        delta = ((valor_hub - valor_fixa) / valor_fixa) * 100.0

        if np.isfinite(delta):
            deltas.append(delta)
            ids_validos.append(id_paciente)

    return np.array(deltas, dtype=float), ids_validos


def gerar_outputs_consolidados():
    print("\n=== GENERATING CONSOLIDATED ACADEMIC OUTPUTS ===")

    tempo_comum = np.arange(0.0, 5.0, PASSO_JANELA_MIN)
    metricas_lista = ["HR", "SDNN", "RMSSD"]

    idiomas = {
        "pt": {
            "x": "Tempo Relativo da Etapa (min)",
            "y_delta": "Variação Média (Δ%)",
            "x_box": "Etapa Experimental",
            "y_box": "Variação Global (Δ%)",
        },
        "en": {
            "x": "Relative Stage Time (min)",
            "y_delta": "Mean Variation (Δ%)",
            "x_box": "Experimental Stage",
            "y_box": "Global Variation (Δ%)",
        },
    }

    linhas_tabela_summary = []
    linhas_tabela_individual = []

    for idioma, lang in idiomas.items():
        for metrica in metricas_lista:
            plt.figure(figsize=(6.5, 4.2))
            linhas_plotadas = 0

            for chave_hub in ["hub1", "hub2"]:
                listagem_hub = dados_series_temporais[metrica][chave_hub]

                if len(listagem_hub) == 0:
                    continue

                matriz_deltas = np.array([item["v"] for item in listagem_hub], dtype=float)

                if matriz_deltas.size == 0:
                    continue

                with np.errstate(invalid="ignore"):
                    valores_medios_delta = np.nanmean(matriz_deltas, axis=0)

                mascara = np.isfinite(valores_medios_delta)

                if np.sum(mascara) > 0:
                    label = (
                        CONFIG_ETAPAS[chave_hub]["label_pt"]
                        if idioma == "pt"
                        else CONFIG_ETAPAS[chave_hub]["label_en"]
                    )

                    plt.plot(
                        tempo_comum[mascara],
                        valores_medios_delta[mascara],
                        label=label,
                        color=CONFIG_ETAPAS[chave_hub]["color"],
                        linestyle=CONFIG_ETAPAS[chave_hub]["ls"],
                        linewidth=2.0,
                        marker="o",
                        markersize=2,
                        alpha=0.9,
                    )

                    linhas_plotadas += 1

            if linhas_plotadas > 0:
                plt.axhline(0, color="#7f7f7f", linestyle="--", linewidth=1.0)
                plt.xlabel(lang["x"])
                plt.ylabel(f"{metrica} - {lang['y_delta']}")
                plt.gca().spines["top"].set_visible(False)
                plt.gca().spines["right"].set_visible(False)
                plt.grid(True, linestyle="--", alpha=0.5)
                plt.legend(frameon=True, loc="upper right")
                plt.tight_layout()
                save_plot(f"population_continuous_mean_{metrica.lower()}_{idioma}")

            plt.close()

            data_boxplot = []
            labels_boxplot = []
            cores_boxplot = []

            print(f"\n[DEBUG] {metrica}")
            print(f"  participantes com fixa/hub1/hub2 por ID:")

            for etapa_hub in ["hub1", "hub2"]:
                delta_percentual_indiv, ids_validos = calcular_deltas_boxplot_por_paciente(
                    metrica,
                    etapa_hub,
                )

                print(f"  {etapa_hub}: {len(delta_percentual_indiv)} participantes válidos")

                if len(delta_percentual_indiv) == 0:
                    continue

                data_boxplot.append(delta_percentual_indiv)
                labels_boxplot.append("Hub 1" if etapa_hub == "hub1" else "Hub 2")
                cores_boxplot.append(CONFIG_ETAPAS[etapa_hub]["color"])

                if idioma == "pt":
                    for id_paciente, delta in zip(ids_validos, delta_percentual_indiv):
                        linhas_tabela_individual.append(
                            {
                                "patient_id": id_paciente,
                                "metric": metrica,
                                "stage": etapa_hub,
                                "delta_percent": float(delta),
                            }
                        )

                    linhas_tabela_summary.append(
                        {
                            "metric": metrica,
                            "stage": etapa_hub,
                            "n": int(len(delta_percentual_indiv)),
                            "delta_mean": float(np.mean(delta_percentual_indiv)),
                            "delta_std": (
                                float(np.std(delta_percentual_indiv, ddof=1))
                                if len(delta_percentual_indiv) > 1
                                else 0.0
                            ),
                            "delta_min": float(np.min(delta_percentual_indiv)),
                            "delta_max": float(np.max(delta_percentual_indiv)),
                        }
                    )

            if data_boxplot:
                plt.figure(figsize=(5.0, 4.2))

                try:
                    bp = plt.boxplot(
                        data_boxplot,
                        tick_labels=labels_boxplot,
                        patch_artist=True,
                        showmeans=True,
                    )
                except TypeError:
                    bp = plt.boxplot(
                        data_boxplot,
                        labels=labels_boxplot,
                        patch_artist=True,
                        showmeans=True,
                    )

                for patch, color in zip(bp["boxes"], cores_boxplot):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.65)
                    patch.set_edgecolor("#4d4d4d")

                for whisker in bp["whiskers"]:
                    whisker.set(color="#4d4d4d", linestyle="--", linewidth=1.0)

                for cap in bp["caps"]:
                    cap.set(color="#4d4d4d", linewidth=1.0)

                for median in bp["medians"]:
                    median.set(color="black", linewidth=1.5)

                for mean_marker in bp["means"]:
                    mean_marker.set(
                        marker="D",
                        markerfacecolor="white",
                        markeredgecolor="black",
                        markersize=5,
                    )

                plt.axhline(0, color="#7f7f7f", linestyle="--", linewidth=1.0)
                plt.xlabel(lang["x_box"])
                plt.ylabel(f"Δ% {metrica} - {lang['y_box']}")
                plt.gca().spines["top"].set_visible(False)
                plt.gca().spines["right"].set_visible(False)
                plt.grid(True, axis="y", linestyle="--", alpha=0.5)
                plt.tight_layout()
                save_plot(f"population_boxplot_delta_{metrica.lower()}_{idioma}")

            plt.close()

    if linhas_tabela_summary:
        df_summary = pd.DataFrame(linhas_tabela_summary)
        save_table(df_summary, "summary_population_delta_metrics")

        print("\n=== POPULATION DELTA METRICS SUMMARY ===")
        print(df_summary.round(4).to_string(index=False))

    if linhas_tabela_individual:
        df_individual = pd.DataFrame(linhas_tabela_individual)
        save_table(df_individual, "individual_population_delta_metrics")


def main():
    plt.rcParams.update(
        {
            "font.size": 12,
            "font.family": "serif",
        }
    )

    print("Starting automated directory scan for continuous cohort average lines...")

    pastas_analisadas = 0

    diretorios_ignorar = [
        "plots_hrv_population_averages",
        "tables_hrv_population_averages",
        "plots_pt",
        "plots_en",
        ".venv",
        "__pycache__",
        "plots_sdnn_academic",
        "tables_sdnn_academic",
        "plots_hrv_freq_academic",
        "tables_hrv_freq_academic",
        "plots_hrv_time_academic",
        "tables_hrv_time_academic",
        "plots_hrv_general_analysis",
        "tables_hrv_general_analysis",
        "plots_hrv_neurokit",
        "tables_hrv_neurokit",
    ]

    for subpasta in sorted(BASE_DIR.iterdir()):
        partes_nome = subpasta.name.split("_")

        if not subpasta.is_dir():
            continue

        if subpasta.name in diretorios_ignorar:
            continue

        if len(partes_nome) > 1 and len(partes_nome[-1]) == 8:
            processar_paciente(subpasta)
            pastas_analisadas += 1

    if pastas_analisadas == 0:
        print("\n[ERROR] No valid patient data folders detected.")
    else:
        print(f"Scan completed. Total folders processed: {pastas_analisadas}")
        gerar_outputs_consolidados()


if __name__ == "__main__":
    main()