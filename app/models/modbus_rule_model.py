from app import db

class ModbusRule(db.Model):
    __tablename__ = 'modbus_rule'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0) # For resolving conflicts
    stop_on_trigger = db.Column(db.Boolean, default=False) # For hysteresis

    conditions = db.relationship('ModbusCondition', backref='modbus_rule', lazy=True, cascade="all, delete-orphan")
    actions = db.relationship('ModbusAction', backref='modbus_rule', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ModbusRule {self.name}>'