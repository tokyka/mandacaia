import logging
import threading
import time
import random
import struct
import argparse
from pymodbus.server import StartSerialServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext
from pymodbus import FramerType
from pymodbus import ModbusDeviceIdentification

# Configura o sistema de logging para que as mensagens apareçam no console.
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

# --- Configuração dos Slaves e Registradores ---
SLAVE_CONFIG = {
    10: {
        "name": "Reservatorio_Acumulacao",
        "registers": [
            {"function": "Nível", "type": "input_register", "address": 30001, "data_type": "float32", "unit": "%"},
            {"function": "Volume", "type": "holding_register", "address": 40001, "data_type": "int32", "unit": "litros"},
        ]
    },
    20: {
        "name": "Reservatorio_Distribuicao",
        "registers": [
            {"function": "Nível", "type": "input_register", "address": 30001, "data_type": "float32", "unit": "%"},
            {"function": "Volume", "type": "holding_register", "address": 40001, "data_type": "int32", "unit": "litros"},
        ]
    },
    30: {
        "name": "Motobomba",
        "registers": [
            {"function": "Acionamento (Liga/Desliga)", "type": "coil", "address": 1, "data_type": "boolean"},
            {"function": "Tensão", "type": "input_register", "address": 30001, "data_type": "float32", "unit": "V"},
            {"function": "Corrente", "type": "input_register", "address": 30005, "data_type": "float32", "unit": "A"},
            {"function": "Potência da bomba", "type": "holding_register", "address": 40001, "data_type": "float32", "unit": "Watts"},
            {"function": "Consumo", "type": "input_register", "address": 30020, "data_type": "float32", "unit": "kWh"},
        ]
    }
}

def list_slave_configuration():
    """Imprime a configuração dos slaves e seus registradores e sai."""
    print("--- Configuração dos Slaves Modbus ---")
    for slave_id, config in SLAVE_CONFIG.items():
        print(f"\nSlave Address: {slave_id} ({config['name']})")
        for reg in config["registers"]:
            print(f"    - Função: {reg['function']}")
            print(f"      Tipo de Registrador: {reg['type']}")
            print(f"      Endereço: {reg['address']}")
            print(f"      Tipo de Dado: {reg['data_type']}")
            if 'unit' in reg:
                print(f"      Unidade: {reg['unit']}")
    print("\n--- Fim da Configuração ---")

# --- Funções Auxiliares ---
def adjust_address(reg_type, address):
    """Ajusta o endereço do protocolo para o endereço 0-indexed da biblioteca."""
    if reg_type == 'input_register': return address - 30001
    if reg_type == 'holding_register': return address - 40001
    if reg_type == 'coil': return address - 1
    if reg_type == 'discrete_input': return address - 10001
    return address

def float_to_registers(value):
    """Converte um valor float para uma lista de 2 registradores de 16 bits (big-endian)."""
    packed = struct.pack('>f', value)
    return [int.from_bytes(packed[0:2], 'big'), int.from_bytes(packed[2:4], 'big')]

def registers_to_float(registers):
    """Converte uma lista de 2 registradores de 16 bits para um float (big-endian)."""
    if not registers or len(registers) < 2:
        return 0.0
    packed = int.to_bytes(registers[0], 2, 'big') + int.to_bytes(registers[1], 2, 'big')
    return struct.unpack('>f', packed)[0]

def int_to_registers(value):
    """Converte um valor int para uma lista de 2 registradores de 16 bits (big-endian)."""
    return [(value >> 16) & 0xFFFF, value & 0xFFFF]

def registers_to_int(registers):
    """Converte uma lista de 2 registradores de 16 bits para um int (big-endian)."""
    if not registers or len(registers) < 2:
        return 0
    return (registers[0] << 16) | registers[1]

# --- Thread de Simulação --- 
def simulation_thread(context):
    """Thread que atualiza dinamicamente os valores dos escravos."""
    log.info("Thread de simulação de dados iniciada.")
    
    CICLO_DE_ATUALIZACAO_S = 2
    consumo_percentual_por_ciclo = 0.5
    vazao_L_por_s = (3 * 1000) / 3600  # 3 m³/h convertidos para L/s
    volume_por_ciclo_L = vazao_L_por_s * CICLO_DE_ATUALIZACAO_S
    
    energy_accumulator_ws = 0.0
    POWER_FACTOR = 0.75 # Fator de potência estimado para o motor
    FALLBACK_POWER_WATTS = 245.17 # Potência nominal de fallback (0.33 CV)

    while True:
        try:
            # --- Ler dados atuais dos slaves ---
            addr_nivel_acum = adjust_address("input_register", 30001)
            current_level_acum = registers_to_float(context[10].getValues(4, addr_nivel_acum, count=2))

            addr_nivel_dist = adjust_address("input_register", 30001)
            current_level_dist = registers_to_float(context[20].getValues(4, addr_nivel_dist, count=2))

            addr_volume_acum = adjust_address("holding_register", 40001)
            capacidade_acum_L = registers_to_int(context[10].getValues(3, addr_volume_acum, count=2)) or 50000

            addr_volume_dist = adjust_address("holding_register", 40001)
            capacidade_dist_L = registers_to_int(context[20].getValues(3, addr_volume_dist, count=2)) or 25000

            addr_bomba_coil = adjust_address("coil", 1)
            is_pump_on = context[30].getValues(1, addr_bomba_coil, count=1)[0]

            # --- Simular consumo do reservatório de distribuição ---
            level_dist_after_consumption = current_level_dist
            if not is_pump_on:
                level_dist_after_consumption = max(0, current_level_dist - consumo_percentual_por_ciclo)

            # --- Inicializar variáveis de simulação para este ciclo ---
            final_level_acum = current_level_acum
            final_level_dist = level_dist_after_consumption
            voltage = 0.0
            current = 0.0
            simulated_power = 0.0

            if is_pump_on:
                # --- Simulação de Níveis com a bomba ligada ---
                delta_percent_acum = (volume_por_ciclo_L / capacidade_acum_L) * 100
                final_level_acum = max(0, current_level_acum - delta_percent_acum)
                delta_percent_dist = (volume_por_ciclo_L / capacidade_dist_L) * 100
                final_level_dist = min(100, level_dist_after_consumption + delta_percent_dist)

                # --- Simulação Elétrica Consistente ---
                # 1. Determinar a potência real a ser usada
                addr_potencia = adjust_address("holding_register", 40001)
                power_from_register = registers_to_float(context[30].getValues(3, addr_potencia, count=2))
                
                if power_from_register > 0:
                    simulated_power = power_from_register
                else:
                    simulated_power = FALLBACK_POWER_WATTS # Usa o fallback se o master ainda não escreveu

                # 2. Simular a tensão
                voltage = random.uniform(210.0, 230.0)

                # 3. Calcular a corrente baseada na potência real, tensão e fator de potência
                if voltage * POWER_FACTOR > 0:
                    current = simulated_power / (voltage * POWER_FACTOR)
                else:
                    current = 0.0
                
                # --- Calcular consumo de energia ---
                energy_ws_cycle = simulated_power * CICLO_DE_ATUALIZACAO_S
                energy_accumulator_ws += energy_ws_cycle
                kwh = energy_accumulator_ws / (3600 * 1000)
                addr_consumo = adjust_address("input_register", 30020)
                context[30].setValues(4, addr_consumo, float_to_registers(kwh))

            # --- Escrever Valores Simulados de volta nos Registradores ---
            context[10].setValues(4, addr_nivel_acum, float_to_registers(final_level_acum))
            context[20].setValues(4, addr_nivel_dist, float_to_registers(final_level_dist))

            # Dados elétricos (serão 0 se a bomba estiver desligada)
            addr_tensao = adjust_address("input_register", 30001)
            context[30].setValues(4, addr_tensao, float_to_registers(voltage))
            addr_corrente = adjust_address("input_register", 30005)
            context[30].setValues(4, addr_corrente, float_to_registers(current))
            
            # Escreve a potência real simulada (ou 0 se a bomba estiver desligada)
            addr_potencia = adjust_address("holding_register", 40001)
            context[30].setValues(3, addr_potencia, float_to_registers(simulated_power))

            # --- Log ---
            pump_status_str = "ON" if is_pump_on else "OFF"
            volume_acum_L = (final_level_acum / 100) * capacidade_acum_L
            volume_dist_L = (final_level_dist / 100) * capacidade_dist_L

            log.info(f"Simulador: Acum.: {final_level_acum:.2f}% ({volume_acum_L:.1f}L) | Dist.: {final_level_dist:.2f}% ({volume_dist_L:.1f}L) | Bomba: {pump_status_str}")

        except Exception as e:
            log.error(f"Erro na thread de simulação: {e}", exc_info=True)
        
        time.sleep(CICLO_DE_ATUALIZACAO_S)

def run_server():
    """Configura e inicia o servidor Modbus com a nova lógica de simulação."""
    slaves = {}
    for slave_id in SLAVE_CONFIG:
        # Aloca espaço suficiente para os registradores.
        slaves[slave_id] = ModbusDeviceContext(
            di=ModbusSequentialDataBlock(0, [0]*100),
            co=ModbusSequentialDataBlock(0, [0]*100),
            hr=ModbusSequentialDataBlock(0, [0]*100),
            ir=ModbusSequentialDataBlock(0, [0]*100)
        )

    context = slaves

    # --- Define Níveis Iniciais ---
    initial_level_acum = 80.0
    initial_level_dist = 25.0
    log.info(f"Níveis Iniciais: Acumulação={initial_level_acum}%, Distribuição={initial_level_dist}%")
    
    addr_nivel_acum = adjust_address("input_register", 30001)
    context[10].setValues(4, addr_nivel_acum, float_to_registers(initial_level_acum))
    
    addr_nivel_dist = adjust_address("input_register", 30001)
    context[20].setValues(4, addr_nivel_dist, float_to_registers(initial_level_dist))

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Mandacaia-Sim'
    identity.ProductCode = 'MSIM'
    identity.MajorMinorRevision = '1.0.0'

    # Inicia a thread de simulação em segundo plano
    updater = threading.Thread(target=simulation_thread, args=(context,))
    updater.daemon = True
    updater.start()

    port = '/tmp/ttyS0'
    log.info(f"--- Iniciando servidor Modbus RTU na porta {port} ---")
    log.info("--- Servidor pronto e escutando. Pressione Ctrl+C para parar. ---")

    StartSerialServer(
        context=context,
        framer=FramerType.RTU,
        identity=identity,
        port=port,
        baudrate=115200,
        parity='N',
        bytesize=8,
        stopbits=1
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor de Simulação Modbus RTU")
    parser.add_argument("-l", "--list", action="store_true",
                        help="Lista a configuração dos slaves e seus registradores e sai.")
    args = parser.parse_args()

    if args.list:
        list_slave_configuration()
    else:
        run_server()
