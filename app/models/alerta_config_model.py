from app import db
from flask_wtf import FlaskForm
from wtforms import FloatField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime

class AlertaConfig(db.Model):
    __tablename__ = "alerta_config"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    reservatorio_id = db.Column(db.Integer, db.ForeignKey('reservatorio.id'), nullable=False)

    limite_inferior = db.Column(db.Float, nullable=False)
    limite_superior = db.Column(db.Float, nullable=False)
    email_notificacao = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    timestamp_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    timestamp_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, reservatorio_id, limite_inferior, limite_superior, email_notificacao=False, ativo=True):
        self.reservatorio_id = reservatorio_id
        self.limite_inferior = limite_inferior
        self.limite_superior = limite_superior
        self.email_notificacao = email_notificacao
        self.ativo = ativo

class AlertaConfigForm(FlaskForm):
    reservatorio = SelectField('Reservatório', coerce=int, validators=[DataRequired()])
    limite_inferior = FloatField('Limite Inferior', validators=[DataRequired(), NumberRange(min=0)])
    limite_superior = FloatField('Limite Superior', validators=[DataRequired(), NumberRange(min=0)])
    email_notificacao = BooleanField('Notificar por E-mail')
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar Configuração')
