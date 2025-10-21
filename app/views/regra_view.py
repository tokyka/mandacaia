from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models.regra_model import Regra
from app.models.condicao_model import Condicao
from app.models.acao_model import Acao
from app.models.regra_form import RegraForm

@app.route('/regras_modbus/')
def listar_regras():
    regras = Regra.query.all()
    return render_template('regras/lista.html', regras=regras, title='Lista de Regras')

@app.route('/regras_modbus/criar', methods=['GET', 'POST'])
def criar_regra():
    form = RegraForm()
    if form.validate_on_submit():
        try:
            nova_regra = Regra(
                nome=form.nome.data,
                descricao=form.descricao.data,
                habilitada=form.habilitada.data
            )

            for condicao_form in form.condicoes:
                nova_condicao = Condicao(
                    variavel=condicao_form.variavel.data,
                    operador=condicao_form.operador.data,
                    valor=condicao_form.valor.data
                )
                nova_regra.condicoes.append(nova_condicao)

            for acao_form in form.acoes:
                nova_acao = Acao(
                    tipo_acao=acao_form.tipo_acao.data,
                    registrador_alvo=acao_form.registrador_alvo.data,
                    valor=acao_form.valor.data
                )
                nova_regra.acoes.append(nova_acao)

            db.session.add(nova_regra)
            db.session.commit()
            flash('Nova regra criada com sucesso!', 'success')
            return redirect(url_for('listar_regras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar a regra: {e}', 'danger')

    return render_template('regras/editor.html', form=form, title='Criar Nova Regra')

@app.route('/regras_modbus/editar/<int:regra_id>', methods=['GET', 'POST'])
def editar_regra(regra_id):
    regra = Regra.query.get_or_404(regra_id)
    form = RegraForm(obj=regra)

    if form.validate_on_submit():
        try:
            regra.nome = form.nome.data
            regra.descricao = form.descricao.data
            regra.habilitada = form.habilitada.data

            # Limpar condições e ações antigas
            for condicao in regra.condicoes:
                db.session.delete(condicao)
            for acao in regra.acoes:
                db.session.delete(acao)

            # Adicionar novas condições e ações
            for condicao_form in form.condicoes:
                nova_condicao = Condicao(
                    variavel=condicao_form.variavel.data,
                    operador=condicao_form.operador.data,
                    valor=condicao_form.valor.data,
                    regra_id=regra.id
                )
                db.session.add(nova_condicao)

            for acao_form in form.acoes:
                nova_acao = Acao(
                    tipo_acao=acao_form.tipo_acao.data,
                    registrador_alvo=acao_form.registrador_alvo.data,
                    valor=acao_form.valor.data,
                    regra_id=regra.id
                )
                db.session.add(nova_acao)

            db.session.commit()
            flash('Regra atualizada com sucesso!', 'success')
            return redirect(url_for('listar_regras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a regra: {e}', 'danger')

    # Populating the form for GET request
    if request.method == 'GET':
        form.condicoes.entries = []
        for condicao in regra.condicoes:
            condicao_form = form.condicoes.append_entry()
            condicao_form.variavel.data = condicao.variavel
            condicao_form.operador.data = condicao.operador
            condicao_form.valor.data = condicao.valor

        form.acoes.entries = []
        for acao in regra.acoes:
            acao_form = form.acoes.append_entry()
            acao_form.tipo_acao.data = acao.tipo_acao
            acao_form.registrador_alvo.data = acao.registrador_alvo
            acao_form.valor.data = acao.valor


    return render_template('regras/editor.html', form=form, title='Editar Regra', regra=regra)

@app.route('/regras_modbus/remover/<int:regra_id>', methods=['POST'])
def remover_regra(regra_id):
    try:
        regra = Regra.query.get_or_404(regra_id)
        db.session.delete(regra)
        db.session.commit()
        flash('Regra removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover a regra: {e}', 'danger')
    return redirect(url_for('listar_regras'))
