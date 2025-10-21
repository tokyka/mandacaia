import logging
import time
import struct
import os
import argparse
from pymodbus.client import ModbusSerialClient
from sqlalchemy import create_engine, text

# --- Configuração do Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

# --- Configuração do Banco de Dados ---
# (Valores padrão baseados no seu config.py)
USERNAME = os.environ.get('DB_USER', 'mandacaia_user')
PASSWORD = os.environ.get('DB_PASSWORD', 'Mandacaia2025')
SERVER = os.environ.get('DB_HOST', '127.0.0.1')
PORT = os.environ.get('DB_PORT', '3306')
DB = os.environ.get('DB_NAME', 'mandacaia')

DB_URI = f'mariadb+mariadbconnector://{USERNAME}:{PASSWORD}@{SERVER}:{PORT}/{DB}'

# --- Funções Auxiliares ---
def registers_to_float(registers):
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

def get_control_config(session):
    """Busca e estrutura a configuração de controle do banco de dados."""
    query = text("""
        SELECT 
            m.id as motobomba_id,
            (SELECT ms.slave_id FROM modbus_slave ms WHERE ms.id = m.modbus_slave_id) as bomba_slave_id,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = m.modbus_slave_id AND fr.funcao = 'Acionamento (Liga/Desliga)') as bomba_coil_addr,
            m.potencia as bomba_potencia,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = m.modbus_slave_id AND fr.funcao = 'Potência') as bomba_potencia_addr,
            
            acum.id as acum_id,
            acum_ms.slave_id as acum_slave_id,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = acum_ms.id AND fr.funcao = 'Nível') as acum_level_addr,
            acum_ac.limite_inferior as acum_lim_inf,
            acum_ac.limite_superior as acum_lim_sup,
            acum.capacidade_maxima as acum_capacidade,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = acum_ms.id AND fr.funcao = 'Volume') as acum_volume_addr,

            dist.id as dist_id,
            dist_ms.slave_id as dist_slave_id,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = dist_ms.id AND fr.funcao = 'Nível') as dist_level_addr,
            dist_ac.limite_inferior as dist_lim_inf,
            dist_ac.limite_superior as dist_lim_sup,
            dist.capacidade_maxima as dist_capacidade,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = dist_ms.id AND fr.funcao = 'Volume') as dist_volume_addr

        FROM motobomba m
        JOIN reservatorio acum ON m.reservatorio_fonte_id = acum.id
        JOIN reservatorio dist ON m.reservatorio_destino_id = dist.id
        JOIN modbus_slave acum_ms ON acum.modbus_slave_id = acum_ms.id
        JOIN modbus_slave dist_ms ON dist.modbus_slave_id = dist_ms.id
        JOIN alerta_config acum_ac ON acum_ac.reservatorio_id = acum.id
        JOIN alerta_config dist_ac ON dist_ac.reservatorio_id = dist.id
        WHERE m.funcao = 'PRINCIPAL'
        LIMIT 1;
    """)
    result = session.execute(query).first()
    if not result:
        return None
    return result._asdict()

def run_controller():
    log.info("--- Iniciando Master V2 (Controlador) ---")

    try:
        engine = create_engine(DB_URI)
        with engine.connect() as connection:
            config = get_control_config(connection)
            if not config:
                log.error("Não foi possível carregar a configuração de controle do banco de dados. Verifique se uma bomba principal e seus reservatórios estão configurados.")
                return
            log.info(f"Motobomba: Slave ID {config['bomba_slave_id']}")

            # Inicializar cliente Modbus após carregar a configuração do DB
            client = ModbusSerialClient(port='/tmp/ttyS1', baudrate=115200, timeout=2)
            if not client.connect():
                log.error("Falha ao conectar ao cliente Modbus. Verifique a porta e se o slave está rodando.")
                return

        # Escrever capacidade máxima dos reservatórios nos slaves
        log.info(f"Escrevendo capacidade máxima do Reservatório de Acumulação ({config['acum_capacidade']}L) no Slave {config['acum_slave_id']}.")
        client.write_registers(address=config['acum_volume_addr'] - 40001, values=int_to_registers(int(config['acum_capacidade'])), device_id=config['acum_slave_id'])
        
        log.info(f"Escrevendo capacidade máxima do Reservatório de Distribuição ({config['dist_capacidade']}L) no Slave {config['dist_slave_id']}.")
        client.write_registers(address=config['dist_volume_addr'] - 40001, values=int_to_registers(int(config['dist_capacidade'])), device_id=config['dist_slave_id'])

        # --- Validação de endereços Modbus --- 
        if config['bomba_coil_addr'] is None:
            log.error("Endereço da bobina de acionamento da bomba não encontrado no banco de dados. Verifique a configuração do registrador 'Acionamento' para a motobomba principal.")
            return
        if config['acum_level_addr'] is None:
            log.error("Endereço do registrador de nível do reservatório de acumulação não encontrado no banco de dados.")
            return
        if config['dist_level_addr'] is None:
            log.error("Endereço do registrador de nível do reservatório de distribuição não encontrado no banco de dados.")
            return
        # Escrever potência da bomba no slave
        if config['bomba_potencia_addr'] is None:
            log.error("Endereço do registrador de potência da bomba não encontrado no banco de dados.")
            return
        try:
            potencia_str = config['bomba_potencia']
            potencia_cv = 0.0
            if '/' in potencia_str:
                num, den = map(int, potencia_str.split('/'))
                potencia_cv = float(num) / float(den)
            else:
                potencia_cv = float(potencia_str)
                        
            # Converter CV para Watts (1 CV = 735.499 Watts)
            potencia_watts = potencia_cv * 735.499
                        
            log.info(f"Escrevendo potência da bomba ({potencia_cv:.2f} CV = {potencia_watts:.2f} Watts) no Slave {config['bomba_slave_id']}.")
            client.write_registers(address=config['bomba_potencia_addr'] - 40001, values=float_to_registers(potencia_watts), device_id=config['bomba_slave_id'])
        except ValueError:
            log.error(f"Valor de potência da bomba inválido no banco de dados: '{config['bomba_potencia']}'. Esperado um número ou fração (ex: '1/3', '0.5', '1').")
            return
    except Exception as e:
        log.error(f"Erro ao conectar ou consultar o banco de dados: {e}", exc_info=True)

    try:
        while True:
            # 1. Ler níveis atuais dos reservatórios
            log.info("Lendo níveis atuais dos reservatórios...")
            resp_acum = client.read_input_registers(address=config['acum_level_addr'] - 30001, count=2, device_id=config['acum_slave_id'])
            resp_dist = client.read_input_registers(address=config['dist_level_addr'] - 30001, count=2, device_id=config['dist_slave_id'])

            if resp_acum.isError() or resp_dist.isError():
                log.warning("Erro ao ler nível de um dos reservatórios. Pulando ciclo.")
                time.sleep(10)
                continue

            nivel_acum = registers_to_float(resp_acum.registers)
            nivel_dist = registers_to_float(resp_dist.registers)
            log.info(f"Níveis atuais -> Acumulação: {nivel_acum:.2f}% | Distribuição: {nivel_dist:.2f}%")

            # 2. Ler estado atual da bomba
            current_pump_status_resp = client.read_coils(address=config['bomba_coil_addr'] - 1, count=1, device_id=config['bomba_slave_id'])
            if current_pump_status_resp.isError():
                log.warning("Erro ao ler estado da bomba. Pulando ciclo.")
                time.sleep(10)
                continue
            current_pump_status = current_pump_status_resp.bits[0]
            log.info(f"Estado atual da bomba: {'ON' if current_pump_status else 'OFF'}")

            # 3. Aplicar lógica de controle
            desired_pump_status = current_pump_status

            # Lógica para LIGAR
            if not current_pump_status and (nivel_acum >= config['acum_lim_inf'] and nivel_dist <= config['dist_lim_inf']):
                log.info("CONDIÇÃO DE LIGAR ATINGIDA: Nível de acumulação OK e nível de distribuição baixo.")
                desired_pump_status = True
            
            # Lógica para DESLIGAR
            if current_pump_status and (nivel_acum <= config['acum_lim_inf'] or nivel_dist >= config['dist_lim_sup']):
                log.info("CONDIÇÃO DE DESLIGAR ATINGIDA: Nível de acumulação baixo OU nível de distribuição alto.")
                desired_pump_status = False

            # 4. Atuar se o estado desejado for diferente do atual
            if desired_pump_status != current_pump_status:
                log.warning(f"Ação: Alterando estado da bomba para {'ON' if desired_pump_status else 'OFF'}.")
                client.write_coil(address=config['bomba_coil_addr'] - 1, value=desired_pump_status, device_id=config['bomba_slave_id'])
            else:
                log.info("Nenhuma ação necessária. Mantendo estado atual da bomba.")

            log.info("Ciclo de controle finalizado. Aguardando 10 segundos.")
            time.sleep(10)

    except KeyboardInterrupt:
        log.info("Interrupção pelo usuário. Encerrando controlador.")
    finally:
        client.close()
        log.info("Conexão Modbus fechada.")

def run_test_mode():
    """Conecta no BD, busca todos os registradores e tenta ler cada um."""
    log.info("--- Iniciando Master em MODO DE TESTE ---")
    try:
        engine = create_engine(DB_URI)
        with engine.connect() as connection:
            query = text("""
                SELECT 
                    ms.slave_id, ms.nome as slave_name, 
                    mr.endereco, mr.tipo, mr.data_type, fr.funcao as funcao_nome
                FROM modbus_register mr
                JOIN modbus_slave ms ON mr.slave_id = ms.id
                JOIN funcao_registrador fr ON mr.funcao_id = fr.id
                ORDER BY ms.slave_id, mr.endereco;
            """)
            registers_to_test = connection.execute(query).fetchall()
            log.info(f"{len(registers_to_test)} registradores encontrados no banco de dados para teste.")
    except Exception as e:
        log.error(f"Erro ao conectar ou consultar o banco de dados: {e}")
        return

    client = ModbusSerialClient(port='/tmp/ttyS1', baudrate=115200, timeout=2)
    if not client.connect():
        log.error("Falha ao conectar ao cliente Modbus. Verifique a porta e se o slave está rodando.")
        return

    try:
        for reg in registers_to_test:
            log.info(f"Testando: Slave {reg.slave_id} ({reg.slave_name}) - '{reg.funcao_nome}' - Endereço {reg.endereco} (Tipo DB: {reg.data_type})")
            addr = reg.endereco
            response = None
            
            count = 2 if reg.data_type == 'float32' or reg.data_type == 'int32' else 1

            if reg.tipo == 'holding_register':
                response = client.read_holding_registers(address=addr - 40001, count=count, device_id=reg.slave_id)
            elif reg.tipo == 'input_register':
                response = client.read_input_registers(address=addr - 30001, count=count, device_id=reg.slave_id)
            elif reg.tipo == 'coil':
                response = client.read_coils(address=addr - 1, count=count, device_id=reg.slave_id)
            elif reg.tipo == 'discrete_input':
                response = client.read_discrete_inputs(address=addr - 10001, count=count, device_id=reg.slave_id)

            if not response or response.isError():
                log.error(f"  --> ERRO: {response}")
            else:
                if reg.data_type == 'float32' and hasattr(response, 'registers'):
                    valor_decodificado = registers_to_float(response.registers)
                    log.info(f"  --> SUCESSO: Valor lido: {response.registers} -> Decodificado: {valor_decodificado:.2f}")
                elif reg.data_type == 'int32' and hasattr(response, 'registers'):
                    valor_decodificado = registers_to_int(response.registers)
                    log.info(f"  --> SUCESSO: Valor lido: {response.registers} -> Decodificado: {valor_decodificado}")
                else:
                    valor_lido = response.registers if hasattr(response, 'registers') else response.bits
                    log.info(f"  --> SUCESSO: Valor lido: {valor_lido}")
    finally:
        client.close()
        log.info("\n--- Teste finalizado. Conexão Modbus fechada. ---")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Controlador e Testador Modbus RTU")
        parser.add_argument("-t", "--test", action="store_true",
                            help="Roda em modo de teste, lendo todos os registradores do BD.")
        args = parser.parse_args()

        if args.test:
            run_test_mode()
        else:
            run_controller()
    except Exception as e:
        log.error(f"Erro fatal durante a execução do script: {e}", exc_info=True)
