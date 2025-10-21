#import urllib.parse

DEBUG = False
SERVER_NAME = "localhost:9000"

import os

USERNAME = os.environ.get('DB_USER', 'mandacaia_user')
PASSWORD = os.environ.get('DB_PASSWORD', 'Mandacaia2025') # Senha que você confirmou que funciona
SERVER = os.environ.get('DB_HOST', '127.0.0.1') # Host que você confirmou que funciona
PORT = os.environ.get('DB_PORT', '3306')
DB = os.environ.get('DB_NAME', 'mandacaia') # Nome do DB que você confirmou que funciona

SQLALCHEMY_DATABASE_URI = f'mariadb+mariadbconnector://{USERNAME}:{PASSWORD}@{SERVER}:{PORT}/{DB}'
# Removido '?unix_socket=' pois não é necessário para conexão TCP/IP e pode causar problemas se o socket não existir.
SQLALCHEMY_TRACK_MODIFICATIONS = True
