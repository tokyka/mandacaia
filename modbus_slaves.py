#!/usr/bin/env python3
import logging
import threading
import time
import random
import argparse
import struct
from pymodbus.server.sync import StartSerialServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian

# --- Configuração dos Slaves e Registradores ---
SLAVE_CONFIG = {
    10: {
        "name": "Reservatorio_Acumulacao",
        "registers": [
            {"function": "Nível", "type": "input_register", "address": 30001, "data_type": "float32", "unit": "%"},
            {"function": "Volume", "type": "holding_register", "address": 40001, "data_type": "float32", "unit": "litros"},
        ]
    },
    20: {
        "name": "Reservatorio_Distribuicao",
        "registers": [
            {"function": "Nível", "type": "input_register", "address": 30001, "data_type": "float32", "unit": "%"},
            {"function": "Volume", "type": "holding_register", "address": 40001, "data_type": "float32", "unit": "litros"},
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

# --- Configuração de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

class LoggingModbusSlaveContext(ModbusSlaveContext):
    """Slave context que loga apenas requisições externas (do master)."""
    def __init__(self, slave_id, *args, **kwargs):
        self.slave_id = slave_id
        super().__init__(*args, **kwargs)

    def getValues(self, fc, address, count=1):
        if threading.current_thread().name != "Thread-Simulador":
            log.info(f"REQUISIÇÃO MASTER (para Slave {self.slave_id}) -> FC: {fc}, Addr: {address}, Count: {count}")
        return super().getValues(fc, address, count)

    def setValues(self, fc, address, values):
        if threading.current_thread().name != "Thread-Simulador":
            log.info(f"REQUISIÇÃO MASTER (para Slave {self.slave_id}) -> FC: {fc}, Addr: {address}, Valores: {values}")
        return super().setValues(fc, address, values)

def list_slave_configuration():
    """Imprime a configuração dos slaves e seus registradores e sai."""
    print("--- Configuração dos Slaves Modbus ---")
    for slave_id, config in SLAVE_CONFIG.items():
        print(f"\n[+] Slave Address: {slave_id} ({config['name']})")
        for reg in config["registers"]:
            print(f"    - Função: {reg['function']}")
            print(f"      Tipo de Registrador: {reg['type']}")
            print(f"      Endereço: {reg['address']}")
            print(f"      Tipo de Dado: {reg['data_type']}")
            if 'unit' in reg:
                print(f"      Unidade: {reg['unit']}")
    print("\n--- Fim da Configuração ---")

def adjust_address(addr, reg_type):
    """Ajusta o endereço do protocolo Modbus para o endereço 0-indexed da biblioteca."""
    if reg_type == 'input_register': return addr - 30001
    if reg_type == 'holding_register': return addr - 40001
    if reg_type == 'coil': return addr - 1
    if reg_type == 'discrete_input': return addr - 10001
    return addr

def get_register_map(slave_config):
    """Cria um mapa de acesso rápido para os registradores."""
    reg_map = {}
    for slave_id, config in slave_config.items():
        if slave_id not in reg_map:
            reg_map[slave_id] = {}
        for reg in config["registers"]:
            reg_map[slave_id][reg["function"]] = {
                "address": reg["address"],
                "type": reg["type"],
                "adjusted_address": adjust_address(reg["address"], reg["type"])
            }
    return reg_map

def updating_thread(context, register_map):
    """Thread que atualiza dinamicamente os valores dos escravos."""
    log.info("Thread de atualização de valores iniciada.")
    
    CICLO_DE_ATUALIZACAO_S = 2
    consumo_percentual_por_ciclo = 0.5
    vazao_L_por_s = (3 * 1000) / 3600  # 3 m³/h convertidos para L/s
    volume_por_ciclo_L = vazao_L_por_s * CICLO_DE_ATUALIZACAO_S
    
    # Capacidades fixas para cálculo de porcentagem
    capacidade_reservatorios = {10: 50000, 20: 25000} # Capacidade em Litros
    
    # Acumulador de energia para o cálculo de kWh
    energy_accumulator_ws = 0.0

    while True:
        try:
            # --- 1. Simular Consumo do Reservatório de Distribuição (Slave 20) ---
            reg_nivel_dist = register_map[20]["Nível"]
            decoder_dist = BinaryPayloadDecoder.fromRegisters(
                context[20].getValues(4, reg_nivel_dist["adjusted_address"], count=2),
                byteorder=Endian.Big, wordorder=Endian.Big
            )
            current_level_dist = decoder_dist.decode_32bit_float()
            new_level_dist = max(0, current_level_dist - consumo_percentual_por_ciclo)
            
            builder_dist = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            builder_dist.add_32bit_float(new_level_dist)
            context[20].setValues(4, reg_nivel_dist["adjusted_address"], builder_dist.to_registers())

            # --- Ler níveis atuais para log e fallback ---
            reg_nivel_acum = register_map[10]["Nível"]
            decoder_acum_fallback = BinaryPayloadDecoder.fromRegisters(
                context[10].getValues(4, reg_nivel_acum["adjusted_address"], count=2),
                byteorder=Endian.Big, wordorder=Endian.Big
            )
            new_level_acum = decoder_acum_fallback.decode_32bit_float() # Valor inicial para o log
            new_level_dist_bomba = new_level_dist # Valor inicial para o log

            # --- 2. Verificar estado da bomba e simular transferência ---
            reg_acionamento_bomba = register_map[30]["Acionamento (Liga/Desliga)"]
            is_pump_on = context[30].getValues(1, reg_acionamento_bomba["adjusted_address"], count=1)[0]

            voltage, current = 0.0, 0.0
            
            if is_pump_on:
                # Simular vazão entre reservatórios
                # Retira do reservatório de acumulação (10)
                reg_nivel_acum = register_map[10]["Nível"]
                decoder_acum = BinaryPayloadDecoder.fromRegisters(
                    context[10].getValues(4, reg_nivel_acum["adjusted_address"], count=2),
                    byteorder=Endian.Big, wordorder=Endian.Big
                )
                current_level_acum = decoder_acum.decode_32bit_float()
                delta_percent_acum = (volume_por_ciclo_L / capacidade_reservatorios[10]) * 100
                new_level_acum = max(0, current_level_acum - delta_percent_acum)
                
                builder_acum = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder_acum.add_32bit_float(new_level_acum)
                context[10].setValues(4, reg_nivel_acum["adjusted_address"], builder_acum.to_registers())

                # Adiciona ao reservatório de distribuição (20)
                # Re-lê o nível que foi alterado pelo consumo
                decoder_dist_bomba = BinaryPayloadDecoder.fromRegisters(
                    context[20].getValues(4, reg_nivel_dist["adjusted_address"], count=2),
                    byteorder=Endian.Big, wordorder=Endian.Big
                )
                current_level_dist_bomba = decoder_dist_bomba.decode_32bit_float()
                delta_percent_dist = (volume_por_ciclo_L / capacidade_reservatorios[20]) * 100
                new_level_dist_bomba = min(100, current_level_dist_bomba + delta_percent_dist)

                builder_dist_bomba = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder_dist_bomba.add_32bit_float(new_level_dist_bomba)
                context[20].setValues(4, reg_nivel_dist["adjusted_address"], builder_dist_bomba.to_registers())

                # Simular dados elétricos da bomba (Slave 30)
                voltage = random.uniform(210.0, 230.0)
                current = random.uniform(4.5, 5.5)
                
                # Ler potência escrita pelo mestre
                reg_potencia_bomba = register_map[30]["Potência da bomba"]
                pot_decoder = BinaryPayloadDecoder.fromRegisters(
                    context[30].getValues(3, reg_potencia_bomba["adjusted_address"], count=2),
                    byteorder=Endian.Big, wordorder=Endian.Big
                )
                power_watts = pot_decoder.decode_32bit_float()

                # Calcular energia e consumo acumulado (kWh)
                energy_ws_cycle = power_watts * CICLO_DE_ATUALIZACAO_S
                energy_accumulator_ws += energy_ws_cycle
                kwh = energy_accumulator_ws / (3600 * 1000)

                # Escrever consumo
                reg_consumo = register_map[30]["Consumo"]
                builder_kwh = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder_kwh.add_32bit_float(kwh)
                context[30].setValues(4, reg_consumo["adjusted_address"], builder_kwh.to_registers())

            # Escrever Tensão e Corrente (sempre, zerado se a bomba estiver desligada)
            reg_tensao = register_map[30]["Tensão"]
            builder_v = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            builder_v.add_32bit_float(voltage)
            context[30].setValues(4, reg_tensao["adjusted_address"], builder_v.to_registers())

            reg_corrente = register_map[30]["Corrente"]
            builder_c = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            builder_c.add_32bit_float(current)
            context[30].setValues(4, reg_corrente["adjusted_address"], builder_c.to_registers())

            # --- 3. Log Unificado ---
            pump_status_str = "ON" if is_pump_on else "OFF"
            log.info(f"Simulador: Nível Acum.: {new_level_acum:.2f}% | Nível Dist.: {new_level_dist_bomba if is_pump_on else new_level_dist:.2f}% | Bomba: {pump_status_str} | Tensão: {voltage:.2f}V | Corrente: {current:.2f}A")

            time.sleep(CICLO_DE_ATUALIZACAO_S)

        except Exception as e:
            log.error(f"Erro na thread de atualização: {e}", exc_info=True)
            time.sleep(5)

def run_server(scenario=1):
    """Configura e inicia o servidor Modbus com base no cenário escolhido."""
    slaves = {}
    register_map = get_register_map(SLAVE_CONFIG)

    for slave_id, config in SLAVE_CONFIG.items():
        # Aloca espaço suficiente para os registradores. 200 é um valor seguro.
        slaves[slave_id] = LoggingModbusSlaveContext(slave_id,
            co=ModbusSequentialDataBlock(0, [False] * 200),
            di=ModbusSequentialDataBlock(0, [False] * 200),
            ir=ModbusSequentialDataBlock(0, [0] * 200),
            hr=ModbusSequentialDataBlock(0, [0] * 200),
            zero_mode=True
        )

    # Definir níveis iniciais com base no cenário
    initial_levels = {'acumulacao': 80.0, 'distribuicao': 50.0} # Padrão
    if scenario == 1:
        initial_levels['acumulacao'] = 80.0
        initial_levels['distribuicao'] = 25.0
    elif scenario == 2:
        initial_levels['acumulacao'] = 35.0
        initial_levels['distribuicao'] = 25.0
    elif scenario == 3:
        initial_levels['acumulacao'] = 25.0
        initial_levels['distribuicao'] = 25.0
    elif scenario == 4:
        initial_levels['acumulacao'] = 20.0
        initial_levels['distribuicao'] = 20.0
    elif scenario == 5:
        initial_levels['acumulacao'] = 80.0
        initial_levels['distribuicao'] = 60.0

    log.info(f"--- Iniciando Cenário de Simulação: {scenario} ---")
    log.info(f"Nível Inicial Acumulação: {initial_levels['acumulacao']:.1f}%, Distribuição: {initial_levels['distribuicao']:.1f}%")

    # Inicializar input_registers e coils com valores padrão
    for slave_id, config in SLAVE_CONFIG.items():
        for reg in config["registers"]:
            addr = adjust_address(reg["address"], reg["type"])
            if reg["type"] == "input_register":
                builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder.add_32bit_float(0.0)
                slaves[slave_id].setValues(4, addr, builder.to_registers())
            elif reg["type"] == "coil":
                slaves[slave_id].setValues(1, addr, [False])

    # Inicializar valores
    builder_acum_init = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
    builder_acum_init.add_32bit_float(initial_levels['acumulacao'])
    addr_acum = register_map[10]["Nível"]["adjusted_address"]
    slaves[10].setValues(4, addr_acum, builder_acum_init.to_registers())

    builder_dist_init = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
    builder_dist_init.add_32bit_float(initial_levels['distribuicao'])
    addr_dist = register_map[20]["Nível"]["adjusted_address"]
    slaves[20].setValues(4, addr_dist, builder_dist_init.to_registers())


    # Inicializar todos os registradores input_register e coil com valores padrão
    for slave_id, config in SLAVE_CONFIG.items():
        for reg in config["registers"]:
            addr = adjust_address(reg["address"], reg["type"])

            # Verificação de segurança: garantir que o endereço ajustado esteja dentro do intervalo alocado
            if addr < 0 or addr >= 200:
                log.warning(f"Endereço fora do intervalo alocado: Slave {slave_id}, Função '{reg['function']}', Endereço ajustado: {addr}")
                continue

            if reg["type"] == "input_register":
                builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder.add_32bit_float(0.0)
                slaves[slave_id].setValues(4, addr, builder.to_registers())
                log.info(f"Inicializado input_register: Slave {slave_id}, Função '{reg['function']}', Addr: {addr}, Valor: 0.0")

            elif reg["type"] == "coil":
                slaves[slave_id].setValues(1, addr, [False])
                log.info(f"Inicializado coil: Slave {slave_id}, Função '{reg['function']}', Addr: {addr}, Valor: False")
            elif reg["type"] == "holding_register":
                builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder.add_32bit_float(0.0)
                slaves[slave_id].setValues(3, addr, builder.to_registers())
                log.info(f"Inicializado holding_register: Slave {slave_id}, Função '{reg['function']}', Addr: {addr}, Valor: 0.0")

    # Holding registers são inicializados com 0 por padrão (zero_mode=True)
    context = ModbusServerContext(slaves=slaves, single=False)
    
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Mandacaia-Sim-Independente'
    #updater = threading.Thread(target=updating_thread, args=(context, register_map))
    updater = threading.Thread(target=updating_thread, args=(context, register_map), name="Thread-Simulador")
    updater.daemon = True
    updater.start()

    log.info("Iniciando servidor Modbus RTU na porta /tmp/ttyS0...")
    log.info("Pressione Ctrl+C para parar.")
    
    StartSerialServer(
        context=context,
        identity=identity,
        port='/tmp/ttyS0',
        framer=ModbusRtuFramer,
        baudrate=115200
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicia o servidor de simulação Modbus com configuração fixa.")
    parser.add_argument("-l", "--list", action="store_true",
                        help="Lista a configuração dos slaves e seus registradores e sai.")
    parser.add_argument("-s", "--simulate", type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help="Número do cenário a ser simulado (1-5). Padrão: 1.")
    args = parser.parse_args()

    if args.list:
        list_slave_configuration()
    else:
        run_server(scenario=args.simulate)
