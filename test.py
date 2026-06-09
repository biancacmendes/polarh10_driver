import asyncio
import csv
import logging
import time
from bleak import BleakScanner, BleakClient
from polar_python.parsers import parse_polar_data

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")

DEVICE_ADDRESS = "A0:9E:1A:EB:ED:38"
OUTPUT_FILE = "dados_ecg_polar.csv"

# UUIDs obtidos diretamente das especificações de hardware da Polar H10
PMD_CONTROL_UUID = "fb005c81-02e7-f387-11e5-6709d0000a11"
PMD_DATA_UUID = "fb005c82-02e7-f387-11e5-6709d0000a11"

async def main():
    logging.info("Iniciando varredura para localizar a Polar H10...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)
    
    if not device:
        logging.error(f"Dispositivo {DEVICE_ADDRESS} nao encontrado.")
        return

    logging.info(f"Dispositivo localizado. Conectando via pipeline nativa do Bleak...")
    
    # Abrimos o arquivo CSV para gravação contínua
    with open(OUTPUT_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "sequence", "ecg_microvolts"])
        
        sequence_counter = 0

        # Handler simplificado que recebe os pacotes brutos e usa o parser funcional
        def pmd_data_handler(characteristic, data: bytearray):
            nonlocal sequence_counter
            try:
                # O parser funcional do pacote apenas converte os bytes em objetos de dados
                parsed_records = parse_polar_data(data)
                if not parsed_records:
                    return

                for record in parsed_records:
                    if record.__class__.__name__ == "ECGData":
                        # Captura as amostras por reflexão para manter compatibilidade com a lib
                        samples = getattr(record, "samples", None) or getattr(record, "values", None) or getattr(record, "data", None)
                        if samples:
                            current_time = time.time()
                            for sample in samples:
                                sequence_counter += 1
                                writer.writerow([current_time, sequence_counter, sample])
                            logging.info(f"Gravadas {len(samples)} amostras de ECG no CSV.")
            except Exception as parse_err:
                logging.error(f"Erro ao processar pacote: {parse_err}")

        # Conectamos usando o cliente puro do Bleak
        async with BleakClient(device) as client:
            logging.info("Conexao estabelecida. Atualizando mapeamento de servicos...")
            
            # Acessar a propriedade força o Bleak a indexar os descritores no D-Bus pacificamente
            _ = client.services
            await asyncio.sleep(1.0)

            logging.info("Inscrevendo nas notificacoes do canal de telemetria...")
            await client.start_notify(PMD_DATA_UUID, pmd_data_handler)

            logging.info("Enviando comando de inicializacao para o firmware da cinta...")
            # Envia a requisição de inicialização de ECG (OpCode 1, Sensor 1, 130Hz, 14bits)
            # Esse comando ativa a transmissão sem disparar erros de autenticação no BlueZ
            ecg_start_command = bytearray([0x01, 0x01, 0x00, 0x01, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])
            await client.write_gatt_char(PMD_CONTROL_UUID, ecg_start_command, response=True)

            logging.info("Fluxo ativo. Coletando dados... Pressione Ctrl+C para encerrar.")
            while True:
                await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info(f"\nSessao finalizada. Arquivo gerado com sucesso: {OUTPUT_FILE}")