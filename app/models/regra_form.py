from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, FieldList, FormField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class CondicaoForm(FlaskForm):
    """Sub-formulário para uma condição."""
    variavel = SelectField('Variável', choices=[
        ('Nivel_Reservatorio_Acumulacao', 'Nível do Reservatório de Acumulação (%)'),
        ('Volume_Reservatorio_Acumulacao', 'Volume do Reservatório de Acumulação (L)'),
        ('Nivel_Reservatorio_Distribuicao', 'Nível do Reservatório de Distribuição (%)'),
        ('Volume_Reservatorio_Distribuicao', 'Volume do Reservatório de Distribuição (L)'),
        ('Tensao_Motobomba', 'Tensão da Motobomba (V)'),
        ('Corrente_Motobomba', 'Corrente da Motobomba (A)'),
        ('Potencia_Motobomba', 'Potência da Motobomba (W)'),
        ('Consumo_Motobomba', 'Consumo da Motobomba (kWh)')
    ], validators=[DataRequired()])
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
        ('Salvar_Historico', 'Salvar no Histórico'),
        ('Notificar_Email', 'Notificar por E-mail')
        # Adicione outras ações conforme necessário
    ], validators=[DataRequired()])
    # O campo 'alvo' pode ser adicionado dinamicamente com JS se necessário
    registrador_alvo = SelectField('Alvo (opcional)', coerce=int, validators=[Optional()])
    registrador_alvo_texto = StringField('Alvo (opcional)', validators=[Length(max=100)])
    valor = StringField('Valor (opcional)', validators=[Length(max=100)])

class RegraForm(FlaskForm):
    """Formulário principal para criar/editar uma regra."""
    nome = StringField('Nome da Regra', validators=[DataRequired(), Length(min=3, max=100)])
    descricao = StringField('Descrição', validators=[Length(max=255)])
    habilitada = BooleanField('Habilitada', default=True)

    condicoes = FieldList(FormField(CondicaoForm), min_entries=1)
    acoes = FieldList(FormField(AcaoForm), min_entries=1)

    submit = SubmitField('Salvar Regra')
