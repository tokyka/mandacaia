
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import enum

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mariadb+mariadbconnector://mandacaia_user:fHWb2vFIDxLHyEKNMOxZZbWGi2@127.0.0.1:3306/mandacaia_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class MyEnum(enum.Enum):
    one = 'one'
    two = 'two'
    three = 'three'

class MyModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    my_enum = db.Column(db.Enum(MyEnum))

