from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, NumberRange

class ModbusSlave(db.Model):
    __tablename__ = "modbus_slave"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    slave_id = db.Column(db.Integer, nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, server_default='Indefinido')
    last_seen = db.Column(db.DateTime, nullable=True)
    
    registradores = db.relationship('ModbusRegister', backref='modbus_slave', lazy=True, cascade="all, delete-orphan")

    def __init__(self, nome, slave_id):
        self.nome = nome
        self.slave_id = slave_id
        self.status = 'Indefinido'

class ModbusRegister(db.Model):
    __tablename__ = "modbus_register"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    slave_id = db.Column(db.Integer, db.ForeignKey('modbus_slave.id'), nullable=False)
    endereco = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # e.g., coil, discrete_input, input_register, holding_register
    acesso = db.Column(db.String(20), nullable=False) # Read/Write, Read-Only
    tamanho = db.Column(db.String(20), nullable=False) # 1 bit, 16 bits
    data_type = db.Column(db.String(20), nullable=False, server_default='int16') # Tipo de dado do valor
    descricao = db.Column(db.String(120), nullable=True)
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_registrador.id'), nullable=False)

    funcao = db.relationship('FuncaoRegistrador', backref=db.backref('registradores', lazy='dynamic'))

    def __init__(self, slave_id, endereco, tipo, funcao_id, acesso, tamanho, data_type='int16', descricao=None):
        self.slave_id = slave_id
        self.endereco = endereco
        self.tipo = tipo
        self.funcao_id = funcao_id
        self.acesso = acesso
        self.tamanho = tamanho
        self.data_type = data_type
        self.descricao = descricao

class ModbusSlaveForm(FlaskForm):
    nome = StringField('Nome do Escravo', validators=[DataRequired(), Length(min=2, max=80)])
    slave_id = IntegerField('ID do Escravo', validators=[DataRequired()])
    submit = SubmitField('Salvar')

    # def validate_slave_id(self, slave_id):
    #     if ModbusSlave.query.filter_by(slave_id=slave_id.data).first():
    #         raise ValidationError('Este ID de Escravo já está em uso. Por favor, escolha outro.')

class ModbusRegisterForm(FlaskForm):
    endereco = IntegerField('Endereço do Registrador', validators=[DataRequired()])
    tipo = SelectField('Tipo de Registrador', choices=[('coil', 'Coil (0xxxx)'), ('discrete_input', 'Discrete Input (1xxxx)'), ('input_register', 'Input Register (3xxxx)'), ('holding_register', 'Holding Register (4xxxx)')], validators=[DataRequired()])
    acesso = SelectField('Acesso', choices=[('Read/Write', 'Leitura/Escrita'), ('Read-Only', 'Somente Leitura')], validators=[DataRequired()])
    tamanho = SelectField('Tamanho', choices=[('1 bit', '1 bit'), ('16 bits', '16 bits'), ('32 bits', '32 bits')], validators=[DataRequired()])
    data_type = SelectField('Tipo de Dado', choices=[('int16', 'Integer 16-bit'), ('uint16', 'Unsigned Int 16-bit'), ('int32', 'Integer 32-bit'), ('uint32', 'Unsigned Int 32-bit'), ('float32', 'Float 32-bit'), ('boolean', 'Boolean')], validators=[DataRequired()], default='int16')
    descricao = StringField('Descrição (Opcional)', validators=[Length(max=120)])
    submit = SubmitField('Salvar Registrador')

class DeleteForm(FlaskForm):
    submit = SubmitField('Excluir')