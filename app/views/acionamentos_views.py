from app import app

@app.route('/listar_acionamentos')
def list_acionamentos():
    return 'Mandacaia - Monitoramento dos reservatórios de agua potável - Listar acionamentos'