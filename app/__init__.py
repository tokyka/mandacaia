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

from app.models import acionamento_model
from app.models import alerta_config_model
from app.models import modbus_data_model
from app.models import modbus_model
from app.models import motobomba_alerta_config_model
from app.models import motobomba_model
from app.models import nivel_model
from app.models import reservatorio_model
from app.models import situacao_model
from app.models import usuario_model
from .views import login_view, acionamentos_view, reservatorio_view, motobomba_view, usuarios_view, nivel_view, index_view, monitoramento_view, modbus_view, grupo_bombeamento_view, funcao_registrador_view, database_view

# Configuração de logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('/home/carlos/python/mandacaia/logs/mandacaia.log', maxBytes=10240,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Mandacaia startup')
