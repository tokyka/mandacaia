from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, FieldList, FormField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class CondicaoForm(FlaskForm):
    """Sub-formulário para uma condição."""
    variavel = SelectField('Variável', validators=[DataRequired()])
    operador = SelectField('Operador', choices=[
        ('==', 'Igual a'),
        ('!=', 'Diferente de'),
        ('>', 'Maior que'),
        ('<', 'Menor que'),
        ('>=', 'Maior ou igual a'),
        ('<=', 'Menor ou igual a')
    ], validators=[DataRequired()])
    valor = StringField('Valor', validators=[DataRequired(), Length(max=100)])

class AcaoForm(FlaskForm):
    """Sub-formulário para uma ação."""
    tipo_acao = SelectField('Ação', choices=[
        ('Ligar_Motobomba', 'Ligar Motobomba'),
        ('Desligar_Motobomba', 'Desligar Motobomba'),
        ('Escrever_em_Registrador', 'Escrever em Registrador'),
        ('Salvar_Historico', 'Salvar no Histórico'),
        ('Notificar_Email', 'Notificar por E-mail')
    ], validators=[DataRequired()])
    motobomba_alvo = SelectField('Motobomba Alvo', validators=[Optional()])
    registrador_alvo = SelectField('Registrador Alvo', validators=[Optional()])
    valor = StringField('Valor para Escrita', validators=[Optional(), Length(max=100)])

class RegraForm(FlaskForm):
    """Formulário principal para criar/editar uma regra."""
    name = StringField('Nome da Regra', validators=[DataRequired(), Length(min=3, max=100)])
    description = StringField('Descrição', validators=[Length(max=255)])
    enabled = BooleanField('Habilitada', default=True)

    conditions = FieldList(FormField(CondicaoForm), min_entries=0)
    actions = FieldList(FormField(AcaoForm), min_entries=0)

    submit = SubmitField('Salvar Regra')
