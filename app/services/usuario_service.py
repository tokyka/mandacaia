from app import db
from ..models import usuario_model


def cadastrar_usuario(usuario):
    db.session.add(usuario)
    db.session.commit()
    return usuario

def listar_usuario_nome(nome):
    usuario = usuario_model.Usuario.query.filter_by(nome=nome).first()
    return usuario

def listar_usuario_id(id):
    usuario = usuario_model.Usuario.query.filter_by(id=id).first()
    return usuario

def atualizar_usuario(usuario_anterior, usuario_novo):
    usuario_anterior.nome = usuario_novo.nome
    if usuario_novo.senha:
        usuario_anterior.set_password(usuario_novo.senha)
    usuario_anterior.privilegio = usuario_novo.privilegio
    usuario_anterior.email = usuario_novo.email
    usuario_anterior.enviar_email = usuario_novo.enviar_email
    db.session.commit()
