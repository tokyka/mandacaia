from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, FloatField # Importar FloatField
from wtforms.validators import DataRequired, Length, NumberRange, Optional # Importar NumberRange

class Tiporeservatorio(db.Model):
    __tablename__ = "tipo_de_reservatorio"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)

    def __init__(self, tipo):
        self.tipo = tipo


class Reservatorio(db.Model):
    __tablename__ = "reservatorio"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    nome = db.Column(db.String(30), nullable=False)
    descricao = db.Column(db.String(80), nullable=False)
    capacidade_maxima = db.Column(db.Float, nullable=False, default=1000.0) # Novo campo
    tipo_id = db.Column(db.Integer, db.ForeignKey("tipo_de_reservatorio.id"))
    tipos = db.relationship("Tiporeservatorio", backref="reservatorios")
    alertas_config = db.relationship('AlertaConfig', cascade='all, delete-orphan', lazy=True, backref='reservatorio')

    # Relacionamento com ModbusSlave
    modbus_slave_id = db.Column(db.Integer, db.ForeignKey('modbus_device.id'), nullable=True)
    modbus_slave = db.relationship('ModbusDevice', backref='reservatorios')

    def __init__(self, nome, descricao, capacidade_maxima, tipos, modbus_slave_id=None): # Atualizado __init__
        self.nome = nome
        self.descricao = descricao
        self.capacidade_maxima = capacidade_maxima
        self.tipos = tipos
        self.modbus_slave_id = modbus_slave_id

class ReservatorioForm(FlaskForm):
    nome = StringField('Nome do Reservatório', validators=[DataRequired(), Length(min=2, max=30)])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(min=5, max=80)])
    capacidade_maxima = FloatField('Capacidade Máxima (Litros)', validators=[DataRequired(), NumberRange(min=1)]) # Novo campo no formulário
    tipo = SelectField('Tipo', coerce=int, validators=[DataRequired()])
    modbus_slave_id = SelectField('Dispositivo Modbus', coerce=int, validators=[Optional()])
    submit = SubmitField('Salvar')
