from apscheduler.schedulers.background import BackgroundScheduler
from modbus_master import ModbusMaster
from models import db, Leitura

modbus = ModbusMaster()

def ler_escravos():
    escravos = {
        'cisterna_a': 1,
        'cisterna_b': 2,
        'caixa_superior': 3
    }
    for nome, id_escravo in escravos.items():
        try:
            valor = modbus.read_input_registers(id_escravo, address=0, count=1)[0]
            leitura = Leitura(nome_escravo=nome, valor=valor)
            db.session.add(leitura)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao ler {nome}: {e}")

def iniciar_agendador():
    scheduler = BackgroundScheduler()
    scheduler.add_job(ler_escravos, 'interval', seconds=10)
    scheduler.start()

