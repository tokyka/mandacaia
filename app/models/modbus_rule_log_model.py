from app import db
import datetime

class ModbusRuleLog(db.Model):
    __tablename__ = 'modbus_rule_log'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('modbus_rule.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    condition_result = db.Column(db.Boolean, nullable=False)
    action_executed = db.Column(db.Boolean, nullable=False)

    rule = db.relationship('ModbusRule', backref=db.backref('modbus_logs', lazy=True))

    def __repr__(self):
        return f'<ModbusRuleLog Rule:{self.rule_id} @ {self.timestamp} Result:{self.condition_result} Action:{self.action_executed}>'