import logging
import time
import struct
import os
import argparse
import datetime # Nova importação
import threading
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
def get_control_config(session):
    """Busca e estrutura a configuração de controle do banco de dados."""
    query = text("""
        SELECT 
            m.id as motobomba_id,
            (SELECT ms.slave_id FROM modbus_slave ms WHERE ms.id = m.modbus_slave_id) as bomba_slave_id,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = m.modbus_slave_id AND fr.funcao = 'Acionamento (Liga/Desliga)') as bomba_coil_addr,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = m.modbus_slave_id AND fr.funcao = 'Consumo') as bomba_consumo_addr,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = m.modbus_slave_id AND fr.funcao = 'Tensão') as bomba_tensao_addr,
            (SELECT mr.endereco FROM modbus_register mr JOIN funcao_registrador fr ON mr.funcao_id = fr.id WHERE mr.slave_id = m.modbus_slave_id AND fr.funcao = 'Corrente') as bomba_corrente_addr,
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

def get_situacao_ids(session):
    """Busca os IDs das situações 'Ciclo iniciado' e 'Ciclo finalizado'."""
    query_iniciado = text("SELECT id FROM situacao WHERE situacao = 'Ciclo iniciado'")
    query_finalizado = text("SELECT id FROM situacao WHERE situacao = 'Ciclo finalizado'")
    iniciado_id = session.execute(query_iniciado).scalar_one_or_none()
    finalizado_id = session.execute(query_finalizado).scalar_one_or_none()
    if iniciado_id is None or finalizado_id is None:
        raise ValueError("Situações 'Ciclo iniciado' ou 'Ciclo finalizado' não encontradas na tabela 'situacao'.")
    return iniciado_id, finalizado_id

def start_acionamento_cycle(session, motobomba_id, situacao_iniciado_id):
    """Insere um novo registro de acionamento no banco de dados."""
    log.info(f"Registrando novo acionamento para motobomba {motobomba_id}.")
    insert_query = text("""
        INSERT INTO acionamento (mb_id, data, hora_lig, situacao_id)
        VALUES (:mb_id, :data, :hora_lig, :situacao_id)
    """)
    result = session.execute(insert_query, {
        'mb_id': motobomba_id,
        'data': datetime.date.today(),
        'hora_lig': datetime.datetime.now().time(),
        'situacao_id': situacao_iniciado_id
    })
    session.commit()
    return result.lastrowid # Retorna o ID do novo acionamento

def end_acionamento_cycle(session, acionamento_id, consumo_kwh, situacao_finalizado_id):
    """Finaliza um registro de acionamento existente no banco de dados."""
    log.info(f"Finalizando acionamento {acionamento_id} com consumo {consumo_kwh:.2f} kWh.")
    update_query = text("""
        UPDATE acionamento
        SET hora_des = :hora_des, consumo_kwh = :consumo_kwh, situacao_id = :situacao_id
        WHERE id = :acionamento_id
    """)
    session.execute(update_query, {
        'hora_des': datetime.datetime.now().time(),
        'consumo_kwh': consumo_kwh,
        'situacao_id': situacao_finalizado_id,
        'acionamento_id': acionamento_id
    })
    session.commit()

def get_unfinished_acionamento(session, motobomba_id, situacao_iniciado_id):
    """Busca um acionamento não finalizado para a motobomba especificada."""
    query = text("""
        SELECT id, hora_lig FROM acionamento
        WHERE mb_id = :mb_id AND situacao_id = :situacao_id AND hora_des IS NULL
    """)
    result = session.execute(query, {
        'mb_id': motobomba_id,
        'situacao_id': situacao_iniciado_id
    }).first()
    return result # Retorna um Row ou None

def save_nivel_readings(session, acum_id, nivel_acum_percent, acum_capacidade, dist_id, nivel_dist_percent, dist_capacidade):
    """Calcula o volume a partir da porcentagem e salva no banco de dados."""
    try:
        # Calcula o volume atual em litros
        volume_acum = (nivel_acum_percent / 100) * acum_capacidade
        volume_dist = (nivel_dist_percent / 100) * dist_capacidade

        log.info(f"Salvando volumes no BD: AC={volume_acum:.0f}L ({nivel_acum_percent:.2f}%), DI={volume_dist:.0f}L ({nivel_dist_percent:.2f}%)")
        
        query = text("""
            INSERT INTO nivel (reservatorio_id, valor, data, hora)
            VALUES (:res_id, :valor, :data, :hora)
        """)
        now = datetime.datetime.now()
        today = now.date()
        current_time = now.time()

        # A coluna 'valor' armazena o volume em litros (inteiro)
        session.execute(query, {'res_id': acum_id, 'valor': int(volume_acum), 'data': today, 'hora': current_time})
        session.execute(query, {'res_id': dist_id, 'valor': int(volume_dist), 'data': today, 'hora': current_time})
        
        session.commit()
        log.info("Volumes salvos com sucesso.")
    except Exception as e:
        log.error(f"Erro ao salvar níveis no banco de dados: {e}")
        session.rollback()

def update_slave_statuses(client, stop_event, lock):
    """Thread que periodicamente verifica o status de todos os slaves."""
    log.info("Thread de verificação de status iniciada.")
    engine = create_engine(DB_URI)
    
    while not stop_event.is_set():
        try:
            with engine.connect() as connection:
                # Buscar todos os slaves do banco de dados
                slaves_query = text("SELECT id, slave_id, nome FROM modbus_slave")
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
                    update_query = text("""
                        UPDATE modbus_slave
                        SET status = :status, last_seen = :last_seen
                        WHERE id = :id
                    """)
                    connection.execute(update_query, {'status': status, 'last_seen': now, 'id': slave.id})
                    connection.commit()
                    log.info(f"Status do slave {slave.nome} atualizado para: {status}")

        except Exception as e:
            log.error(f"Erro na thread de verificação de status: {e}", exc_info=True)
        
        # Aguardar 60 segundos ou até o evento de parada ser acionado
        stop_event.wait(60)
    
    log.info("Thread de verificação de status finalizada.")


def run_controller():
    log.info("--- Iniciando Master V3 (Controlador) ---") # Atualizado para V3

    current_acionamento_id = None # Variável para rastrear o ID do acionamento atual
    connection = None # Inicializa a conexão como None
    client = None # Inicializa o cliente Modbus como None
    status_thread = None # Para a thread de verificação de status
    stop_event = threading.Event() # Evento para parar a thread

    try:
        engine = create_engine(DB_URI)
        connection = engine.connect() # Abre a conexão explicitamente

        # Obter IDs das situações
        situacao_iniciado_id, situacao_finalizado_id = get_situacao_ids(connection)

        config = get_control_config(connection)
        if not config:
            log.error("Não foi possível carregar a configuração de controle do banco de dados. Verifique se uma bomba principal e seus reservatórios estão configurados.")
            return
        log.info("Configuração de controle carregada do banco de dados com sucesso.")
        log.info(f"Motobomba: Slave ID {config['bomba_slave_id']}")

        # Inicializar cliente Modbus após carregar a configuração do DB
        client = ModbusSerialClient(port='/tmp/ttyS1', baudrate=115200, timeout=2) # Porta corrigida para ttyS1
        if not client.connect():
            log.error("Falha ao conectar ao cliente Modbus. Verifique a porta e se o slave está rodando.")
            return

        # Criar e compartilhar o Lock para acesso ao cliente Modbus
        modbus_lock = threading.Lock()

        # --- Iniciar a thread de verificação de status ---
        status_thread = threading.Thread(target=update_slave_statuses, args=(client, stop_event, modbus_lock))
        status_thread.daemon = True
        status_thread.start()

        # Escrever capacidade máxima dos reservatórios nos slaves
        with modbus_lock:
            log.info(f"Escrevendo capacidade máxima do Reservatório de Acumulação ({config['acum_capacidade']}L) no Slave {config['acum_slave_id']}.")
            client.write_registers(address=config['acum_volume_addr'] - 40001, values=int_to_registers(int(config['acum_capacidade'])), device_id=config['acum_slave_id'])
            
            log.info(f"Escrevendo capacidade máxima do Reservatório de Distribuição ({config['dist_capacidade']}L) no Slave {config['dist_slave_id']}.")
            client.write_registers(address=config['dist_volume_addr'] - 40001, values=int_to_registers(int(config['dist_capacidade'])), device_id=config['dist_slave_id'])

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
            
            potencia_watts = potencia_cv * 735.499
            
            with modbus_lock:
                log.info(f"Escrevendo potência da bomba ({potencia_cv:.2f} CV = {potencia_watts:.2f} Watts) no Slave {config['bomba_slave_id']}.")
                client.write_registers(address=config['bomba_potencia_addr'] - 40001, values=float_to_registers(potencia_watts), device_id=config['bomba_slave_id'])
        except ValueError:
            log.error(f"Valor de potência da bomba inválido no banco de dados: '{config['bomba_potencia']}'. Esperado um número ou fração (ex: '1/3', '0.5', '1').")
            return

        # --- Validação de endereços Modbus ---
        if config['bomba_coil_addr'] is None:
            log.error("Endereço da bobina de acionamento da bomba não encontrado no banco de dados. Verifique a configuração do registrador 'Acionamento (Liga/Desliga)' para a motobomba principal.")
            return
        # ... (outras validações de endereço) ...

        # --- Lógica de Recuperação de Estado (Master Reiniciado) ---
        with modbus_lock:
            log.info("Verificando estado da bomba no Modbus para recuperação...")
            modbus_pump_status_resp = client.read_coils(address=config['bomba_coil_addr'] - 1, count=1, device_id=config['bomba_slave_id'])
        
        if modbus_pump_status_resp.isError():
            log.error("Erro ao ler estado da bomba no Modbus durante a inicialização. Não é possível recuperar o estado.")
            return
        is_pump_on_modbus = modbus_pump_status_resp.bits[0]
        log.info(f"Estado da bomba no Modbus: {'ON' if is_pump_on_modbus else 'OFF'}.")

        unfinished_acionamento = get_unfinished_acionamento(connection, config['motobomba_id'], situacao_iniciado_id)

        # ... (lógica de recuperação de estado) ...

        # --- Loop principal de controle ---
        while True:
            # 1. Ler níveis atuais dos reservatórios
            with modbus_lock:
                log.info("Lendo níveis atuais dos reservatórios...")
                resp_acum = client.read_input_registers(address=config['acum_level_addr'] - 30001, count=2, device_id=config['acum_slave_id'])
                resp_dist = client.read_input_registers(address=config['dist_level_addr'] - 30001, count=2, device_id=config['dist_slave_id'])

            if resp_acum.isError() or resp_dist.isError():
                log.warning("Erro ao ler nível de um dos reservatórios. Pulando ciclo.")
                time.sleep(10)
                continue

            nivel_acum = registers_to_float(resp_acum.registers)
            nivel_dist = registers_to_float(resp_dist.registers)

            save_nivel_readings(connection, config['acum_id'], nivel_acum, config['acum_capacidade'], config['dist_id'], nivel_dist, config['dist_capacidade'])

            # 2. Ler estado atual da bomba
            with modbus_lock:
                current_pump_status_resp = client.read_coils(address=config['bomba_coil_addr'] - 1, count=1, device_id=config['bomba_slave_id'])
            
            if current_pump_status_resp.isError():
                log.warning("Erro ao ler estado da bomba. Pulando ciclo.")
                time.sleep(10)
                continue
            current_pump_status = current_pump_status_resp.bits[0]

            # 3. Ler dados elétricos da bomba
            with modbus_lock:
                resp_tensao = client.read_input_registers(address=config['bomba_tensao_addr'] - 30001, count=2, device_id=config['bomba_slave_id'])
                resp_corrente = client.read_input_registers(address=config['bomba_corrente_addr'] - 30001, count=2, device_id=config['bomba_slave_id'])
                resp_potencia = client.read_holding_registers(address=config['bomba_potencia_addr'] - 40001, count=2, device_id=config['bomba_slave_id'])

            tensao = registers_to_float(resp_tensao.registers) if not resp_tensao.isError() else 0.0
            corrente = registers_to_float(resp_corrente.registers) if not resp_corrente.isError() else 0.0
            potencia = registers_to_float(resp_potencia.registers) if not resp_potencia.isError() else 0.0

            # ... (log unificado) ...

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
            # ... (lógica de ligar/desligar) ...

            # 4. Atuar se o estado desejado for diferente do atual
            if desired_pump_status != current_pump_status:
                log.warning(f"Ação: Alterando estado da bomba para {'ON' if desired_pump_status else 'OFF'}.")
                with modbus_lock:
                    client.write_coil(address=config['bomba_coil_addr'] - 1, value=desired_pump_status, device_id=config['bomba_slave_id'])
                
                if desired_pump_status:
                    current_acionamento_id = start_acionamento_cycle(connection, config['motobomba_id'], situacao_iniciado_id)
                else: # Bomba desligou
                    acionamento_id_to_close = current_acionamento_id
                    # Se por algum motivo o ID foi perdido, tenta recuperar o último ciclo aberto
                    if acionamento_id_to_close is None:
                        log.warning("current_acionamento_id é None ao tentar desligar a bomba. Tentando recuperar o ciclo aberto mais recente no banco de dados...")
                        unfinished = get_unfinished_acionamento(connection, config['motobomba_id'], situacao_iniciado_id)
                        if unfinished:
                            acionamento_id_to_close = unfinished.id
                            log.info(f"Ciclo aberto {acionamento_id_to_close} recuperado para finalização.")
                        else:
                            log.error("Não foi possível encontrar um ciclo de acionamento aberto para finalizar. O registro de consumo para este ciclo pode ser perdido.")

                    # Ler consumo do slave
                    with modbus_lock:
                        consumo_kwh_resp = client.read_input_registers(address=config['bomba_consumo_addr'] - 30001, count=2, device_id=config['bomba_slave_id'])
                    consumo_kwh = registers_to_float(consumo_kwh_resp.registers) if not consumo_kwh_resp.isError() else 0.0
                    
                    if acionamento_id_to_close is not None:
                        end_acionamento_cycle(connection, acionamento_id_to_close, consumo_kwh, situacao_finalizado_id)
                    
                    current_acionamento_id = None
            else:
                log.info("Nenhuma ação necessária. Mantendo estado atual da bomba.")

            log.info("Ciclo de controle finalizado. Aguardando 10 segundos.")
            time.sleep(10)

    except KeyboardInterrupt:
        log.info("Interrupção pelo usuário. Encerrando controlador.")
    finally:
        stop_event.set() # Sinaliza para a thread de status parar
        if status_thread:
            status_thread.join() # Espera a thread de status finalizar
        if connection:
            connection.close()
        if client:
            client.close()
        log.info("Conexão Modbus fechada.")

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
