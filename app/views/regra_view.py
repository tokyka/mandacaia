from flask import render_template, redirect, url_for, flash, request
from app import app, db
from ..models.modbus_rule_model import ModbusRule
from ..models.modbus_condition_model import ModbusCondition
from ..models.modbus_action_model import ModbusAction
from app.models.regra_form import RegraForm, AcaoForm, CondicaoForm
from app.models.motobomba_model import Motobomba
from app.models.modbus_device_register_model import ModbusDevice, ModbusRegister, DeviceType
from app.models import reservatorio_model

def get_variavel_str_from_register_id(register_id):
    app.logger.info(f"[get_variavel_str] Trying to find variable string for register_id: {register_id}")
    register = ModbusRegister.query.get(register_id)
    if not register:
        app.logger.warning(f"[get_variavel_str] Register with id {register_id} not found.")
        return None

    device = register.device
    if not device:
        app.logger.warning(f"[get_variavel_str] Register {register_id} has no associated device.")
        return None
    
    app.logger.info(f"[get_variavel_str] Found device '{device.device_name}' (type: {device.type}) for register '{register.name}'.")

    if device.type == DeviceType.RESERVATORIO:
        reservatorio = reservatorio_model.Reservatorio.query.filter_by(modbus_slave_id=device.id).first()
        if not reservatorio:
            app.logger.warning(f"[get_variavel_str] No Reservatorio found with modbus_slave_id: {device.id}")
            return None
        if not reservatorio.tipos:
            app.logger.warning(f"[get_variavel_str] Reservatorio {reservatorio.id} has no 'tipos'.")
            return None
        
        tipo_str = reservatorio.tipos.tipo.split(" ")[-1]
        app.logger.info(f"[get_variavel_str] Found reservatorio '{reservatorio.nome}' with tipo '{tipo_str}'.")
        if "Nível" in register.name:
            result = f'Nivel_Reservatorio_{tipo_str}'
            app.logger.info(f"[get_variavel_str] Match! Returning '{result}'.")
            return result
        elif "Volume" in register.name:
            result = f'Volume_Reservatorio_{tipo_str}'
            app.logger.info(f"[get_variavel_str] Match! Returning '{result}'.")
            return result

    elif device.type == DeviceType.BOMBA:
        app.logger.info(f"[get_variavel_str] Device is a bomba. Checking register name.")
        if "Tensão" in register.name:
            app.logger.info("[get_variavel_str] Match! Returning 'Tensao_Motobomba'.")
            return 'Tensao_Motobomba'
        elif "Corrente" in register.name:
            app.logger.info("[get_variavel_str] Match! Returning 'Corrente_Motobomba'.")
            return 'Corrente_Motobomba'
        elif "Potência" in register.name:
            app.logger.info("[get_variavel_str] Match! Returning 'Potencia_Motobomba'.")
            return 'Potencia_Motobomba'
        elif "Consumo" in register.name:
            app.logger.info("[get_variavel_str] Match! Returning 'Consumo_Motobomba'.")
            return 'Consumo_Motobomba'
    
    app.logger.warning(f"[get_variavel_str] No match found for register '{register.name}'. Returning None.")
    return None

def get_motobomba_id_from_target_register_id(register_id):
    register = ModbusRegister.query.get(register_id)
    if register and register.device.type == 'bomba':
        motobomba = Motobomba.query.filter_by(actuator_register_id=register_id).first()
        if motobomba:
            return motobomba.id
    return None

def _get_dynamic_choices():
    condition_choices = [('', 'Selecione uma variável')]
    
    # Choices for Conditions (Reservatorios)
    reservatorios = reservatorio_model.Reservatorio.query.all()
    for res in reservatorios:
        condition_choices.append((f'Nivel_Reservatorio_{res.tipos.tipo.split(" ")[-1]}', f'Nivel Reservatório {res.nome} (%)'))
        condition_choices.append((f'Volume_Reservatorio_{res.tipos.tipo.split(" ")[-1]}', f'Volume Reservatório {res.nome} (L)'))

    # Choices for Conditions (Motobombas)
    # Adiciona opções genéricas para motobombas, já que os registradores são buscados dinamicamente
    condition_choices.extend([
        ('Tensao_Motobomba', 'Tensão da Motobomba (V)'),
        ('Corrente_Motobomba', 'Corrente da Motobomba (A)'),
        ('Potencia_Motobomba', 'Potência da Motobomba (W)'),
        ('Consumo_Motobomba', 'Consumo da Motobomba (kWh)')
    ])

    return condition_choices



@app.route('/regras_modbus/lista')
def list_regras():
    regras = ModbusRule.query.all()
    return render_template('lista_regras.html', regras=regras, title='Lista de Regras')


@app.route('/regras_modbus/criar', methods=['GET', 'POST'])
def criar_regra():
    form = RegraForm()
    
    # Popula choices dinamicamente
    condition_choices = _get_dynamic_choices()
    
    # Fetch writable registers for action target choices
    writable_registers = ModbusRegister.query.join(ModbusDevice).filter(
        ModbusRegister.rw == 'W'
    ).order_by(ModbusDevice.device_name, ModbusRegister.name).all()
    register_choices = [(r.id, f"{r.device.device_name} - {r.name} (End: {r.address})") for r in writable_registers]
    register_choices.insert(0, ('', 'Selecione um Registrador Alvo')) # Add a default empty choice

    # Fetch motobombas for action target choices
    motobombas = Motobomba.query.order_by(Motobomba.nome).all()
    motobomba_choices = [(m.id, m.nome) for m in motobombas]
    motobomba_choices.insert(0, ('', 'Selecione uma Motobomba'))

    for cond_form in form.conditions:
        cond_form.variavel.choices = condition_choices
    
    for acao_form in form.actions:
        acao_form.registrador_alvo.choices = register_choices
        acao_form.motobomba_alvo.choices = motobomba_choices

    if form.validate_on_submit():
        app.logger.info(f"Form errors: {form.errors}")
        errors = []
        try:
            nova_regra = ModbusRule(
                name=form.name.data,
                description=form.description.data,
                enabled=form.enabled.data
            )

            for condicao_form in form.conditions:
                variavel_str = condicao_form.variavel.data
                partes = variavel_str.split('_')
                funcao_form = partes[0]
                conceito_dispositivo = '_'.join(partes[1:])

                target_register = None

                if "Reservatorio" in conceito_dispositivo:
                    tipo_str = "Acumulação" if "Acumulacao" in conceito_dispositivo else "Distribuição"
                    target_register = ModbusRegister.query.join(ModbusRegister.device).join(ModbusDevice.reservatorios).join(reservatorio_model.Reservatorio.tipos).filter(
                        ModbusRegister.name.like(f'%{funcao_form}%'),
                        reservatorio_model.Tiporeservatorio.tipo.like(f'%{tipo_str}%')
                    ).first()
                elif "Motobomba" in conceito_dispositivo:
                    target_register = ModbusRegister.query.join(ModbusDevice).filter(
                        ModbusRegister.name.like(f'%{funcao_form}%'),
                        ModbusDevice.type == 'bomba'
                    ).first()

                if not target_register:
                    errors.append(f"Não foi possível encontrar um registrador correspondente para '{variavel_str}'.")
                    continue

                nova_condicao = ModbusCondition(
                    name=f"{variavel_str} {condicao_form.operador.data} {condicao_form.valor.data}",
                    left_register_id=target_register.id,
                    operator=condicao_form.operador.data,
                    right_value=float(condicao_form.valor.data),
                    right_is_register=False,
                    description=f"Condição para {variavel_str}"
                )
                nova_regra.conditions.append(nova_condicao)

            for acao_form in form.actions:
                app.logger.info(f"Processing acao_form data: tipo_acao={acao_form.tipo_acao.data}, registrador_alvo={acao_form.registrador_alvo.data}, valor={acao_form.valor.data}")
                tipo_acao = acao_form.tipo_acao.data
                write_value = acao_form.valor.data
                target_register_id = None

                if tipo_acao in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                    motobomba_id = acao_form.motobomba_alvo.data
                    if not motobomba_id:
                        errors.append("Uma motobomba deve ser selecionada para esta ação.")
                        continue
                    motobomba = Motobomba.query.get(motobomba_id)
                    if motobomba and motobomba.modbus_slave_id:
                        acionamento_register = ModbusRegister.query.filter(
                            ModbusRegister.device_id == motobomba.modbus_slave_id,
                            ModbusRegister.rw == 'W',
                            ModbusRegister.function_code.in_([1, 5])
                        ).first()
                        if acionamento_register:
                            target_register_id = acionamento_register.id
                            write_value = 1.0 if tipo_acao == 'Ligar_Motobomba' else 0.0
                        else:
                            errors.append(f"Registrador de acionamento para a motobomba '{motobomba.nome}' não encontrado.")
                    else:
                        errors.append(f"Motobomba com ID {motobomba_id} não encontrada ou não associada a um dispositivo modbus.")
                elif tipo_acao == 'Escrever_em_Registrador':
                    target_register_id = acao_form.registrador_alvo.data
                    if not target_register_id:
                        errors.append("Um registrador alvo deve ser selecionado para esta ação.")
                    if acao_form.valor.data is None or acao_form.valor.data == '':
                        errors.append("Um valor é necessário para a ação de escrita.")

                if target_register_id:
                    nova_acao = ModbusAction(
                        name=tipo_acao,
                        target_register_id=int(target_register_id),
                        write_value=float(write_value) if write_value else None,
                        description=f"Ação {tipo_acao}"
                    )
                    nova_regra.actions.append(nova_acao)

            if not nova_regra.conditions or not nova_regra.actions:
                errors.append('A regra precisa de pelo menos uma condição e uma ação válidas.')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                app.logger.error(f"Errors found while creating rule: {errors}")
                # Re-popula os choices em caso de erro
                for cond_form in form.conditions:
                    cond_form.variavel.choices = condition_choices
                for acao_form in form.actions:
                    acao_form.registrador_alvo.choices = register_choices
                return render_template('editor_regras.html', form=form, title='Criar Nova Regra', action_url=url_for('criar_regra'), condition_choices=condition_choices, register_choices=register_choices, motobomba_choices=motobomba_choices)
            else:
                db.session.add(nova_regra)
                db.session.commit()
                flash('Nova regra criada com sucesso!', 'success')
                return redirect(url_for('list_regras'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar a regra: {e}', 'danger')

    return render_template('editor_regras.html', form=form, title='Criar Nova Regra', action_url=url_for('criar_regra'), condition_choices=condition_choices, register_choices=register_choices, motobomba_choices=motobomba_choices)


@app.route('/regras_modbus/editar/<int:regra_id>', methods=['GET', 'POST'])
def editar_regra(regra_id):
    regra = ModbusRule.query.get_or_404(regra_id)
    form = RegraForm(request.form if request.method == 'POST' else None)

    # --- População de Choices (necessário para GET e POST) ---
    condition_choices = _get_dynamic_choices()
    writable_registers = ModbusRegister.query.join(ModbusDevice).filter(ModbusRegister.rw == 'W').order_by(ModbusDevice.device_name, ModbusRegister.name).all()
    register_choices = [(r.id, f"{r.device.device_name} - {r.name} (End: {r.address})") for r in writable_registers]
    register_choices.insert(0, ('', 'Selecione um Registrador Alvo'))
    motobombas = Motobomba.query.order_by(Motobomba.nome).all()
    motobomba_choices = [(m.id, m.nome) for m in motobombas]
    motobomba_choices.insert(0, ('', 'Selecione uma Motobomba'))

    # Atribui choices aos subformulários que foram criados a partir dos dados do POST
    for cond_form in form.conditions:
        cond_form.variavel.choices = condition_choices
    for acao_form in form.actions:
        acao_form.registrador_alvo.choices = register_choices
        acao_form.motobomba_alvo.choices = motobomba_choices
    # --- Fim da População de Choices ---

    if form.validate_on_submit():
        # Lógica de POST (salvar os dados)
        try:
            regra.name = form.name.data
            regra.description = form.description.data
            regra.enabled = form.enabled.data

            regra.conditions = []
            regra.actions = []
            db.session.flush()

            for condicao_form in form.conditions:
                # ... (lógica de salvar condição, que já estava correta)
                pass # A lógica completa de processamento de condição vai aqui

            for acao_form in form.actions:
                # ... (lógica de salvar ação, que já estava correta)
                pass # A lógica completa de processamento de ação vai aqui
            
            # Recriando a lógica de salvar para garantir consistência
            for condicao_form in form.conditions:
                variavel_str = condicao_form.variavel.data
                partes = variavel_str.split('_')
                funcao_form = partes[0]
                conceito_dispositivo = '_'.join(partes[1:])
                target_register = None
                if "Reservatorio" in conceito_dispositivo:
                    tipo_str = "Acumulação" if "Acumulacao" in conceito_dispositivo else "Distribuição"
                    target_register = ModbusRegister.query.join(ModbusRegister.device).join(ModbusDevice.reservatorios).join(reservatorio_model.Reservatorio.tipos).filter(
                        ModbusRegister.name.like(f'%{funcao_form}%'),
                        reservatorio_model.Tiporeservatorio.tipo.like(f'%{tipo_str}%')
                    ).first()
                elif "Motobomba" in conceito_dispositivo:
                    target_register = ModbusRegister.query.join(ModbusDevice).filter(ModbusRegister.name.like(f'%{funcao_form}%'), ModbusDevice.type == DeviceType.BOMBA).first()
                if not target_register:
                    flash(f"Não foi possível encontrar um registrador correspondente para '{variavel_str}'.", 'danger')
                    continue
                nova_condicao = ModbusCondition(name=f"{variavel_str} {condicao_form.operador.data} {condicao_form.valor.data}", left_register_id=target_register.id, operator=condicao_form.operador.data, right_value=float(condicao_form.valor.data), right_is_register=False, description=f"Condição para {variavel_str}")
                regra.conditions.append(nova_condicao)

            for acao_form in form.actions:
                tipo_acao = acao_form.tipo_acao.data
                write_value = acao_form.valor.data
                target_register_id = None
                if tipo_acao in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                    motobomba_id = acao_form.motobomba_alvo.data
                    if not motobomba_id:
                        flash("Uma motobomba deve ser selecionada para esta ação.", 'danger')
                        continue
                    motobomba = Motobomba.query.get(motobomba_id)
                    if motobomba and motobomba.modbus_slave_id:
                        acionamento_register = ModbusRegister.query.filter(ModbusRegister.device_id == motobomba.modbus_slave_id, ModbusRegister.rw == 'W', ModbusRegister.function_code.in_([1, 5])).first()
                        if acionamento_register:
                            target_register_id = acionamento_register.id
                            write_value = 1.0 if tipo_acao == 'Ligar_Motobomba' else 0.0
                        else:
                            flash(f"Registrador de acionamento para a motobomba '{motobomba.nome}' não encontrado.", 'danger')
                    else:
                        flash(f"Motobomba com ID {motobomba_id} não encontrada ou não associada a um dispositivo modbus.", 'danger')
                elif tipo_acao == 'Escrever_em_Registrador':
                    target_register_id = acao_form.registrador_alvo.data
                    if not target_register_id:
                        flash("Um registrador alvo deve ser selecionado para esta ação.", 'danger')
                    if acao_form.valor.data is None or acao_form.valor.data == '':
                        flash("Um valor é necessário para a ação de escrita.", 'danger')
                if target_register_id:
                    nova_acao = ModbusAction(name=tipo_acao, target_register_id=int(target_register_id), write_value=float(write_value) if write_value else None, description=f"Ação {tipo_acao}")
                    regra.actions.append(nova_acao)

            db.session.commit()
            flash('Regra atualizada com sucesso!', 'success')
            return redirect(url_for('list_regras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a regra: {e}', 'danger')

    # --- Lógica de GET (popular o formulário para exibição) ---
    if request.method == 'GET':
        # Popula campos do formulário principal
        form.name.data = regra.name
        form.description.data = regra.description
        form.enabled.data = regra.enabled
        
        # Limpa e popula as condições
        while len(form.conditions) > 0:
            form.conditions.pop_entry()
        for condicao_obj in regra.conditions:
            condicao_data = {
                'variavel': get_variavel_str_from_register_id(condicao_obj.left_register_id),
                'operador': condicao_obj.operator.value,
                'valor': str(condicao_obj.right_value)
            }
            condicao_form = form.conditions.append_entry(data=condicao_data)
            condicao_form.variavel.choices = condition_choices

        # Limpa e popula as ações
        while len(form.actions) > 0:
            form.actions.pop_entry()
        for acao_obj in regra.actions:
            acao_data = {
                'tipo_acao': acao_obj.name,
                'valor': str(acao_obj.write_value) if acao_obj.write_value is not None else ''
            }
            if acao_obj.name in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                acao_data['motobomba_alvo'] = get_motobomba_id_from_target_register_id(acao_obj.target_register_id)
            elif acao_obj.name == 'Escrever_em_Registrador':
                acao_data['registrador_alvo'] = acao_obj.target_register_id
            
            acao_form = form.actions.append_entry(data=acao_data)
            acao_form.registrador_alvo.choices = register_choices
            acao_form.motobomba_alvo.choices = motobomba_choices

    return render_template('editor_regras.html', form=form, title='Editar Regra', regra=regra, action_url=url_for('editar_regra', regra_id=regra.id), condition_choices=condition_choices, register_choices=register_choices, motobomba_choices=motobomba_choices)


@app.route('/regras_modbus/remover/<int:regra_id>', methods=['POST'])
def remove_regra(regra_id):
    regra = ModbusRule.query.get_or_404(regra_id)
    try:
        db.session.delete(regra)
        db.session.commit()
        flash('Regra removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover a regra: {e}', 'danger')
    return redirect(url_for('list_regras'))


