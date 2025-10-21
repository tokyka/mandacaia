from app import db


class Teste(db.Model):
    __tablename__ = "teste"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    nome = db.Column(db.String(30))

    def __init__(self, nome):
        self.nome = nome
