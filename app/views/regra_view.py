from flask import render_template, redirect, url_for, flash, request
from app import app, db
from ..models.modbus_rule_model import ModbusRule
from ..models.modbus_condition_model import ModbusCondition
from ..models.modbus_action_model import ModbusAction
from app.models.regra_form import RegraForm, AcaoForm
from app.models.motobomba_model import Motobomba

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
        del AcaoForm.registrador_alvo.kwargs['choices']
        try:
            nova_regra = ModbusRule(
                name=form.nome.data,
                description=form.descricao.data,
                enabled=form.habilitada.data
            )

            for condicao_form in form.condicoes:
                nova_condicao = Condicao(
                    variavel=condicao_form.variavel.data,
                    operador=condicao_form.operador.data,
                    valor=condicao_form.valor.data
                )
                nova_regra.condicoes.append(nova_condicao)

            for acao_form in form.acoes:
                registrador_alvo = acao_form.registrador_alvo.data if acao_form.tipo_acao.data in ['Ligar_Motobomba', 'Desligar_Motobomba'] else acao_form.registrador_alvo_texto.data
                nova_acao = Acao(
                    tipo_acao=acao_form.tipo_acao.data,
                    registrador_alvo=registrador_alvo,
                    valor=acao_form.valor.data
                )
                nova_regra.acoes.append(nova_acao)

            db.session.add(nova_regra)
            db.session.commit()
            flash('Nova regra criada com sucesso!', 'success')
            return redirect(url_for('listar_regras'))
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
    for acao_form in form.acoes:
        acao_form.registrador_alvo.choices = motobomba_choices

    if form.validate_on_submit():
        try:
            regra.name = form.nome.data
            regra.description = form.descricao.data
            regra.enabled = form.habilitada.data

            # Clear existing collections before adding new ones
            regra.condicoes = []
            regra.acoes = []
            db.session.flush() # Apply the clear operation

            for condicao_data in form.condicoes.data:
                nova_condicao = ModbusCondition(
                    name="Placeholder Name",
                    left_register_id=1,
                    operator="==",
                    right_value=0.0,
                    right_is_register=False,
                    description="Placeholder Description"
                )
                regra.condicoes.append(nova_condicao)

            for acao_form in form.acoes.data:
                nova_acao = ModbusAction(
                    name="Placeholder Name",
                    target_register_id=1,
                    write_value=0.0,
                    description="Placeholder Description"
                )
                regra.acoes.append(nova_acao)

            db.session.commit()
            flash('Regra atualizada com sucesso!', 'success')
            return redirect(url_for('list_regras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a regra: {e}', 'danger')
    else:
        # For GET request or validation failure, ensure choices are set
        for acao_form in form.acoes:
            acao_form.registrador_alvo.choices = motobomba_choices

    return render_template('editor_regras.html', form=form, title='Editar Regra', regra=regra, action_url=url_for('editar_regra', regra_id=regra.id))

@app.route('/regras_modbus/remover/<int:regra_id>', methods=['POST'])
def remove_regra(regra_id): # Changed 'id' to 'regra_id'
    regra = ModbusRule.query.get_or_404(regra_id) # Changed 'id' to 'regra_id'
    try: # Added try block
        db.session.delete(regra)
        db.session.commit()
        flash('Regra removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover a regra: {e}', 'danger')
    return redirect(url_for('list_regras')) # Changed 'listar_regras' to 'list_regras'
