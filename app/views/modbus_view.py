from app import app, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from ..models.modbus_device_register_model import ModbusDevice, ModbusRegister, ModbusDeviceForm, ModbusRegisterForm, DeleteForm
 # Importar o novo modelo

@app.route("/modbus/status")
def status():
    """Exibe o status mais recente de todos os slaves, lido do banco de dados."""
    slaves = ModbusDevice.query.order_by(ModbusDevice.slave_id).all()
    return render_template("modbus_status.html", slaves=slaves)

@app.route("/modbus/lista")
def lista_modbus():
    slaves = ModbusDevice.query.all()
    form = DeleteForm()
    return render_template("lista_modbus.html", slaves=slaves, form=form)

@app.route("/modbus/novo_dispositivo", methods=["GET", "POST"])
def novo_dispositivo():
    form = ModbusDeviceForm()

    if form.validate_on_submit():
        novo_slave = ModbusDevice(device_name=form.device_name.data, ip_address=form.ip_address.data, slave_id=form.slave_id.data, type=form.type.data, ativo=form.ativo.data)
        db.session.add(novo_slave)
        db.session.commit() # Commit para obter o ID do novo escravo

        registradores_data = request.form.get('registradores_json')
        if registradores_data:
            import json
            registradores_list = json.loads(registradores_data)
            tipo_to_fc_map = {'coil': 1, 'discrete_input': 2, 'holding_register': 3, 'input_register': 4}
            rw_map = {'Read/Write': 'W', 'Read-Only': 'R'}

            for reg_data in registradores_list:
                new_register = ModbusRegister(
                    device_id=novo_slave.id,
                    name=reg_data.get('name'),
                    function_code=tipo_to_fc_map.get(reg_data.get('tipo')),
                    address=reg_data.get('endereco'),
                    data_type=reg_data.get('data_type', 'int'),
                    scale=float(reg_data.get('scale', 1.0)),
                    rw=rw_map.get(reg_data.get('acesso'), 'R'),
                    descricao=reg_data.get('descricao')
                )
                db.session.add(new_register)
            db.session.commit()

        flash("Escravo Modbus criado com sucesso!", "success")
        return redirect(url_for("lista_modbus"))

    return render_template("novo_dispositivo.html", form=form)

@app.route("/modbus/atualiza/<int:id>", methods=["GET", "POST"])
def atualiza_modbus(id):
    slave = ModbusDevice.query.get_or_404(id)
    form = ModbusDeviceForm(original_slave_id=slave.slave_id, obj=slave)
    if form.validate_on_submit():
        slave.device_name = form.device_name.data
        slave.ip_address = form.ip_address.data
        slave.slave_id = form.slave_id.data
        slave.type = form.type.data
        slave.ativo = form.ativo.data

        from ..models.motobomba_model import Motobomba
        from ..models.modbus_action_model import ModbusAction
        
        # Get IDs of registers to be deleted
        register_ids_to_delete = [reg.id for reg in ModbusRegister.query.filter_by(device_id=slave.id).with_entities(ModbusRegister.id)]

        if register_ids_to_delete:
            # Delete dependent ModbusActions
            ModbusAction.query.filter(
                ModbusAction.target_register_id.in_(register_ids_to_delete)
            ).delete(synchronize_session=False)

            # Unlink motobombas from these registers
            Motobomba.query.filter(
                Motobomba.actuator_register_id.in_(register_ids_to_delete)
            ).update(
                {Motobomba.actuator_register_id: None},
                synchronize_session=False
            )

            # Now it's safe to delete the registers
            ModbusRegister.query.filter_by(device_id=slave.id).delete(synchronize_session=False)
        
        registradores_data = request.form.get('registradores_json')
        if registradores_data:
            import json
            registradores_list = json.loads(registradores_data)
            tipo_to_fc_map = {'coil': 1, 'discrete_input': 2, 'holding_register': 3, 'input_register': 4}
            rw_map = {'Read/Write': 'W', 'Read-Only': 'R'}

            for reg_data in registradores_list:
                new_register = ModbusRegister(
                    device_id=slave.id,
                    name=reg_data.get('name'),
                    function_code=tipo_to_fc_map.get(reg_data.get('tipo')),
                    address=reg_data.get('endereco'),
                    data_type=reg_data.get('data_type', 'int'),
                    scale=float(reg_data.get('scale', 1.0)),
                    rw=rw_map.get(reg_data.get('acesso'), 'R'),
                    descricao=reg_data.get('descricao')
                )
                db.session.add(new_register)
        
        db.session.commit()
        flash("Escravo Modbus atualizado com sucesso!", "success")
        return redirect(url_for("lista_modbus"))
    else:
        flash("Erro ao atualizar Escravo Modbus! Verifique os dados.", "danger")

    # Para o método GET, carregar os registradores existentes
    if request.method == 'GET':
        form.type.data = slave.type.value
    fc_to_tipo_map = {1: 'coil', 2: 'discrete_input', 3: 'holding_register', 4: 'input_register'}
    registradores_existentes = [{
        'id': reg.id,
        'name': reg.name, # New field
        'function_code': reg.function_code, # New field
        'tipo': fc_to_tipo_map.get(reg.function_code),
        'endereco': reg.address, # endereco to address
        'data_type': reg.data_type,
        'scale': reg.scale, # New field
        'rw': reg.rw.value, # acesso to rw
        'descricao': reg.descricao,
    } for reg in slave.registers]
    
    return render_template("atualiza_modbus.html", form=form, slave=slave, registradores_existentes=registradores_existentes)

@app.route("/modbus/next_address")
def next_modbus_address():
    device_id = request.args.get('slave_id', type=int)
    register_type = request.args.get('type')

    if not device_id or not register_type:
        return jsonify({'error': 'Parâmetros slave_id e type são obrigatórios'}), 400

    tipo_to_fc_map = {'coil': 1, 'discrete_input': 2, 'holding_register': 3, 'input_register': 4}
    function_code = tipo_to_fc_map.get(register_type)

    if not function_code:
        return jsonify({'error': 'Tipo de registrador inválido'}), 400

    # Mapeamento de function_code para sua faixa inicial (simplified for now)
    base_addresses = {
        1: 1,   # Coils
        2: 10001, # Discrete Inputs
        3: 40001, # Holding Registers
        4: 30001  # Input Registers
    }

    base_address = base_addresses[function_code]
    
    # Encontrar o maior endereço para o tipo e device_id especificados
    max_address = db.session.query(db.func.max(ModbusRegister.address)) \
        .filter(ModbusRegister.device_id == device_id) \
        .filter(ModbusRegister.function_code == function_code) \
        .scalar()

    if max_address is not None:
        next_address = max_address + 1
    else:
        next_address = base_address

    return jsonify({'next_address': next_address})


@app.route("/modbus/exclui/<int:id>", methods=["POST"])
def exclui_modbus(id):
    slave = ModbusDevice.query.get_or_404(id)
    db.session.delete(slave)
    db.session.commit()
    flash("Escravo Modbus excluído com sucesso!", "success")
    return redirect(url_for("lista_modbus"))
