from app import db
from flask_wtf import FlaskForm
from wtforms import FloatField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime

class MotobombaAlertaConfig(db.Model):
    __tablename__ = "motobomba_alerta_config"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    motobomba_id = db.Column(db.Integer, db.ForeignKey('motobomba.id'), nullable=False)
    motobomba = db.relationship('Motobomba', backref='alertas_config')
    perc_variacao_tensao = db.Column(db.Float, nullable=False, default=10.0) # Alterado para 10.0%
    perc_variacao_corrente = db.Column(db.Float, nullable=False, default=15.0) # Alterado para 15.0%
    email_notificacao = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    timestamp_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    timestamp_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, motobomba_id, perc_variacao_tensao, perc_variacao_corrente, email_notificacao=False, ativo=True):
        self.motobomba_id = motobomba_id
        self.perc_variacao_tensao = perc_variacao_tensao
        self.perc_variacao_corrente = perc_variacao_corrente
        self.email_notificacao = email_notificacao
        self.ativo = ativo

class MotobombaAlertaConfigForm(FlaskForm):
    motobomba = SelectField('Motobomba', coerce=int, validators=[DataRequired()])
    perc_variacao_tensao = FloatField('Variação de Tensão (%)', default=10.0, validators=[DataRequired(), NumberRange(min=0, max=100)]) # Alterado para 10.0%
    perc_variacao_corrente = FloatField('Variação de Corrente (%)', default=15.0, validators=[DataRequired(), NumberRange(min=0, max=100)]) # Alterado para 15.0%
    email_notificacao = BooleanField('Notificar por E-mail')
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar Configuração')