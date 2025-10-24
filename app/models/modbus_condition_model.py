from app import db
from sqlalchemy.dialects.mysql import ENUM

class ModbusCondition(db.Model):
    __tablename__ = 'modbus_condition'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('modbus_rule.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    left_register_id = db.Column(db.Integer, db.ForeignKey('modbus_register.id'), nullable=False)
    operator = db.Column(ENUM('>', '<', '>=', '<=', '==', '!=', name='condition_operator_type'), nullable=False)
    right_value = db.Column(db.Float, nullable=True) # Value for comparison
    right_is_register = db.Column(db.Boolean, nullable=False, default=False) # If right_value refers to another register's ID
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ModbusCondition {self.name}>'