"""Pruebas de las correcciones de seguridad y de lógica de metas/transacciones."""
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config
import routes.auth as auth_routes
from application.services import metas_service
from application.services.auth_service import AuthService
from models import Base, CategoriaUsuario, MetaAhorro, Transaccion, Usuario, sembrar_categorias
from routes.metas import (
    MontoBody, TotalBody, abonar_meta, ajustar_meta, eliminar_meta, retirar_meta,
)
from routes.transacciones import (
    TransaccionCreate, TransaccionUpdate, crear_transaccion, editar_transaccion, eliminar_transaccion,
)

HOY = date(2026, 11, 17)


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    sembrar_categorias(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _usuario(db, **extra):
    u = Usuario(nombre='Ana', correo=f'ana{len(extra)}@example.com', contrasena_hash='x', **extra)
    db.add(u)
    db.commit()
    return u


def _meta(db, uid, **extra):
    datos = dict(usuario_id=uid, nombre='🏖️ Viaje', monto_objetivo=1_000_000, monto_actual=0, tipo='ahorro')
    datos.update(extra)
    m = MetaAhorro(**datos)
    db.add(m)
    db.commit()
    return m


def _movs(db, uid):
    return db.query(Transaccion).filter_by(usuario_id=uid).order_by(Transaccion.id).all()


# ── Metas: operaciones atómicas en el servidor ─────────────────────

def test_abonar_suma_a_la_meta_y_registra_el_gasto(db):
    u = _usuario(db)
    m = _meta(db, u.id)
    r = abonar_meta(m.id, MontoBody(monto=200_000), str(u.id), db)
    assert r['nuevo_total'] == 200_000
    movs = _movs(db, u.id)
    assert [(t.tipo, t.categoria, float(t.monto), t.descripcion) for t in movs] == [
        ('gasto', 'Aporte manual a meta', 200_000, f'__manual_meta_{m.id}__')]
    with pytest.raises(HTTPException):
        abonar_meta(m.id, MontoBody(monto=-5), str(u.id), db)


def test_ajustar_hacia_abajo_separa_este_mes_de_meses_anteriores(db):
    u = _usuario(db)
    m = _meta(db, u.id, monto_actual=500_000)            # 500 mil de meses anteriores
    metas_service.abonar(db, u.id, m, 100_000, HOY)      # 100 mil este mes
    r = metas_service.ajustar_total(db, u.id, m, 350_000, HOY)  # retira 250 mil
    assert r['devuelto_este_mes'] == 100_000
    assert r['devuelto_meses_anteriores'] == 150_000
    ajustes = [(t.tipo, float(t.monto)) for t in _movs(db, u.id) if 'ajuste' in t.descripcion]
    assert ajustes == [('gasto', -100_000), ('ingreso', 150_000)]
    assert float(m.monto_actual) == 350_000


def test_ajustar_a_cero_es_valido_y_negativo_no(db):
    u = _usuario(db)
    m = _meta(db, u.id, monto_actual=10_000)
    assert ajustar_meta(m.id, TotalBody(nuevo_total=0), str(u.id), db)['nuevo_monto'] == 0
    with pytest.raises(HTTPException):
        ajustar_meta(m.id, TotalBody(nuevo_total=-1), str(u.id), db)


def test_eliminar_meta_borra_sus_movimientos_y_otro_usuario_no_puede(db):
    u = _usuario(db)
    otro = _usuario(db, rol='empleado')
    m = _meta(db, u.id)
    metas_service.abonar(db, u.id, m, 50_000, HOY)
    with pytest.raises(HTTPException):
        eliminar_meta(m.id, str(otro.id), db)
    eliminar_meta(m.id, str(u.id), db)
    assert db.query(MetaAhorro).count() == 0
    assert _movs(db, u.id) == []


def test_retirar_solo_metas_completadas(db):
    u = _usuario(db)
    m = _meta(db, u.id, monto_actual=100)
    with pytest.raises(HTTPException):
        retirar_meta(m.id, str(u.id), db)
    metas_service.ajustar_total(db, u.id, m, 1_000_000, HOY)
    assert retirar_meta(m.id, str(u.id), db)['devuelto'] == 1_000_000


# ── Automáticos en el servidor ──────────────────────────────────────

def test_aporte_automatico_una_vez_por_mes_y_dia_31_en_noviembre(db):
    u = _usuario(db)
    m = _meta(db, u.id, modo='automatico', monto_automatico=150_000, dia_automatico=31,
              fecha_creacion=datetime(2026, 10, 1))
    assert metas_service.procesar_automaticos(db, u.id, date(2026, 11, 29))['aportes'] == []
    r = metas_service.procesar_automaticos(db, u.id, date(2026, 11, 30))   # noviembre tiene 30 días
    assert r['aportes'][0]['aporte'] == 150_000
    metas_service.procesar_automaticos(db, u.id, date(2026, 11, 30))
    auto = [t for t in _movs(db, u.id) if t.descripcion == f'__auto_meta_{m.id}__']
    assert len(auto) == 1 and auto[0].fecha == date(2026, 11, 30)
    assert float(m.monto_actual) == 150_000


def test_aporte_automatico_no_pasa_del_objetivo(db):
    u = _usuario(db)
    m = _meta(db, u.id, monto_actual=950_000, modo='automatico', monto_automatico=200_000,
              dia_automatico=5, fecha_creacion=datetime(2026, 10, 1))
    metas_service.procesar_automaticos(db, u.id, HOY)
    assert float(m.monto_actual) == 1_000_000 and m.completada


def test_salario_automatico_respeta_dia_y_no_duplica(db):
    u = _usuario(db, ingreso_mensual=2_500_000, fecha_salario=date(2026, 1, 20))
    metas_service.procesar_automaticos(db, u.id, date(2026, 11, 19))
    assert _movs(db, u.id) == []
    metas_service.procesar_automaticos(db, u.id, date(2026, 11, 20))
    metas_service.procesar_automaticos(db, u.id, date(2026, 11, 25))
    salarios = [t for t in _movs(db, u.id) if t.descripcion == '__auto_salario__']
    assert len(salarios) == 1 and float(salarios[0].monto) == 2_500_000
    assert salarios[0].categoria == 'Salario'


def test_salario_usa_otros_ingresos_si_salario_esta_oculta(db):
    u = _usuario(db, ingreso_mensual=1_000_000, fecha_salario=date(2026, 1, 1))
    db.add(CategoriaUsuario(usuario_id=u.id, nombre='Salario', tipo='ingreso', personalizada=False))
    db.commit()
    metas_service.procesar_automaticos(db, u.id, HOY)
    assert _movs(db, u.id)[0].categoria == 'Otros ingresos'


# ── Transacciones: validaciones ─────────────────────────────────────

def _crear(db, uid, **campos):
    datos = dict(tipo='gasto', categoria='Alimentación', monto=10_000, fecha='2026-11-10')
    datos.update(campos)
    return crear_transaccion(TransaccionCreate(**datos), str(uid), db)


def test_no_acepta_montos_negativos_ni_etiquetas_internas(db):
    u = _usuario(db)
    with pytest.raises(HTTPException):
        _crear(db, u.id, monto=-50_000)
    with pytest.raises(HTTPException):
        _crear(db, u.id, descripcion='__auto_salario__', tipo='ingreso', categoria='Salario')
    with pytest.raises(HTTPException):
        _crear(db, u.id, descripcion='__manual_meta_3__')


def test_movimientos_de_meta_no_se_editan_ni_borran_sueltos(db):
    u = _usuario(db)
    m = _meta(db, u.id)
    metas_service.abonar(db, u.id, m, 50_000, HOY)
    t = _movs(db, u.id)[0]
    with pytest.raises(HTTPException):
        editar_transaccion(t.id, TransaccionUpdate(monto=1), str(u.id), db)
    with pytest.raises(HTTPException):
        eliminar_transaccion(t.id, str(u.id), db)


# ── Seguridad ────────────────────────────────────────────────────────

def test_textos_guardados_no_pueden_contener_html(db):
    u = _usuario(db)
    m = _meta(db, u.id, nombre='<img src=x onerror=alert(1)>Viaje')
    assert '<' not in m.nombre and '>' not in m.nombre
    assert 'Viaje' in m.nombre


def test_claves_secretas_no_usan_valores_conocidos(monkeypatch, tmp_path):
    monkeypatch.setattr(config, '_ARCHIVO_CLAVES_LOCALES', tmp_path / 'claves.json')
    monkeypatch.setenv('JWT_SECRET_KEY', 'finanbot_jwt_secret_2026')
    monkeypatch.delenv('FINANBOT_ENV', raising=False)
    generada = config._clave_secreta('JWT_SECRET_KEY')
    assert generada != 'finanbot_jwt_secret_2026' and len(generada) >= 32
    assert config._clave_secreta('JWT_SECRET_KEY') == generada            # estable entre reinicios
    monkeypatch.setenv('FINANBOT_ENV', 'produccion')
    with pytest.raises(RuntimeError):
        config._clave_secreta('JWT_SECRET_KEY')


def test_cors_no_permite_cualquier_origen():
    assert '*' not in config.settings.CORS_ORIGINS


def _request(ip='10.0.0.1'):
    return Request({'type': 'http', 'method': 'POST', 'path': '/api/auth/login', 'headers': [],
                    'client': (ip, 1234), 'query_string': b''})


def test_login_bloquea_tras_intentos_fallidos(db, monkeypatch):
    monkeypatch.setattr(auth_routes, '_intentos_login', {})
    AuthService.registrar(db, nombre='Ana', correo='ana@example.com', contrasena='Secreta123')
    for _ in range(config.settings.LOGIN_MAX_INTENTOS):
        assert auth_routes._autenticar_con_limite(db, 'ana@example.com', 'mala', _request()) is None
    with pytest.raises(HTTPException) as error:
        auth_routes._autenticar_con_limite(db, 'ana@example.com', 'Secreta123', _request())
    assert error.value.status_code == 429


def test_login_correcto_reinicia_el_contador(db, monkeypatch):
    monkeypatch.setattr(auth_routes, '_intentos_login', {})
    AuthService.registrar(db, nombre='Ana', correo='ana@example.com', contrasena='Secreta123')
    for _ in range(config.settings.LOGIN_MAX_INTENTOS - 1):
        auth_routes._autenticar_con_limite(db, 'ana@example.com', 'mala', _request())
    assert auth_routes._autenticar_con_limite(db, 'ana@example.com', 'Secreta123', _request())
    assert auth_routes._autenticar_con_limite(db, 'ana@example.com', 'mala', _request()) is None
    assert auth_routes._autenticar_con_limite(db, 'ana@example.com', 'Secreta123', _request())


# ── IA: memoria persistente y métricas ──────────────────────────────

def test_memoria_de_la_ia_se_recupera_desde_la_base_de_datos(db, monkeypatch):
    import finanbot_ia_2
    from models import Chat
    from routes.chat_route import _hidratar_memoria_desde_bd
    monkeypatch.setattr(finanbot_ia_2, '_memoria', {})
    u = _usuario(db)
    conv = '11111111-1111-1111-1111-111111111111'
    db.add_all([Chat(usuario_id=u.id, conversacion_id=conv, mensaje='Gano 2 millones', respuesta='Anotado'),
                Chat(usuario_id=u.id, conversacion_id=conv, mensaje='¿Cuánto ahorro?', respuesta='El 20%')])
    db.commit()
    _hidratar_memoria_desde_bd(db, u.id, conv, f'conv:{conv}')
    assert list(finanbot_ia_2._memoria[f'conv:{conv}']) == [
        ('user', 'Gano 2 millones'), ('bot', 'Anotado'), ('user', '¿Cuánto ahorro?'), ('bot', 'El 20%')]


def test_metricas_de_la_ia(monkeypatch):
    import finanbot_ia_2
    from collections import deque
    monkeypatch.setattr(finanbot_ia_2, '_metricas', deque(maxlen=200))
    finanbot_ia_2.registrar_metrica('responder', {'tipo': 'openai', 'modelo': 'm1'}, 'alto', 'chat', 3.2, ok=True)
    finanbot_ia_2.registrar_metrica('responder', {'tipo': 'openai', 'modelo': 'm1'}, 'bajo', 'chat', 0, ok=False)
    r = finanbot_ia_2.resumen_metricas()
    assert r['total'] == 2 and r['exitosas'] == 1 and r['por_modelo'] == {'m1': 1}


# ── API: rutas que fallaban ─────────────────────────────────────────

def test_descargas_aceptan_nombres_con_tildes():
    from archivos_util import cabecera_descarga
    cabecera = cabecera_descarga('FinanBot_Ana_María_Muñoz.xlsx')['Content-Disposition']
    cabecera.encode('latin-1')                                  # una cabecera HTTP válida
    assert 'filename="FinanBot_Ana_Maria_Munoz.xlsx"' in cabecera
    assert "filename*=UTF-8''FinanBot_Ana_Mar%C3%ADa_Mu%C3%B1oz.xlsx" in cabecera


def test_ruta_calendario_disponibles_no_choca_con_anio_mes():
    from sqlalchemy.pool import StaticPool
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from database import get_db
    from extensions import obtener_usuario_id_requerido
    from routes.calendario import router
    u = _usuario(db)
    app = FastAPI()
    app.include_router(router, prefix='/api/calendario')
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[obtener_usuario_id_requerido] = lambda: str(u.id)
    with TestClient(app) as cliente:
        assert cliente.get('/api/calendario/disponibles/2026').status_code == 200
        assert cliente.get('/api/calendario/2026/11').status_code == 200
    db.close()
    engine.dispose()


def test_swagger_agrupa_todas_las_rutas():
    import presentation.api as api
    spec = api.create_app().openapi()
    sin_grupo = [p for p, ops in spec['paths'].items() if p.startswith('/api')
                 for o in ops.values() if not o.get('tags')]
    assert sin_grupo == []
    assert spec['components']['schemas']['MetaCreate']['examples']
