import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from models import Base, MetaAhorro, Transaccion, Usuario
from routes.chat_route import _agregar_avisos_metas
from routes.metas import MetaCreate, crear_meta, obtener_metas, obtener_metas_calculadas
from routes.recomendaciones import obtener_recomendaciones
from timezone import bogota_today


@pytest.fixture
def db_sessions():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine)
    try:
        yield sessions
    finally:
        engine.dispose()


def _usuario(db):
    user = Usuario(
        nombre='Usuario de prueba',
        correo='metas@example.com',
        contrasena_hash='hash',
    )
    db.add(user)
    db.commit()
    return user


def test_guarda_tipo_de_meta_y_calcula_limites_desde_transacciones_historicas(db_sessions):
    hoy = bogota_today()
    inicio_mes = hoy.replace(day=1)
    gasto_mes_anterior = inicio_mes - timedelta(days=1)
    inicio_anio = hoy.replace(month=1, day=1)
    gasto_anio_anterior = inicio_anio - timedelta(days=1)
    gasto_anual_esperado = 250_000 + (75_000 if gasto_mes_anterior.year == hoy.year else 0)

    with db_sessions() as db:
        usuario = _usuario(db)
        db.add_all([
            MetaAhorro(
                usuario_id=usuario.id,
                nombre='Octubre',
                monto_objetivo=1_000_000,
                tipo='gasto_mensual',
            ),
            MetaAhorro(
                usuario_id=usuario.id,
                nombre='Año',
                monto_objetivo=50_000_000,
                tipo='gasto_anual',
            ),
            Transaccion(
                usuario_id=usuario.id,
                categoria='Alimentación',
                tipo='gasto',
                monto=250_000,
                fecha=hoy,
            ),
            Transaccion(
                usuario_id=usuario.id,
                categoria='Alimentación',
                tipo='gasto',
                monto=75_000,
                fecha=gasto_mes_anterior,
            ),
            Transaccion(
                usuario_id=usuario.id,
                categoria='Alimentación',
                tipo='gasto',
                monto=100_000,
                fecha=gasto_anio_anterior,
            ),
            Transaccion(
                usuario_id=usuario.id,
                categoria='Alimentación',
                tipo='gasto',
                monto=500_000,
                fecha=hoy + timedelta(days=1),
            ),
            Transaccion(
                usuario_id=usuario.id,
                categoria='Alimentación',
                tipo='gasto',
                monto=900_000,
                descripcion='__manual_meta_3__',
                fecha=hoy,
            ),
        ])
        db.commit()
        user_id = str(usuario.id)

    with db_sessions() as db:
        result = obtener_metas(user_id, db)

    by_type = {meta['tipo']: meta for meta in result}
    assert by_type['gasto_mensual']['monto_actual'] == 250_000
    assert by_type['gasto_mensual']['periodo'] == hoy.strftime('%Y-%m')
    assert by_type['gasto_anual']['monto_actual'] == gasto_anual_esperado
    assert by_type['gasto_anual']['periodo'] == str(hoy.year)
    with db_sessions() as db:
        assert db.query(Transaccion).count() == 5


def test_crea_meta_de_ahorro_por_compatibilidad_y_rechaza_tipo_invalido(db_sessions):
    with db_sessions() as db:
        usuario = _usuario(db)
        created = crear_meta(
            MetaCreate(
                nombre='Viaje',
                monto_objetivo=2_000_000,
                monto_actual=100_000,
                fecha_limite=(bogota_today() + timedelta(days=90)).isoformat(),
                modo='automatico',
                monto_automatico=150_000,
                dia_automatico=5,
                icono='✈️',
                categoria='viaje',
                prioridad='alta',
            ),
            str(usuario.id),
            db,
        )
        stored = db.query(MetaAhorro).filter_by(id=created['id']).one()
        assert stored.tipo == 'ahorro'
        assert stored.icono == '✈️'
        assert stored.categoria == 'viaje'
        assert stored.prioridad == 'alta'
        assert stored.monto_actual == 100_000
        assert stored.modo == 'automatico'
        serialized = obtener_metas_calculadas(usuario.id, db)[0]
        assert serialized['icono'] == '✈️'
        assert serialized['categoria'] == 'viaje'
        assert serialized['prioridad'] == 'alta'

        with pytest.raises(HTTPException) as error:
            crear_meta(
                MetaCreate(nombre='Inválida', monto_objetivo=1_000, tipo='gasto'),
                str(usuario.id),
                db,
            )

    assert error.value.status_code == 400


def test_informa_cuando_el_gasto_supera_el_limite(db_sessions):
    with db_sessions() as db:
        usuario = _usuario(db)
        db.add(MetaAhorro(
            usuario_id=usuario.id,
            nombre='Presupuesto del mes',
            tipo='gasto_mensual',
            monto_objetivo=100_000,
        ))
        db.add(Transaccion(
            usuario_id=usuario.id,
            categoria='Alimentación',
            tipo='gasto',
            monto=120_000,
            fecha=bogota_today(),
        ))
        db.commit()
        user_id = str(usuario.id)

    with db_sessions() as db:
        meta = obtener_metas(user_id, db)[0]

    assert meta['excedida'] is True
    assert meta['disponible'] == -20_000


def test_alcanzar_el_tope_de_gasto_tambien_genera_alerta(db_sessions):
    with db_sessions() as db:
        usuario = _usuario(db)
        db.add(MetaAhorro(
            usuario_id=usuario.id,
            nombre='Tope mensual',
            tipo='gasto_mensual',
            monto_objetivo=100_000,
        ))
        db.add(Transaccion(
            usuario_id=usuario.id,
            categoria='Alimentación',
            tipo='gasto',
            monto=100_000,
            fecha=bogota_today(),
        ))
        db.commit()
        meta = obtener_metas(str(usuario.id), db)[0]

    assert meta['excedida'] is True
    assert meta['disponible'] == 0


def test_completar_meta_de_ahorro_se_muestra_como_logro(db_sessions):
    with db_sessions() as db:
        usuario = _usuario(db)
        db.add(MetaAhorro(
            usuario_id=usuario.id,
            nombre='Ahorro para viaje',
            tipo='ahorro',
            monto_objetivo=500_000,
            monto_actual=500_000,
            completada=False,
        ))
        db.commit()
        meta = obtener_metas(str(usuario.id), db)[0]

    assert meta['completada'] is True
    assert meta['excedida'] is False


def test_chat_advierte_limites_y_felicita_solo_ahorro_completado():
    contexto = {
        'limites_gasto_excedidos': [{
            'nombre': 'Tope anual', 'tipo': 'gasto_anual',
            'monto_actual': 1_100_000, 'monto_objetivo': 1_000_000,
        }],
        'metas': [{'id': 7, 'nombre': 'Viaje', 'objetivo': 500_000}],
    }
    respuesta = _agregar_avisos_metas(
        'Respuesta de FinanBot.',
        contexto,
        {'tipo': 'meta_abonada', 'id': 7, 'nombre': 'Viaje', 'nuevo_total': 500_000},
    )

    assert 'Límite de gasto alcanzado o superado' in respuesta
    assert 'no es una felicitación' in respuesta
    assert '¡Felicitaciones! Completaste tu meta de ahorro' in respuesta


def test_recomendaciones_trata_tope_de_gasto_alcanzado_como_alerta(db_sessions):
    with db_sessions() as db:
        usuario = _usuario(db)
        db.add(MetaAhorro(
            usuario_id=usuario.id,
            nombre='Tope del mes',
            tipo='gasto_mensual',
            monto_objetivo=100_000,
        ))
        db.add(Transaccion(
            usuario_id=usuario.id,
            categoria='Alimentación',
            tipo='gasto',
            monto=100_000,
            fecha=bogota_today(),
        ))
        db.commit()

        recomendaciones = obtener_recomendaciones(str(usuario.id), db=db)

    alertas = [item for item in recomendaciones if item['tipo'] == 'alerta']
    assert any('Límite de gasto mensual alcanzado' in item['titulo'] for item in alertas)
    assert not any('Tope del mes' in item['titulo'] and item['tipo'] == 'exito' for item in recomendaciones)
