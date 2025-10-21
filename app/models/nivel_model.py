from app import db


class Nivel(db.Model):
    __tablename__ = "nivel"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    valor = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    reservatorio_id = db.Column(db.Integer, db.ForeignKey("reservatorio.id"), nullable=False)
    reservatorio = db.relationship("Reservatorio", backref="niveis")

    def __init__(self, valor, data, hora, reservatorio):
        self.valor = valor
        self.data = data
        self.hora = hora
        self.reservatorio = reservatorio
