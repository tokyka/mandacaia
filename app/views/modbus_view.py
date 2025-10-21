from app import app, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from ..models.modbus_model import ModbusSlave, ModbusSlaveForm, ModbusRegister, DeleteForm
from ..models.funcao_registrador_model import FuncaoRegistrador # Importar o novo modelo

@app.route("/modbus/status")
def status():
    """Exibe o status mais recente de todos os slaves, lido do banco de dados."""
    slaves = ModbusSlave.query.order_by(ModbusSlave.slave_id).all()
    return render_template("modbus_status.html", slaves=slaves)

@app.route("/modbus/lista")
def lista_modbus():
    slaves = ModbusSlave.query.all()
    form = DeleteForm()
    return render_template("lista_modbus.html", slaves=slaves, form=form)

@app.route("/modbus/novo", methods=["GET", "POST"])
def novo_modbus():
    form = ModbusSlaveForm()
    funcoes = FuncaoRegistrador.query.all()
    funcoes_serializable = [{'id': f.id, 'funcao': f.funcao} for f in funcoes] # Serializar FuncaoRegistrador

    if form.validate_on_submit():
        new_slave = ModbusSlave(
            nome=form.nome.data,
            slave_id=form.slave_id.data
        )
        db.session.add(new_slave)
        db.session.commit() # Commit para obter o ID do novo escravo

        registradores_data = request.form.get('registradores_json')
        if registradores_data:
            import json
            registradores_list = json.loads(registradores_data)
            for reg_data in registradores_list:
                new_register = ModbusRegister(
                    slave_id=new_slave.id,
                    endereco=reg_data['endereco'],
                    tipo=reg_data['tipo'],
                    funcao_id=reg_data['funcao_id'],
                    acesso=reg_data['acesso'], # Adicionado
                    tamanho=reg_data['tamanho'], # Adicionado
                    descricao=reg_data.get('descricao')
                )
                db.session.add(new_register)
            db.session.commit()

        flash("Escravo Modbus criado com sucesso!", "success")
        return redirect(url_for("lista_modbus"))

    return render_template("novo_modbus.html", form=form, funcoes=funcoes_serializable)

@app.route("/modbus/atualiza/<int:id>", methods=["GET", "POST"])
def atualiza_modbus(id):
    slave = ModbusSlave.query.get_or_404(id)
    form = ModbusSlaveForm(obj=slave)
    funcoes = FuncaoRegistrador.query.all()
    funcoes_serializable = [{'id': f.id, 'funcao': f.funcao} for f in funcoes] # Serializar FuncaoRegistrador

    if request.method == 'POST':
        if form.validate_on_submit():
            slave.nome = form.nome.data
            slave.slave_id = form.slave_id.data
            
            ModbusRegister.query.filter_by(slave_id=slave.id).delete()
            
            registradores_data = request.form.get('registradores_json')
            if registradores_data:
                import json
                registradores_list = json.loads(registradores_data)
                for reg_data in registradores_list:
                    # Garantir que funcao_id não seja uma string vazia
                    funcao_id = reg_data.get('funcao_id')
                    if funcao_id:
                        new_register = ModbusRegister(
                            slave_id=slave.id,
                            endereco=reg_data['endereco'],
                            tipo=reg_data['tipo'],
                            funcao_id=int(funcao_id),
                            acesso=reg_data.get('acesso', ''), # Adicionado com default
                            tamanho=reg_data.get('tamanho', ''), # Adicionado com default
                            data_type=reg_data.get('data_type', 'int16'), # Adicionado com default
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
        'endereco': reg.endereco,
        'tipo': reg.tipo,
        'descricao': reg.descricao,
        'funcao_id': reg.funcao_id,
        'acesso': reg.acesso,
        'tamanho': reg.tamanho,
        'data_type': reg.data_type
    } for reg in slave.registradores]
    
    return render_template("atualiza_modbus.html", form=form, slave=slave, funcoes=funcoes_serializable, registradores_existentes=registradores_existentes)

@app.route("/modbus/next_address")
def next_modbus_address():
    slave_id = request.args.get('slave_id', type=int)
    register_type = request.args.get('type')

    if not slave_id or not register_type:
        return jsonify({'error': 'Parâmetros slave_id e type são obrigatórios'}), 400

    # Mapeamento de tipo de registrador para sua faixa inicial
    base_addresses = {
        'coil': 1,
        'discrete_input': 10001,
        'input_register': 30001,
        'holding_register': 40001
    }

    if register_type not in base_addresses:
        return jsonify({'error': 'Tipo de registrador inválido'}), 400

    base_address = base_addresses[register_type]
    
    # Encontrar o maior endereço para o tipo e slave_id especificados
    max_address = db.session.query(db.func.max(ModbusRegister.endereco)) \
        .filter(ModbusRegister.slave_id == slave_id) \
        .filter(ModbusRegister.tipo == register_type) \
        .scalar()

    if max_address is not None:
        next_address = max_address + 1
    else:
        next_address = base_address

    return jsonify({'next_address': next_address})


@app.route("/modbus/exclui/<int:id>", methods=["POST"])
def exclui_modbus(id):
    slave = ModbusSlave.query.get_or_404(id)
    db.session.delete(slave)
    db.session.commit()
    flash("Escravo Modbus excluído com sucesso!", "success")
    return redirect(url_for("lista_modbus"))
