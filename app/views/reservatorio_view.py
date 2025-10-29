from app import app, db
from flask import request, redirect, render_template, url_for, flash
from ..models import reservatorio_model
from ..models.reservatorio_model import ReservatorioForm
from ..models.modbus_device_register_model import ModbusDevice, ModbusRegister # Importar ModbusDevice e ModbusRegister

@app.route('/reservatorios/lista_reservatorios')
def list_tanks():
    reservatorios = reservatorio_model.Reservatorio.query.join(
        reservatorio_model.Tiporeservatorio, isouter=True
    ).options(db.joinedload(reservatorio_model.Reservatorio.modbus_slave)).all()
    return render_template("lista_reservatorios.html", reservatorios=reservatorios)

@app.route('/reservatorios/novo_reservatorio', methods=["GET", "POST"])
def new_tank():
    form = ReservatorioForm()
    # Popula as opções do SelectField dinamicamente
    form.tipo.choices = [(t.id, t.tipo) for t in reservatorio_model.Tiporeservatorio.query.all()]
    slaves = ModbusDevice.query.all()
    form.modbus_slave_id.choices = [(s.id, s.name) for s in slaves]
    form.modbus_slave_id.choices.insert(0, (0, 'Nenhum')) # Adicionar opção para nenhum slave

    # Popula registradores de nível (leitura, Input Register ou Holding Register)
    level_registers = ModbusRegister.query.filter(
        ModbusRegister.rw == 'R',
        ModbusRegister.function_code.in_([3, 4])
    ).all()
    form.level_register_id.choices = [(r.id, f'{r.device.device_name} - {r.name}') for r in level_registers]
    form.level_register_id.choices.insert(0, (0, 'Nenhum'))

    if form.validate_on_submit():
        tipo_obj = reservatorio_model.Tiporeservatorio.query.get(form.tipo.data)
        
        # Tratar o valor '0' como None
        modbus_slave_id = form.modbus_slave_id.data if form.modbus_slave_id.data != 0 else None
        level_register_id = form.level_register_id.data if form.level_register_id.data != 0 else None

        novo_reservatorio = reservatorio_model.Reservatorio(
            nome=form.nome.data,
            descricao=form.descricao.data,
            capacidade_maxima=form.capacidade_maxima.data,
            tipos=tipo_obj,
            modbus_slave_id=modbus_slave_id,
            level_register_id=level_register_id
        )
        db.session.add(novo_reservatorio)
        db.session.commit()
        flash('Reservatório cadastrado com sucesso!', 'success')
        return redirect(url_for('list_tanks'))

    return render_template("novo_reservatorio.html", form=form)

@app.route('/reservatorios/atualiza_reservatorio/<int:id>', methods=["GET", "POST"])
def update_tank(id):
    reservatorio = reservatorio_model.Reservatorio.query.get_or_404(id)
    form = ReservatorioForm(obj=reservatorio)
    
    # Popula as opções do SelectField dinamicamente
    form.tipo.choices = [(t.id, t.tipo) for t in reservatorio_model.Tiporeservatorio.query.all()]
    slaves = ModbusDevice.query.all()
    form.modbus_slave_id.choices = [(s.id, s.device_name) for s in slaves]
    form.modbus_slave_id.choices.insert(0, (0, 'Nenhum'))

    # Popula registradores de nível (leitura, Input Register ou Holding Register)
    level_registers = ModbusRegister.query.filter(
        ModbusRegister.rw == 'R',
        ModbusRegister.function_code.in_([3, 4])
    ).all()
    form.level_register_id.choices = [(r.id, f'{r.device.device_name} - {r.name}') for r in level_registers]
    form.level_register_id.choices.insert(0, (0, 'Nenhum'))

    if form.validate_on_submit():
        form.populate_obj(reservatorio)
        reservatorio.tipos = reservatorio_model.Tiporeservatorio.query.get(form.tipo.data)
        # Tratar o valor '0' como None
        reservatorio.modbus_slave_id = form.modbus_slave_id.data if form.modbus_slave_id.data != 0 else None
        reservatorio.level_register_id = form.level_register_id.data if form.level_register_id.data != 0 else None
        db.session.commit()
        flash('Reservatório atualizado com sucesso!', 'success')
        return redirect(url_for('list_tanks'))

    # Para o GET request, garantir que os valores selecionados sejam os corretos
    if request.method == 'GET':
        form.tipo.data = reservatorio.tipo_id
        form.capacidade_maxima.data = reservatorio.capacidade_maxima
        form.modbus_slave_id.data = reservatorio.modbus_slave_id if reservatorio.modbus_slave_id else 0
        form.level_register_id.data = reservatorio.level_register_id if reservatorio.level_register_id else 0

    return render_template("atualiza_reservatorio.html", form=form, reservatorio=reservatorio)

@app.route('/reservatorios/remove_reservatorio/<int:id>')
def delete_tank(id):
    reservatorio = reservatorio_model.Reservatorio.query.get_or_404(id)
    db.session.delete(reservatorio)
    db.session.commit()
    flash('Reservatório removido com sucesso!', 'success')
    return redirect(url_for('list_tanks'))