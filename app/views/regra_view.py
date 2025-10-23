from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models.regra_model import Regra
from app.models.condicao_model import Condicao
from app.models.acao_model import Acao
from app.models.regra_form import RegraForm, AcaoForm
from app.models.motobomba_model import Motobomba

@app.route('/regras_modbus/lista')
def listar_regras():
    regras = Regra.query.all()
    return render_template('lista_regras.html', regras=regras, title='Lista de Regras')

@app.route('/regras_modbus/criar', methods=['GET', 'POST'])
def criar_regra():
    motobombas = Motobomba.query.all()
    motobomba_choices = [(mb.id, mb.nome) for mb in motobombas]
    AcaoForm.registrador_alvo.kwargs = {'choices': motobomba_choices}
    form = RegraForm()

    if form.validate_on_submit():
        # Cleanup class modification
        del AcaoForm.registrador_alvo.kwargs['choices']
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
                registrador_alvo = acao_form.registrador_alvo.data if acao_form.tipo_acao.data in ['Ligar_Motobomba', 'Desligar_Motobomba'] else acao_form.registrador_alvo_texto.data
                nova_acao = Acao(
                    tipo_acao=acao_form.tipo_acao.data,
                    registrador_alvo=registrador_alvo,
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

    # Cleanup class modification
    if 'choices' in AcaoForm.registrador_alvo.kwargs:
        del AcaoForm.registrador_alvo.kwargs['choices']
    return render_template('editor_regras.html', form=form, title='Criar Nova Regra', action_url=url_for('criar_regra'))

@app.route('/regras_modbus/editar/<int:regra_id>', methods=['GET', 'POST'])
def editar_regra(regra_id):
    regra = Regra.query.get_or_404(regra_id)
    motobombas = Motobomba.query.all()
    motobomba_choices = [(mb.id, mb.nome) for mb in motobombas]
    
    # Hack to set choices on the nested form
    AcaoForm.registrador_alvo.kwargs = {'choices': motobomba_choices}

    form = RegraForm(obj=regra)

    if form.validate_on_submit():
        try:
            regra.nome = form.nome.data
            regra.descricao = form.descricao.data
            regra.habilitada = form.habilitada.data

            # Clear existing collections before adding new ones
            regra.condicoes = []
            regra.acoes = []
            db.session.flush() # Apply the clear operation

            for condicao_data in form.condicoes.data:
                regra.condicoes.append(Condicao(**condicao_data))

            for acao_data in form.acoes.data:
                if acao_data['tipo_acao'] in ['Ligar_Motobomba', 'Desligar_Motobomba']:
                    acao_data['registrador_alvo'] = acao_data['registrador_alvo']
                else:
                    acao_data['registrador_alvo'] = acao_data['registrador_alvo_texto']
                
                if 'registrador_alvo_texto' in acao_data:
                    del acao_data['registrador_alvo_texto']

                regra.acoes.append(Acao(**acao_data))

            db.session.commit()
            flash('Regra atualizada com sucesso!', 'success')
            return redirect(url_for('listar_regras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a regra: {e}', 'danger')
        finally:
            # Clean up the class-level kwargs
            if 'choices' in AcaoForm.registrador_alvo.kwargs:
                del AcaoForm.registrador_alvo.kwargs['choices']
    else:
        # For GET request or validation failure, ensure choices are set
        for acao_form in form.acoes:
            acao_form.registrador_alvo.choices = motobomba_choices

    # Cleanup for GET request if not submitting
    if request.method == 'GET' and 'choices' in AcaoForm.registrador_alvo.kwargs:
         del AcaoForm.registrador_alvo.kwargs['choices']

    return render_template('editor_regras.html', form=form, title='Editar Regra', regra=regra, action_url=url_for('editar_regra', regra_id=regra.id))

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
