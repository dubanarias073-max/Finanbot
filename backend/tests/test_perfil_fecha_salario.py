import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Base, Usuario
from routes.perfil import PerfilUpdate, actualizar_perfil


def test_perfil_update_accepts_fecha_salario():
    payload = PerfilUpdate(nombre='Ana', ingreso_mensual=2500000, fecha_salario='2026-08-20')

    assert payload.nombre == 'Ana'
    assert payload.ingreso_mensual == 2500000
    assert payload.fecha_salario == '2026-08-20'


@pytest.mark.parametrize('rol', ['estudiante', 'empleado', 'independiente', 'emprendedor'])
def test_onboarding_exige_ingreso_mensual_y_permite_dia_de_pago_sin_definir(rol):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    usuario = Usuario(
        nombre='Ana',
        correo=f'{rol}@example.com',
        contrasena_hash='hash',
        fecha_salario=date(2026, 8, 20),
    )
    db.add(usuario)
    db.commit()

    try:
        actualizar_perfil(
            PerfilUpdate(
                rol=rol,
                ingreso_mensual=10000,
                fecha_salario=None,
                onboarding_completado=True,
            ),
            str(usuario.id),
            db,
        )

        db.refresh(usuario)
        assert float(usuario.ingreso_mensual) == 10000
        assert usuario.fecha_salario is None
        assert usuario.onboarding_completado is True
    finally:
        db.close()
        engine.dispose()


def test_onboarding_rechaza_ingreso_mensual_vacio_o_menor_al_minimo():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    usuario = Usuario(
        nombre='Ana',
        correo='sin-ingreso@example.com',
        contrasena_hash='hash',
    )
    db.add(usuario)
    db.commit()

    try:
        with pytest.raises(HTTPException) as error:
            actualizar_perfil(
                PerfilUpdate(onboarding_completado=True),
                str(usuario.id),
                db,
            )
        assert error.value.status_code == 400

        with pytest.raises(HTTPException) as error:
            actualizar_perfil(
                PerfilUpdate(ingreso_mensual=0),
                str(usuario.id),
                db,
            )
        assert error.value.status_code == 400
    finally:
        db.close()
        engine.dispose()
