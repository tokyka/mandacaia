from app import app, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from ..models import reservatorio_model, motobomba_model, nivel_model, acionamento_model, situacao_model, alerta_config_model, motobomba_alerta_config_model # Importar motobomba_alerta_config_model
from ..models.alerta_config_model import AlertaConfigForm, AlertaConfig
from ..models.motobomba_alerta_config_model import MotobombaAlertaConfigForm, MotobombaAlertaConfig # Importar o formulário e o modelo de alerta de motobomba
from sqlalchemy import desc # Importar desc para ordenação
import datetime

@app.route('/monitoramento/config/alertas')
def configure_alertas_de_monitoramento():
    """
    Exibe um dashboard com o status geral dos reservatórios e motobombas.
    """
    reservatorios = reservatorio_model.Reservatorio.query.all()

    # Preparar dados dos reservatórios para o template
    reservatorios_data = []
    for res in reservatorios:
        ultimo_nivel = nivel_model.Nivel.query.filter_by(reservatorio_id=res.id).order_by(desc(nivel_model.Nivel.data), desc(nivel_model.Nivel.hora)).first()
        nivel_atual = ultimo_nivel.valor if ultimo_nivel else 0
        porcentagem = (nivel_atual / res.capacidade_maxima) * 100 if res.capacidade_maxima > 0 else 0

        # Define o status baseado em faixas fixas de porcentagem
        if porcentagem <= 33:
            status_alerta = "baixo"
        elif porcentagem <= 66:
            status_alerta = "normal"  # 'normal' é usado como 'médio' no sistema
        else:
            status_alerta = "alto"

        reservatorios_data.append({
            'id': res.id,
            'nome': res.nome,
            'nivel_atual': nivel_atual,
            'porcentagem': round(porcentagem, 2),
            'status_alerta': status_alerta
        })

    motobombas = motobomba_model.Motobomba.query.all()
    # Lógica para obter os últimos níveis, status de acionamento, alertas, etc.
    return render_template('dashboard_monitoramento.html',
                           reservatorios_data=reservatorios_data, # Passar os dados processados
                           motobombas=motobombas)

# Nova rota para requisições AJAX
@app.route('/monitoramento/api/niveis_reservatorios')
def get_niveis_reservatorios():
    reservatorios = reservatorio_model.Reservatorio.query.all()
    reservatorios_data = []
    for res in reservatorios:
        ultimo_nivel = nivel_model.Nivel.query.filter_by(reservatorio_id=res.id).order_by(desc(nivel_model.Nivel.data), desc(nivel_model.Nivel.hora)).first()
        nivel_atual = ultimo_nivel.valor if ultimo_nivel else 0
        porcentagem = (nivel_atual / res.capacidade_maxima) * 100 if res.capacidade_maxima > 0 else 0

        # Define o status baseado em faixas fixas de porcentagem
        if porcentagem <= 33:
            status_alerta = "baixo"
        elif porcentagem <= 66:
            status_alerta = "normal"  # 'normal' é usado como 'médio' no sistema
        else:
            status_alerta = "alto"

        # Mapeamento de status para dados visuais esperados pelo template
        status_map = {
            "normal": ("Médio", "bg-warning"),
            "baixo": ("Baixo", "bg-danger"),
            "alto": ("Alto", "bg-primary")
        }
        status_nivel, cor_barra = status_map.get(status_alerta, ("Desconhecido", "bg-secondary"))


        reservatorios_data.append({
            'id': res.id,
            'nome': res.nome,
            'nivel_atual': nivel_atual,
            'porcentagem': round(porcentagem, 2),
            'status_alerta': status_alerta,
            'capacidade_maxima': res.capacidade_maxima,
            'status_nivel': status_nivel,
            'cor_barra': cor_barra
        })
    return jsonify(reservatorios_data)


@app.route('/monitoramento/reservatorio/<int:id>')
def reservatorio_detalhes(id):
    """
    Exibe detalhes e histórico de um reservatório específico.
    """
    reservatorio = reservatorio_model.Reservatorio.query.get_or_404(id)
    niveis_historico_raw = nivel_model.Nivel.query.filter_by(reservatorio_id=id).order_by(nivel_model.Nivel.data.desc(), nivel_model.Nivel.hora.desc()).limit(100).all()

    print(f"DEBUG: Níveis históricos para reservatório {id}: {niveis_historico_raw}") # LINHA DE DEBUG

    # Formatar data e hora para o JavaScript
    niveis_historico = []
    for nivel in niveis_historico_raw:
        niveis_historico.append({
            'valor': nivel.valor,
            'data': nivel.data.strftime('%Y-%m-%d'), # Formatar data
            'hora': nivel.hora.strftime('%H:%M:%S')  # Formatar hora
        })

    return render_template('reservatorio_detalhes.html', # Caminho corrigido
                           reservatorio=reservatorio,
                           niveis_historico=niveis_historico)

@app.route('/monitoramento/motobomba/<int:id>')
def motobomba_detalhes(id):
    """
    Exibe detalhes e histórico de uma motobomba específica.
    """
    motobomba = motobomba_model.Motobomba.query.get_or_404(id)
    # Correção: Usar mb_id para filtrar
    acionamentos_historico = acionamento_model.Acionamento.query.filter_by(mb_id=id).order_by(acionamento_model.Acionamento.data.desc(), acionamento_model.Acionamento.hora_lig.desc()).limit(100).all()
    # Lógica para gráficos, acionamento manual, etc.

    return render_template('motobomba_detalhes.html', # Caminho corrigido
                           motobomba=motobomba,
                           acionamentos_historico=acionamentos_historico)

# Exemplo de rota para acionamento manual (requer autenticação/autorização)
@app.route('/monitoramento/motobomba/<int:id>/acionar', methods=['POST'])
def acionar_motobomba(id):
    # Lógica para acionar a motobomba
    flash('Motobomba acionada com sucesso!', 'success')
    return redirect(url_for('motobomba_detalhes', id=id))

# Exemplo de rota para configuração de alertas de reservatório
@app.route('/monitoramento/alertas/reservatorio', methods=['GET', 'POST'])
@app.route('/monitoramento/alertas/reservatorio/<int:id>', methods=['GET', 'POST'])
def configurar_alertas_reservatorio(id=None):
    form = AlertaConfigForm()
    reservatorios = reservatorio_model.Reservatorio.query.all()
    form.reservatorio.choices = [(r.id, r.nome) for r in reservatorios]

    if id: # Se for edição
        alerta_config = AlertaConfig.query.get_or_404(id)
        if request.method == 'GET':
            form = AlertaConfigForm(obj=alerta_config)
            form.reservatorio.choices = [(r.id, r.nome) for r in reservatorios] # Recarregar choices
            form.reservatorio.data = alerta_config.reservatorio_id # Preencher o campo selecionado
    else: # Se for criação
        alerta_config = None

    if form.validate_on_submit():
        if alerta_config: # Atualizar
            alerta_config.reservatorio_id = form.reservatorio.data
            alerta_config.limite_inferior = form.limite_inferior.data
            alerta_config.limite_superior = form.limite_superior.data
            alerta_config.email_notificacao = form.email_notificacao.data
            alerta_config.ativo = form.ativo.data
            db.session.commit()
            flash('Configuração de alerta de reservatório atualizada com sucesso!', 'success')
        else: # Criar
            novo_alerta = AlertaConfig(
                reservatorio_id=form.reservatorio.data,
                limite_inferior=form.limite_inferior.data,
                limite_superior=form.limite_superior.data,
                email_notificacao=form.email_notificacao.data,
                ativo=form.ativo.data
            )
            db.session.add(novo_alerta)
            db.session.commit()
            flash('Configuração de alerta de reservatório criada com sucesso!', 'success')
        return redirect(url_for('configurar_alertas_reservatorio'))

    alertas_existentes = AlertaConfig.query.all() # Para exibir na tabela
    return render_template('configurar_alertas.html', form=form, alertas_existentes=alertas_existentes) # Renderiza o template de alertas de reservatório

@app.route('/monitoramento/alertas/reservatorio/excluir/<int:id>', methods=['POST']) # Nova rota para exclusão de alerta de reservatório
def excluir_alerta_reservatorio(id):
    alerta_config = AlertaConfig.query.get_or_404(id)
    db.session.delete(alerta_config)
    db.session.commit()
    flash('Configuração de alerta de reservatório excluída com sucesso!', 'success')
    return redirect(url_for('configurar_alertas_reservatorio'))


# Nova rota para configuração de alertas de motobomba
@app.route('/monitoramento/alertas/motobomba', methods=['GET', 'POST'])
@app.route('/monitoramento/alertas/motobomba/<int:id>', methods=['GET', 'POST'])
def configurar_alertas_motobomba(id=None):
    form = MotobombaAlertaConfigForm()
    motobombas = motobomba_model.Motobomba.query.all()
    form.motobomba.choices = [(m.id, m.nome) for m in motobombas]

    if id: # Se for edição
        alerta_config = MotobombaAlertaConfig.query.get_or_404(id)
        if request.method == 'GET':
            form = MotobombaAlertaConfigForm(obj=alerta_config)
            form.motobomba.choices = [(m.id, m.nome) for m in motobombas] # Recarregar choices
            form.motobomba.data = alerta_config.motobomba_id # Preencher o campo selecionado
    else: # Se for criação
        alerta_config = None

    if form.validate_on_submit():
        if alerta_config: # Atualizar
            alerta_config.motobomba_id = form.motobomba.data
            alerta_config.perc_variacao_tensao = form.perc_variacao_tensao.data
            alerta_config.perc_variacao_corrente = form.perc_variacao_corrente.data
            alerta_config.email_notificacao = form.email_notificacao.data
            alerta_config.ativo = form.ativo.data
            db.session.commit()
            flash('Configuração de alerta de motobomba atualizada com sucesso!', 'success')
        else: # Criar
            novo_alerta = MotobombaAlertaConfig(
                motobomba_id=form.motobomba.data,
                perc_variacao_tensao=form.perc_variacao_tensao.data,
                perc_variacao_corrente=form.perc_variacao_corrente.data,
                email_notificacao=form.email_notificacao.data,
                ativo=form.ativo.data
            )
            db.session.add(novo_alerta)
            db.session.commit()
            flash('Configuração de alerta de motobomba criada com sucesso!', 'success')
        return redirect(url_for('configurar_alertas_motobomba'))

    alertas_existentes_motobomba = MotobombaAlertaConfig.query.all() # Para exibir na tabela
    return render_template('configurar_alertas_motobomba.html', form=form, alertas_existentes_motobomba=alertas_existentes_motobomba)

@app.route('/monitoramento/alertas/motobomba/excluir/<int:id>', methods=['POST']) # Nova rota para exclusão de alerta de motobomba
def excluir_alerta_motobomba(id):
    alerta_config = MotobombaAlertaConfig.query.get_or_404(id)
    db.session.delete(alerta_config)
    db.session.commit()
    flash('Configuração de alerta de motobomba excluída com sucesso!', 'success')
    return redirect(url_for('configurar_alertas_motobomba'))

@app.route('/monitoramento/reservatorios')
def monitoramento_reservatorios():
    reservatorios = reservatorio_model.Reservatorio.query.all()
    return render_template('painel_reservatorio.html', reservatorios=reservatorios)

@app.route('/monitoramento/motobombas')
def monitoramento_motobombas():
    return render_template('painel_motobomba.html')


@app.route('/monitoramento/api/status_motobomba')
def get_status_motobomba():
    """Fornece o status atual da motobomba principal via JSON."""
    try:
        # Encontrar a motobomba principal
        motobomba_principal = motobomba_model.Motobomba.query.filter_by(funcao='PRINCIPAL').first()
        if not motobomba_principal:
            return jsonify({'status': 'ERRO', 'texto_status': 'Bomba principal não configurada'}), 500

        # Encontrar o último ciclo de acionamento para essa bomba
        ultimo_acionamento = acionamento_model.Acionamento.query.filter_by(mb_id=motobomba_principal.id).order_by(desc(acionamento_model.Acionamento.data), desc(acionamento_model.Acionamento.hora_lig)).first()

        runtime_str = '00:00:00'
        if ultimo_acionamento and ultimo_acionamento.hora_des is None:
            # Se o último ciclo não tem hora de desligar, a bomba está ligada
            now = datetime.datetime.now()
            start_datetime = datetime.datetime.combine(ultimo_acionamento.data, ultimo_acionamento.hora_lig)
            runtime_delta = now - start_datetime
            
            hours, remainder = divmod(runtime_delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

            return jsonify({
                'status': 'LIGADA',
                'texto_status': 'Sistema em operação',
                'classe_css': 'status-on',
                'potencia': motobomba_principal.potencia,
                'runtime': runtime_str
            })
        else:
            # Se não há ciclos ou o último ciclo foi finalizado, está desligada
            return jsonify({
                'status': 'DESLIGADA',
                'texto_status': 'Sistema parado',
                'classe_css': 'status-off',
                'potencia': motobomba_principal.potencia,
                'runtime': runtime_str
            })

    except Exception as e:
        # Em caso de erro, retorna um status de erro claro
        return jsonify({'status': 'ERRO', 'texto_status': str(e)}), 500