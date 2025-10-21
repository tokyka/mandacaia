from app import app
from app import db
from flask import request, redirect, flash, render_template, url_for
from ..services import usuario_service
from ..models.usuario_model import Usuario, UsuarioForm


@app.route('/usuario/listar_usuarios')
def lista_usuarios():
    return render_template("lista_usuarios.html", usuarios=Usuario.query.all())

@app.route('/usuario/novo_usuario', methods=["GET", "POST"])
def novo_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        nome = form.nome.data
        senha = form.senha.data
        email = form.email.data
        priv = form.privilegio.data
        enviar_email = form.enviar_email.data
        usuario = usuario_service.listar_usuario_nome(nome)
        if usuario is None:
            novo_usuario = Usuario(nome=nome,senha=senha,privilegio=str(priv),
                                                 email=email, enviar_email=enviar_email)
            usuario_service.cadastrar_usuario(novo_usuario)
            return redirect(url_for('lista_usuarios'))
        else:
            flash(f'Erro - Usuário "{nome}" cadastrado, tente outro nome de usuário!', 'error')
            return redirect(url_for('novo_usuario'))
    return render_template("novo_usuario.html", form=form)

@app.route('/usuario/atualiza_usuario/<int:id>', methods=["GET", "POST"])
def atualiza_usuario(id):
    usuario = Usuario.query.filter_by(id=id).first()
    form = UsuarioForm(obj=usuario)
    if form.validate_on_submit():
        usuario.nome = form.nome.data
        usuario.privilegio = form.privilegio.data
        usuario.email = form.email.data
        usuario.enviar_email = form.enviar_email.data
        if form.senha.data:
            usuario.set_password(form.senha.data)
        db.session.commit()
        return redirect(url_for('lista_usuarios'))
    return render_template("atualiza_usuario.html", usuario=usuario, form=form)

@app.route('/usuario/remove_usuario/<int:id>')
def remove_usuario(id):
    Usuario.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('lista_usuarios'))
