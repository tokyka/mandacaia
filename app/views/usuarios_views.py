from app import app, db
from ..services import usuario_service
from ..models import usuario_model, teste_model
from flask import render_template, request, redirect, url_for, flash


@app.route('/listar_usuarios')
def lista_usuarios():
    teste_db = teste_model.Teste(nome="teste")
    db.session.add(teste_db)
    db.session.commit()
    return render_template("lista_usuarios.html", usuarios=usuario_model.Usuario.query.all())

@app.route('/novo_usuario', methods=["GET", "POST"])
def novo_usuario():
    if request.method == 'GET':
        return render_template("novo_usuario.html")

    if request.method == 'POST':
        nome = request.form.get('usuario')
        senha = request.form.get('senha')
        email = request.form.get('email')
        priv = request.form.get('privilegios')
        if request.form.get('enviar_email'):
            enviar_email = 1
        else:
            enviar_email = 0
        if nome and senha:
            usuario = usuario_service.listar_usuario_nome(nome)
            if usuario is None:
                novo_usuario = usuario_model.Usuario(nome=nome,senha=senha,privilegio=str(priv),
                                                     email=email, enviar_email=enviar_email)
                usuario_service.cadastrar_usuario(novo_usuario)
                return redirect(url_for('lista_usuarios'))
            else:
                flash('Usuário já cadastrado, tente outro nome de usuário!', 'error')
        else:
            flash('Usuário ou senha em branco!', 'error')
