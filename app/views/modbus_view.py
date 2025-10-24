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

@app.route("/modbus/novo", methods=["GET", "POST"])
def novo_modbus():
    form = ModbusDeviceForm()

    if form.validate_on_submit():
        novo_slave = ModbusDevice(name=form.nome.data, slave_id=form.slave_id.data)
        db.session.add(new_slave)
        db.session.commit() # Commit para obter o ID do novo escravo

        registradores_data = request.form.get('registradores_json')
        if registradores_data:
            import json
            registradores_list = json.loads(registradores_data)
            for reg_data in registradores_list:
                new_register = ModbusRegister(
                    device_id=new_slave.id, # slave_id to device_id
                    name="Placeholder Name", # New field - Frontend JSON structure needs update
                    function_code=1, # Placeholder - Frontend JSON structure needs update
                    address=reg_data['endereco'], # endereco to address
                    data_type="int", # Placeholder - Frontend JSON structure needs update
                    scale=1.0, # Placeholder - Frontend JSON structure needs update
                    rw="R", # Placeholder - Frontend JSON structure needs update
                    descricao=reg_data.get('descricao')
                )
                db.session.add(new_register)
            db.session.commit()

        flash("Escravo Modbus criado com sucesso!", "success")
        return redirect(url_for("lista_modbus"))

    return render_template("novo_modbus.html", form=form)

@app.route("/modbus/atualiza/<int:id>", methods=["GET", "POST"])
def atualiza_modbus(id):
    slave = ModbusDevice.query.get_or_404(id)
    form = ModbusDeviceForm(obj=slave)
    if form.validate_on_submit():
        slave.name = form.nome.data
        slave.slave_id = form.slave_id.data
        
        ModbusRegister.query.filter_by(device_id=slave.id).delete() # slave_id to device_id
        
        registradores_data = request.form.get('registradores_json')
        if registradores_data:
            import json
            registradores_list = json.loads(registradores_data)
            for reg_data in registradores_list:
                # Garantir que funcao_id não seja uma string vazia
                # funcao_id = reg_data.get('funcao_id') # Removed
                # if funcao_id: # Removed
                    new_register = ModbusRegister(
                        device_id=slave.id, # slave_id to device_id
                        name="Placeholder Name", # New field - Frontend JSON structure needs update
                        function_code=1, # Placeholder - Frontend JSON structure needs update
                        address=reg_data['endereco'], # endereco to address
                        data_type="int", # Placeholder - Frontend JSON structure needs update
                        scale=1.0, # Placeholder - Frontend JSON structure needs update
                        rw="R", # Placeholder - Frontend JSON structure needs update
                        descricao=reg_data.get('descricao')
                    )
                    db.session.add(new_register)
        
        db.session.commit()
        flash("Escravo Modbus atualizado com sucesso!", "success")
        return redirect(url_for("lista_modbus"))
    else:
        flash("Erro ao atualizar Escravo Modbus! Verifique os dados.", "danger")

    # Para o método GET, carregar os registradores existentes
    registradores_existentes = [{
        'id': reg.id,
        'name': reg.name, # New field
        'function_code': reg.function_code, # New field
        'address': reg.address, # endereco to address
        'data_type': reg.data_type,
        'scale': reg.scale, # New field
        'rw': reg.rw, # acesso to rw
        'descricao': reg.descricao,
    } for reg in slave.registradores]
    
    return render_template("atualiza_modbus.html", form=form, slave=slave, registradores_existentes=registradores_existentes)

@app.route("/modbus/next_address")
def next_modbus_address():
    device_id = request.args.get('device_id', type=int) # slave_id to device_id
    function_code = request.args.get('function_code', type=int) # register_type to function_code

    if not device_id or not function_code:
        return jsonify({'error': 'Parâmetros device_id e function_code são obrigatórios'}), 400

    # Mapeamento de function_code para sua faixa inicial (simplified for now)
    base_addresses = {
        1: 1,   # Coils
        2: 10001, # Discrete Inputs
        3: 40001, # Holding Registers
        4: 30001  # Input Registers
    }

    if function_code not in base_addresses:
        return jsonify({'error': 'Código de função inválido'}), 400

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
