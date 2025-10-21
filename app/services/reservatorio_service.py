from app import db


def cadastrar_reservatorio(reservatorio):
    db.session.add(reservatorio)
    db.session.commit()
    return reservatorio