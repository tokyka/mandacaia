from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, ValidationError, BooleanField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
import enum
from sqlalchemy import Enum

class DeviceType(enum.Enum):
    RESERVATORIO = 'reservatorio'
    BOMBA = 'bomba'
    SENSOR = 'sensor'
    OUTRO = 'outro'

class RegisterRWType(enum.Enum):
    READ = 'R'
    WRITE = 'W'

class ModbusDevice(db.Model):
    __tablename__ = "modbus_device"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    device_name = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(100), nullable=True) # IP address for TCP or serial port for RTU
    slave_id = db.Column(db.Integer, nullable=False, unique=True)
    type = db.Column(
        Enum(DeviceType, native_enum=False, name="device_type_enum", values_callable=lambda x: [member.value for member in x]),
        nullable=False,
        info={"compare_type": False}
    )
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    
    registers = db.relationship('ModbusRegister', back_populates='device', lazy=True, cascade="all, delete-orphan")
    motobombas = db.relationship('Motobomba', back_populates='modbus_slave')
    reservatorios = db.relationship('Reservatorio', back_populates='modbus_slave')

    def __init__(self, device_name, ip_address, slave_id, type: DeviceType, ativo=True):
        self.device_name = device_name
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
    data_type = db.Column(db.String(20), nullable=False, default='int16')
    scale = db.Column(db.Float, nullable=False, default=1.0)
    rw = db.Column(
        Enum(RegisterRWType, native_enum=False, name="register_rw_enum", values_callable=lambda x: [member.value for member in x]),
        nullable=False,
        info={"compare_type": False}
    )
    last_value = db.Column(db.Float, nullable=True) # Last read value, updated automatically
    descricao = db.Column(db.String(120), nullable=True)

    device = db.relationship('ModbusDevice', back_populates='registers')

    def __init__(self, device_id, name, function_code, address, data_type, scale, rw: RegisterRWType, descricao=None):
        self.device_id = device_id
        self.name = name
        self.function_code = function_code
        self.address = address
        self.data_type = data_type
        self.scale = scale
        self.rw = rw
        self.descricao = descricao

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'name': self.name,
            'function_code': self.function_code,
            'address': self.address,
            'data_type': self.data_type,
            'scale': self.scale,
            'rw': self.rw.value, # Converte o Enum para string
            'last_value': self.last_value,
            'descricao': self.descricao
        }

class ModbusDeviceForm(FlaskForm):
    device_name = StringField('Nome do Dispositivo', validators=[DataRequired(), Length(min=2, max=80)])
    ip_address = StringField('Endereço IP / Porta Serial', validators=[Optional(), Length(max=100)])
    slave_id = IntegerField('ID do Escravo', validators=[DataRequired(), NumberRange(min=1, max=247)])
    type = SelectField('Tipo de Dispositivo', choices=[(choice.value, choice.value.capitalize()) for choice in DeviceType], validators=[DataRequired()])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar Dispositivo')

    def __init__(self, original_slave_id=None, *args, **kwargs):
        super(ModbusDeviceForm, self).__init__(*args, **kwargs)
        self.original_slave_id = original_slave_id

    def validate_slave_id(self, slave_id):
        if slave_id.data != self.original_slave_id:
            if ModbusDevice.query.filter_by(slave_id=slave_id.data).first():
                raise ValidationError('Este ID de Escravo já está em uso. Por favor, escolha outro.')

class ModbusRegisterForm(FlaskForm):
    name = StringField('Nome do Registrador', validators=[DataRequired(), Length(min=2, max=100)])
    function_code = SelectField('Código de Função Modbus', coerce=int, choices=[(1, 'Coil (1)'), (2, 'Discrete Input (2)'), (3, 'Holding Register (3)'), (4, 'Input Register (4)')], validators=[DataRequired()])
    address = IntegerField('Endereço do Registrador', validators=[DataRequired(), NumberRange(min=0)])
    data_type = SelectField('Tipo de Dado', 
                            choices=[('int16', 'Integer 16-bit'), 
                                     ('uint16', 'Unsigned Int 16-bit'), 
                                     ('int32', 'Integer 32-bit'), 
                                     ('uint32', 'Unsigned Int 32-bit'), 
                                     ('float32', 'Float 32-bit'), 
                                     ('boolean', 'Boolean')], 
                            validators=[DataRequired()])
    scale = FloatField('Fator de Escala', validators=[DataRequired()])
    rw = SelectField('Acesso', choices=[(choice.value, choice.value) for choice in RegisterRWType], validators=[DataRequired()])
    descricao = StringField('Descrição (Opcional)', validators=[Length(max=120)])
    submit = SubmitField('Salvar Registrador')

class DeleteForm(FlaskForm):
    submit = SubmitField('Excluir')
