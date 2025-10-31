from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__, static_folder='static')
app.config.from_object('config')
app.secret_key = b'[l)aYf(+Y0tID}NtPBi>@|"*tBhJ@U.aEoB[_,Np1=k@m.R\\Egj)JoLV?QU|!iO('
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

from app.models.acionamento_model import Acionamento
from app.models.alerta_config_model import AlertaConfig
from app.models.modbus_data_model import ModbusData
from app.models.modbus_device_register_model import ModbusDevice, ModbusRegister
from app.models.motobomba_alerta_config_model import MotobombaAlertaConfig
from app.models.motobomba_model import Motobomba
from app.models.nivel_model import Nivel
from app.models.reservatorio_model import Reservatorio
from app.models.situacao_model import Situacao
from app.models.usuario_model import Usuario
from app.models.modbus_rule_model import ModbusRule
from app.models.modbus_condition_model import ModbusCondition
from app.models.modbus_action_model import ModbusAction
from app.models.modbus_rule_log_model import ModbusRuleLog
from app.models.modbus_master_config_model import ModbusMasterConfig
from .views import login_view, acionamentos_view, reservatorio_view, motobomba_view, usuarios_view, nivel_view, index_view, monitoramento_view, modbus_view, grupo_bombeamento_view, database_view, regra_view

# Configuração de logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/mandacaia.log', maxBytes=10240,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Mandacaia startup')
