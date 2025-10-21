from app import db
import datetime

class Acionamento(db.Model):
    __tablename__ = "acionamento"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.date.today)
    hora_lig = db.Column(db.Time, nullable=False, default=datetime.datetime.now().time)
    hora_des = db.Column(db.Time, nullable=True)   # Hora em que a bomba foi desligada
    tensao = db.Column(db.Float, nullable=True)
    corrente = db.Column(db.Float, nullable=True)
    potencia = db.Column(db.Float, nullable=True)
    consumo = db.Column(db.Float, nullable=True)
    consumo_kwh = db.Column(db.Float, nullable=True) # Consumo em kWh

    mb_id = db.Column(db.Integer, db.ForeignKey("motobomba.id"))
    motobomba = db.relationship("Motobomba", backref="acionamentos")

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    usuario = db.relationship("Usuario", backref="acionamentos")

    situacao_id = db.Column(db.SmallInteger, db.ForeignKey("situacao.id"))
    situacao = db.relationship("Situacao", backref="acionamentos")

    def __init__(self, motobomba, usuario, situacao, data=None, hora_lig=None, hora_des=None, tensao=None, corrente=None, potencia=None, consumo=None, consumo_kwh=None):
        self.motobomba = motobomba
        self.usuario = usuario
        self.situacao = situacao
        self.data = data or datetime.date.today()
        self.hora_lig = hora_lig or datetime.datetime.now().time()
        self.hora_des = hora_des
        self.tensao = tensao
        self.corrente = corrente
        self.potencia = potencia
        self.consumo = consumo
        self.consumo_kwh = consumo_kwh

    @property
    def duracao(self):
        if self.hora_des:
            # Combina a data com as horas para criar objetos datetime
            start_dt = datetime.datetime.combine(self.data, self.hora_lig)
            end_dt = datetime.datetime.combine(self.data, self.hora_des)

            # Caso o ciclo passe da meia-noite
            if end_dt < start_dt:
                end_dt += datetime.timedelta(days=1)

            return end_dt - start_dt
        return None  # Retorna None se a bomba ainda estiver ligada