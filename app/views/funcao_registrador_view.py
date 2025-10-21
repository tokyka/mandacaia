from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models.funcao_registrador_model import FuncaoRegistrador, FuncaoRegistradorForm

@app.route('/modbus_escravo/lista_funcoes')
def lista_funcoes():
    funcoes = FuncaoRegistrador.query.all()
    return render_template('lista_funcoes.html', funcoes=funcoes)

@app.route('/modbus_escravo/nova_funcao', methods=['GET', 'POST'])
def nova_funcao():
    form = FuncaoRegistradorForm()
    if form.validate_on_submit():
        nova = FuncaoRegistrador(funcao=form.funcao.data)
        db.session.add(nova)
        db.session.commit()
        flash('Função criada com sucesso!', 'success')
        return redirect(url_for('lista_funcoes'))
    return render_template('nova_funcao.html', form=form)

@app.route('/modbus_escravo/atualiza_funcao/<int:id>', methods=['GET', 'POST'])
def atualiza_funcao(id):
    funcao = FuncaoRegistrador.query.get_or_404(id)
    form = FuncaoRegistradorForm(obj=funcao)
    
    # Custom validation to allow updating the object with the same name
    if request.method == 'POST':
        # A simple check to see if the new name is different from the old one
        # and if it already exists in the database.
        new_name = form.funcao.data
        if new_name != funcao.funcao and FuncaoRegistrador.query.filter_by(funcao=new_name).first():
            flash('Este nome de função já existe. Por favor, escolha outro.', 'danger')
            return render_template('atualiza_funcao.html', form=form, funcao=funcao)

        if form.validate_on_submit():
            funcao.funcao = new_name
            db.session.commit()
            flash('Função atualizada com sucesso!', 'success')
            return redirect(url_for('lista_funcoes'))

    return render_template('atualiza_funcao.html', form=form, funcao=funcao)

@app.route('/modbus_escravo/remove_funcao/<int:id>', methods=['POST'])
def remove_funcao(id):
    funcao = FuncaoRegistrador.query.get_or_404(id)
    
    # Check if the function is being used by any register
    if funcao.registradores.first():
        flash('Não é possível excluir esta função, pois ela está sendo utilizada por um ou mais registradores.', 'danger')
    else:
        db.session.delete(funcao)
        db.session.commit()
        flash('Função removida com sucesso!', 'success')
        
    return redirect(url_for('lista_funcoes'))
