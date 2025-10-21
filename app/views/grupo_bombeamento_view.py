from app import app, db
from flask import render_template, redirect, url_for, flash, request
from ..models.motobomba_model import GrupoBombeamento, GrupoBombeamentoForm

@app.route('/grupos_bombeamento')
def lista_grupos():
    grupos = GrupoBombeamento.query.all()
    return render_template('lista_grupos.html', grupos=grupos)

@app.route('/grupos_bombeamento/novo', methods=['GET', 'POST'])
def novo_grupo():
    form = GrupoBombeamentoForm()
    if form.validate_on_submit():
        novo = GrupoBombeamento(nome=form.nome.data, descricao=form.descricao.data)
        db.session.add(novo)
        db.session.commit()
        flash('Grupo de Bombeamento criado com sucesso!', 'success')
        return redirect(url_for('lista_grupos'))
    return render_template('novo_grupo.html', form=form)

@app.route('/grupos_bombeamento/atualiza/<int:id>', methods=['GET', 'POST'])
def atualiza_grupo(id):
    grupo = GrupoBombeamento.query.get_or_404(id)
    form = GrupoBombeamentoForm(obj=grupo)
    if form.validate_on_submit():
        form.populate_obj(grupo)
        db.session.commit()
        flash('Grupo de Bombeamento atualizado com sucesso!', 'success')
        return redirect(url_for('lista_grupos'))
    return render_template('atualiza_grupo.html', form=form, grupo=grupo)

@app.route('/grupos_bombeamento/remove/<int:id>')
def remove_grupo(id):
    grupo = GrupoBombeamento.query.get_or_404(id)
    if grupo.motobombas:
        flash('Erro: Não é possível remover um grupo que contém motobombas associadas.', 'danger')
        return redirect(url_for('lista_grupos'))
    
    db.session.delete(grupo)
    db.session.commit()
    flash('Grupo de Bombeamento removido com sucesso!', 'success')
    return redirect(url_for('lista_grupos'))
