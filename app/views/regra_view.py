from app import app, db
from flask import render_template, redirect, url_for, request, flash, jsonify
from ..models import ModbusRule, ModbusCondition, ModbusAction, ModbusRegister, Reservatorio, Motobomba
from ..models.regra_form import RegraForm

@app.route('/modbus_regras/lista')
def lista_regras():
    regras = ModbusRule.query.all()
    return render_template('regra/lista.html', regras=regras)

@app.route('/modbus_regras/nova', methods=['GET', 'POST'])
def criar_regra():
    form = RegraForm()

    # Preencher choices
    registradores = ModbusRegister.query.all()
    reservatorios = Reservatorio.query.all()
    motobombas = Motobomba.query.all()

    registrador_choices = [(r.id, f"Registrador: {r.name}") for r in registradores]
    reservatorio_choices = [(r.id, f"Reservatório: {r.nome}") for r in reservatorios]
    motobomba_choices = [(m.id, m.nome) for m in motobombas]

    for cond in form.conditions:
        cond.variavel.choices = registrador_choices + reservatorio_choices

    for acao in form.actions:
        acao.motobomba_alvo.choices = motobomba_choices
        acao.registrador_alvo.choices = registrador_choices

    if form.validate_on_submit():
        regra = ModbusRule(
            name=form.name.data,
            description=form.description.data,
            enabled=form.enabled.data
        )
        db.session.add(regra)
        db.session.flush()

        for cond_form in form.conditions.data:
            cond = ModbusCondition(
                rule_id=regra.id,
                name="Condição",
                left_register_id=cond_form['variavel'],
                operator=cond_form['operador'],
                right_value=float(cond_form['valor']),
                right_is_register=False
            )
            db.session.add(cond)

        for acao_form in form.actions.data:
            acao = ModbusAction(
                rule_id=regra.id,
                name=acao_form['tipo_acao'],
                target_register_id=acao_form['registrador_alvo'],
                write_value=float(acao_form['valor']),
                description="Auto"
            )
            db.session.add(acao)

        db.session.commit()
        flash('Regra criada com sucesso!', 'success')
        return redirect(url_for('lista_regras'))

    return render_template('regra/form_nova.html', form=form)

@app.route('/modbus_regras/editar/<int:id>', methods=['GET', 'POST'])
def editar_regra(id):
    regra = ModbusRule.query.get_or_404(id)
    form = RegraForm()

    # Preencher choices
    registradores = ModbusRegister.query.all()
    reservatorios = Reservatorio.query.all()
    motobombas = Motobomba.query.all()

    registrador_choices = [(r.id, f"Registrador: {r.name}") for r in registradores]
    reservatorio_choices = [(r.id, f"Reservatório: {r.nome}") for r in reservatorios]
    motobomba_choices = [(m.id, m.nome) for m in motobombas]

    # Preencher choices para todas as entradas, incluindo as adicionadas dinamicamente
    for cond_entry in form.conditions.entries:
        cond_entry.form.variavel.choices = registrador_choices + reservatorio_choices

    for acao_entry in form.actions.entries:
        acao_entry.form.motobomba_alvo.choices = motobomba_choices
        acao_entry.form.registrador_alvo.choices = registrador_choices

    print("Form submitted?", form.is_submitted())
    print("Form valid?", form.validate_on_submit())
    print("Form errors:", form.errors)

    if request.method == 'GET':
        form.name.data = regra.name
        form.description.data = regra.description
        form.enabled.data = regra.enabled

        form.conditions.entries = []
        for cond in regra.conditions:
            cond_form = {
                'variavel': cond.left_register_id,
                'operador': cond.operator,
                'valor': cond.right_value
            }
            form.conditions.append_entry(cond_form)

        form.actions.entries = []
        for acao in regra.actions:
            acao_form = {
                'tipo_acao': acao.name,
                'motobomba_alvo': None,
                'registrador_alvo': acao.target_register_id,
                'valor': acao.write_value
            }
            form.actions.append_entry(acao_form)

    if form.validate_on_submit():
        regra.name = form.name.data
        regra.description = form.description.data
        regra.enabled = form.enabled.data

        ModbusCondition.query.filter_by(rule_id=regra.id).delete()
        ModbusAction.query.filter_by(rule_id=regra.id).delete()

        for cond_form in form.conditions.data:
            cond = ModbusCondition(
                rule_id=regra.id,
                name="Condição",
                left_register_id=cond_form['variavel'],
                operator=cond_form['operador'],
                right_value=float(cond_form['valor']),
                right_is_register=False
            )
            db.session.add(cond)

        for acao_form in form.actions.data:
            acao = ModbusAction(
                rule_id=regra.id,
                name=acao_form['tipo_acao'],
                target_register_id=acao_form['registrador_alvo'],
                write_value=float(acao_form['valor']),
                description="Auto"
            )
            db.session.add(acao)

        db.session.commit()
        flash('Regra atualizada com sucesso!', 'success')
        return redirect(url_for('listar_regras'))

    return render_template('regra/form_editar.html', form=form)


@app.route('/modbus_regras/remove/<int:id>', methods=['GET', 'POST'])
def excluir_regra(id):
    regra = ModbusRule.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(regra)
        db.session.commit()
        flash('Regra excluída com sucesso!', 'success')
        return redirect(url_for('lista_regras'))
    return render_template('regra/confirma_exclusao.html', regra=regra)

@app.route('/modbus_regras/api/opcoes_variavel')
def opcoes_variavel():
    reservatorios = Reservatorio.query.all()
    print(f"Reservatorios = {reservatorios}")
    resultado = []
    for r in reservatorios:
        resultado.append({
            'id': r.id,
            'label': f"{r.nome} (nível %)",
            'tipo': 'percentual'
        })
        resultado.append({
            'id': r.id,
            'label': f"{r.nome} (volume L)",
            'tipo': 'volume'
        })
    return jsonify(resultado)

@app.route('/modbus_regras/api/opcoes_motobomba')
def opcoes_motobomba():
    motobombas = Motobomba.query.all()
    return jsonify([{'id': m.id, 'nome': m.nome} for m in motobombas])

@app.route('/modbus_regras/api/opcoes_registrador')
def opcoes_registrador():
    registradores = ModbusRegister.query.all()
    return jsonify([{'id': r.id, 'name': r.name} for r in registradores])

