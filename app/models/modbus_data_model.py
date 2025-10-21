from app import db
import datetime

class ModbusData(db.Model):
    __tablename__ = 'modbus_data'
    id = db.Column(db.Integer, primary_key=True)
    register_id = db.Column(db.Integer, db.ForeignKey('modbus_register.id', ondelete='CASCADE'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    register = db.relationship('ModbusRegister', backref=db.backref('data', lazy='dynamic', cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<ModbusData {self.value} @ {self.timestamp}>'
