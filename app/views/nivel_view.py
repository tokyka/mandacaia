from app import app
from app import db
from flask import request, redirect, render_template, url_for
from ..models import nivel_model


@app.route('/lista_niveis')
def levels_list():
    return render_template("lista_niveis.html", niveis=nivel_model.Nivel.query.all())