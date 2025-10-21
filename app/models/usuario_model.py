from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email


class Usuario(db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    nome = db.Column(db.String(30), unique=True, nullable=False)
    senha = db.Column(db.String(256), nullable=False)
    privilegio = db.Column(db.String(20), nullable=False )
    email = db.Column(db.String(50))
    enviar_email = db.Column(db.Boolean)

    def __init__(self, nome, senha, privilegio, email, enviar_email):
        self.nome = nome
        self.set_password(senha)
        self.privilegio = privilegio
        self.email = email
        self.enviar_email = enviar_email

    def set_password(self, senha):
        self.senha = generate_password_hash(senha, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, senha):
        return check_password_hash(self.senha, senha)


class UsuarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    privilegio = SelectField('Privilégio', choices=[('usuario', 'Usuário'), ('administrador', 'Administrador')])
    enviar_email = BooleanField('Enviar Email')
    submit = SubmitField('Salvar')
