from app import app, db
from flask import request, redirect, render_template, url_for, flash
from ..models import reservatorio_model
from ..models.modbus_device_register_model import ModbusDevice
from ..models.motobomba_model import Motobomba, MotobombaForm, GrupoBombeamento, FuncaoBomba, StatusRotacao, Tubospvc, TensaoTrabalho

def _populate_form_choices(form):
    """Helper para popular as escolhas dos SelectFields do formulário."""
    # Popula tubos
    tubos = Tubospvc.query.all()
    form.succao.choices = [(str(t.id), t.pol) for t in tubos]
    form.recalque.choices = [(str(t.id), t.pol) for t in tubos]

    # Popula slaves
    slaves = ModbusDevice.query.all()
    form.modbus_slave_id.choices = [(s.id, s.name) for s in slaves]
    form.modbus_slave_id.choices.insert(0, (0, 'Nenhum'))

    # Popula reservatórios
    reservatorios = reservatorio_model.Reservatorio.query.all()
    reservatorio_choices = [(r.id, r.nome) for r in reservatorios]
    form.reservatorio_fonte_id.choices = reservatorio_choices[:]
    form.reservatorio_destino_id.choices = reservatorio_choices[:]
    form.reservatorio_fonte_id.choices.insert(0, (0, 'Nenhum'))
    form.reservatorio_destino_id.choices.insert(0, (0, 'Nenhum'))

    # Popula Grupos de Bombeamento
    grupos = GrupoBombeamento.query.all()
    form.grupo_bombeamento_id.choices = [(g.id, g.nome) for g in grupos]
    form.grupo_bombeamento_id.choices.insert(0, (0, 'Nenhum'))

@app.route('/motobombas/lista_motobombas')
def list_pumps():
    motobombas = Motobomba.query.options(
        db.joinedload(Motobomba.modbus_slave),
        db.joinedload(Motobomba.reservatorio_fonte),
        db.joinedload(Motobomba.reservatorio_destino),
        db.joinedload(Motobomba.grupo_bombeamento)  # Eager load
    ).all()
    return render_template("lista_motobombas.html", motobombas=motobombas)

@app.route('/motobombas/nova_motobomba', methods=["GET", "POST"])
def new_pump():
    form = MotobombaForm()
    _populate_form_choices(form)

    if form.validate_on_submit():
        succao_obj = Tubospvc.query.get(int(form.succao.data))
        recalque_obj = Tubospvc.query.get(int(form.recalque.data))

        # Tratar valores '0' como None
        modbus_slave_id = form.modbus_slave_id.data if form.modbus_slave_id.data != 0 else None
        reservatorio_fonte_id = form.reservatorio_fonte_id.data if form.reservatorio_fonte_id.data != 0 else None
        reservatorio_destino_id = form.reservatorio_destino_id.data if form.reservatorio_destino_id.data != 0 else None
        grupo_bombeamento_id = form.grupo_bombeamento_id.data if form.grupo_bombeamento_id.data != 0 else None

        nova_motobomba = Motobomba(
            nome=form.nome.data,
            descricao=form.descricao.data,
            modelo=form.modelo.data,
            fabricante=form.fabricante.data,
            potencia=form.potencia.data,
            succao=succao_obj,
            recalque=recalque_obj,
            tensao_de_trabalho=form.tensao_de_trabalho.data,
            modbus_slave_id=modbus_slave_id,
            reservatorio_fonte_id=reservatorio_fonte_id,
            reservatorio_destino_id=reservatorio_destino_id,
            grupo_bombeamento_id=grupo_bombeamento_id,
            funcao=FuncaoBomba[form.funcao.data],
            status_rotacao=StatusRotacao[form.status_rotacao.data]
        )
        db.session.add(nova_motobomba)
        db.session.commit()
        flash('Motobomba cadastrada com sucesso!', 'success')
        return redirect(url_for('list_pumps'))

    return render_template("nova_motobomba.html", form=form)

@app.route('/motobombas/atualiza_motobomba/<int:id>', methods=["GET", "POST"])
def update_pump(id):
    motobomba = Motobomba.query.get_or_404(id)
    form = MotobombaForm(obj=motobomba)
    _populate_form_choices(form)

    if form.validate_on_submit():
        motobomba.nome = form.nome.data
        motobomba.descricao = form.descricao.data
        motobomba.modelo = form.modelo.data
        motobomba.fabricante = form.fabricante.data
        motobomba.potencia = form.potencia.data
        motobomba.succao = Tubospvc.query.get(int(form.succao.data))
        motobomba.recalque = Tubospvc.query.get(int(form.recalque.data))
        motobomba.tensao_de_trabalho = TensaoTrabalho(form.tensao_de_trabalho.data)
        
        # Tratar valores '0' como None
        motobomba.modbus_slave_id = form.modbus_slave_id.data if form.modbus_slave_id.data != 0 else None
        motobomba.reservatorio_fonte_id = form.reservatorio_fonte_id.data if form.reservatorio_fonte_id.data != 0 else None
        motobomba.reservatorio_destino_id = form.reservatorio_destino_id.data if form.reservatorio_destino_id.data != 0 else None
        motobomba.grupo_bombeamento_id = form.grupo_bombeamento_id.data if form.grupo_bombeamento_id.data != 0 else None

        motobomba.funcao = FuncaoBomba[form.funcao.data]
        motobomba.status_rotacao = StatusRotacao[form.status_rotacao.data]

        db.session.commit()
        flash('Motobomba atualizada com sucesso!', 'success')
        return redirect(url_for('list_pumps'))

    # Para o GET request, garantir que os valores selecionados sejam os corretos
    if request.method == 'GET':
        form.succao.data = str(motobomba.succao_id)
        form.recalque.data = str(motobomba.recalque_id)
        form.tensao_de_trabalho.data = motobomba.tensao_de_trabalho.value
        form.modbus_slave_id.data = motobomba.modbus_slave_id or 0
        form.reservatorio_fonte_id.data = motobomba.reservatorio_fonte_id or 0
        form.reservatorio_destino_id.data = motobomba.reservatorio_destino_id or 0
        form.grupo_bombeamento_id.data = motobomba.grupo_bombeamento_id or 0
        form.funcao.data = motobomba.funcao.name
        form.status_rotacao.data = motobomba.status_rotacao.name

    return render_template("atualiza_motobomba.html", form=form, motobomba=motobomba)

@app.route('/motobombas/remove_motobomba/<int:id>')
def delete_pump(id):
    motobomba = Motobomba.query.get_or_404(id)
    db.session.delete(motobomba)
    db.session.commit()
    flash('Motobomba removida com sucesso!', 'success')
    return redirect(url_for('list_pumps'))