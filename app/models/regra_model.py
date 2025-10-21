from app import db

class Regra(db.Model):
    __tablename__ = 'regra'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.String(255))
    habilitada = db.Column(db.Boolean, default=True)

    condicoes = db.relationship('Condicao', backref='regra', lazy=True, cascade="all, delete-orphan")
    acoes = db.relationship('Acao', backref='regra', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Regra {self.nome}>'
