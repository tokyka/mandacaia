from app import app

@app.route('/nova_motobomba')
def new_pump():
    return 'Mandacaia - Monitoramento dos reservatórios de agua potável - Nova motobomba'

@app.route('/listar_motobomba')
def list_pumps():
    return 'Mandacaia - Monitoramento dos reservatórios de agua potável - Listar motobombas'