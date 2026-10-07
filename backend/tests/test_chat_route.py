import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Categoria, sembrar_categorias


def test_siembra_categorias_y_es_idempotente():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        sembrar_categorias(db)
        total = db.query(Categoria).count()
        sembrar_categorias(db)

        categoria = db.query(Categoria).filter_by(nombre='Alimentación').one()
        assert categoria.tipo == 'gasto'
        assert categoria.icono == '🍔'
        assert db.query(Categoria).count() == total
    finally:
        db.close()
