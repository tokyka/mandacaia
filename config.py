import os

DEBUG = False
SERVER_NAME = "localhost:9000"

USERNAME = os.environ.get('DB_USER', 'mandacaia_user')
PASSWORD = os.environ.get('DB_PASSWORD', 'fHWb2vFIDxLHyEKNMOxZZbWGi2') # Senha que você confirmou que funciona
SERVER = os.environ.get('DB_HOST', '127.0.0.1') # Host que você confirmou que funciona
PORT = os.environ.get('DB_PORT', '3306')
DB = os.environ.get('DB_NAME', 'mandacaia_db') # Nome do DB que você confirmou que funciona

SQLALCHEMY_DATABASE_URI = f'mariadb+mariadbconnector://{USERNAME}:{PASSWORD}@{SERVER}:{PORT}/{DB}'
SQLALCHEMY_TRACK_MODIFICATIONS = True
