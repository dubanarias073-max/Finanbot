"""Pruebas de RNF de seguridad (Taller 6): hash de contraseñas y control de acceso."""
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from application.services.auth_service import AuthService  # noqa: E402
from database import Base, get_db  # noqa: E402
from models import Usuario  # noqa: E402
from presentation.api import create_app  # noqa: E402


@pytest.fixture()
def cliente():
    motor = create_engine(
        'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=motor)
    fabrica = sessionmaker(bind=motor)

    def _db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    app = create_app()
    app.dependency_overrides[get_db] = _db
    yield TestClient(app), fabrica
    motor.dispose()


def test_contrasena_se_guarda_con_bcrypt_y_nunca_en_texto_plano(cliente):
    _, fabrica = cliente
    with fabrica() as db:
        AuthService.registrar(
            db, nombre='Ana', correo='ana-rnf@example.com', contrasena='Clave#12345',
            pregunta_seguridad='¿Color favorito?', respuesta_seguridad='azul',
        )
        usuario = db.query(Usuario).filter_by(correo='ana-rnf@example.com').one()
        assert usuario.contrasena_hash.startswith('$2')
        assert 'Clave#12345' not in usuario.contrasena_hash


@pytest.mark.parametrize('ruta', [
    '/api/transacciones/',
    '/api/metas/',
    '/api/recomendaciones/',
    '/api/perfil/',
    '/api/chat-historial/conversaciones',
    '/api/chat/adjuntos/00000000-0000-0000-0000-000000000000',
])
def test_endpoints_protegidos_rechazan_peticiones_sin_token(cliente, ruta):
    http, _ = cliente
    assert http.get(ruta).status_code == 401


def test_endpoints_protegidos_rechazan_token_invalido(cliente):
    http, _ = cliente
    respuesta = http.get('/api/metas/', headers={'Authorization': 'Bearer token-falso'})
    assert respuesta.status_code == 401
    respuesta = http.post(
        '/api/chat/adjuntos/url',
        headers={'Authorization': 'Bearer token-falso'},
        json={'url': 'https://ejemplo.com/a.png'},
    )
    assert respuesta.status_code == 401
