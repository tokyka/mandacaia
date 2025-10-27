from flask import render_template, redirect, url_for, flash, request
from app import app, db
from ..models.modbus_rule_model import ModbusRule
from ..models.modbus_condition_model import ModbusCondition
from ..models.modbus_action_model import ModbusAction
from app.models.regra_form import RegraForm, AcaoForm, CondicaoForm
from app.models.motobomba_model import Motobomba
from app.models.modbus_device_register_model import ModbusDevice, ModbusRegister
from app.models import reservatorio_model


@app.route('/regras_modbus/lista')
def list_regras():
    regras = ModbusRule.query.all()
    return render_template('lista_regras.html', regras=regras, title='Lista de Regras')


@app.route('/regras_modbus/criar', methods=['GET', 'POST'])
def criar_regra():
    motobombas = Motobomba.query.all()
    motobomba_choices = [(mb.id, mb.nome) for mb in motobombas]
    AcaoForm.registrador_alvo.kwargs = {'choices': motobomba_choices}
    form = RegraForm()

    if form.validate_on_submit():
        # Cleanup class modification
        if 'choices' in AcaoForm.registrador_alvo.kwargs:
            del AcaoForm.registrador_alvo.kwargs['choices']
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
                    
                    target_register = ModbusRegister.query.join(ModbusDevice).join(
                        reservatorio_model.Reservatorio, 
                        reservatorio_model.Reservatorio.modbus_slave_id == ModbusDevice.id
                    ).join(
                        reservatorio_model.Tiporeservatorio, 
                        reservatorio_model.Reservatorio.tipo_id == reservatorio_model.Tiporeservatorio.id
                    ).filter(
                        ModbusRegister.name.like(f'{funcao_form}%'),
                        reservatorio_model.Tiporeservatorio.tipo.like(f'%{tipo_str}%')
                    ).first()

                elif "Motobomba" in conceito_dispositivo:
                    target_register = ModbusRegister.query.join(ModbusDevice).filter(
                        ModbusRegister.name.like(f'{funcao_form}%'),
                        ModbusDevice.type == 'bomba'
                    ).first()

                if not target_register:
                    flash(f"Não foi possível encontrar um registrador correspondente para '{variavel_str}'.", 'danger')
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
                tipo_acao = acao_form.tipo_acao.data
                write_value = acao_form.valor.data
                target_register_id = None

                if tipo_acao in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                    motobomba_id = acao_form.registrador_alvo.data
                    motobomba = Motobomba.query.get(motobomba_id)
                    if motobomba and motobomba.modbus_slave_id:
                        acionamento_register = ModbusRegister.query.filter(
                            ModbusRegister.device_id == motobomba.modbus_slave_id,
                            ModbusRegister.name.like('Acionamento%')
                        ).first()
                        if acionamento_register:
                            target_register_id = acionamento_register.id
                            write_value = 1.0 if tipo_acao == 'Ligar_Motobomba' else 0.0
                        else:
                            flash(f"Registrador de acionamento para a motobomba '{motobomba.nome}' não encontrado.", 'danger')
                    else:
                        flash(f"Motobomba com ID {motobomba_id} não encontrada ou não associada a um dispositivo modbus.", 'danger')

                elif acao_form.registrador_alvo_texto.data:
                    register_name = acao_form.registrador_alvo_texto.data
                    register = ModbusRegister.query.filter_by(name=register_name).first()
                    if register:
                        target_register_id = register.id
                    else:
                        flash(f"Registrador alvo '{register_name}' não encontrado.", 'danger')

                if target_register_id:
                    nova_acao = ModbusAction(
                        name=tipo_acao,
                        target_register_id=target_register_id,
                        write_value=float(write_value) if write_value else None,
                        description=f"Ação {tipo_acao}"
                    )
                    nova_regra.actions.append(nova_acao)

            if not nova_regra.conditions or not nova_regra.actions:
                flash('A regra precisa de pelo menos uma condição e uma ação válidas.', 'warning')
            else:
                db.session.add(nova_regra)
                db.session.commit()
                flash('Nova regra criada com sucesso!', 'success')
                return redirect(url_for('list_regras'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar a regra: {e}', 'danger')

    # Cleanup class modification
    if 'choices' in AcaoForm.registrador_alvo.kwargs:
        del AcaoForm.registrador_alvo.kwargs['choices']
    return render_template('editor_regras.html', form=form, title='Criar Nova Regra', action_url=url_for('criar_regra'))


@app.route('/regras_modbus/editar/<int:regra_id>', methods=['GET', 'POST'])
def editar_regra(regra_id):
    regra = ModbusRule.query.get_or_404(regra_id)
    form = RegraForm(obj=regra)
    motobombas = Motobomba.query.all()
    motobomba_choices = [(mb.id, mb.nome) for mb in motobombas]

    # Set choices for each existing acao_form in the FieldList
    for acao_form in form.actions:
        acao_form.registrador_alvo.choices = motobomba_choices

    if form.validate_on_submit():
        try:
            regra.name = form.name.data
            regra.description = form.description.data
            regra.enabled = form.enabled.data

            # Clear existing collections before adding new ones
            regra.conditions = []
            regra.actions = []
            db.session.flush() # Apply the clear operation

            for condicao_form in form.conditions:
                variavel_str = condicao_form.variavel.data
                partes = variavel_str.split('_')
                funcao_form = partes[0]
                conceito_dispositivo = '_'.join(partes[1:])

                target_register = None

                if "Reservatorio" in conceito_dispositivo:
                    tipo_str = "Acumulação" if "Acumulacao" in conceito_dispositivo else "Distribuição"
                    target_register = ModbusRegister.query.join(ModbusDevice).join(
                        reservatorio_model.Reservatorio, 
                        reservatorio_model.Reservatorio.modbus_slave_id == ModbusDevice.id
                    ).join(
                        reservatorio_model.Tiporeservatorio, 
                        reservatorio_model.Reservatorio.tipo_id == reservatorio_model.Tiporeservatorio.id
                    ).filter(
                        ModbusRegister.name.like(f'{funcao_form}%'),
                        reservatorio_model.Tiporeservatorio.tipo.like(f'%{tipo_str}%')
                    ).first()

                elif "Motobomba" in conceito_dispositivo:
                    target_register = ModbusRegister.query.join(ModbusDevice).filter(
                        ModbusRegister.name.like(f'{funcao_form}%'),
                        ModbusDevice.type == 'bomba'
                    ).first()

                if not target_register:
                    flash(f"Não foi possível encontrar um registrador correspondente para '{variavel_str}'.", 'danger')
                    continue

                nova_condicao = ModbusCondition(
                    name=f"{variavel_str} {condicao_form.operador.data} {condicao_form.valor.data}",
                    left_register_id=target_register.id,
                    operator=condicao_form.operador.data,
                    right_value=float(condicao_form.valor.data),
                    right_is_register=False,
                    description=f"Condição para {variavel_str}"
                )
                regra.conditions.append(nova_condicao)

            for acao_form in form.actions:
                tipo_acao = acao_form.tipo_acao.data
                write_value = acao_form.valor.data
                target_register_id = None

                if tipo_acao in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                    motobomba_id = acao_form.registrador_alvo.data
                    motobomba = Motobomba.query.get(motobomba_id)
                    if motobomba and motobomba.modbus_slave_id:
                        acionamento_register = ModbusRegister.query.filter(
                            ModbusRegister.device_id == motobomba.modbus_slave_id,
                            ModbusRegister.name.like('Acionamento%')
                        ).first()
                        if acionamento_register:
                            target_register_id = acionamento_register.id
                            write_value = 1.0 if tipo_acao == 'Ligar_Motobomba' else 0.0
                        else:
                            flash(f"Registrador de acionamento para a motobomba '{motobomba.nome}' não encontrado.", 'danger')
                    else:
                        flash(f"Motobomba com ID {motobomba_id} não encontrada ou não associada a um dispositivo modbus.", 'danger')

                elif acao_form.registrador_alvo_texto.data:
                    register_name = acao_form.registrador_alvo_texto.data
                    register = ModbusRegister.query.filter_by(name=register_name).first()
                    if register:
                        target_register_id = register.id
                    else:
                        flash(f"Registrador alvo '{register_name}' não encontrado.", 'danger')

                if target_register_id:
                    nova_acao = ModbusAction(
                        name=tipo_acao,
                        target_register_id=target_register_id,
                        write_value=float(write_value) if write_value else None,
                        description=f"Ação {tipo_acao}"
                    )
                    regra.actions.append(nova_acao)

            db.session.commit()
            flash('Regra atualizada com sucesso!', 'success')
            return redirect(url_for('list_regras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a regra: {e}', 'danger')
    else:
        # For GET request or validation failure, ensure choices are set
        for acao_form in form.actions:
            acao_form.registrador_alvo.choices = motobomba_choices

        # Manually populate conditions for GET request
        form.conditions.entries = []
        for condicao_obj in regra.conditions:
            condicao_form = CondicaoForm()
            condicao_form.operador.data = condicao_obj.operator
            condicao_form.valor.data = str(condicao_obj.right_value)
            condicao_form.variavel.data = get_variavel_str_from_register_id(condicao_obj.left_register_id)
            form.conditions.append_entry(condicao_form)

        # Manually populate actions for GET request
        form.actions.entries = []
        for acao_obj in regra.actions:
            acao_form = AcaoForm()
            acao_form.tipo_acao.data = acao_obj.name
            acao_form.valor.data = str(acao_obj.write_value) if acao_obj.write_value is not None else ''
            
            # Reverse lookup for registrador_alvo
            if acao_obj.name in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                acao_form.registrador_alvo.data = get_motobomba_id_from_target_register_id(acao_obj.target_register_id)
            else:
                # For other actions, assume registrador_alvo_texto is used
                # This is a simplification, as the model only stores target_register_id
                # If the original form used registrador_alvo_texto, we need to retrieve the register name
                register = ModbusRegister.query.get(acao_obj.target_register_id)
                if register:
                    acao_form.registrador_alvo_texto.data = register.name

            form.actions.append_entry(acao_form)

    return render_template('editor_regras.html', form=form, title='Editar Regra', regra=regra, action_url=url_for('editar_regra', regra_id=regra.id))


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


