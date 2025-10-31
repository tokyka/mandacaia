from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class ModbusMasterConfig(db.Model):
    __tablename__ = "modbus_master_config"
    id = db.Column(db.Integer, primary_key=True)
    port = db.Column(db.String(80), nullable=False, default='/dev/ttyUSB0')
    baudrate = db.Column(db.Integer, nullable=False, default=9600)
    parity = db.Column(db.String(1), nullable=False, default='N')
    stopbits = db.Column(db.Integer, nullable=False, default=1)
    bytesize = db.Column(db.Integer, nullable=False, default=8)
    timeout = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f"<ModbusMasterConfig(port='{self.port}', baudrate={self.baudrate})>"

class ModbusMasterConfigForm(FlaskForm):
    port = StringField('Porta Serial', validators=[DataRequired(), Length(min=3, max=80)])
    baudrate = IntegerField('Baud Rate', validators=[DataRequired(), NumberRange(min=1)])
    parity = StringField('Paridade (N, E, O)', validators=[DataRequired(), Length(min=1, max=1)])
    stopbits = IntegerField('Stop Bits', validators=[DataRequired(), NumberRange(min=1)])
    bytesize = IntegerField('Byte Size', validators=[DataRequired(), NumberRange(min=5, max=8)])
    timeout = IntegerField('Timeout (segundos)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Salvar Configuração')
