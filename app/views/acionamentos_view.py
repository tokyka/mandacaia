from app import app, db
from flask import render_template
from ..models.acionamento_model import Acionamento

@app.route('/acionamentos')
def list_acionamentos():
    """Exibe uma lista paginada de todos os registros de acionamento."""
    # Ordena para mostrar os acionamentos mais recentes primeiro
    acionamentos = Acionamento.query.options(
        db.joinedload(Acionamento.motobomba)
    ).order_by(Acionamento.data.desc(), Acionamento.hora_lig.desc()).all()
    
    return render_template('lista_acionamentos.html', acionamentos=acionamentos)
