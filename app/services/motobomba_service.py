from app import db


def cadastrar_motobomba(motobomba):
    db.session.add(motobomba)
    db.session.commit()
    return motobomba