from flask import request, redirect, render_template, url_for, flash
from app import app, db
from ..models import situacao_model, reservatorio_model, motobomba_model, nivel_model, modbus_device_register_model
from datetime import date, time

@app.route('/base_de_dados/inicie_tabelas', methods=["GET", "POST"])
def initialize_database():
    if request.method == 'POST':
        try:
            populate_db()
            flash('Base de dados inicializada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao inicializar a base de dados: {e}', 'danger')
        return redirect(url_for('initialize_database'))

    # GET request
    situacoes = situacao_model.Situacao.query.all()
    reservatorios = reservatorio_model.Reservatorio.query.all()
    tubos = motobomba_model.Tubospvc.query.all()
    return render_template("init_database.html", situacoes=situacoes, reservatorios=reservatorios, tubos=tubos)


def populate_db():
    #tabela tipo_de_reservatorio
    if not reservatorio_model.Tiporeservatorio.query.first():
        tipo_1 = reservatorio_model.Tiporeservatorio(tipo="Reservatório de Distribuição")
        tipo_2 = reservatorio_model.Tiporeservatorio(tipo="Reservatório de Acumulação")
        db.session.add(tipo_1)
        db.session.add(tipo_2)
        db.session.commit()

    #tabela tubos
    tubos_data = [
        {'pol': '1/2"', 'mm': '20 mm'},
        {'pol': '3/4"', 'mm': '25 mm'},
        {'pol': '1"', 'mm': '32 mm'},
        {'pol': '1 1/4"', 'mm': '40 mm'},
        {'pol': '1 1/2"', 'mm': '50 mm'},
        {'pol': '2"', 'mm': '60 mm'},
        {'pol': '2 1/2"', 'mm': '75 mm'},
        {'pol': '3"', 'mm': '85 mm'},
        {'pol': '3 1/2"', 'mm': '0 mm'},
        {'pol': '4"', 'mm': '110 mm'},
        {'pol': '5"', 'mm': '127 mm'},
        {'pol': '6"', 'mm': '150 mm'},
        {'pol': '8"', 'mm': '200 mm'},
        {'pol': '10"', 'mm': '254 mm'},
        {'pol': '12"', 'mm': '304 mm'},
    ]

    for data in tubos_data:
        existing_tubo = motobomba_model.Tubospvc.query.filter_by(pol=data['pol']).first()
        if not existing_tubo:
            new_tubo = motobomba_model.Tubospvc(pol=data['pol'], mm=data['mm'])
            db.session.add(new_tubo)
    db.session.commit()

    # #tabela funcao_registrador - REMOVED
    # funcoes = [
    #     "Nível", "Tensão", "Corrente", "Potência", "Volume",
    #     "Acionamento (Liga/Desliga)", "Status", "Análise Espectral de Fluxo", "Consumo"
    # ]
    # funcoes_map = {}
    # for f_nome in funcoes:
    #     funcao_obj = funcao_registrador_model.FuncaoRegistrador.query.filter_by(funcao=f_nome).first()
    #     if not funcao_obj:
    #         funcao_obj = funcao_registrador_model.FuncaoRegistrador(funcao=f_nome)
    #         db.session.add(funcao_obj)
    #     funcoes_map[f_nome] = funcao_obj
    # db.session.commit()

    # Configurar Escravos e Registradores Modbus Padrão
    slaves_config = {
        1: {"name": "Motobomba Principal", "type": "bomba", "associar_a": ("motobomba", "Bomba Principal")},
        2: {"name": "Reservatório de Acumulação", "type": "reservatorio", "associar_a": ("reservatorio", "Reservatório Secundário")},
        3: {"name": "Reservatório de Distribuição", "type": "reservatorio", "associar_a": ("reservatorio", "Reservatório Principal")}
    }
    registers_config = [
        # Bomba
        {"device_id": 1, "address": 1, "function_code": 1, "name": "Acionamento (Liga/Desliga)", "rw": "W", "data_type": "bool", "scale": 1.0},
        {"device_id": 1, "address": 40100, "function_code": 3, "name": "Tensão", "rw": "R", "data_type": "float", "scale": 0.1},
        {"device_id": 1, "address": 40101, "function_code": 3, "name": "Corrente", "rw": "R", "data_type": "float", "scale": 0.1},
        {"device_id": 1, "address": 40105, "function_code": 3, "name": "Consumo", "rw": "R", "data_type": "float", "scale": 1.0},
        # Reservatórios
        {"device_id": 2, "address": 30001, "function_code": 4, "name": "Nível", "rw": "R", "data_type": "float", "scale": 1.0},
        {"device_id": 2, "address": 40001, "function_code": 3, "name": "Volume", "rw": "W", "data_type": "float", "scale": 1.0},
        {"device_id": 3, "address": 30001, "function_code": 4, "name": "Nível", "rw": "R", "data_type": "float", "scale": 1.0},
        {"device_id": 3, "address": 40001, "function_code": 3, "name": "Volume", "rw": "W", "data_type": "float", "scale": 1.0},
    ]

    # Adicionar motobomba e reservatórios antes de associar slaves
    if not motobomba_model.Motobomba.query.filter_by(nome="Bomba Principal").first():
        new_pump = motobomba_model.Motobomba(nome="Bomba Principal", descricao="Bomba Principal do sistema")
        db.session.add(new_pump)

    if not reservatorio_model.Reservatorio.query.filter_by(nome="Reservatório Secundário").first():
        tipo_inferior = reservatorio_model.Tiporeservatorio.query.filter_by(tipo="Reservatório de Acumulação").first()
        res_2 = reservatorio_model.Reservatorio(nome="Reservatório Secundário", descricao="Reservatório de água de reuso", capacidade_maxima=1000.0, tipos=tipo_inferior)
        db.session.add(res_2)

    if not reservatorio_model.Reservatorio.query.filter_by(nome="Reservatório Principal").first():
        tipo_superior = reservatorio_model.Tiporeservatorio.query.filter_by(tipo="Reservatório de Distribuição").first()
        res_1 = reservatorio_model.Reservatorio(nome="Reservatório Principal", descricao="Reservatório de água potável principal", capacidade_maxima=11000.0, tipos=tipo_superior)
        db.session.add(res_1)
    db.session.commit()


    for slave_id, config in slaves_config.items():
        device = modbus_device_register_model.ModbusDevice.query.filter_by(slave_id=slave_id).first()
        if not device:
            device = modbus_device_register_model.ModbusDevice(name=config["name"], slave_id=slave_id, type=config["type"])
            db.session.add(device)
            db.session.commit()

        # Associar ao equipamento
        tipo_equip, nome_equip = config["associar_a"]
        if tipo_equip == "motobomba":
            pump = motobomba_model.Motobomba.query.filter_by(nome=nome_equip).first()
            if pump and pump.modbus_slave_id is None:
                pump.modbus_slave_id = device.id # slave.id to device.id
        elif tipo_equip == "reservatorio":
            tank = reservatorio_model.Reservatorio.query.filter_by(nome=nome_equip).first()
            if tank and tank.modbus_slave_id is None:
                tank.modbus_slave_id = device.id # slave.id to device.id
    db.session.commit()

    for reg_config in registers_config:
        device = modbus_device_register_model.ModbusDevice.query.filter_by(slave_id=reg_config["device_id"]).first()
        if not device: continue

        # Procura por um registrador para este NOME e DISPOSITIVO
        reg = modbus_device_register_model.ModbusRegister.query.filter_by(
            device_id=device.id,
            name=reg_config["name"]
        ).first()

        if reg:
            # Se existe, verifica se os dados estão corretos e atualiza se necessário
            if reg.address != reg_config["address"] or reg.function_code != reg_config["function_code"]:
                reg.address = reg_config["address"]
                reg.function_code = reg_config["function_code"]
                reg.rw = reg_config["rw"]
                reg.data_type = reg_config["data_type"]
                reg.scale = reg_config["scale"]
        else:
            # Se não existe, cria um novo
            new_reg = modbus_device_register_model.ModbusRegister(
                device_id=device.id,
                name=reg_config["name"],
                function_code=reg_config["function_code"],
                address=reg_config["address"],
                data_type=reg_config["data_type"],
                scale=reg_config["scale"],
                rw=reg_config["rw"],
                descricao=f'{reg_config["name"]} do {device.name}'
            )
            db.session.add(new_reg)
    db.session.commit()


    #tabela situacao
    if not situacao_model.Situacao.query.first():
        # Status de ciclo
        sit_ciclo_iniciado = situacao_model.Situacao(situacao="Ciclo iniciado")
        sit_ciclo_finalizado = situacao_model.Situacao(situacao="Ciclo finalizado")
        sit_ciclo_interrompido = situacao_model.Situacao(situacao="Ciclo interrompido")

        # Status de eventos e falhas
        sit_funcionando = situacao_model.Situacao(situacao="Funcionando")
        sit_subtensao = situacao_model.Situacao(situacao="Subtensão")
        sit_sobretensao = situacao_model.Situacao(situacao="Sobretensão")
        sit_falta_energia = situacao_model.Situacao(situacao="Falta de energia eletrica")
        sit_nivel_minimo = situacao_model.Situacao(situacao="Reservatório inferior abaixo do nível mínimo")
        sit_nivel_maximo = situacao_model.Situacao(situacao="Reservatório superior cheio")
        sit_entrada_ar = situacao_model.Situacao(situacao="Entrada de ar")

        db.session.add_all([
            sit_ciclo_iniciado, sit_ciclo_finalizado, sit_ciclo_interrompido,
            sit_funcionando, sit_subtensao, sit_sobretensao, sit_falta_energia,
            sit_nivel_minimo, sit_nivel_maximo, sit_entrada_ar
        ])
        db.session.commit()

    # Adicionar níveis de exemplo
    res_1 = reservatorio_model.Reservatorio.query.filter_by(nome="Reservatório Principal").first()
    res_2 = reservatorio_model.Reservatorio.query.filter_by(nome="Reservatório Secundário").first()

    if res_1 and not nivel_model.Nivel.query.filter_by(reservatorio=res_1).first():
        niveis_res1 = [
            nivel_model.Nivel(valor=1000, data=date(2025, 10, 1), hora=time(8, 0, 0), reservatorio=res_1),
            nivel_model.Nivel(valor=1500, data=date(2025, 10, 1), hora=time(10, 0, 0), reservatorio=res_1),
            nivel_model.Nivel(valor=2000, data=date(2025, 10, 1), hora=time(12, 0, 0), reservatorio=res_1),
            nivel_model.Nivel(valor=2500, data=date(2025, 10, 1), hora=time(14, 0, 0), reservatorio=res_1),
            nivel_model.Nivel(valor=3000, data=date(2025, 10, 1), hora=time(16, 0, 0), reservatorio=res_1),
        ]
        db.session.add_all(niveis_res1)
        db.session.commit()

    if res_2 and not nivel_model.Nivel.query.filter_by(reservatorio=res_2).first():
        niveis_res2 = [
            nivel_model.Nivel(valor=300, data=date(2025, 10, 1), hora=time(9, 0, 0), reservatorio=res_2),
            nivel_model.Nivel(valor=500, data=date(2025, 10, 1), hora=time(11, 0, 0), reservatorio=res_2),
            nivel_model.Nivel(valor=600, data=date(2025, 10, 1), hora=time(13, 0, 0), reservatorio=res_2),
            nivel_model.Nivel(valor=800, data=date(2025, 10, 1), hora=time(15, 0, 0), reservatorio=res_2),
            nivel_model.Nivel(valor=900, data=date(2025, 10, 1), hora=time(17, 0, 0), reservatorio=res_2),
        ]
        db.session.add_all(niveis_res2)
        db.session.commit()
