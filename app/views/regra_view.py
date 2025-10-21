from flask import render_template, redirect, url_for, flash
from app import app, db
from app.models.regra_model import Regra
from app.models.condicao_model import Condicao
from app.models.acao_model import Acao
from app.models.regra_form import RegraForm

@app.route('/regras/editor', methods=['GET', 'POST'])
def editor_regras():
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
            return redirect(url_for('editor_regras')) # Redireciona para a mesma página ou uma lista de regras
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar a regra: {e}', 'danger')

    return render_template('regras/editor.html', form=form, title='Editor de Regras')
