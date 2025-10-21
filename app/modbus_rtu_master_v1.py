import logging
import struct
import time
from pymodbus.client import ModbusSerialClient

# --- Configuração do Logging ---
# Mude para logging.DEBUG para ver os pacotes de envio e recebimento
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

# --- Funções Auxiliares ---
def adjust_address(reg_type, address):
    """Ajusta o endereço do protocolo para o endereço 0-indexed da biblioteca."""
    if reg_type == 'input_register': return address - 30001
    if reg_type == 'holding_register': return address - 40001
    if reg_type == 'coil': return address - 1
    return address

def registers_to_float(registers):
    """Converte uma lista de 2 registradores de 16 bits para um float (big-endian)."""
    if not registers or len(registers) < 2:
        return 0.0
    packed = int.to_bytes(registers[0], 2, 'big') + int.to_bytes(registers[1], 2, 'big')
    return struct.unpack('>f', packed)[0]

# --- Funções de Leitura por Dispositivo ---
def read_reservoir_data(client, slave_id, name):
    """Lê e exibe os dados de um slave de reservatório."""
    print(f"\n--- Lendo dados do {name} (ID: {slave_id}) ---")
    
    # Ler Nível (Input Register)
    addr_nivel = adjust_address("input_register", 30001)
    response = client.read_input_registers(address=addr_nivel, count=2, device_id=slave_id)
    if response.isError():
        print(f"  Nível: ERRO - {response}")
    else:
        nivel = registers_to_float(response.registers)
        print(f"  Nível: {nivel:.2f} %")

    # Ler Volume (Holding Register)
    addr_volume = adjust_address("holding_register", 40001)
    response = client.read_holding_registers(address=addr_volume, count=2, device_id=slave_id)
    if response.isError():
        print(f"  Volume: ERRO - {response}")
    else:
        volume = registers_to_float(response.registers)
        print(f"  Volume: {volume:.2f} litros")

def read_pump_data(client, slave_id):
    """Lê e exibe os dados do slave da motobomba."""
    print(f"\n--- Lendo dados da Motobomba (ID: {slave_id}) ---")

    # Ler Acionamento (Coil)
    addr_coil = adjust_address("coil", 1)
    response = client.read_coils(address=addr_coil, count=1, device_id=slave_id)
    if response.isError():
        print(f"  Acionamento: ERRO - {response}")
    else:
        status = "ON" if response.bits[0] else "OFF"
        print(f"  Acionamento: {status}")

    # Ler Tensão, Corrente, Consumo (Input Registers)
    addr_tensao = adjust_address("input_register", 30001)
    resp_tensao = client.read_input_registers(address=addr_tensao, count=2, device_id=slave_id)
    if resp_tensao.isError():
        print(f"  Tensão: ERRO - {resp_tensao}")
    else:
        print(f"  Tensão: {registers_to_float(resp_tensao.registers):.2f} V")

    addr_corrente = adjust_address("input_register", 30005)
    resp_corrente = client.read_input_registers(address=addr_corrente, count=2, device_id=slave_id)
    if resp_corrente.isError():
        print(f"  Corrente: ERRO - {resp_corrente}")
    else:
        print(f"  Corrente: {registers_to_float(resp_corrente.registers):.2f} A")

    addr_consumo = adjust_address("input_register", 30020)
    resp_consumo = client.read_input_registers(address=addr_consumo, count=2, device_id=slave_id)
    if resp_consumo.isError():
        print(f"  Consumo: ERRO - {resp_consumo}")
    else:
        print(f"  Consumo: {registers_to_float(resp_consumo.registers):.4f} kWh")

    # Ler Potência (Holding Register)
    addr_potencia = adjust_address("holding_register", 40001)
    resp_potencia = client.read_holding_registers(address=addr_potencia, count=2, device_id=slave_id)
    if resp_potencia.isError():
        print(f"  Potência: ERRO - {resp_potencia}")
    else:
        print(f"  Potência: {registers_to_float(resp_potencia.registers):.2f} Watts")

def run_master():
    """ Roda o cliente Modbus em loop para monitorar os dados da simulação. """
    client = ModbusSerialClient(
        port='/tmp/ttyS1',
        baudrate=115200,
        timeout=1
    )
    print("--- Iniciando Cliente Modbus RTU Master ---")
    if not client.connect():
        print("!!! Falha ao conectar ao cliente Modbus !!!")
        return

    try:
        while True:
            print("\n" + "="*50)
            print(f"Iniciando novo ciclo de leitura... ({time.ctime()})")
            read_reservoir_data(client, 10, "Reservatorio_Acumulacao")
            read_reservoir_data(client, 20, "Reservatorio_Distribuicao")
            read_pump_data(client, 30)
            print("="*50)
            print("Ciclo de leitura concluído. Aguardando 5 segundos (Pressione Ctrl+C para sair)...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n--- Interrupção pelo usuário. Encerrando... ---")
    finally:
        client.close()
        print("\n--- Conexão com o cliente fechada ---")

if __name__ == "__main__":
    run_master()
