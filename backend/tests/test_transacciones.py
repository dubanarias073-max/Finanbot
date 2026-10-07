import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from models import Base, Categoria, Tienda, Transaccion, Usuario
from routes.transacciones import eliminar_transaccion


@pytest.fixture
def db_sessions():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine)
    try:
        yield sessions
    finally:
        engine.dispose()


def test_eliminar_transaccion_persiste_el_borrado_en_base_de_datos(db_sessions):
    with db_sessions() as db:
        db.add(Usuario(
            nombre='Usuario de prueba',
            correo='transacciones@example.com',
            contrasena_hash='hash',
        ))
        db.add(Categoria(nombre='Alimentación', tipo='gasto', icono='🍔'))
        db.commit()
        usuario = db.query(Usuario).filter_by(correo='transacciones@example.com').one()
        transaccion = Transaccion(
            usuario_id=usuario.id,
            categoria='Alimentación',
            tipo='gasto',
            monto=25000,
            fecha=date(2026, 10, 14),
        )
        db.add(transaccion)
        db.commit()
        transaccion_id = transaccion.id
        usuario_id = str(usuario.id)

    with db_sessions() as db:
        resultado = eliminar_transaccion(transaccion_id, usuario_id, db)
        assert resultado['mensaje'] == '✅ Transacción eliminada!'

    with db_sessions() as db:
        assert db.query(Transaccion).filter_by(id=transaccion_id).first() is None


def test_no_elimina_transaccion_de_otro_usuario(db_sessions):
    with db_sessions() as db:
        db.add(Usuario(
            nombre='Dueño',
            correo='dueno@example.com',
            contrasena_hash='hash',
        ))
        db.add(Usuario(
            nombre='Otro usuario',
            correo='otro@example.com',
            contrasena_hash='hash',
        ))
        db.add(Categoria(nombre='Alimentación', tipo='gasto', icono='🍔'))
        db.commit()
        dueno = db.query(Usuario).filter_by(correo='dueno@example.com').one()
        otro = db.query(Usuario).filter_by(correo='otro@example.com').one()
        transaccion = Transaccion(
            usuario_id=dueno.id,
            categoria='Alimentación',
            tipo='gasto',
            monto=25000,
            fecha=date(2026, 10, 14),
        )
        db.add(transaccion)
        db.commit()
        transaccion_id = transaccion.id

        with pytest.raises(HTTPException) as error:
            eliminar_transaccion(transaccion_id, str(otro.id), db)

        assert error.value.status_code == 404
        assert db.query(Transaccion).filter_by(id=transaccion_id).first() is not None


def test_elimina_tienda_si_era_la_ultima_transaccion_asociada(db_sessions):
    with db_sessions() as db:
        usuario = Usuario(
            nombre='Usuario de prueba',
            correo='tienda-huerfana@example.com',
            contrasena_hash='hash',
        )
        db.add(usuario)
        db.add(Categoria(nombre='Alimentación', tipo='gasto', icono='🍔'))
        db.commit()
        tienda = Tienda(
            usuario_id=usuario.id,
            nombre='Tienda de prueba',
            latitud=4.65,
            longitud=-74.06,
        )
        db.add(tienda)
        db.commit()
        transaccion = Transaccion(
            usuario_id=usuario.id,
            categoria='Alimentación',
            tipo='gasto',
            monto=25000,
            fecha=date(2026, 10, 14),
            tienda_id=tienda.id,
        )
        db.add(transaccion)
        db.commit()
        transaccion_id = transaccion.id
        tienda_id = tienda.id
        usuario_id = str(usuario.id)

    with db_sessions() as db:
        eliminar_transaccion(transaccion_id, usuario_id, db)

    with db_sessions() as db:
        assert db.query(Transaccion).filter_by(id=transaccion_id).first() is None
        assert db.query(Tienda).filter_by(id=tienda_id).first() is None


def test_conserva_tienda_si_otras_transacciones_siguen_asociadas(db_sessions):
    with db_sessions() as db:
        usuario = Usuario(
            nombre='Usuario de prueba',
            correo='tienda-compartida@example.com',
            contrasena_hash='hash',
        )
        db.add(usuario)
        db.add(Categoria(nombre='Alimentación', tipo='gasto', icono='🍔'))
        db.commit()
        tienda = Tienda(
            usuario_id=usuario.id,
            nombre='Tienda compartida',
            latitud=4.65,
            longitud=-74.06,
        )
        db.add(tienda)
        db.commit()
        transacciones = [
            Transaccion(
                usuario_id=usuario.id,
                categoria='Alimentación',
                tipo='gasto',
                monto=monto,
                fecha=date(2026, 10, 14),
                tienda_id=tienda.id,
            )
            for monto in (25000, 18000)
        ]
        db.add_all(transacciones)
        db.commit()
        transaccion_id = transacciones[0].id
        restante_id = transacciones[1].id
        tienda_id = tienda.id
        usuario_id = str(usuario.id)

    with db_sessions() as db:
        eliminar_transaccion(transaccion_id, usuario_id, db)

    with db_sessions() as db:
        assert db.query(Transaccion).filter_by(id=transaccion_id).first() is None
        assert db.query(Transaccion).filter_by(id=restante_id).first() is not None
        assert db.query(Tienda).filter_by(id=tienda_id).first() is not None
