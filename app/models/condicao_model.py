from app import db

class Condicao(db.Model):
    __tablename__ = 'condicao'
    id = db.Column(db.Integer, primary_key=True)
    regra_id = db.Column(db.Integer, db.ForeignKey('regra.id'), nullable=False)

    # Detalhes da condição
    variavel = db.Column(db.String(100), nullable=False)  # Ex: 'Nivel_Reservatorio_A'
    operador = db.Column(db.String(10), nullable=False)    # Ex: '<=', '>=', '=='
    valor = db.Column(db.String(100), nullable=False)     # Ex: '20'

    def __repr__(self):
        return f'<Condicao {self.variavel} {self.operador} {self.valor}>'
