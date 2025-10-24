from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from enum import Enum
from sqlalchemy import DateTime
import datetime

# --- Enums para novas funcionalidades ---

class FuncaoBomba(Enum):
    PRINCIPAL = "Principal"
    RESERVA = "Reserva"

class StatusRotacao(Enum):
    ATIVA = "Ativa"
    EM_ESPERA = "Em espera"

class TensaoTrabalho(Enum):
    V110 = "110 V"
    V220 = "220 V"
    V380 = "380 V"
    V440 = "440 V"

# --- Novas Tabelas ---

class GrupoBombeamento(db.Model):
    __tablename__ = "grupo_bombeamento"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(150))
    
    # Relacionamento reverso para as bombas no grupo
    motobombas = db.relationship('Motobomba', back_populates='grupo_bombeamento')

    def __init__(self, nome, descricao=""):
        self.nome = nome
        self.descricao = descricao

# --- Tabelas Modificadas ---

class Motobomba(db.Model):
    __tablename__ = "motobomba"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(30), nullable=False)
    fabricante = db.Column(db.String(30), nullable=False)
    potencia = db.Column(db.String(10), nullable=False)
    succao_id = db.Column(db.SmallInteger, db.ForeignKey("tubos.id"), nullable=False)
    succao = db.relationship("Tubospvc", foreign_keys="[Motobomba.succao_id]", backref="motobombas_succao")
    recalque_id = db.Column(db.SmallInteger, db.ForeignKey("tubos.id"), nullable=False)
    recalque = db.relationship("Tubospvc", foreign_keys="[Motobomba.recalque_id]", backref="motobombas_recalque")
    tensao_de_trabalho = db.Column(db.Enum(TensaoTrabalho), nullable=False)

    # Relacionamento com ModbusSlave
    modbus_slave_id = db.Column(db.Integer, db.ForeignKey('modbus_device.id'), nullable=True)
    modbus_slave = db.relationship('ModbusDevice', backref='motobombas')

    # Relacionamentos com Reservatorios (fonte e destino)
    reservatorio_fonte_id = db.Column(db.Integer, db.ForeignKey('reservatorio.id'), nullable=True)
    reservatorio_destino_id = db.Column(db.Integer, db.ForeignKey('reservatorio.id'), nullable=True)
    reservatorio_fonte = db.relationship('Reservatorio', foreign_keys=[reservatorio_fonte_id], backref='bombas_fonte')
    reservatorio_destino = db.relationship('Reservatorio', foreign_keys=[reservatorio_destino_id], backref='bombas_destino')

    # --- Novos Campos para Rotação e Gerenciamento ---
    grupo_bombeamento_id = db.Column(db.Integer, db.ForeignKey('grupo_bombeamento.id'), nullable=True)
    grupo_bombeamento = db.relationship('GrupoBombeamento', back_populates='motobombas')
    
    funcao = db.Column(db.Enum(FuncaoBomba), nullable=False, default=FuncaoBomba.PRINCIPAL)
    status_rotacao = db.Column(db.Enum(StatusRotacao), nullable=False, default=StatusRotacao.EM_ESPERA)
    ultimo_acionamento = db.Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, nome, descricao, modelo, fabricante, potencia, succao, recalque, tensao_de_trabalho, 
                 modbus_slave_id=None, reservatorio_fonte_id=None, reservatorio_destino_id=None,
                 grupo_bombeamento_id=None, funcao=FuncaoBomba.PRINCIPAL, status_rotacao=StatusRotacao.EM_ESPERA):
        self.nome = nome
        self.descricao = descricao
        self.modelo = modelo
        self.fabricante = fabricante
        self.potencia = potencia
        self.succao = succao
        self.recalque = recalque
        self.modbus_slave_id = modbus_slave_id
        self.reservatorio_fonte_id = reservatorio_fonte_id
        self.reservatorio_destino_id = reservatorio_destino_id
        self.grupo_bombeamento_id = grupo_bombeamento_id
        self.funcao = funcao
        self.status_rotacao = status_rotacao
        
        if isinstance(tensao_de_trabalho, str):
            self.tensao_de_trabalho = TensaoTrabalho(tensao_de_trabalho)
        else:
            self.tensao_de_trabalho = tensao_de_trabalho

class Tubospvc(db.Model):
    __tablename__ = "tubos"
    id = db.Column(db.SmallInteger, primary_key=True, autoincrement=True, nullable=False)
    pol = db.Column(db.String(10), nullable=False)
    mm = db.Column(db.String(10), nullable=False)

    def __init__(self, pol, mm):
        self.pol = pol
        self.mm = mm

class MotobombaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(min=5, max=100)])
    modelo = StringField('Modelo', validators=[DataRequired(), Length(min=2, max=30)])
    fabricante = StringField('Fabricante', validators=[DataRequired(), Length(min=2, max=30)])
    potencia = StringField('Potência', validators=[DataRequired(), Length(min=2, max=10)])
    succao = SelectField('Sucção (pol)', validators=[DataRequired()])
    recalque = SelectField('Recalque (pol)', validators=[DataRequired()])
    tensao_de_trabalho = SelectField('Tensão de Trabalho', choices=[(choice.value, choice.name) for choice in TensaoTrabalho], validators=[DataRequired()])
    
    # Campos de associação
    modbus_slave_id = SelectField('Dispositivo Modbus', coerce=int, validators=[Optional()])
    reservatorio_fonte_id = SelectField('Reservatório Fonte (de onde puxa)', coerce=int, validators=[Optional()])
    reservatorio_destino_id = SelectField('Reservatório Destino (para onde envia)', coerce=int, validators=[Optional()])
    
    # --- Novos Campos para Rotação ---
    grupo_bombeamento_id = SelectField('Grupo de Bombeamento', coerce=int, validators=[Optional()])
    funcao = SelectField('Função no Grupo', choices=[(choice.name, choice.value) for choice in FuncaoBomba], validators=[DataRequired()])
    status_rotacao = SelectField('Status de Rotação', choices=[(choice.name, choice.value) for choice in StatusRotacao], validators=[DataRequired()])
    
    submit = SubmitField('Salvar')

class GrupoBombeamentoForm(FlaskForm):
    nome = StringField('Nome do Grupo', validators=[DataRequired(), Length(min=3, max=50)])
    descricao = StringField('Descrição', validators=[Optional(), Length(max=150)])
    submit = SubmitField('Salvar')