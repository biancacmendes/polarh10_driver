# Polar H10 BioSignal Capture Platform

Este projeto consiste numa plataforma integrada para a aquisição, processamento, streaming e persistência de biossinais em tempo real, focada no sinal de eletrocardiograma (ECG) e na variabilidade da frequência cardíaca (HRV) obtidos através do sensor Polar H10. O sistema combina um motor assíncrono de alto desempenho com uma interface gráfica multiplataforma desenvolvida em PyQt6, oferecendo suporte para protocolos experimentais controlados localmente ou de forma remota através de um ecossistema complementar de biofeedback.

## Arquitetura do Sistema

A plataforma foi projetada seguindo princípios de modularidade e separação de conceitos, dividindo-se em cinco camadas lógicas fundamentais:

1. Camada de Aquisição (Core)
Responsável por estabelecer e gerenciar a comunicação de baixa latência com o hardware Polar H10 via Bluetooth Low Energy (BLE). Baseia-se na biblioteca Bleak e implementa a ativação dos canais de telemetria Gatt específicos do fabricante através de comandos de inicialização de firmware (frequência de 130Hz com resolução de 14 bits). O fluxo de pacotes é indexado e depositado numa fila assíncrona (asyncio.Queue).

2. Camada de Processamento e Transmissão (Gateways)
Consome os dados brutos da fila assíncrona para executar algoritmos de detecção de picos R (R-peak detection) em tempo real. A partir dos intervalos entre batimentos (intervalos RR), deriva os indicadores de variabilidade cardíaca. Os dados consolidados são empacotados em estruturas JSON e distribuídos por servidores WebSockets internos para os consumidores locais ou na rede.

3. Camada de Gerenciamento de Sessão (App)
O componente SessionController monitora e valida o estado ativo das gravações, segregando as fases do protocolo para garantir que os dados fisiológicos fiquem perfeitamente alinhados com as etapas do estudo.

4. Camada de Persistência Otimizada (Storage)
O StorageManager centraliza os buffers de sinais em memória. Em vez de utilizar formatos de texto pesados durante a aquisição, a persistência é realizada através de matrizes binárias do NumPy (.npy) de ponto flutuante com dupla precisão (float64). Isto elimina o overhead de escrita no disco, prevenindo a perda de pacotes fisiológicos.

5. Camada de Interface Gráfica (UI)
Estruturada sob um modelo de janelas empilhadas (QStackedWidget) gerido pela classe MainWindow. Cada etapa do experimento possui uma página dedicada isolada, forçando o investigador a seguir uma sequência metodológica estrita para mitigar falhas operacionais em ambiente laboratorial.

## Estrutura Detalhada do Repositório

Abaixo encontra-se a organização completa dos ficheiros do projeto:

```bash
├── app
│   ├── __init__.py
│   ├── async_worker.py          (Gerenciador do ciclo de vida assíncrono e transições)
│   ├── constants.py             (Constantes globais, caminhos e configurações de tela)
│   ├── hub_launcher.py          (Orquestrador e trabalhador para execução de subprocessos OS)
│   ├── session_controller.py    (Controlador de estado das gravações estáticas e remotas)
│   └── storage_manager.py       (Gerenciador de gravação binária NumPy e buffers)
├── config
│   ├── config.yaml              (Parâmetros de inicialização do sensor e gateways)
│   └── data_loader.py           (Rotina de leitura e parsing de ficheiros de configuração)
├── core
│   ├── hrv_metrics.py           (Algoritmos de extração de métricas de HRV no domínio do tempo)
│   ├── polar_client.py          (Cliente BLE, manipulação de serviços Gatt e filas)
│   ├── rpeak_detector.py        (Processador de sinal para identificação de ondas R)
│   ├── signal_processor.py      (Filtros digitais para atenuação de ruído e harmónicos)
│   ├── websocket_gateway.py     (Servidor WebSocket de telemetria padrão)
│   └── websocket_gateway_dashboard.py (Servidor WebSocket alternativo com suporte visual)
├── data_captures
│   └── time_evaluation.py       (Script para validação de integridade temporal dos logs)
├── ui
│   ├── __init__.py
│   ├── main_window.py           (Janela principal PyQt6, conexões de sinais e slots)
│   └── pages
│       ├── __init__.py
│       ├── fixed_stage_page.py  (Painel da etapa fixa de 5 minutos com gráfico integrado)
│       ├── hub_boot_page.py     (Painel de verificação de prontidão e lançamento de serviços)
│       ├── hub_stage_page.py    (Painel de monitorização e gravação orientada pelo Hub)
│       ├── loading_page.py      (Painel de progresso da ligação Bluetooth inicial)
│       └── participant_page.py  (Formulário de triagem e recolha de metadados)
├── interface.py                 (Protótipo monolítico de teste de interface)
├── main_interface.py            (Ponto de entrada oficial para a aplicação gráfica)
├── main.py                      (Ponto de entrada oficial para execução em modo terminal)
├── requirements.txt             (Lista de dependências e bibliotecas do ecossistema)
├── venv_setup.sh                (Script bash para automação do ambiente virtual)
└── visualize.py                 (Módulo de pós-processamento, filtragem e geração de PDFs)
```


## Requisitos do Sistema e Dependências

Para garantir a execução correta de todos os módulos, certifique-se de preencher os seguintes pré-requisitos:

* Sistema Operacional: Linux (distribuições baseadas em Ubuntu/Debian são recomendadas devido à integração nativa estável do Bleak com o daemon BlueZ via D-Bus) ou macOS.
* Versão do Python: Python 3.12 estritamente. O script de automação rejeitará outras versões devido a compatibilidades de binários das bibliotecas PySide6/PyQt6 e NumPy.
* Node.js e NPM: Necessários caso pretenda utilizar as funcionalidades de dashboard do ecossistema hub-ue externo.
* Serviços de Sistema: Acesso ao systemctl para gerenciamento do serviço bluetooth local.

Mapeamento de Pastas do HubLauncher:
O ficheiro hub_launcher.py possui caminhos absolutos apontando para ~/Desktop/bianca/hub-ue/apps/hub e ~/Desktop/bianca/hub-ue. Caso o seu projeto esteja localizado noutro diretório do computador, altere obrigatoriamente as variáveis self.hub_dir e self.project_dir no construtor da classe HubLauncher antes de iniciar a execução da plataforma.

## Instalação e Preparação do Ambiente

### Instalação Automatizada
O projeto disponibiliza um script em bash que valida o interpretador, cria o ambiente isolado, atualiza os gerenciadores de pacotes e instala as dependências necessárias. Execute-o a partir da raiz do repositório:

chmod +x venv_setup.sh
./venv_setup.sh

### Instalação Manual
Caso prefira realizar os passos individualmente no seu terminal:

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

Se a sua distribuição Linux apresentar erros de timeout ou falhas ao indexar os descritores GATT do sensor Polar H10, limpe o cache do subsistema BlueZ reiniciando o serviço correspondente:

sudo systemctl restart bluetooth

## Execução da Plataforma

Para lançar a aplicação visual com todo o encadeamento de páginas e trabalhadores assíncronos em segundo plano, ative o ambiente virtual e execute o ponto de entrada gráfico:

source .venv/bin/activate
python main_interface.py

## Fluxo de Operação e Protocolo Experimental

A aplicação gráfica divide o processo de recolha de dados em cinco fases sequenciais acopladas a sinais lógicos:

Fase 1: Inicialização e Conectividade (LoadingPage)
O trabalhador CoreAsyncWorker inicia um loop assíncrono em segundo plano. Ele carrega as definições contidas em config/config.yaml, localiza o dispositivo Polar H10 via BleakScanner, estabelece o emparelhamento, subscreve as notificações da característica Gatt e abre as portas WebSocket. O progresso de cada etapa é reportado de 0 a 100% na barra visual da interface.

Fase 2: Inicialização do Ecossistema de Biofeedback (HubBootPage)
Após confirmar a estabilidade da ligação com o sensor, a interface avança para a ativação do Hub. Ao clicar em "Subir Biofeedback Hub", o HubLauncherWorker dispara recursivamente comandos em bash no modo headless para iniciar a API central do Hub, conectar a ponte de dados biofeedback-polarh10 e rodar o servidor de desenvolvimento do painel de controle web. O sistema aguarda os tempos de resposta de rede e atualiza a interface para o estado de prontidão.

Fase 3: Triagem e Cadastro do Participante (ParticipantPage)
Exibe um formulário estruturado para recolha de informações do sujeito do teste. Inclui campos para Nome Completo, Idade, Gênero, ingestão recente de Cafeína (menos de 6 horas) e Horas de Sono. O preenchimento do campo de nome é obrigatório para validação. Ao avançar, o sistema gera uma hash UUID truncada de 8 caracteres alfanuméricos maiúsculos que servirá como identificador exclusivo daquela sessão.

Fase 4: Etapa Estática / Linha de Base (FixedStagePage)
Fase dedicada à gravação de 5 minutos (300 segundos) de repouso para estabelecer a linha de base fisiológica do participante. Ao clicar em "Iniciar 5 Minutos", um QTimer regressivo de 1 segundo é acionado. O sinal elétrico do coração (ECG) é plotado dinamicamente no componente gráfico da página a uma taxa de atualização contínua. Ao esgotar o tempo, o sistema encerra os ficheiros automaticamente e muda de página de forma autônoma.

Fase 5: Etapa Sincronizada / Controle Remoto (HubStagePage)
Nesta fase, o controlo da persistência de dados é delegado ao ecossistema externo. O CoreAsyncWorker escuta ativamente o estado da variável recording_enabled vinda do gateway através de consultas de polling de 100ms. Quando o investigador clica em iniciar gravação no dashboard web externo (Node.js/React), a interface recebe o gatilho, altera o estado visual para "GRAVAÇÃO INICIADA PELO HUB" e passa a guardar as informações em disco com sincronização temporal absoluta com os estímulos externos.

## Especificação do Armazenamento de Dados

O armazenamento é estruturado de forma rigorosa pelo StorageManager dentro do diretório data_captures. Cada participante ganha uma pasta exclusiva nomeada com o padrão Nome_ID para evitar colisões de dados.

Os ficheiros gerados utilizam as seguintes nomenclaturas e formatos:

data_captures/
└── Nome_Completo_ID/
    ├── Nome_Completo_ID_Etapa_Fixa_5min_TIMESTAMP_ecg.npy
    ├── Nome_Completo_ID_Etapa_Fixa_5min_TIMESTAMP_hrv.npy
    ├── Nome_Completo_ID_Etapa_Sincronizada_Hub_TIMESTAMP_ecg.npy
    └── Nome_Completo_ID_Etapa_Sincronizada_Hub_TIMESTAMP_hrv.npy

Estrutura Interna dos Ficheiros Binários (.npy)
* Ficheiros ECG: Matriz NumPy bidimensional estruturada em duas colunas [Timestamp UNIX, Valor Bruto ECG em Microvolts]. Contém 130 amostras por segundo de gravação.
* Ficheiros HRV: Matriz NumPy tridimensional contendo as colunas [Timestamp UNIX, Intervalo RR em segundos, Frequência Cardíaca instantânea derivada]. As linhas são adicionadas dinamicamente apenas quando um pico R é validado pelo processador.

Os metadados clínicos do participante coletados na Fase 3 são armazenados na mesma pasta sob o formato de texto plano legível para auditoria analítica futura.

## Especificações de Rede e Formato JSON (WebSockets)

O ecossistema opera com separação de tráfego através de três portas e rotas locais distintas:

* Canal de Telemetria (ws://localhost:8765/stream): Canal unidirecional de streaming contínuo contendo os vetores de amostras elétricas e o dicionário com as últimas métricas calculadas pela pipeline core.
* Canal de Coordenação (ws://localhost:8765/control): Canal focado no recebimento e processamento de instruções de configuração e sinalização de estados.
* Canal da Ponte Externa (ws://127.0.0.1:8787/ws): Rota de comunicação dedicada para acoplamento do fluxo de telemetria com as aplicações web do ecossistema hub-ue.

Modelo estrutural do payload JSON emitido pelo servidor na rota stream:

{
  "seq": 2481,
  "samples": [142, 145, 139, 131, 125, 133],
  "metrics": {
    "rr": 0.842,
    "hr": 71.2,
    "rmssd": 35.8,
    "sdnn": 42.1,
    "pnn50": 0.15,
    "lf_hf": 1.6
  }
}

## Módulo de Visualização e Análise Analítica

Para além do processamento em tempo real, o repositório inclui a ferramenta visualize.py encarregue do pós-processamento estatístico dos dados acumulados no laboratório. 

O script realiza as seguintes operações matemáticas:
1. Carrega as matrizes NumPy (.npy) de ECG e HRV correspondentes a todas as etapas de uma sessão (Repouso, Sincronizada 1 e Sincronizada 2).
2. Converte os índices e reconstrói as linhas de tempo com base na amostragem nominal de 130Hz.
3. Aplica um filtro de média móvel uniforme (scipy.ndimage.uniform_filter1d) com uma janela parametrizada de 30 pontos sobre a série de intervalos RR para remover batimentos ectópicos e ruídos de leitura mecânica.
4. Gera relatórios gráficos vetoriais de alta fidelidade sobrepostos e divididos por subfiguras com escalas de amplitude e tempo equalizadas de forma idêntica.
5. Exporta automaticamente os resultados finais em formato PDF para uma pasta denominada plots dentro do diretório do próprio participante.

Para rodar o gerador de relatórios analíticos:
python visualize.py

Nota de Configuração: Antes de executar o script de visualização, abra o ficheiro visualize.py e atualize o objeto PATIENT_DIR localizado no topo do arquivo com o caminho absoluto da pasta do participante que deseja analisar.

## Resolução de Problemas Comuns (Troubleshooting)

1. Interface Congelada na Fase de Carregamento
Isto ocorre quando o daemon do Bluetooth no Linux bloqueia o socket do dispositivo ou quando o endereço MAC do sensor foi alterado. Verifique se o endereço inserido no ficheiro config/config.yaml condiz com o identificador impresso na etiqueta física da sua cinta Polar H10 e aplique um reinício forçado no serviço de bluetooth do sistema operacional.

2. O Botão Continuar Não Ativa na Fase do Hub
Significa que um dos três subprocessos disparados pelo HubLauncherWorker falhou ao tentar inicializar. Certifique-se de que navegou até às pastas do hub-ue usando o seu terminal externo e executou a instalação das dependências do Node.js através do comando npm install antes de tentar rodar a plataforma unificada em Python. Verifique também se nenhuma outra aplicação local está a utilizar as portas lógicas 8765, 8787 ou 5173.

## Licença

NA
