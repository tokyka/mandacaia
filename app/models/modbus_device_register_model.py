from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, ValidationError, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
import sqlalchemy as sa

class ModbusDevice(db.Model):
    __tablename__ = "modbus_device"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(100), nullable=True) # IP address for TCP or serial port for RTU
    slave_id = db.Column(db.Integer, nullable=False, unique=True)
    type = db.Column(sa.Enum('reservatorio', 'bomba', 'sensor', 'outro', name='device_type'), nullable=False)
    ativo = db.Column(sa.Boolean, nullable=False, default=True)
    
    registers = db.relationship('ModbusRegister', backref='modbus_device', lazy=True, cascade="all, delete-orphan")

    def __init__(self, name, ip_address, slave_id, type, ativo=True):
        self.name = name
        self.ip_address = ip_address
        self.slave_id = slave_id
        self.type = type
        self.ativo = ativo

class ModbusRegister(db.Model):
    __tablename__ = "modbus_register"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('modbus_device.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False) # e.g., "Nível (%)", "Tensão (V)"
    function_code = db.Column(db.Integer, nullable=False) # Modbus function code (1, 2, 3, 4)
    address = db.Column(db.Integer, nullable=False)
    data_type = db.Column(sa.Enum('int', 'float', 'bool', name='register_data_type'), nullable=False)
    scale = db.Column(db.Float, nullable=False, default=1.0)
    rw = db.Column(sa.Enum('R', 'W', name='register_rw_type'), nullable=False) # Read/Write
    last_value = db.Column(db.Float, nullable=True) # Last read value, updated automatically
    descricao = db.Column(db.String(120), nullable=True)

    device = db.relationship('ModbusDevice', backref=db.backref('modbus_registers', lazy='dynamic'))

    def __init__(self, device_id, name, function_code, address, data_type, scale, rw, descricao=None):
        self.device_id = device_id
        self.name = name
        self.function_code = function_code
        self.address = address
        self.data_type = data_type
        self.scale = scale
        self.rw = rw
        self.descricao = descricao

class ModbusDeviceForm(FlaskForm):
    name = StringField('Nome do Dispositivo', validators=[DataRequired(), Length(min=2, max=80)])
    ip_address = StringField('Endereço IP / Porta Serial', validators=[Optional(), Length(max=100)])
    slave_id = IntegerField('ID do Escravo', validators=[DataRequired(), NumberRange(min=1, max=247)])
    type = SelectField('Tipo de Dispositivo', choices=[('reservatorio', 'Reservatório'), ('bomba', 'Bomba'), ('sensor', 'Sensor'), ('outro', 'Outro')], validators=[DataRequired()])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar Dispositivo')

    def validate_slave_id(self, slave_id):
        if ModbusDevice.query.filter_by(slave_id=slave_id.data).first():
            raise ValidationError('Este ID de Escravo já está em uso. Por favor, escolha outro.')

class ModbusRegisterForm(FlaskForm):
    name = StringField('Nome do Registrador', validators=[DataRequired(), Length(min=2, max=100)])
    function_code = SelectField('Código de Função Modbus', coerce=int, choices=[(1, 'Coil (1)'), (2, 'Discrete Input (2)'), (3, 'Holding Register (3)'), (4, 'Input Register (4)')], validators=[DataRequired()])
    address = IntegerField('Endereço do Registrador', validators=[DataRequired(), NumberRange(min=0)])
    data_type = SelectField('Tipo de Dado', choices=[('int', 'Inteiro'), ('float', 'Float'), ('bool', 'Booleano')], validators=[DataRequired()])
    scale = FloatField('Fator de Escala', validators=[DataRequired()])
    rw = SelectField('Acesso', choices=[('R', 'Leitura'), ('W', 'Escrita')], validators=[DataRequired()])
    descricao = StringField('Descrição (Opcional)', validators=[Length(max=120)])
    submit = SubmitField('Salvar Registrador')

class DeleteForm(FlaskForm):
    submit = SubmitField('Excluir')