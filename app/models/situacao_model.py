from app import db


class Situacao(db.Model):
    __tablename__ = "situacao"
    id = db.Column(db.SmallInteger, primary_key=True, autoincrement=True, nullable=False)
    situacao = db.Column(db.String(50), nullable=False)

    def __init__(self, situacao):
        self.situacao = situacao
