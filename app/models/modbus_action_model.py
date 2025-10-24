from app import db

class ModbusAction(db.Model):
    __tablename__ = 'modbus_action'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('modbus_rule.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    target_register_id = db.Column(db.Integer, db.ForeignKey('modbus_register.id'), nullable=False)
    write_value = db.Column(db.Float, nullable=True) # Value to write (e.g., 1.0 for True, 0.0 for False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ModbusAction {self.name}>'