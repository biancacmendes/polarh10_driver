import numpy as np
from pathlib import Path

def calcular_tempos():
    diretorio_base = Path.home() / "Desktop" / "bianca" / "polarh10_driver" / "data_captures"
    frequencia = 65

    if not diretorio_base.exists():
        print(f"Diretorio {diretorio_base} nao encontrado.")
        return

    for paciente_dir in sorted(diretorio_base.iterdir()):
        if paciente_dir.is_dir():
            print(f"Paciente: {paciente_dir.name}")
            
            arquivos = sorted(list(paciente_dir.glob("*.npy")))
            
            if not arquivos:
                print("  Nenhum arquivo .npy encontrado nesta pasta.")
            
            for arquivo in arquivos:
                try:
                    dados = np.load(arquivo)
                    num_amostras = len(dados)
                    duracao_total_segundos = num_amostras / frequencia
                    
                    minutos = int(duracao_total_segundos // 60)
                    segundos = int(duracao_total_segundos % 60)
                    
                    print(f"  Arquivo: {arquivo.name} | Duracao: {minutos}m {segundos}s | Amostras: {num_amostras}")
                except Exception as e:
                    print(f"  Erro ao processar {arquivo.name}: {e}")
            print()

if __name__ == "__main__":
    calcular_tempos()