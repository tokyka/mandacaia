from app import db
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

class FuncaoRegistrador(db.Model):
    __tablename__ = "funcao_registrador"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    funcao = db.Column(db.String(50), nullable=False, unique=True)

    def __init__(self, funcao):
        self.funcao = funcao

class FuncaoRegistradorForm(FlaskForm):
    funcao = StringField('Nome da Função', validators=[DataRequired(), Length(min=3, max=50)])
    submit = SubmitField('Salvar')

    def validate_funcao(self, funcao):
        # Para verificar se o nome da função já existe, 
        # precisamos diferenciar entre a criação de uma nova função e a atualização de uma existente.
        # No entanto, uma validação simples que bloqueia duplicatas é um bom começo.
        if FuncaoRegistrador.query.filter(FuncaoRegistrador.funcao == funcao.data).first():
            raise ValidationError('Este nome de função já existe. Por favor, escolha outro.')
