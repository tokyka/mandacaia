from app import app

@app.route('/novo_reservatorio')
def new_cistern():
    return 'Mandacaia - Monitoramento dos reservatórios de agua potável - Novo Reservatório de água'

@app.route('/listar_reservatorios')
def list_cisterns():
    return 'Mandacaia - Monitoramento dos reservatórios de agua potável - Listar Reservatórios de água'
