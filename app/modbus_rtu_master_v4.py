import logging
import time
import struct
import os
import argparse
import datetime # Nova importação
import threading
from pymodbus.client import ModbusSerialClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.modbus_rule_model import ModbusRule
from app.models.modbus_condition_model import ModbusCondition
from app.models.modbus_action_model import ModbusAction
from app.models.modbus_device_register_model import ModbusRegister

# --- Configuração do Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

# --- Configuração do Banco de Dados ---
# Adiciona o diretório raiz ao sys.path para permitir a importação do config
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import SQLALCHEMY_DATABASE_URI as DB_URI

# --- Funções Auxiliares de Conversão ---
def registers_to_float(registers):
    if not registers or len(registers) < 2:
        return 0.0
    packed = int.to_bytes(registers[0], 2, 'big') + int.to_bytes(registers[1], 2, 'big')
    return struct.unpack('>f', packed)[0]

def float_to_registers(value):
    """Converte float32 para dois registradores de 16 bits"""
    try:
        packed = struct.pack('>f', value)
        return [struct.unpack('>H', packed[i:i+2])[0] for i in range(0, 4, 2)]
    except Exception as e:
        log.error(f"Erro ao converter float para registradores: {e}, valor: {value}")
        return [0, 0]

def int_to_registers(value):
    """Converte um valor int para uma lista de 2 registradores de 16 bits (big-endian)."""
    try:
        return [(value >> 16) & 0xFFFF, value & 0xFFFF]
    except Exception as e:
        log.error(f"Erro ao converter int para registradores: {e}, valor: {value}")
        return [0, 0]

def registers_to_int(registers):
    """Converte uma lista de 2 registradores de 16 bits para um int (big-endian)."""
    if not registers or len(registers) < 2:
        return 0
    try:
        return (registers[0] << 16) | registers[1]
    except Exception as e:
        log.error(f"Erro ao converter registradores para int: {e}, registradores: {registers}")
        return 0

# --- Funções de Interação com o Banco de Dados (Configuração e Acionamento) ---




def update_slave_statuses(client, stop_event, lock):
    """Thread que periodicamente verifica o status de todos os slaves."""
    log.info("Thread de verificação de status iniciada.")
    engine = create_engine(DB_URI)
    
    while not stop_event.is_set():
        try:
            with engine.connect() as connection:
                # Buscar todos os slaves do banco de dados
                slaves_query = text("SELECT id, slave_id, device_name as nome FROM modbus_device WHERE ativo = TRUE")
                slaves = connection.execute(slaves_query).fetchall()
                
                for slave in slaves:
                    log.info(f"Verificando status do slave: {slave.nome} (ID: {slave.slave_id})")
                    
                    response = None
                    with lock: # Adquirir o lock antes de usar o cliente modbus
                        # Tenta ler um registrador simples (ex: holding register 0)
                        response = client.read_holding_registers(address=0, count=1, device_id=slave.slave_id)
                    
                    now = datetime.datetime.now()
                    if not response.isError():
                        status = "Online"
                    else:
                        status = "Offline"
                    
                    # Atualizar o status no banco de dados
                    # Esta tabela não existe mais, a informação de status foi movida para modbus_device
                    # A coluna 'status' e 'last_seen' precisam ser adicionadas ao modelo ModbusDevice
                    # Por agora, vamos comentar a atualização para evitar erros, mas isso precisa ser resolvido.
                    # update_query = text("""
                    #     UPDATE modbus_device
                    #     SET status = :status, last_seen = :last_seen
                    #     WHERE id = :id
                    # """)
                    # connection.execute(update_query, {'status': status, 'last_seen': now, 'id': slave.id})
                    # connection.commit()
                    log.info(f"Status do slave {slave.nome} verificado como: {status}")

        except Exception as e:
            log.error(f"Erro na thread de verificação de status: {e}", exc_info=True)
        
        # Aguardar 60 segundos ou até o evento de parada ser acionado
        stop_event.wait(60)
    
    log.info("Thread de verificação de status finalizada.")



def get_register_type_from_code(code):
    if code == 1: return 'coil'
    if code == 2: return 'discrete_input'
    if code == 3: return 'holding_register'
    if code == 4: return 'input_register'
    return None

def read_register_value(client, lock, register):
    """Lê e decodifica o valor de um registrador Modbus."""
    with lock:
        addr = register.address
        count = 2 if register.data_type in ['float32', 'int32'] else 1
        register_type = get_register_type_from_code(register.function_code)
        
        if register_type == 'holding_register':
            response = client.read_holding_registers(address=addr - 40001, count=count, device_id=register.device.slave_id)
        elif register_type == 'input_register':
            response = client.read_input_registers(address=addr - 30001, count=count, device_id=register.device.slave_id)
        elif register_type == 'coil':
            response = client.read_coils(address=addr - 1, count=count, device_id=register.device.slave_id)
        elif register_type == 'discrete_input':
            response = client.read_discrete_inputs(address=addr - 10001, count=count, device_id=register.device.slave_id)
        else:
            log.error(f"Tipo de registrador desconhecido: {register_type}")
            return None, False

    if not response or response.isError():
        log.warning(f"Erro ao ler registrador {register.name} (Endereço: {addr}, Slave: {register.device.slave_id})")
        return None, False

    if register.data_type == 'float32':
        return registers_to_float(response.registers), True
    elif register.data_type == 'int32':
        return registers_to_int(response.registers), True
    elif register.data_type == 'boolean':
        return response.bits[0], True
    else: # int16, uint16
        return response.registers[0], True

def evaluate_rules(client, session, lock):
    """Busca, avalia e executa as regras Modbus."""
    log.info("Iniciando avaliação de regras...")
    try:
        rules = session.query(ModbusRule).filter_by(enabled=True).order_by(ModbusRule.priority.desc()).all()
        log.info(f"{len(rules)} regras habilitadas encontradas.")

        for rule in rules:
            log.info(f"Avaliando regra: '{rule.name}'")
            try:
                conditions_met = True
                for condition in rule.conditions:
                    left_register = session.get(ModbusRegister, condition.left_register_id)
                    if not left_register:
                        log.error(f"Registrador esquerdo (ID: {condition.left_register_id}) não encontrado para a condição '{condition.name}'. Pulando regra.")
                        conditions_met = False
                        break

                    # Lê o valor atual do registrador
                    current_value, success = read_register_value(client, lock, left_register)
                    if not success:
                        log.warning(f"Não foi possível ler o valor para a condição '{condition.name}'. Pulando regra.")
                        conditions_met = False
                        break
                    
                    log.info(f"  Condição '{condition.name}': Valor lido de '{left_register.name}' = {current_value}. Comparando com {condition.right_value} usando o operador '{condition.operator}'.")

                    # Avalia a condição
                    op = condition.operator.value # Use .value to get the string '=='
                    value_to_compare = condition.right_value

                    condition_is_true = False
                    if op == '==': condition_is_true = (current_value == value_to_compare)
                    elif op == '!=': condition_is_true = (current_value != value_to_compare)
                    elif op == '>':  condition_is_true = (current_value > value_to_compare)
                    elif op == '<':  condition_is_true = (current_value < value_to_compare)
                    elif op == '>=': condition_is_true = (current_value >= value_to_compare)
                    elif op == '<=': condition_is_true = (current_value <= value_to_compare)

                    if not condition_is_true:
                        conditions_met = False
                        log.info(f"  Condição '{condition.name}' não atendida. Parando avaliação para esta regra.")
                        break # Para de checar outras condições para esta regra

                if conditions_met:
                    log.warning(f"REGRA ATIVADA: '{rule.name}'. Todas as condições foram atendidas. Executando ações.")
                    if not rule.actions:
                        log.info(f"  Regra '{rule.name}' não possui ações configuradas. Nenhuma ação será executada.")
                    for action in rule.actions:
                        target_register = session.get(ModbusRegister, action.target_register_id)
                        if not target_register:
                            log.error(f"Registrador alvo (ID: {action.target_register_id}) não encontrado para a ação '{action.name}'. Pulando ação.")
                            continue

                        value_to_write = action.write_value
                        log.info(f"  Ação '{action.name}': Escrevendo valor {value_to_write} em '{target_register.name}' (Slave: {target_register.device.slave_id}, Endereço: {target_register.address})")

                        # Converte o valor para o formato do registrador
                        if target_register.data_type == 'float32':
                            values_to_write = float_to_registers(float(value_to_write))
                        elif target_register.data_type == 'int32':
                            values_to_write = int_to_registers(int(value_to_write))
                        else: # boolean, int16, uint16
                            values_to_write = int(value_to_write)

                        # Escreve no registrador/bobina
                        with lock:
                            register_type = get_register_type_from_code(target_register.function_code)
                            log.info(f"  Tentando escrever em um registrador do tipo: {register_type}")
                            response = None
                            if register_type == 'holding_register':
                                log.info(f"    --> Escrevendo em Holding Register. Endereço: {target_register.address - 40001}, Valor: {values_to_write}")
                                response = client.write_registers(target_register.address - 40001, values_to_write, device_id=target_register.device.slave_id)
                            elif register_type == 'coil':
                                log.info(f"    --> Escrevendo em Coil. Endereço: {target_register.address - 1}, Valor: {bool(value_to_write)}")
                                response = client.write_coil(target_register.address - 1, bool(value_to_write), device_id=target_register.device.slave_id)
                            else:
                                log.error(f"Tipo de registrador '{register_type}' não suporta escrita para a ação '{action.name}'.")

                            if response and response.isError():
                                log.error(f"  --> ERRO DE ESCRITA MODBUS: {response}")
                            elif response:
                                log.info(f"  --> Escrita Modbus bem-sucedida.")
                    
                    if rule.stop_on_trigger:
                        log.info(f"Regra '{rule.name}' tem 'stop_on_trigger' ativado. Parando a avaliação de outras regras neste ciclo.")
                        break # Para de avaliar outras regras

            except Exception as e:
                log.error(f"Erro ao avaliar a regra '{rule.name}': {e}", exc_info=True)

    except Exception as e:
        log.error(f"Erro ao buscar regras do banco de dados: {e}", exc_info=True)

def run_controller():
    log.info("--- Iniciando Master V4 (Controlador com Regras) ---")

    connection = None
    client = None
    status_thread = None
    stop_event = threading.Event()

    try:
        engine = create_engine(DB_URI)
        Session = sessionmaker(bind=engine)
        db_session = Session()

        client = ModbusSerialClient(port='/tmp/ttyS1', baudrate=115200, timeout=2)
        if not client.connect():
            log.error("Falha ao conectar ao cliente Modbus. Verifique a porta e se o slave está rodando.")
            return

        modbus_lock = threading.Lock()

        status_thread = threading.Thread(target=update_slave_statuses, args=(client, stop_event, modbus_lock))
        status_thread.daemon = True
        status_thread.start()

        # --- Loop principal de controle baseado em regras ---
        while not stop_event.is_set():
            evaluate_rules(client, db_session, modbus_lock)
            
            log.info("Ciclo de avaliação de regras finalizado. Aguardando 15 segundos.")
            time.sleep(15)

    except KeyboardInterrupt:
        log.info("Interrupção pelo usuário. Encerrando controlador.")
    except Exception as e:
        log.error(f"Erro inesperado no controlador: {e}", exc_info=True)
    finally:
        stop_event.set()
        if status_thread:
            status_thread.join()
        if db_session:
            db_session.close()
        if client:
            client.close()
        log.info("Conexões com Modbus e Banco de Dados fechadas.")

def run_test_mode():
    """Conecta no BD, busca todos os registradores e tenta ler cada um."""
    log.info("--- Iniciando Master em MODO DE TESTE ---")

    client = None # Inicializa o cliente como None
    connection = None # Inicializa a conexão como None

    try:
        engine = create_engine(DB_URI)
        connection = engine.connect() # Abre a conexão explicitamente

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

        if not registers_to_test:
            log.error("Nenhum registrador encontrado no banco de dados")
            return

    except Exception as e:
        log.error(f"Erro ao conectar ou consultar o banco de dados: {e}")
        return

    client = ModbusSerialClient(port='/tmp/ttyS1', baudrate=115200, timeout=2, retries=3)
    if not client.connect():
        log.error("Falha ao conectar ao cliente Modbus. Verifique a porta e se o slave está rodando.")
        return

    try:
        for reg in registers_to_test:
            log.info(f"Testando: Slave {reg.slave_id} ({reg.slave_name}) - '{reg.funcao_nome}' - Endereço {reg.endereco} (Tipo DB: {reg.data_type})")
            addr = reg.endereco
            response = None
            
            count = 2 if reg.data_type in ['float32', 'int32'] else 1

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
        if connection: # Garante que a conexão seja fechada se foi aberta
            connection.close()
        if client: # Garante que o cliente seja fechado se foi conectado
            client.close()
        log.info("\n--- Teste finalizado. Conexão Modbus fechada. ---")


def main():
    """Função principal com parser de argumentos"""
    parser = argparse.ArgumentParser(description='Modbus Master Controller')
    parser.add_argument('--test', action='store_true', help='Executar em modo de teste')
    parser.add_argument('--controller', action='store_true', help='Executar em modo controlador')

    args = parser.parse_args()

    if args.test:
        run_test_mode()
    elif args.controller:
        run_controller()
    else:
        # Se nenhum argumento for passado, executar controlador por padrão
        run_controller()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Erro fatal durante a execução do script: {e}", exc_info=True)
