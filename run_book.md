# Runbook Operacional
## Plataforma de Captura Polar H10 com Biofeedback Hub

## 1. Objetivo

Este runbook descreve o procedimento operacional para preparar, iniciar, executar, monitorar e encerrar uma sessão de aquisição de ECG e HRV com a cinta Polar H10, incluindo:

- conexão Bluetooth com a Polar H10;
- inicialização da aplicação desktop;
- inicialização do Biofeedback Hub;
- inicialização da ponte Polar H10;
- inicialização do dashboard;
- cadastro do participante;
- gravação de baseline de cinco minutos;
- gravação da etapa de realidade virtual;
- salvamento dos arquivos `.npy`;
- verificação dos dados;
- tratamento de falhas;
- encerramento seguro do sistema.

O documento deve ser seguido antes, durante e após cada sessão experimental.

---

# 2. Escopo

Este runbook se aplica ao pacote:

```text
polarh10_driver
```

Ponto de entrada principal:

```text
main_interface.py
```

A aplicação utiliza:

- Python;
- PyQt6;
- asyncio;
- Bluetooth Low Energy;
- Polar H10;
- WebSocket;
- Biofeedback Hub;
- Node.js e npm;
- arquivos NumPy no formato `.npy`.

---

# 3. Fluxo operacional resumido

```text
Preparar computador
    ↓
Preparar Polar H10
    ↓
Ativar ambiente virtual
    ↓
Executar main_interface.py
    ↓
Conectar com a Polar H10
    ↓
Subir Biofeedback Hub
    ↓
Subir ponte Polar H10
    ↓
Subir dashboard
    ↓
Cadastrar participante
    ↓
Gravar baseline de 5 minutos
    ↓
Salvar baseline
    ↓
Aguardar comando START do Hub VR
    ↓
Gravar sessão VR
    ↓
Receber comando STOP
    ↓
Salvar sessão VR
    ↓
Finalizar sessão
    ↓
Verificar arquivos
    ↓
Fazer backup
```

---

# 4. Responsabilidades

## 4.1 Operador da coleta

O operador deve:

- verificar o ambiente;
- preparar o equipamento;
- iniciar os serviços;
- confirmar a conexão com a Polar H10;
- acompanhar o baseline;
- monitorar a gravação da etapa VR;
- verificar o salvamento dos arquivos;
- registrar ocorrências;
- realizar o encerramento seguro.

## 4.2 Pesquisador responsável

O pesquisador responsável deve:

- manter o protocolo atualizado;
- garantir a anonimização dos participantes;
- verificar a conformidade ética;
- definir o local seguro de armazenamento;
- revisar os dados após a coleta;
- manter versões estáveis do software.

## 4.3 Equipe técnica

A equipe técnica deve:

- manter o ambiente Python;
- manter o Biofeedback Hub;
- manter o dashboard;
- revisar falhas de conexão;
- validar alterações no código;
- garantir compatibilidade das dependências;
- manter os arquivos de configuração.

---

# 5. Pré-requisitos

## 5.1 Hardware

- computador com Bluetooth funcional;
- cinta Polar H10;
- faixa torácica compatível;
- bateria da Polar H10 com carga adequada;
- headset de realidade virtual;
- rede local funcional, quando necessária;
- espaço livre em disco;
- acesso ao projeto Biofeedback Hub.

## 5.2 Software

- Python 3.11 ou 3.12;
- ambiente virtual Python;
- dependências instaladas;
- Node.js;
- npm;
- Biofeedback Hub;
- utilitário `biofeedback-polarh10`;
- dashboard configurado;
- permissões Bluetooth;
- terminal Bash em Linux ou macOS.

## 5.3 Arquivos obrigatórios

Verificar a existência de:

```text
main_interface.py
requirements.txt
config/config.yaml
app/constants.py
app/hub_launcher.py
core/polar_client.py
ui/main_window.py
```

## 5.4 Diretórios obrigatórios

Verificar a existência ou possibilidade de criação de:

```text
data_captures/
logging/
```

---

# 6. Estrutura esperada do projeto

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
├── venv_setup.sh
└── README.md
```

---

# 7. Preparação inicial do ambiente

## 7.1 Acessar o projeto

Abra o terminal:

```bash
cd /caminho/para/polarh10_driver
```

Confirme o diretório:

```bash
pwd
```

Liste os arquivos:

```bash
ls
```

Confirme a presença de:

```text
main_interface.py
requirements.txt
config/
app/
core/
ui/
```

---

# 8. Criação do ambiente virtual

Este procedimento é necessário apenas na primeira instalação ou após remoção do ambiente.

## 8.1 Criar o ambiente

```bash
python3 -m venv .venv
```

## 8.2 Ativar o ambiente

Linux ou macOS:

```bash
source .venv/bin/activate
```

## 8.3 Confirmar o ambiente

```bash
which python
```

O caminho deve apontar para:

```text
polarh10_driver/.venv/bin/python
```

## 8.4 Atualizar ferramentas de instalação

```bash
python -m pip install --upgrade pip setuptools wheel
```

## 8.5 Instalar dependências

```bash
pip install -r requirements.txt
```

## 8.6 Validar instalação

```bash
python -c "import PyQt6"
python -c "import numpy"
python -c "import pyqtgraph"
```

Caso o pacote use `bleak`, validar:

```bash
python -c "import bleak"
```

---

# 9. Uso do script de configuração

Caso o projeto utilize `venv_setup.sh`:

```bash
chmod +x venv_setup.sh
./venv_setup.sh
```

Após a execução:

```bash
source .venv/bin/activate
```

Confirme as dependências:

```bash
pip list
```

---

# 10. Configuração da aplicação

## 10.1 Arquivo principal

O arquivo de configuração está localizado em:

```text
config/config.yaml
```

Antes da coleta, revisar:

- identificação do dispositivo;
- endereço Bluetooth, quando aplicável;
- host do gateway;
- portas WebSocket;
- opções de visualização;
- processamento de sinal;
- filtros;
- cálculo de HRV;
- parâmetros de amostragem;
- comportamento do dashboard.

## 10.2 Constantes

As constantes gerais estão em:

```text
app/constants.py
```

Itens principais:

```python
CONFIG_PATH = "config/config.yaml"
DATA_ROOT_FOLDER = "data_captures"
CAPTURE_DURATION_SECONDS = 300
MAX_PLOT_POINTS = 300
```

## 10.3 Baseline

A duração padrão é:

```text
300 segundos
```

Equivalente a:

```text
5 minutos
```

## 10.4 Diretório de saída

Os dados são salvos em:

```text
data_captures/
```

Verificar permissão:

```bash
touch data_captures/test_write.tmp
rm data_captures/test_write.tmp
```

---

# 11. Configuração do Biofeedback Hub

## 11.1 Caminhos

Revisar:

```text
app/hub_launcher.py
```

Valores atuais esperados:

```python
self.hub_dir = os.path.expanduser(
    "~/Desktop/bianca/hub-ue/apps/hub"
)

self.project_dir = os.path.expanduser(
    "~/Desktop/bianca/hub-ue"
)
```

Substituir pelos caminhos reais da máquina.

## 11.2 Endpoints utilizados

```text
Polar stream:
ws://localhost:8765/stream
```

```text
Polar control:
ws://localhost:8765/control
```

```text
Hub:
ws://127.0.0.1:8787/ws
```

```text
Dashboard:
http://127.0.0.1:5173
```

## 11.3 Validar o ambiente do Hub

```bash
cd ~/Desktop/bianca/hub-ue/apps/hub
source .venv/bin/activate
```

Validar o comando:

```bash
which biofeedback-hub
```

Validar a ponte:

```bash
which biofeedback-polarh10
```

## 11.4 Validar Node.js

```bash
node --version
npm --version
```

## 11.5 Instalar dependências do dashboard

```bash
cd ~/Desktop/bianca/hub-ue
npm install
```

---

# 12. Teste manual dos serviços

Antes da primeira coleta, testar os serviços separadamente.

## 12.1 Terminal 1: Hub

```bash
cd ~/Desktop/bianca/hub-ue/apps/hub
source .venv/bin/activate
biofeedback-hub
```

Confirmar que o processo permanece ativo.

## 12.2 Terminal 2: ponte Polar

```bash
cd ~/Desktop/bianca/hub-ue/apps/hub
source .venv/bin/activate

biofeedback-polarh10 \
    --polar-ws "ws://localhost:8765/stream" \
    --polar-control-ws "ws://localhost:8765/control" \
    --hub-ws "ws://127.0.0.1:8787/ws"
```

## 12.3 Terminal 3: dashboard

```bash
cd ~/Desktop/bianca/hub-ue
npm run dev:dashboard
```

## 12.4 Validar dashboard

Abrir:

```text
http://127.0.0.1:5173
```

## 12.5 Encerrar testes manuais

Pressionar:

```text
Ctrl + C
```

em cada terminal.

---

# 13. Verificação de portas

Antes da coleta:

```bash
lsof -i :8765
lsof -i :8787
lsof -i :5173
```

Resultado esperado antes da inicialização:

```text
nenhum processo utilizando as portas
```

Caso existam processos antigos, encerrar com cautela:

```bash
kill <PID>
```

Caso necessário:

```bash
kill -9 <PID>
```

Utilizar `kill -9` apenas quando o processo não responder ao encerramento normal.

---

# 14. Preparação da Polar H10

## 14.1 Preparação física

1. Umedecer os eletrodos da faixa.
2. Conectar o módulo Polar H10 à faixa.
3. Posicionar a cinta no tórax.
4. Ajustar a faixa para contato firme.
5. Confirmar que o participante está confortável.

## 14.2 Verificações

Confirmar:

- bateria adequada;
- cinta próxima ao computador;
- Bluetooth habilitado;
- Polar Flow ou outro aplicativo fechado;
- ausência de conexão concorrente;
- sensor corretamente posicionado.

## 14.3 Teste de detecção

Executar:

```bash
python test/scan.py
```

Confirmar que a Polar H10 aparece na lista.

---

# 15. Preparação do participante

Antes da coleta:

- confirmar o código do participante;
- confirmar consentimento;
- revisar critérios de inclusão e exclusão;
- registrar consumo de cafeína;
- registrar horas de sono;
- verificar condições que possam interferir no ECG;
- orientar o participante a reduzir movimentos;
- explicar as etapas do procedimento;
- confirmar que o participante está confortável.

Evitar utilizar o nome completo nos arquivos quando o protocolo exigir anonimização.

---

# 16. Checklist pré-coleta

Antes de executar a aplicação, confirmar:

```text
[ ] Computador ligado
[ ] Fonte de energia conectada
[ ] Bluetooth habilitado
[ ] Polar H10 posicionada
[ ] Eletrodos umedecidos
[ ] Participante confortável
[ ] Headset VR preparado
[ ] Ambiente virtual ativo
[ ] Dependências instaladas
[ ] Configuração revisada
[ ] Caminhos do Hub corretos
[ ] Portas disponíveis
[ ] Dashboard instalado
[ ] Diretório de dados com escrita
[ ] Espaço em disco disponível
[ ] Relógio do sistema correto
[ ] Código do participante definido
```

---

# 17. Inicialização da aplicação

## 17.1 Abrir o terminal

```bash
cd /caminho/para/polarh10_driver
```

## 17.2 Ativar o ambiente

```bash
source .venv/bin/activate
```

## 17.3 Executar

```bash
python main_interface.py
```

## 17.4 Resultado esperado

A aplicação deve abrir uma janela com:

- tela de carregamento;
- mensagem de status;
- barra de progresso;
- botão de cancelamento.

---

# 18. Tela de carregamento

Durante a inicialização, a aplicação executa:

1. carregamento da configuração;
2. busca da Polar H10;
3. conexão Bluetooth;
4. início do stream de ECG;
5. inicialização do gateway;
6. início do processamento interno.

Mensagens esperadas:

```text
Carregando arquivos de configuração
Buscando sensor Polar H10 via Bluetooth
Ativando canais de transmissão internos
Inicializando portas do WebSocket Gateway
Todos os sistemas online
```

## 18.1 Critério de sucesso

A aplicação deve avançar automaticamente para a tela de inicialização do Hub.

## 18.2 Critério de falha

Considerar falha quando:

- a Polar não é encontrada;
- a aplicação fica indefinidamente na busca;
- ocorre exceção no terminal;
- o gateway não inicia;
- a interface deixa de responder.

---

# 19. Inicialização do Hub pela interface

Na tela do Hub:

1. pressionar o botão de inicialização;
2. aguardar a subida do Biofeedback Hub;
3. aguardar a subida da ponte Polar;
4. aguardar a subida do dashboard;
5. confirmar que o botão de continuar foi habilitado;
6. pressionar continuar.

## 19.1 Serviços esperados

```text
Biofeedback Hub
biofeedback-polarh10
npm run dev:dashboard
```

## 19.2 Verificação independente

Em outro terminal:

```bash
lsof -i :8787
lsof -i :5173
```

Abrir:

```text
http://127.0.0.1:5173
```

## 19.3 Critério de sucesso

- Hub ativo;
- ponte ativa;
- dashboard acessível;
- interface habilita continuação.

---

# 20. Cadastro do participante

Preencher:

- nome ou código;
- idade;
- gênero;
- consumo de cafeína;
- horas de sono;
- observações.

Recomenda-se utilizar:

```text
P001
P002
P003
```

em vez do nome completo.

## 20.1 Validação manual

Antes de avançar:

```text
[ ] Identificador correto
[ ] Idade correta
[ ] Gênero preenchido
[ ] Cafeína registrada
[ ] Horas de sono registradas
[ ] Observações revisadas
```

---

# 21. Gravação do baseline

## 21.1 Preparação

Antes de iniciar:

- participante sentado ou em posição definida pelo protocolo;
- sem falar;
- sem movimentos excessivos;
- respiração espontânea;
- headset ainda não iniciado, quando aplicável;
- ECG visível no gráfico;
- sinal sem perda evidente.

## 21.2 Iniciar

Pressionar:

```text
Iniciar 5 Minutos
```

## 21.3 Comportamento esperado

- contador inicia em 05:00;
- botão de início é desabilitado;
- ECG continua sendo exibido;
- amostras são adicionadas ao buffer;
- HRV é armazenada quando disponível;
- ao final, os arquivos são salvos;
- a interface avança para a etapa do Hub.

## 21.4 Monitoramento

Durante o baseline, observar:

- continuidade do ECG;
- ausência de saturação;
- ausência de sinal constante;
- ausência de perda de contato;
- estabilidade da interface;
- contador regressivo;
- mensagens no terminal.

## 21.5 Interrupção

Interromper a sessão quando ocorrer:

- desconforto do participante;
- perda persistente do ECG;
- erro crítico da aplicação;
- desconexão da cinta;
- queda de energia;
- falha do computador;
- violação do protocolo.

Registrar a ocorrência.

## 21.6 Critério de sucesso

- duração concluída;
- arquivo ECG criado;
- arquivo HRV criado;
- dados não vazios;
- avanço para a etapa VR.

---

# 22. Etapa controlada pelo Hub VR

Após o baseline, a interface entra em estado de espera.

## 22.1 Estado inicial

A interface deve indicar:

```text
Aguardando comando do Hub
```

## 22.2 Comando START

Quando o Hub ativa:

```text
recording_enabled = true
```

o worker emite:

```text
START
```

A aplicação deve:

- preparar o armazenamento;
- iniciar a gravação;
- atualizar o estado visual;
- armazenar ECG;
- armazenar HRV.

## 22.3 Durante a gravação

Confirmar:

- indicador de aquisição ativo;
- ECG sendo atualizado;
- experiência VR em execução;
- Hub conectado;
- ausência de erros no terminal;
- participante sendo monitorado.

## 22.4 Comando STOP

Quando o Hub desativa:

```text
recording_enabled = false
```

o worker emite:

```text
STOP
```

A aplicação deve:

- parar a gravação;
- salvar ECG;
- salvar HRV;
- atualizar o estado visual.

## 22.5 Critério de sucesso

- START recebido;
- gravação ativa;
- STOP recebido;
- arquivos salvos;
- interface indica finalização.

---

# 23. Finalização da sessão

Após a etapa VR:

1. confirmar que a gravação foi finalizada;
2. confirmar que os arquivos foram salvos;
3. pressionar o botão de finalizar;
4. fechar a interface;
5. aguardar o encerramento dos processos;
6. verificar que as portas foram liberadas.

## 23.1 Verificar portas

```bash
lsof -i :8765
lsof -i :8787
lsof -i :5173
```

## 23.2 Encerrar processos residuais

Listar:

```bash
ps aux | grep biofeedback
ps aux | grep npm
ps aux | grep node
```

Encerrar quando necessário:

```bash
kill <PID>
```

---

# 24. Verificação dos arquivos

## 24.1 Localizar a pasta

```bash
find data_captures -maxdepth 2 -type f
```

## 24.2 Estrutura esperada

```text
data_captures/
└── Participante_ID/
    ├── *_Etapa_Fixa_5min_*_ecg.npy
    ├── *_Etapa_Fixa_5min_*_hrv.npy
    ├── *_Etapa_Hub_*_ecg.npy
    └── *_Etapa_Hub_*_hrv.npy
```

## 24.3 Verificar tamanho

```bash
ls -lh data_captures/Participante_ID/
```

Arquivos com poucos bytes ou tamanho zero indicam falha.

## 24.4 Carregar os arquivos

```python
import numpy as np

ecg = np.load("arquivo_ecg.npy")
hrv = np.load("arquivo_hrv.npy")

print("ECG:", ecg.shape)
print("HRV:", hrv.shape)

print(ecg[:5])
print(hrv[:5])
```

## 24.5 Verificar conteúdo

O ECG deve ter duas colunas:

```text
timestamp
valor_ecg
```

A HRV deve ter três colunas:

```text
timestamp
intervalo_rr
frequência_cardíaca
```

## 24.6 Critérios mínimos

```text
[ ] Arquivo ECG existe
[ ] Arquivo HRV existe
[ ] ECG possui amostras
[ ] HRV possui amostras
[ ] Valores não são todos zero
[ ] Timestamps existem
[ ] Nomes das etapas estão corretos
[ ] Participante correto
```

---

# 25. Backup dos dados

Após cada sessão:

1. copiar os arquivos para armazenamento seguro;
2. verificar integridade;
3. manter a cópia original;
4. registrar o identificador da sessão;
5. evitar compartilhamento de dados identificáveis.

Exemplo:

```bash
rsync -av data_captures/P001_ID/ /caminho/seguro/P001_ID/
```

Gerar checksum:

```bash
shasum -a 256 data_captures/P001_ID/*
```

Salvar os hashes em arquivo:

```bash
shasum -a 256 data_captures/P001_ID/* \
    > data_captures/P001_ID/checksums.sha256
```

---

# 26. Registro de ocorrências

Após a sessão, registrar:

- código do participante;
- data;
- horário de início;
- horário de término;
- operador;
- status do baseline;
- status da etapa VR;
- perda de conexão;
- interrupções;
- movimentos relevantes;
- problemas no headset;
- problemas no Hub;
- arquivos gerados;
- necessidade de repetir a sessão.

Modelo:

```text
Participante:
Data:
Operador:
Baseline:
Etapa VR:
Arquivos:
Ocorrências:
Ação corretiva:
Resultado final:
```

---

# 27. Procedimento de encerramento normal

1. Finalizar gravação no Hub.
2. Confirmar comando STOP.
3. Confirmar salvamento.
4. Finalizar sessão na interface.
5. Fechar a janela.
6. Confirmar encerramento da Polar.
7. Confirmar encerramento dos gateways.
8. Confirmar encerramento do Hub.
9. Confirmar encerramento do dashboard.
10. Verificar os arquivos.
11. Realizar backup.

---

# 28. Procedimento de encerramento de emergência

Utilizar quando a interface não responde.

## 28.1 Interromper pelo terminal

```text
Ctrl + C
```

## 28.2 Localizar o processo

```bash
ps aux | grep main_interface.py
```

## 28.3 Encerrar

```bash
kill <PID>
```

## 28.4 Encerramento forçado

```bash
kill -9 <PID>
```

## 28.5 Encerrar serviços auxiliares

```bash
pkill -f biofeedback-hub
pkill -f biofeedback-polarh10
pkill -f "npm run dev:dashboard"
```

## 28.6 Verificar arquivos parciais

```bash
find data_captures -type f -mmin -10
```

Como os dados são mantidos em memória até o salvamento, uma interrupção abrupta pode causar perda da sessão ativa.

---

# 29. Troubleshooting

## 29.1 Ambiente virtual não ativa

Erro possível:

```text
No such file or directory
```

Solução:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 29.2 Dependência ausente

Erro:

```text
ModuleNotFoundError
```

Solução:

```bash
pip install -r requirements.txt
```

Para um módulo específico:

```bash
pip install <nome_do_pacote>
```

---

## 29.3 Polar H10 não encontrada

Verificar:

- Bluetooth;
- bateria;
- faixa;
- eletrodos;
- distância;
- aplicativos concorrentes;
- permissões;
- endereço configurado.

Executar:

```bash
python test/scan.py
```

Reiniciar a cinta:

1. remover o módulo da faixa;
2. aguardar alguns segundos;
3. reconectar;
4. repetir a busca.

---

## 29.4 Polar aparece, mas não conecta

Verificar:

- outro aplicativo conectado;
- cache Bluetooth;
- permissões do sistema;
- backend BLE;
- endereço incorreto;
- serviço GATT indisponível.

Ações:

```text
1. Fechar outros aplicativos
2. Desativar e reativar Bluetooth
3. Reiniciar a Polar
4. Reiniciar a aplicação
5. Reiniciar o computador
```

---

## 29.5 Aplicação fecha ao iniciar

Executar pelo terminal:

```bash
python main_interface.py
```

Analisar o traceback.

Possíveis causas:

- erro no YAML;
- dependência ausente;
- importação incorreta;
- caminho inválido;
- erro na interface;
- falha no backend Bluetooth.

---

## 29.6 Arquivo YAML inválido

Validar:

```bash
python -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"
```

Verificar:

- indentação;
- dois-pontos;
- aspas;
- listas;
- valores booleanos.

---

## 29.7 Hub não inicia

Testar manualmente:

```bash
cd ~/Desktop/bianca/hub-ue/apps/hub
source .venv/bin/activate
biofeedback-hub
```

Verificar:

```bash
which biofeedback-hub
```

Reinstalar o pacote, quando necessário.

---

## 29.8 Ponte Polar não inicia

Testar:

```bash
biofeedback-polarh10 \
    --polar-ws "ws://localhost:8765/stream" \
    --polar-control-ws "ws://localhost:8765/control" \
    --hub-ws "ws://127.0.0.1:8787/ws"
```

Verificar:

- porta 8765;
- porta 8787;
- Hub ativo;
- gateway Polar ativo;
- comando instalado.

---

## 29.9 Dashboard não inicia

Verificar:

```bash
node --version
npm --version
```

Instalar dependências:

```bash
npm install
```

Executar:

```bash
npm run dev:dashboard
```

---

## 29.10 Dashboard inacessível

Verificar:

```bash
lsof -i :5173
```

Abrir:

```text
http://127.0.0.1:5173
```

Se a porta mudou, revisar o terminal do npm.

---

## 29.11 Porta ocupada

Listar:

```bash
lsof -i :8765
lsof -i :8787
lsof -i :5173
```

Encerrar:

```bash
kill <PID>
```

---

## 29.12 Baseline não inicia

Verificar:

- botão habilitado;
- participante cadastrado;
- sessão anterior encerrada;
- worker ativo;
- Polar enviando dados;
- ausência de exceções.

---

## 29.13 Contador não atualiza

Verificar:

- timer Qt;
- thread principal não bloqueada;
- estado de gravação;
- logs no terminal.

---

## 29.14 ECG não aparece

Verificar:

- stream ativo;
- dados recebidos;
- formato do pacote;
- chave `ecg`;
- sinal `data_emitted`;
- contato físico da cinta;
- gráfico ativo.

---

## 29.15 ECG constante ou saturado

Verificar:

- eletrodos secos;
- cinta frouxa;
- mau contato;
- artefato de movimento;
- problema na unidade;
- erro no processamento.

Ação:

1. interromper a coleta;
2. reposicionar a cinta;
3. umedecer os eletrodos;
4. repetir o teste.

---

## 29.16 Comando START não chega

Verificar:

- Hub ativo;
- gateway ativo;
- `recording_enabled`;
- conexão WebSocket;
- página do Hub aberta;
- estado anterior;
- mensagens do terminal.

---

## 29.17 Comando STOP não chega

Verificar:

- estado remoto;
- conexão com o Hub;
- lógica de alteração de estado;
- desconexão WebSocket.

Caso necessário, finalizar manualmente a sessão e registrar a ocorrência.

---

## 29.18 Arquivos não são salvos

Verificar:

```bash
ls -ld data_captures
```

Testar escrita:

```bash
touch data_captures/test.tmp
rm data_captures/test.tmp
```

Verificar:

- buffers;
- sessão ativa;
- chamada de `save()`;
- espaço em disco;
- erro no terminal.

---

## 29.19 Arquivos vazios

Possíveis causas:

- gravação não iniciou;
- Polar não enviou dados;
- sessão terminou imediatamente;
- buffer foi limpo;
- formato do pacote incompatível.

---

## 29.20 Processo permanece ativo após fechar

Verificar:

```bash
ps aux | grep biofeedback
ps aux | grep node
```

Encerrar:

```bash
pkill -f biofeedback-hub
pkill -f biofeedback-polarh10
pkill -f "npm run dev:dashboard"
```

---

# 30. Critérios de abortamento da coleta

Abortar a sessão quando ocorrer:

- desconforto do participante;
- perda persistente do sinal;
- falha do headset;
- falha do Hub;
- falha do dashboard;
- ausência de START;
- ausência de STOP;
- corrupção dos dados;
- travamento da interface;
- erro de sincronização;
- queda de energia;
- violação do protocolo.

Sempre registrar:

```text
motivo
horário
etapa
ação tomada
status dos arquivos
```

---

# 31. Critérios de repetição

Repetir a etapa quando:

- baseline incompleto;
- perda significativa de ECG;
- coleta menor que o tempo definido;
- arquivos vazios;
- desconexão da cinta;
- VR interrompida;
- comando START ou STOP incorreto;
- participante movimentou-se fora do protocolo;
- erro de identificação;
- erro no cenário experimental.

A decisão deve seguir o protocolo aprovado.

---

# 32. Boas práticas operacionais

- executar sempre a partir da raiz do projeto;
- manter o terminal visível;
- não atualizar dependências no dia da coleta;
- testar o sistema antes da chegada do participante;
- evitar múltiplas instâncias da aplicação;
- evitar múltiplos processos do Hub;
- manter o computador conectado à energia;
- desabilitar suspensão automática;
- desabilitar atualizações automáticas;
- manter Bluetooth sem outros dispositivos desnecessários;
- registrar qualquer alteração no código;
- usar identificador anonimizado;
- realizar backup imediatamente;
- não editar arquivos originais após a coleta.

---

# 33. Validação periódica do sistema

Antes de um conjunto de coletas:

1. executar teste com hardware;
2. gravar baseline de teste;
3. iniciar e parar gravação pelo Hub;
4. verificar arquivos;
5. validar timestamps;
6. verificar tamanho dos arrays;
7. validar gráfico;
8. testar encerramento normal;
9. testar recuperação após falha;
10. registrar versão do software.

---

# 34. Controle de versão

Registrar em cada campanha:

```text
Versão do repositório:
Commit:
Versão do Python:
Versão do sistema operacional:
Versão do Hub:
Versão do dashboard:
Data da configuração:
Operador:
```

Comandos úteis:

```bash
git rev-parse HEAD
python --version
pip freeze
```

Salvar dependências:

```bash
pip freeze > environment_snapshot.txt
```

---

# 35. Checklist pós-coleta

```text
[ ] Baseline concluído
[ ] Etapa VR concluída
[ ] ECG baseline salvo
[ ] HRV baseline salva
[ ] ECG VR salvo
[ ] HRV VR salva
[ ] Arquivos possuem dados
[ ] Identificador correto
[ ] Ocorrências registradas
[ ] Backup realizado
[ ] Checksums gerados
[ ] Processos encerrados
[ ] Polar removida da faixa
[ ] Equipamentos desligados
```

---

# 36. Checklist de encerramento do dia

```text
[ ] Todas as sessões verificadas
[ ] Dados copiados
[ ] Backup secundário realizado
[ ] Arquivos identificáveis protegidos
[ ] Aplicação encerrada
[ ] Hub encerrado
[ ] Dashboard encerrado
[ ] Portas liberadas
[ ] Polar armazenada
[ ] Headset carregando
[ ] Relatório diário preenchido
```

---

# 37. Comandos rápidos

## Iniciar a aplicação

```bash
cd /caminho/para/polarh10_driver
source .venv/bin/activate
python main_interface.py
```

## Buscar a Polar

```bash
python test/scan.py
```

## Verificar portas

```bash
lsof -i :8765
lsof -i :8787
lsof -i :5173
```

## Verificar processos

```bash
ps aux | grep biofeedback
ps aux | grep node
```

## Encerrar processos

```bash
pkill -f biofeedback-hub
pkill -f biofeedback-polarh10
pkill -f "npm run dev:dashboard"
```

## Listar dados recentes

```bash
find data_captures -type f -mmin -30
```

## Verificar tamanhos

```bash
du -sh data_captures/*
```

---

# 38. Fluxo de recuperação rápida

## Caso 1: Polar não conecta

```text
Fechar a aplicação
    ↓
Fechar aplicativos Bluetooth concorrentes
    ↓
Remover e reconectar o módulo à faixa
    ↓
Reiniciar Bluetooth
    ↓
Executar scan.py
    ↓
Executar main_interface.py
```

## Caso 2: Hub não inicia

```text
Fechar a aplicação
    ↓
Encerrar processos antigos
    ↓
Verificar portas
    ↓
Testar biofeedback-hub manualmente
    ↓
Testar ponte manualmente
    ↓
Testar dashboard manualmente
    ↓
Executar novamente
```

## Caso 3: Dados não foram salvos

```text
Não iniciar nova coleta imediatamente
    ↓
Verificar terminal
    ↓
Verificar data_captures
    ↓
Verificar buffers e logs
    ↓
Registrar ocorrência
    ↓
Repetir sessão apenas se permitido
```

---

# 39. Limitações operacionais conhecidas

- caminhos do Hub definidos diretamente no código;
- dependência de Bash;
- dependência de sinais POSIX;
- inicialização com atrasos fixos;
- ausência de validação explícita das portas na interface;
- armazenamento em memória antes do salvamento;
- risco de perda em encerramento abrupto;
- dados cadastrais parcialmente persistidos;
- nome do participante utilizado em arquivos;
- necessidade de revisar timestamps por amostra;
- suporte ao Windows não garantido.

---

# 40. Recomendação de segurança de dados

Para uso em pesquisa:

- utilizar códigos anonimizados;
- separar dados pessoais dos sinais;
- proteger o arquivo de correspondência;
- restringir acesso;
- criptografar backups;
- não enviar dados por canais não autorizados;
- registrar transferências;
- manter controle de versões;
- seguir o protocolo ético aprovado.

---

# 41. Aprovação operacional

Antes de liberar o sistema para coleta oficial, registrar:

```text
Responsável técnico:
Data da validação:
Versão validada:
Commit:
Hardware testado:
Resultado:
Pendências:
Aprovação:
```

---

# 42. Resumo operacional

```text
1. Preparar a Polar H10
2. Ativar o ambiente virtual
3. Executar main_interface.py
4. Aguardar conexão Bluetooth
5. Subir o Hub pela interface
6. Confirmar o dashboard
7. Cadastrar o participante
8. Gravar baseline de 5 minutos
9. Confirmar salvamento
10. Iniciar experiência VR
11. Confirmar START
12. Confirmar STOP
13. Finalizar a sessão
14. Verificar arquivos
15. Fazer backup
16. Registrar ocorrências
```
