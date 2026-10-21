import re
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

sys.path.append(str(Path(__file__).resolve().parents[1]))

import routes.auth as auth_routes
from application.services.auth_service import AuthService
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from models import Base, LoginAlertToken, PasswordResetCode, PasswordResetLink, Usuario


def _crear_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)()


def _crear_request(origin=None, host='finanbot.example'):
    headers = [(b'host', host.encode())]
    if origin:
        headers.append((b'origin', origin.encode()))
    return Request({
        'type': 'http',
        'http_version': '1.1',
        'method': 'POST',
        'scheme': 'https',
        'server': (host, 443),
        'client': ('127.0.0.1', 12345),
        'root_path': '',
        'path': '/api/auth/login',
        'raw_path': b'/api/auth/login',
        'query_string': b'',
        'headers': headers,
    })


def test_registro_normaliza_correo_y_login_tolera_mayusculas():
    engine, db = _crear_db()
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='  Usuario@Gmail.com ',
            contrasena='Secreta123',
        )

        assert usuario.correo == 'usuario@gmail.com'
        assert AuthService.autenticar(
            db,
            correo='USUARIO@gmail.com',
            contrasena='Secreta123',
        ) == usuario
    finally:
        db.close()
        engine.dispose()


def test_pregunta_seguridad_permite_recuperar_sin_acceso_al_correo():
    engine, db = _crear_db()
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@correo.com',
            contrasena='Secreta123',
            pregunta_seguridad='¿En qué ciudad naciste?',
            respuesta_seguridad='  San   Andrés ',
        )
        assert usuario.respuesta_seguridad != '  San   Andrés '

        pregunta = auth_routes.obtener_pregunta_seguridad(
            auth_routes.PreguntaSeguridadSchema(correo='USUARIO@correo.com'),
            db,
        )
        assert pregunta['pregunta_seguridad'] == '¿En qué ciudad naciste?'

        respuesta = auth_routes.restablecer_con_pregunta(
            auth_routes.RestablecerConPreguntaSchema(
                correo='usuario@correo.com',
                respuesta_seguridad='san andrés',
                nueva_contrasena='NuevaClave123',
            ),
            db,
        )
        assert 'actualizada' in respuesta['mensaje']
        assert AuthService.autenticar(
            db,
            correo='usuario@correo.com',
            contrasena='NuevaClave123',
        ) == usuario
    finally:
        db.close()
        engine.dispose()


def test_pregunta_seguridad_bloquea_tras_cinco_respuestas_incorrectas():
    engine, db = _crear_db()
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@correo.com',
            contrasena='Secreta123',
            pregunta_seguridad='¿En qué ciudad naciste?',
            respuesta_seguridad='Bogotá',
        )
        body = auth_routes.RestablecerConPreguntaSchema(
            correo='usuario@correo.com',
            respuesta_seguridad='respuesta incorrecta',
            nueva_contrasena='NuevaClave123',
        )

        for _ in range(5):
            with pytest.raises(HTTPException) as error:
                auth_routes.restablecer_con_pregunta(body, db)
            assert error.value.status_code == 400

        with pytest.raises(HTTPException) as error:
            auth_routes.restablecer_con_pregunta(
                auth_routes.RestablecerConPreguntaSchema(
                    correo='usuario@correo.com',
                    respuesta_seguridad='Bogotá',
                    nueva_contrasena='NuevaClave123',
                ),
                db,
            )
        assert error.value.status_code == 429
        assert AuthService.autenticar(
            db,
            correo=usuario.correo,
            contrasena='Secreta123',
        ) == usuario
    finally:
        db.close()
        engine.dispose()


def test_pregunta_seguridad_acepta_respuesta_legacy_y_la_protege():
    engine, db = _crear_db()
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@correo.com',
            contrasena='Secreta123',
            pregunta_seguridad='¿En qué ciudad naciste?',
            respuesta_seguridad='Bogotá',
        )
        usuario.respuesta_seguridad = 'Bogotá'
        db.commit()

        auth_routes.restablecer_con_pregunta(
            auth_routes.RestablecerConPreguntaSchema(
                correo='usuario@correo.com',
                respuesta_seguridad='bogotá',
                nueva_contrasena='NuevaClave123',
            ),
            db,
        )
        assert usuario.respuesta_seguridad != 'Bogotá'
        assert AuthService.autenticar(
            db,
            correo=usuario.correo,
            contrasena='NuevaClave123',
        ) == usuario
    finally:
        db.close()
        engine.dispose()


def test_codigo_de_correo_solo_permite_un_cambio_de_contrasena(monkeypatch):
    engine, db = _crear_db()
    enviado = {}
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(auth_routes.settings, 'PUBLIC_BASE_URL', 'https://finanbot.example')
    monkeypatch.setattr(
        auth_routes,
        '_enviar_codigo_recuperacion',
        lambda correo, codigo, enlace=None: enviado.update(
            correo=correo,
            codigo=codigo,
            enlace=enlace,
        ),
    )
    try:
        AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )

        auth_routes.solicitar_recuperacion(
            auth_routes.SolicitarRecuperacionSchema(correo='USUARIO@gmail.com'),
            db,
        )
        guardado = db.query(PasswordResetCode).one()
        assert enviado['correo'] == 'usuario@gmail.com'
        assert enviado['enlace'].startswith('https://finanbot.example/api/auth/restablecer-por-enlace/')
        assert guardado.code_hash != enviado['codigo']

        auth_routes.restablecer_contrasena(
            auth_routes.RestablecerContrasenaSchema(
                correo='usuario@gmail.com',
                codigo=enviado['codigo'],
                nueva_contrasena='NuevaClave123',
            ),
            db,
        )
        assert AuthService.autenticar(
            db,
            correo='usuario@gmail.com',
            contrasena='NuevaClave123',
        ) is not None
        assert db.query(PasswordResetCode).count() == 0
        with pytest.raises(HTTPException) as error:
            auth_routes.restablecer_contrasena(
                auth_routes.RestablecerContrasenaSchema(
                    correo='usuario@gmail.com',
                    codigo=enviado['codigo'],
                    nueva_contrasena='OtraClave123',
                ),
                db,
            )
        assert error.value.status_code == 400
    finally:
        db.close()
        engine.dispose()


def test_login_envia_aviso_y_reportar_acceso_revoca_sesiones(monkeypatch):
    engine, db = _crear_db()
    avisos = []
    codigos_enviados = {}
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(auth_routes.settings, 'PUBLIC_BASE_URL', 'https://finanbot.example')
    monkeypatch.setattr(auth_routes, '_enviar_correo', lambda mensaje: avisos.append(mensaje))
    monkeypatch.setattr(
        auth_routes,
        '_enviar_codigo_recuperacion',
        lambda correo, codigo, enlace=None: codigos_enviados.update(
            correo=correo,
            codigo=codigo,
            enlace=enlace,
        ),
    )
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )
        respuesta = auth_routes.login(
            auth_routes.LoginSchema(correo='usuario@gmail.com', contrasena='Secreta123'),
            _crear_request(),
            db,
        )
        mensaje = avisos.pop()
        html = next(
            part for part in mensaje.walk()
            if part.get_content_type() == 'text/html'
        ).get_content()
        assert 'Sí, fui yo' in html
        assert 'No fui yo' in html
        assert mensaje['To'] == usuario.correo
        assert 'https://finanbot.example/api/auth/acceso-seguridad/' in html
        assert db.query(LoginAlertToken).count() == 1

        token = re.search(
            r'/api/auth/acceso-seguridad/([^?"]+)\?decision=no',
            html,
        ).group(1)
        pagina = auth_routes.confirmar_pagina_acceso(token, 'no', db)
        cuerpo = pagina.body.decode()
        assert 'Reportar acceso desconocido' in cuerpo
        assert 'Ir a iniciar sesión' in cuerpo
        assert int(pagina.headers['content-length']) == len(pagina.body)
        assert usuario.requiere_cambio_contrasena is False

        from extensions import _resolver_usuario_desde_token

        assert _resolver_usuario_desde_token(
            f"Bearer {respuesta['token']}",
            db,
            requerir_usuario=True,
        ) == usuario
        pagina_cambio = auth_routes.procesar_decision_acceso(token, 'no', db)
        assert usuario.requiere_cambio_contrasena is True
        assert codigos_enviados['correo'] == usuario.correo
        cuerpo_cambio = pagina_cambio.body.decode()
        assert 'Acceso reportado y sesiones cerradas' in cuerpo_cambio
        assert 'Crea una contraseña nueva' in cuerpo_cambio
        assert 'id="nueva"' in cuerpo_cambio
        assert 'id="confirmar"' in cuerpo_cambio
        assert int(pagina_cambio.headers['content-length']) == len(pagina_cambio.body)
        with pytest.raises(HTTPException) as error:
            _resolver_usuario_desde_token(
                f"Bearer {respuesta['token']}",
                db,
                requerir_usuario=True,
            )
        assert error.value.status_code == 401
        assert AuthService.autenticar(
            db,
            correo=usuario.correo,
            contrasena='Secreta123',
        ) is None

        auth_routes.restablecer_contrasena(
            auth_routes.RestablecerContrasenaSchema(
                correo=usuario.correo,
                codigo=codigos_enviados['codigo'],
                nueva_contrasena='NuevaClave123',
            ),
            db,
        )
        assert usuario.requiere_cambio_contrasena is False
        assert AuthService.autenticar(
            db,
            correo=usuario.correo,
            contrasena='NuevaClave123',
        ) == usuario
        repetido = auth_routes.procesar_decision_acceso(token, 'no', db)
        assert 'ya se usó' in repetido.body.decode()
    finally:
        db.close()
        engine.dispose()


def test_reportar_acceso_cambia_contrasena_en_la_misma_pagina(monkeypatch):
    engine, db = _crear_db()
    enviado = {}
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(auth_routes.settings, 'PUBLIC_BASE_URL', 'https://finanbot.example')
    monkeypatch.setattr(
        auth_routes,
        '_enviar_codigo_recuperacion',
        lambda correo, codigo, enlace=None: enviado.update(
            correo=correo,
            codigo=codigo,
            enlace=enlace,
        ),
    )
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )
        token_alerta = 'token-de-alerta'
        db.add(LoginAlertToken(
            usuario_id=usuario.id,
            token_hash=auth_routes._hash_codigo(token_alerta),
            expires_at=auth_routes._utcnow() + timedelta(hours=1),
        ))
        db.commit()

        pagina = auth_routes.procesar_decision_acceso(token_alerta, 'no', db)
        formulario = pagina.body.decode()
        assert 'Acceso reportado y sesiones cerradas' in formulario
        assert 'id="nueva"' in formulario
        assert usuario.requiere_cambio_contrasena is True
        token_reset = re.search(
            r'action="/api/auth/restablecer-por-enlace/([^"]+)"',
            formulario,
        ).group(1)
        assert enviado['enlace'].endswith(token_reset)

        respuesta = auth_routes.restablecer_con_enlace(
            token_reset,
            auth_routes.RestablecerConEnlaceSchema(
                nueva_contrasena='ClaveNueva123',
                confirmar_contrasena='ClaveNueva123',
            ),
            db,
        )
        assert 'actualizada' in respuesta['mensaje']
        assert usuario.requiere_cambio_contrasena is False
        assert AuthService.autenticar(
            db,
            correo=usuario.correo,
            contrasena='ClaveNueva123',
        ) == usuario
    finally:
        db.close()
        engine.dispose()


def test_enlace_aviso_usa_origen_frontend_si_no_hay_url_configurada(monkeypatch):
    engine, db = _crear_db()
    avisos = []
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(
        auth_routes.settings,
        'PUBLIC_BASE_URL',
        'http://localhost:5173',
    )
    monkeypatch.setattr(auth_routes, '_enviar_correo', lambda mensaje: avisos.append(mensaje))
    try:
        AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )
        auth_routes.login(
            auth_routes.LoginSchema(correo='usuario@gmail.com', contrasena='Secreta123'),
            _crear_request(origin='http://192.168.1.44:5173'),
            db,
        )

        mensaje = next(
            part for part in avisos[0].walk()
            if part.get_content_type() == 'text/html'
        ).get_content()
        assert 'http://192.168.1.44:5173/api/auth/acceso-seguridad/' in mensaje
        assert 'finanbot.example/api/auth/acceso-seguridad/' not in mensaje
    finally:
        db.close()
        engine.dispose()


def test_no_envia_enlace_localhost_si_no_hay_url_publica(monkeypatch):
    engine, db = _crear_db()
    avisos = []
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(auth_routes.settings, 'PUBLIC_BASE_URL', '')
    monkeypatch.setattr(auth_routes, '_enviar_correo', lambda mensaje: avisos.append(mensaje))
    try:
        AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )
        respuesta = auth_routes.login(
            auth_routes.LoginSchema(correo='usuario@gmail.com', contrasena='Secreta123'),
            _crear_request(origin='http://localhost:5173', host='localhost'),
            db,
        )

        assert not avisos
        assert 'no con localhost' in respuesta['aviso_seguridad']
        assert db.query(LoginAlertToken).count() == 0
    finally:
        db.close()
        engine.dispose()


def test_reenvio_codigo_recuperacion_emite_codigo_nuevo(monkeypatch):
    engine, db = _crear_db()
    enviados = []
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(auth_routes.settings, 'PUBLIC_BASE_URL', 'https://finanbot.example')
    monkeypatch.setattr(
        auth_routes,
        '_enviar_codigo_recuperacion',
        lambda correo, codigo, enlace=None: enviados.append((correo, codigo, enlace)),
    )
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )
        primera = auth_routes.solicitar_recuperacion(
            auth_routes.SolicitarRecuperacionSchema(correo=usuario.correo),
            db,
        )
        assert primera['mensaje']
        db.query(PasswordResetCode).one().created_at = (
            auth_routes._utcnow() - timedelta(minutes=2)
        )
        db.commit()

        segunda = auth_routes.reenviar_codigo_recuperacion(
            auth_routes.SolicitarRecuperacionSchema(correo=usuario.correo),
            db,
        )
        assert segunda['mensaje']
        assert len(enviados) == 2
        assert enviados[0][1] != enviados[1][1]
        assert enviados[0][2] != enviados[1][2]
        assert db.query(PasswordResetCode).one().code_hash == auth_routes._hash_codigo(
            enviados[1][1],
        )
    finally:
        db.close()
        engine.dispose()


def test_enlace_recuperacion_cambia_contrasena_una_vez(monkeypatch):
    engine, db = _crear_db()
    enviado = {}
    monkeypatch.setattr(auth_routes.settings, 'SMTP_USERNAME', 'finanbot@gmail.com')
    monkeypatch.setattr(auth_routes.settings, 'SMTP_APP_PASSWORD', 'app-password')
    monkeypatch.setattr(auth_routes.settings, 'PUBLIC_BASE_URL', 'https://finanbot.example')
    monkeypatch.setattr(
        auth_routes,
        '_enviar_codigo_recuperacion',
        lambda correo, codigo, enlace=None: enviado.update(
            correo=correo,
            codigo=codigo,
            enlace=enlace,
        ),
    )
    try:
        usuario = AuthService.registrar(
            db,
            nombre='Usuario de prueba',
            correo='usuario@gmail.com',
            contrasena='Secreta123',
        )
        auth_routes.solicitar_recuperacion(
            auth_routes.SolicitarRecuperacionSchema(correo=usuario.correo),
            db,
        )
        token = enviado['enlace'].rsplit('/', 1)[1]

        pagina = auth_routes.pagina_restaurar_con_enlace(token, db)
        html = pagina.body.decode()
        assert 'Nueva contraseña' in html
        assert 'confirmar_contrasena' in html
        assert pagina.headers['cache-control'] == 'no-store'

        respuesta = auth_routes.restablecer_con_enlace(
            token,
            auth_routes.RestablecerConEnlaceSchema(
                nueva_contrasena='NuevaClave123',
                confirmar_contrasena='NuevaClave123',
            ),
            db,
        )
        assert 'actualizada' in respuesta['mensaje']
        assert AuthService.autenticar(
            db,
            correo=usuario.correo,
            contrasena='NuevaClave123',
        ) == usuario
        assert db.query(PasswordResetCode).count() == 0
        assert db.query(PasswordResetLink).one().used_at is not None

        with pytest.raises(HTTPException) as error:
            auth_routes.restablecer_con_enlace(
                token,
                auth_routes.RestablecerConEnlaceSchema(
                    nueva_contrasena='OtraClave123',
                    confirmar_contrasena='OtraClave123',
                ),
                db,
            )
        assert error.value.status_code == 400
    finally:
        db.close()
        engine.dispose()


def test_inicio_google_verifica_correo_y_crea_usuario(monkeypatch):
    engine, db = _crear_db()
    monkeypatch.setattr(auth_routes.settings, 'GOOGLE_CLIENT_ID', 'client-id.apps.googleusercontent.com')
    monkeypatch.setattr(
        id_token,
        'verify_oauth2_token',
        lambda token, request, audience, clock_skew_in_seconds: {
            'email': 'google.user@gmail.com',
            'name': 'Google User',
            'email_verified': True,
        },
    )
    try:
        response = auth_routes.login_google(
            auth_routes.GoogleCredentialSchema(credential='verified-google-credential'),
            _crear_request(),
            db,
        )

        usuario = db.query(Usuario).filter_by(correo='google.user@gmail.com').one()
        assert response['usuario']['correo'] == 'google.user@gmail.com'
        assert response['usuario']['nombre'] == 'Google User'
        assert response['token']
        assert usuario.onboarding_completado is False
    finally:
        db.close()
        engine.dispose()


def test_fallo_verificacion_google_registra_motivo_sin_token(monkeypatch, caplog):
    engine, db = _crear_db()
    credential = 'credential-privada'
    monkeypatch.setattr(auth_routes.settings, 'GOOGLE_CLIENT_ID', 'client-id.apps.googleusercontent.com')

    def rechazar_credencial(token, request, audience, clock_skew_in_seconds):
        raise ValueError('Token has wrong audience')

    monkeypatch.setattr(id_token, 'verify_oauth2_token', rechazar_credencial)
    try:
        with pytest.raises(HTTPException) as error:
            auth_routes.login_google(
                auth_routes.GoogleCredentialSchema(credential=credential),
                _crear_request(),
                db,
            )

        assert error.value.status_code == 401
        assert 'Token has wrong audience' in caplog.text
        assert credential not in caplog.text
    finally:
        db.close()
        engine.dispose()


def test_verificacion_google_limita_espera_de_certificados(monkeypatch):
    engine, db = _crear_db()
    request_arguments = {}
    verification_arguments = {}

    class FakeGoogleRequest:
        def __call__(self, url, **kwargs):
            request_arguments.update(kwargs)
            return object()

    monkeypatch.setattr(auth_routes.settings, 'GOOGLE_CLIENT_ID', 'client-id.apps.googleusercontent.com')
    monkeypatch.setattr(google_requests, 'Request', FakeGoogleRequest)

    def verificar(token, request, audience, clock_skew_in_seconds):
        verification_arguments['clock_skew_in_seconds'] = clock_skew_in_seconds
        request('https://www.googleapis.com/oauth2/v3/certs')
        return {
            'email': 'google.user@gmail.com',
            'name': 'Google User',
            'email_verified': True,
        }

    monkeypatch.setattr(id_token, 'verify_oauth2_token', verificar)
    try:
        auth_routes.login_google(
            auth_routes.GoogleCredentialSchema(credential='verified-google-credential'),
            _crear_request(),
            db,
        )
        assert request_arguments['timeout'] == 10
        assert verification_arguments['clock_skew_in_seconds'] == 120
    finally:
        db.close()
        engine.dispose()
