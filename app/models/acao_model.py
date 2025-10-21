from app import db

class Acao(db.Model):
    __tablename__ = 'acao'
    id = db.Column(db.Integer, primary_key=True)
    regra_id = db.Column(db.Integer, db.ForeignKey('regra.id'), nullable=False)

    # Detalhes da ação
    tipo_acao = db.Column(db.String(50), nullable=False)  # Ex: 'ESCREVER_COIL', 'ENVIAR_EMAIL'
    registrador_alvo = db.Column(db.String(100), nullable=True) # Ex: 'Acionamento_Bomba_Principal'
    valor = db.Column(db.String(100), nullable=True)      # Ex: 'True', 'False'

    def __repr__(self):
        return f'<Acao {self.tipo_acao} em {self.registrador_alvo} com valor {self.valor}>'
