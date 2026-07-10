# Polar H10 Driver

Aplicação desktop para aquisição de ECG com a cinta Polar H10, visualização em tempo real, gravação de baseline por cinco minutos e integração com o Biofeedback Hub para sessões de realidade virtual.

## Funcionalidades

- Conexão com a Polar H10 via Bluetooth
- Aquisição contínua de ECG
- Visualização do sinal em tempo real
- Gravação de baseline de cinco minutos
- Integração com Biofeedback Hub e dashboard
- Controle remoto de gravação por comandos `START` e `STOP`
- Armazenamento de ECG e HRV em arquivos `.npy`

## Requisitos

- Python 3.11 ou 3.12
- Bluetooth habilitado
- Polar H10 disponível e não conectada a outro aplicativo
- Node.js e npm para o dashboard
- Biofeedback Hub configurado
- Linux ou macOS para o fluxo atual de inicialização dos processos

## Instalação

Clone o repositório e acesse a pasta:

```bash
git clone <URL_DO_REPOSITORIO>
cd polarh10_driver
```

Crie o ambiente virtual:

```bash
python3 -m venv .venv
```

Ative o ambiente:

```bash
source .venv/bin/activate
```

Atualize o pip:

```bash
python -m pip install --upgrade pip
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Configuração

O arquivo principal de configuração está em:

```text
config/config.yaml
```

Revise os parâmetros relacionados a:

- identificação da Polar H10
- portas WebSocket
- visualização
- filtros e processamento
- opções do dashboard

As principais constantes da aplicação estão em:

```text
app/constants.py
```

A duração padrão do baseline é:

```python
CAPTURE_DURATION_SECONDS = 300
```

Os dados são salvos por padrão em:

```text
data_captures/
```

## Configuração do Biofeedback Hub

Os caminhos do Hub estão definidos em:

```text
app/hub_launcher.py
```

Ajuste estes diretórios conforme a localização do projeto no computador:

```python
self.hub_dir = os.path.expanduser(
    "~/Desktop/bianca/hub-ue/apps/hub"
)

self.project_dir = os.path.expanduser(
    "~/Desktop/bianca/hub-ue"
)
```

O launcher inicia:

1. Biofeedback Hub
2. Ponte Polar H10
3. Dashboard

Endereços utilizados:

```text
Polar stream:  ws://localhost:8765/stream
Polar control: ws://localhost:8765/control
Hub:           ws://127.0.0.1:8787/ws
Dashboard:     http://127.0.0.1:5173
```

Antes de usar a interface, confirme que os seguintes comandos funcionam manualmente.

Biofeedback Hub:

```bash
cd ~/Desktop/bianca/hub-ue/apps/hub
source .venv/bin/activate
biofeedback-hub
```

Ponte Polar H10:

```bash
biofeedback-polarh10 \
    --polar-ws "ws://localhost:8765/stream" \
    --polar-control-ws "ws://localhost:8765/control" \
    --hub-ws "ws://127.0.0.1:8787/ws"
```

Dashboard:

```bash
cd ~/Desktop/bianca/hub-ue
npm install
npm run dev:dashboard
```

## Execução

Execute sempre a partir da raiz do projeto:

```bash
cd polarh10_driver
source .venv/bin/activate
python main_interface.py
```

## Fluxo da interface

### 1. Conexão com a Polar H10

Ao iniciar a aplicação:

- o arquivo de configuração é carregado
- a Polar H10 é localizada
- a conexão Bluetooth é estabelecida
- o stream de ECG é iniciado
- o gateway WebSocket é inicializado

### 2. Inicialização do Hub

Após a conexão com a cinta:

- pressione o botão para iniciar o Biofeedback Hub
- aguarde a inicialização da ponte Polar
- aguarde a inicialização do dashboard
- pressione o botão para continuar

### 3. Cadastro do participante

Preencha os campos da interface e avance para a etapa de baseline.

### 4. Baseline de ECG

Na etapa de baseline:

- pressione o botão de início
- a aplicação registra ECG e HRV por cinco minutos
- o gráfico é atualizado em tempo real
- os dados são salvos automaticamente ao final

### 5. Etapa de realidade virtual

Após o baseline, a aplicação aguarda os comandos do Hub.

Quando o Hub envia:

```text
START
```

a gravação é iniciada.

Quando o Hub envia:

```text
STOP
```

a gravação é encerrada e os arquivos são salvos.

## Dados salvos

Os arquivos são armazenados em:

```text
data_captures/
```

Estrutura aproximada:

```text
data_captures/
└── Nome_ID/
    ├── Nome_ID_Etapa_Fixa_5min_timestamp_ecg.npy
    ├── Nome_ID_Etapa_Fixa_5min_timestamp_hrv.npy
    ├── Nome_ID_Etapa_Hub_timestamp_ecg.npy
    └── Nome_ID_Etapa_Hub_timestamp_hrv.npy
```

### ECG

Cada linha contém:

```text
timestamp, valor_ecg
```

### HRV

Cada linha contém:

```text
timestamp, intervalo_rr, frequência_cardíaca
```

Exemplo de leitura:

```python
import numpy as np

ecg = np.load("arquivo_ecg.npy")
hrv = np.load("arquivo_hrv.npy")

print(ecg.shape)
print(hrv.shape)
```

## Estrutura principal

```text
polarh10_driver/
├── app/
├── config/
├── core/
├── data_captures/
├── test/
├── ui/
├── main_interface.py
├── requirements.txt
└── venv_setup.sh
```

Principais módulos:

```text
app/async_worker.py
    Worker assíncrono responsável pela Polar H10 e pelo gateway.

app/hub_launcher.py
    Inicialização e encerramento do Biofeedback Hub.

app/session_controller.py
    Controle dos estados de gravação.

app/storage_manager.py
    Armazenamento dos buffers e criação dos arquivos NPY.

core/polar_client.py
    Comunicação com a Polar H10.

core/signal_processor.py
    Processamento do ECG.

core/rpeak_detector.py
    Detecção dos picos R.

core/hrv_metrics.py
    Cálculo das métricas de HRV.

ui/main_window.py
    Coordenação da interface e das etapas experimentais.
```

## Testes

Para buscar dispositivos Bluetooth:

```bash
python test/scan.py
```

Para executar os testes disponíveis:

```bash
pytest
```

## Problemas comuns

### Polar H10 não encontrada

Verifique:

- Bluetooth habilitado
- cinta posicionada corretamente
- eletrodos umedecidos
- bateria da cinta
- ausência de conexão com outro aplicativo
- permissões Bluetooth do sistema

### Arquivo de configuração não encontrado

Execute a aplicação a partir da raiz:

```bash
cd polarh10_driver
python main_interface.py
```

### Hub não inicia

Teste manualmente:

```bash
biofeedback-hub
```

```bash
biofeedback-polarh10 \
    --polar-ws "ws://localhost:8765/stream" \
    --polar-control-ws "ws://localhost:8765/control" \
    --hub-ws "ws://127.0.0.1:8787/ws"
```

```bash
npm run dev:dashboard
```

### Porta ocupada

Verifique as portas:

```bash
lsof -i :8765
lsof -i :8787
lsof -i :5173
```

### Arquivos não foram salvos

Verifique:

- se a gravação foi iniciada
- se a Polar estava enviando amostras
- se a pasta `data_captures/` possui permissão de escrita
- se há espaço disponível em disco
- se ocorreu algum erro no terminal

## Encerramento

Ao fechar a aplicação, o sistema tenta:

- parar gravações ativas
- salvar os dados pendentes
- desconectar a Polar H10
- encerrar os gateways
- encerrar os processos do Hub
- finalizar as threads da interface

## Observação sobre os dados

A implementação atual utiliza o nome do participante nos nomes de pastas e arquivos.

Para estudos com participantes humanos, recomenda-se utilizar um identificador anonimizado, como:

```text
P001
P002
P003
```

## Execução rápida

```bash
git clone <URL_DO_REPOSITORIO>
cd polarh10_driver

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python main_interface.py
```
