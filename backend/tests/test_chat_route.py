import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from routes.chat_route import obtener_o_crear_categoria
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Categoria


def test_crea_categoria_si_no_existe():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        categoria = obtener_o_crear_categoria(db, 'Alimentación', 'gasto', '🍔')
        assert categoria is not None
        assert categoria.nombre == 'Alimentación'
        assert categoria.tipo == 'gasto'
        assert db.query(Categoria).count() == 1
    finally:
        db.close()
