import hashlib
import hmac
import html
import ipaddress
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from application.services.auth_service import AuthService
from config import settings
from database import get_db
from extensions import hash_password, obtener_usuario_actual
from models import (
    LoginAlertToken,
    PasswordResetCode,
    PasswordResetLink,
    SecurityResetAttempt,
    Usuario,
)
from timezone import BOGOTA_TIMEZONE

router = APIRouter()
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RegistroSchema(BaseModel):
    nombre: str
    correo: str
    contrasena: str
    pregunta_seguridad: str = Field(min_length=5, max_length=255)
    respuesta_seguridad: str = Field(min_length=1, max_length=255)


class LoginSchema(BaseModel):
    correo: str
    contrasena: str


class GoogleCredentialSchema(BaseModel):
    credential: str


class SolicitarRecuperacionSchema(BaseModel):
    correo: str


class RestablecerContrasenaSchema(BaseModel):
    correo: str
    codigo: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')
    nueva_contrasena: str


class RestablecerConEnlaceSchema(BaseModel):
    nueva_contrasena: str
    confirmar_contrasena: str


class PreguntaSeguridadSchema(BaseModel):
    correo: str


class RestablecerConPreguntaSchema(BaseModel):
    correo: str
    respuesta_seguridad: str = Field(min_length=1, max_length=255)
    nueva_contrasena: str


_usuario_publico = AuthService.usuario_publico


def _correo_configurado() -> bool:
    return bool(settings.SMTP_USERNAME and settings.SMTP_APP_PASSWORD)


def _enviar_correo(mensaje: EmailMessage) -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.ehlo()
        servidor.login(settings.SMTP_USERNAME, settings.SMTP_APP_PASSWORD)
        rechazados = servidor.send_message(mensaje)
        if rechazados:
            raise smtplib.SMTPRecipientsRefused(rechazados)


def _url_base_valida(url: str) -> bool:
    partes = urlsplit(url)
    return (
        partes.scheme in ('http', 'https')
        and bool(partes.hostname and partes.netloc)
        and partes.username is None
        and partes.password is None
        and partes.path in ('', '/')
        and not partes.query
        and not partes.fragment
    )


def _url_local(url: str) -> bool:
    hostname = urlsplit(url).hostname
    if not hostname:
        return True
    if hostname == 'localhost' or hostname.endswith('.localhost'):
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _base_url_publica(request: Request) -> str:
    configurada = settings.PUBLIC_BASE_URL
    origen = request.headers.get('origin', '')
    referente = request.headers.get('referer', '')
    referentes = []
    if referente:
        partes_referer = urlsplit(referente)
        if partes_referer.scheme in ('http', 'https') and partes_referer.netloc:
            referentes.append(f'{partes_referer.scheme}://{partes_referer.netloc}')
    candidatas = [configurada, origen, *referentes, str(request.base_url).rstrip('/')]

    for candidata in candidatas:
        if _url_base_valida(candidata) and not _url_local(candidata):
            return candidata.rstrip('/')
    raise HTTPException(
        status_code=503,
        detail='Configura PUBLIC_BASE_URL con la dirección de FinanBot accesible para tus usuarios.',
    )


def _respuesta_login(usuario: Usuario, db: Session, request: Request) -> dict:
    respuesta = {
        'mensaje': '✅ Inicio de sesión exitoso!',
        'token': AuthService.token(usuario),
        'usuario': _usuario_publico(usuario),
    }
    if not _correo_configurado():
        respuesta['aviso_seguridad'] = (
            'No se pudo enviar el aviso de inicio de sesión porque el correo no está '
            'configurado en el servidor.'
        )
        return respuesta

    try:
        base_url = _base_url_publica(request)
    except HTTPException:
        logger.warning(
            'Aviso de inicio de sesión omitido para %s: configura PUBLIC_BASE_URL '
            'con una dirección accesible desde otros dispositivos.',
            usuario.correo,
        )
        respuesta['aviso_seguridad'] = (
            'No se pudo enviar el aviso: configura PUBLIC_BASE_URL con la IP de red '
            'o el dominio de FinanBot, no con localhost.'
        )
        return respuesta

    db.query(LoginAlertToken).filter(
        LoginAlertToken.expires_at <= _utcnow(),
    ).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    registro = LoginAlertToken(
        usuario_id=usuario.id,
        token_hash=_hash_codigo(token),
        expires_at=_utcnow() + timedelta(hours=24),
    )
    db.add(registro)
    db.commit()

    enlace = f'{base_url}/api/auth/acceso-seguridad/{token}'
    fecha = datetime.now(timezone.utc).astimezone(BOGOTA_TIMEZONE).strftime(
        '%Y-%m-%d %H:%M %Z',
    )
    mensaje = EmailMessage()
    mensaje['Subject'] = 'Nuevo inicio de sesión en FinanBot'
    mensaje['From'] = settings.SMTP_FROM or settings.SMTP_USERNAME
    mensaje['To'] = usuario.correo
    mensaje.set_content(
        'Se inició sesión en tu cuenta de FinanBot.\n'
        f'Fecha y hora: {fecha}\n\n'
        'Si reconoces este acceso, confirma aquí:\n'
        f'{enlace}?decision=si\n\n'
        'Si no reconoces este acceso, repórtalo aquí. Revocaremos tus sesiones '
        'y te enviaremos un código para cambiar la contraseña:\n'
        f'{enlace}?decision=no\n\n'
        'Estos enlaces vencen en 24 horas y solo se pueden usar una vez.'
    )
    nombre = html.escape(usuario.nombre)
    mensaje.add_alternative(
        f"""<!doctype html>
<html lang="es"><body style="font-family:Arial,sans-serif;color:#202033">
<h2>Nuevo inicio de sesión en FinanBot</h2>
<p>Hola {nombre}, se inició sesión en tu cuenta el <strong>{html.escape(fecha)}</strong>.</p>
<p>Si reconoces este acceso:</p>
<p><a href="{enlace}?decision=si">Sí, fui yo</a></p>
<p>Si no lo reconoces, repórtalo. Revocaremos tus sesiones y te enviaremos un código
para cambiar la contraseña:</p>
<p><a href="{enlace}?decision=no">No fui yo</a></p>
<p>Los enlaces vencen en 24 horas y solo se pueden usar una vez.</p>
</body></html>""",
        subtype='html',
    )
    try:
        _enviar_correo(mensaje)
    except (smtplib.SMTPException, OSError):
        logger.exception('No se pudo enviar el aviso de inicio de sesión a %s', usuario.correo)
        db.delete(registro)
        db.commit()
        respuesta['aviso_seguridad'] = (
            'Ingresaste, pero no se pudo enviar el aviso de seguridad a tu correo.'
        )
    return respuesta


def _hash_codigo(codigo: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        codigo.encode(),
        hashlib.sha256,
    ).hexdigest()


def _respuesta_seguridad_valida(guardada: str, recibida: str) -> bool:
    respuesta_normalizada = AuthService.normalizar_respuesta_seguridad(recibida)
    respuesta_guardada = guardada or ''
    hash_recibido = AuthService.hash_respuesta_seguridad(recibida)
    coincide_hash = hmac.compare_digest(
        respuesta_guardada.encode('utf-8'),
        hash_recibido.encode('ascii'),
    )
    coincide_legacy = hmac.compare_digest(
        AuthService.normalizar_respuesta_seguridad(respuesta_guardada).encode('utf-8'),
        respuesta_normalizada.encode('utf-8'),
    )
    return coincide_hash or coincide_legacy


def _enviar_codigo_recuperacion(
    correo: str,
    codigo: str,
    enlace: str | None = None,
) -> None:
    mensaje = EmailMessage()
    mensaje['Subject'] = 'Código para recuperar tu contraseña de FinanBot'
    mensaje['From'] = settings.SMTP_FROM or settings.SMTP_USERNAME
    mensaje['To'] = correo
    mensaje.set_content(
        'Recibimos una solicitud para cambiar la contraseña de tu cuenta FinanBot.\n\n'
        f'Tu código de verificación es: {codigo}\n\n'
        + (
            f'También puedes cambiarla directamente desde este enlace:\n{enlace}\n\n'
            if enlace
            else ''
        )
        + 'El código vence en 10 minutos. Si no solicitaste este cambio, ignora este correo.'
    )
    if enlace:
        mensaje.add_alternative(
            f"""<!doctype html>
<html lang="es"><body style="font-family:Arial,sans-serif;color:#202033">
<h2>Recupera tu contraseña de FinanBot</h2>
<p>Tu código de verificación es: <strong>{html.escape(codigo)}</strong></p>
<p>También puedes cambiarla directamente:</p>
<p><a href="{html.escape(enlace, quote=True)}">Crear una contraseña nueva</a></p>
<p>El código y el enlace vencen en 10 minutos. Si no solicitaste este cambio, ignora este correo.</p>
</body></html>""",
            subtype='html',
        )

    _enviar_correo(mensaje)


def _pagina_resultado_seguridad(
    mensaje: str,
    *,
    accion: str | None = None,
    action_url: str | None = None,
    nota: str | None = None,
) -> HTMLResponse:
    texto = html.escape(mensaje)
    boton = ''
    if accion and action_url:
        boton = (
            f'<form method="post" action="{html.escape(action_url, quote=True)}">'
            '<button type="submit" style="margin-top:12px;padding:12px 18px;border:0;'
            'border-radius:10px;background:#8b5cf6;color:white;font-weight:700;'
            'cursor:pointer">'
            f'{html.escape(accion)}</button></form>'
        )
    texto_nota = f'<p>{html.escape(nota)}</p>' if nota else ''
    return HTMLResponse(
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        '<title>Seguridad de FinanBot</title>'
        '<style>'
        '*,*::before,*::after{box-sizing:border-box}'
        'body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;'
        'font-family:Arial,sans-serif;color:#f4f3ff;'
        'background:linear-gradient(135deg,#11112b,#241b45)}'
        'main{width:min(100%,560px);padding:32px;border:1px solid #514476;'
        'border-radius:20px;background:#191832;box-shadow:0 20px 60px #0005}'
        'h1{margin:0 0 20px;color:#a78bfa;font-size:28px}'
        'p{line-height:1.65;color:#dedcf0}'
        'a{display:inline-block;margin-top:12px;padding:12px 18px;border-radius:10px;'
        'background:#8b5cf6;color:white;text-decoration:none;font-weight:700}'
        '</style></head><body><main><h1>Seguridad de FinanBot</h1>'
        f'<p>{texto}</p>'
        f'{boton}{texto_nota}'
        '<a href="/legacy/pages/login.html">Ir a iniciar sesión</a>'
        '</main></body></html>',
        headers={'Cache-Control': 'no-store'},
    )


def _pagina_cambio_contrasena(token: str, mensaje: str | None = None) -> HTMLResponse:
    action = f'/api/auth/restablecer-por-enlace/{html.escape(token, quote=True)}'
    aviso = (
        f'<p role="status">{html.escape(mensaje)}</p>'
        if mensaje
        else '<p>Elige una contraseña de al menos 6 caracteres. Este enlace vence en 10 minutos y solo se usa una vez.</p>'
    )
    return HTMLResponse(
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta name="robots" content="noindex,nofollow">'
        '<title>Cambiar contraseña · FinanBot</title>'
        '<style>'
        '*,*::before,*::after{box-sizing:border-box}'
        'body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;'
        'font-family:Arial,sans-serif;color:#f4f3ff;background:linear-gradient(135deg,#11112b,#241b45)}'
        'main{width:min(100%,480px);padding:32px;border:1px solid #514476;border-radius:20px;'
        'background:#191832;box-shadow:0 20px 60px #0005}'
        'h1{margin:0 0 12px;color:#a78bfa}p{line-height:1.6;color:#dedcf0}'
        'label{display:block;margin-top:18px;font-weight:700}'
        'input{display:block;width:100%;margin-top:8px;padding:12px;border:1px solid #514476;'
        'border-radius:10px;background:#11112b;color:white;font-size:16px}'
        'button{width:100%;margin-top:22px;padding:13px;border:0;border-radius:10px;'
        'background:#8b5cf6;color:white;font-size:16px;font-weight:700;cursor:pointer}'
        'button:disabled{opacity:.6;cursor:wait}'
        '#mensaje{min-height:24px;margin-top:12px}'
        'a{display:inline-block;margin-top:12px;color:#c4b5fd}'
        '</style></head><body><main><h1>Crea una contraseña nueva</h1>'
        f'{aviso}'
        f'<form id="formulario" action="{action}">'
        '<label for="nueva">Nueva contraseña<input id="nueva" name="nueva" type="password" '
        'autocomplete="new-password" minlength="6" required></label>'
        '<label for="confirmar">Confirma la contraseña<input id="confirmar" name="confirmar" '
        'type="password" autocomplete="new-password" minlength="6" required></label>'
        '<button id="guardar" type="submit">Cambiar contraseña</button>'
        '</form><p id="mensaje" role="status" aria-live="polite"></p>'
        '<a href="/legacy/pages/login.html">Volver al inicio de sesión</a>'
        '<script>'
        "document.getElementById('formulario').addEventListener('submit',async function(event){"
        "event.preventDefault();"
        "const nueva=document.getElementById('nueva').value;"
        "const confirmar=document.getElementById('confirmar').value;"
        "const mensaje=document.getElementById('mensaje');"
        "const boton=document.getElementById('guardar');"
        "if(nueva.length<6){mensaje.textContent='La contraseña debe tener mínimo 6 caracteres.';return;}"
        "if(nueva!==confirmar){mensaje.textContent='Las contraseñas no coinciden.';return;}"
        "boton.disabled=true;mensaje.textContent='Actualizando contraseña...';"
        "try{const respuesta=await fetch(this.action,{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({nueva_contrasena:nueva,confirmar_contrasena:confirmar})});"
        "const datos=await respuesta.json();"
        "if(!respuesta.ok){mensaje.textContent=datos.detail||'No se pudo cambiar la contraseña.';boton.disabled=false;return;}"
        "this.hidden=true;mensaje.textContent=datos.mensaje;"
        "}catch(error){mensaje.textContent='No se pudo conectar con FinanBot. Inténtalo de nuevo.';boton.disabled=false;}"
        '});</script></main></body></html>',
        headers={
            'Cache-Control': 'no-store',
            'Referrer-Policy': 'no-referrer',
        },
    )


def _codigo_recuperacion_reciente(usuario: Usuario, db: Session) -> bool:
    return db.query(PasswordResetCode).filter(
        PasswordResetCode.usuario_id == usuario.id,
        PasswordResetCode.created_at > _utcnow() - timedelta(minutes=1),
    ).first() is not None


def _crear_y_enviar_codigo_recuperacion(
    usuario: Usuario,
    db: Session,
    base_url: str,
) -> str:
    if not _url_base_valida(base_url) or _url_local(base_url):
        raise HTTPException(
            status_code=503,
            detail='Configura PUBLIC_BASE_URL con una dirección accesible para enviar el enlace directo de recuperación.',
        )

    codigo, token, registro_codigo, registro_enlace = _crear_registros_recuperacion(
        usuario,
        db,
    )
    db.commit()

    try:
        enlace = f'{base_url.rstrip("/")}/api/auth/restablecer-por-enlace/{token}'
        _enviar_codigo_recuperacion(usuario.correo, codigo, enlace)
    except (smtplib.SMTPException, OSError):
        logger.exception('No se pudo enviar el código de recuperación a %s', usuario.correo)
        db.delete(registro_codigo)
        db.delete(registro_enlace)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail='No se pudo enviar el correo de recuperación. Inténtalo más tarde.',
        )
    return token


def _crear_registros_recuperacion(
    usuario: Usuario,
    db: Session,
) -> tuple[str, str, PasswordResetCode, PasswordResetLink]:
    db.query(PasswordResetCode).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.query(PasswordResetLink).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.query(PasswordResetLink).filter(
        PasswordResetLink.expires_at <= _utcnow(),
    ).delete(synchronize_session=False)

    codigo = f'{secrets.randbelow(1_000_000):06d}'
    token = secrets.token_urlsafe(32)
    expiracion = _utcnow() + timedelta(minutes=10)
    registro_codigo = PasswordResetCode(
        usuario_id=usuario.id,
        code_hash=_hash_codigo(codigo),
        expires_at=expiracion,
    )
    registro_enlace = PasswordResetLink(
        usuario_id=usuario.id,
        token_hash=_hash_codigo(token),
        expires_at=expiracion,
    )
    db.add_all([registro_codigo, registro_enlace])
    return codigo, token, registro_codigo, registro_enlace


@router.post('/registro', status_code=201)
def registro(body: RegistroSchema, db: Session = Depends(get_db)):
    try:
        AuthService.registrar(
            db,
            nombre=body.nombre,
            correo=body.correo,
            contrasena=body.contrasena,
            pregunta_seguridad=body.pregunta_seguridad,
            respuesta_seguridad=body.respuesta_seguridad or '',
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {'mensaje': '✅ Usuario registrado exitosamente!'}


@router.post('/login')
def login(body: LoginSchema, request: Request, db: Session = Depends(get_db)):
    usuario = AuthService.autenticar(db, correo=body.correo, contrasena=body.contrasena)
    if not usuario:
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')
    return _respuesta_login(usuario, db, request)


@router.get('/google-config')
def google_config():
    return {'client_id': settings.GOOGLE_CLIENT_ID}


@router.post('/google')
def login_google(
    body: GoogleCredentialSchema,
    request: Request,
    db: Session = Depends(get_db),
):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail='El inicio con Google aún no está configurado.')

    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    google_request = google_requests.Request()

    def request_with_timeout(url, **kwargs):
        kwargs.setdefault('timeout', 10)
        return google_request(url, **kwargs)

    try:
        claims = id_token.verify_oauth2_token(
            body.credential,
            request_with_timeout,
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=120,
        )
    except (ValueError, GoogleAuthError) as error:
        logger.warning(
            'No se pudo verificar el token de Google (%s): %s',
            type(error).__name__,
            str(error).replace(body.credential, '[redacted]'),
        )
        raise HTTPException(status_code=401, detail='No se pudo verificar la cuenta de Google.') from error

    correo = claims.get('email', '')
    nombre = claims.get('name', '')
    if claims.get('email_verified') is not True or not correo:
        raise HTTPException(status_code=401, detail='Google no confirmó que el correo te pertenece.')

    try:
        usuario = AuthService.autenticar_google(db, correo=correo, nombre=nombre)
    except IntegrityError:
        db.rollback()
        usuario = db.query(Usuario).filter_by(correo=correo.strip().lower()).first()
        if not usuario:
            raise
    if usuario.requiere_cambio_contrasena:
        raise HTTPException(
            status_code=403,
            detail='Por seguridad, restablece la contraseña de tu cuenta antes de volver a ingresar.',
        )
    return _respuesta_login(usuario, db, request)


@router.post('/solicitar-recuperacion')
def solicitar_recuperacion(
    body: SolicitarRecuperacionSchema,
    db: Session = Depends(get_db),
):
    if not _correo_configurado():
        raise HTTPException(
            status_code=503,
            detail='El envío de recuperación aún no está configurado en el servidor.',
        )

    correo = body.correo.strip().lower()
    usuario = db.query(Usuario).filter_by(correo=correo).first()
    if usuario:
        if _codigo_recuperacion_reciente(usuario, db):
            return {
                'mensaje': 'Si existe una cuenta con ese correo, enviaremos un código de verificación.',
            }
        _crear_y_enviar_codigo_recuperacion(usuario, db, settings.PUBLIC_BASE_URL)

    return {
        'mensaje': 'Si existe una cuenta con ese correo, enviaremos un código de verificación.',
    }


@router.post('/reenviar-codigo-recuperacion')
def reenviar_codigo_recuperacion(
    body: SolicitarRecuperacionSchema,
    db: Session = Depends(get_db),
):
    if not _correo_configurado():
        raise HTTPException(
            status_code=503,
            detail='El envío de recuperación aún no está configurado en el servidor.',
        )

    usuario = db.query(Usuario).filter_by(correo=body.correo.strip().lower()).first()
    if usuario and not _codigo_recuperacion_reciente(usuario, db):
        _crear_y_enviar_codigo_recuperacion(usuario, db, settings.PUBLIC_BASE_URL)

    return {
        'mensaje': 'Si existe una cuenta con ese correo, enviaremos un código de verificación.',
    }


@router.get('/restablecer-por-enlace/{token}', response_class=HTMLResponse)
def pagina_restaurar_con_enlace(token: str, db: Session = Depends(get_db)):
    registro = db.query(PasswordResetLink).filter_by(
        token_hash=_hash_codigo(token),
    ).first()
    if not registro or registro.used_at or registro.expires_at < _utcnow():
        return _pagina_resultado_seguridad(
            'El enlace para cambiar la contraseña no es válido o ya venció. '
            'Solicita uno nuevo desde la pantalla de inicio de sesión.'
        )
    return _pagina_cambio_contrasena(token)


@router.post('/restablecer-por-enlace/{token}')
def restablecer_con_enlace(
    token: str,
    body: RestablecerConEnlaceSchema,
    db: Session = Depends(get_db),
):
    if len(body.nueva_contrasena) < 6:
        raise HTTPException(
            status_code=400,
            detail='La contraseña debe tener mínimo 6 caracteres.',
        )
    if body.nueva_contrasena != body.confirmar_contrasena:
        raise HTTPException(status_code=400, detail='Las contraseñas no coinciden.')

    ahora = _utcnow()
    token_hash = _hash_codigo(token)
    registro = db.query(PasswordResetLink).filter_by(token_hash=token_hash).first()
    if not registro or registro.used_at or registro.expires_at < ahora:
        raise HTTPException(
            status_code=400,
            detail='El enlace para cambiar la contraseña no es válido o ya venció. Solicita uno nuevo.',
        )

    actualizado = db.query(PasswordResetLink).filter(
        PasswordResetLink.id == registro.id,
        PasswordResetLink.used_at.is_(None),
        PasswordResetLink.expires_at > ahora,
    ).update({'used_at': ahora}, synchronize_session=False)
    if actualizado != 1:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail='El enlace para cambiar la contraseña no es válido o ya venció. Solicita uno nuevo.',
        )

    usuario = db.get(Usuario, registro.usuario_id)
    if not usuario:
        db.rollback()
        raise HTTPException(status_code=400, detail='No se encontró la cuenta asociada al enlace.')

    usuario.contrasena_hash = hash_password(body.nueva_contrasena)
    usuario.token_version += 1
    usuario.requiere_cambio_contrasena = False
    db.query(PasswordResetCode).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.query(PasswordResetLink).filter(
        PasswordResetLink.usuario_id == usuario.id,
        PasswordResetLink.id != registro.id,
    ).delete(synchronize_session=False)
    db.commit()
    return {
        'mensaje': 'Contraseña actualizada. Ya puedes iniciar sesión en FinanBot.',
    }


@router.get('/acceso-seguridad/{token}', response_class=HTMLResponse)
def confirmar_pagina_acceso(token: str, decision: str, db: Session = Depends(get_db)):
    if decision not in ('si', 'no'):
        raise HTTPException(status_code=400, detail='La decisión no es válida.')
    registro = db.query(LoginAlertToken).filter_by(token_hash=_hash_codigo(token)).first()
    if not registro or registro.used_at or registro.expires_at < _utcnow():
        return _pagina_resultado_seguridad(
            'Este enlace de seguridad ya se usó o venció. Si no reconoces el acceso, '
            'inicia la recuperación de contraseña desde el inicio de sesión.'
        )

    accion = 'Confirmar que fui yo' if decision == 'si' else 'Reportar acceso desconocido'
    descripcion = (
        'Confirma que reconoces este inicio de sesión.'
        if decision == 'si'
        else 'Al continuar, se cerrarán tus sesiones y se enviará un código para cambiar la contraseña.'
    )
    action_url = f'/api/auth/acceso-seguridad/{token}?decision={decision}'
    return _pagina_resultado_seguridad(
        descripcion,
        accion=accion,
        action_url=action_url,
        nota='Si abriste este enlace por error, cierra esta página sin confirmar.',
    )


@router.post('/acceso-seguridad/{token}', response_class=HTMLResponse)
def procesar_decision_acceso(
    token: str,
    decision: str,
    db: Session = Depends(get_db),
):
    if decision not in ('si', 'no'):
        raise HTTPException(status_code=400, detail='La decisión no es válida.')
    token_hash = _hash_codigo(token)
    registro = db.query(LoginAlertToken).filter_by(token_hash=token_hash).first()
    ahora = _utcnow()
    if not registro or registro.used_at or registro.expires_at < ahora:
        return _pagina_resultado_seguridad(
            'Este enlace de seguridad ya se usó o venció. Si no reconoces el acceso, '
            'inicia la recuperación de contraseña desde el inicio de sesión.'
        )

    actualizado = db.query(LoginAlertToken).filter(
        LoginAlertToken.id == registro.id,
        LoginAlertToken.used_at.is_(None),
        LoginAlertToken.expires_at > ahora,
    ).update({'used_at': ahora}, synchronize_session=False)
    if actualizado != 1:
        return _pagina_resultado_seguridad(
            'Este enlace de seguridad ya se usó o venció.'
        )

    usuario = db.get(Usuario, registro.usuario_id)
    if not usuario:
        db.rollback()
        return _pagina_resultado_seguridad('No se encontró la cuenta asociada a este enlace.')

    if decision == 'si':
        db.commit()
        return _pagina_resultado_seguridad('Gracias. Confirmaste que reconoces el inicio de sesión.')

    usuario.token_version += 1
    usuario.requiere_cambio_contrasena = True
    db.query(PasswordResetCode).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.query(PasswordResetLink).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    codigo, token_reset, registro_codigo, _ = _crear_registros_recuperacion(
        usuario,
        db,
    )
    db.commit()

    mensaje = (
        'Acceso reportado y sesiones cerradas. Cambia ahora tu contraseña para '
        'recuperar el acceso a la cuenta.'
    )
    if _correo_configurado():
        try:
            enlace = None
            if _url_base_valida(settings.PUBLIC_BASE_URL) and not _url_local(
                settings.PUBLIC_BASE_URL,
            ):
                enlace = (
                    f'{settings.PUBLIC_BASE_URL.rstrip("/")}'
                    f'/api/auth/restablecer-por-enlace/{token_reset}'
                )
            _enviar_codigo_recuperacion(usuario.correo, codigo, enlace)
        except (smtplib.SMTPException, OSError):
            logger.exception('No se pudo enviar el código de recuperación a %s', usuario.correo)
            db.delete(registro_codigo)
            db.commit()
            mensaje += (
                ' No fue posible enviar el correo con el código de respaldo; puedes '
                'cambiarla aquí mismo.'
            )
    else:
        mensaje += (
            ' El correo de respaldo no está configurado, pero puedes cambiarla aquí mismo.'
        )

    return _pagina_cambio_contrasena(token_reset, mensaje)


@router.post('/restablecer-contrasena')
def restablecer_contrasena(
    body: RestablecerContrasenaSchema,
    db: Session = Depends(get_db),
):
    if len(body.nueva_contrasena) < 6:
        raise HTTPException(status_code=400, detail='La contraseña debe tener mínimo 6 caracteres')

    usuario = db.query(Usuario).filter_by(correo=body.correo.strip().lower()).first()
    if not usuario:
        raise HTTPException(status_code=400, detail='El código no es válido o venció.')

    codigo = db.query(PasswordResetCode).filter_by(usuario_id=usuario.id).first()
    if not codigo or codigo.expires_at < _utcnow() or codigo.attempts >= 5:
        if codigo:
            db.delete(codigo)
            db.commit()
        raise HTTPException(status_code=400, detail='El código no es válido o venció.')

    if not hmac.compare_digest(codigo.code_hash, _hash_codigo(body.codigo.strip())):
        codigo.attempts += 1
        if codigo.attempts >= 5:
            db.delete(codigo)
        db.commit()
        raise HTTPException(status_code=400, detail='El código no es válido o venció.')

    usuario.contrasena_hash = hash_password(body.nueva_contrasena)
    usuario.token_version += 1
    usuario.requiere_cambio_contrasena = False
    db.query(PasswordResetCode).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.query(PasswordResetLink).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.commit()
    return {'mensaje': '✅ Contraseña actualizada exitosamente'}


@router.post('/pregunta-seguridad')
def obtener_pregunta_seguridad(
    body: PreguntaSeguridadSchema,
    db: Session = Depends(get_db),
):
    correo = body.correo.strip().lower()
    usuario = db.query(Usuario).filter_by(correo=correo).first()
    if not usuario or not usuario.pregunta_seguridad or not usuario.respuesta_seguridad:
        raise HTTPException(
            status_code=404,
            detail='No hay una pregunta de seguridad disponible para esa cuenta. Usa la recuperación por correo.',
        )
    return {'pregunta_seguridad': usuario.pregunta_seguridad}


@router.post('/restablecer-con-pregunta')
def restablecer_con_pregunta(
    body: RestablecerConPreguntaSchema,
    db: Session = Depends(get_db),
):
    if len(body.nueva_contrasena) < 6:
        raise HTTPException(status_code=400, detail='La contraseña debe tener mínimo 6 caracteres')

    correo = body.correo.strip().lower()
    usuario = db.query(Usuario).filter_by(correo=correo).first()
    if not usuario or not usuario.pregunta_seguridad or not usuario.respuesta_seguridad:
        raise HTTPException(status_code=400, detail='La respuesta no es válida o debes usar la recuperación por correo.')

    intento = db.query(SecurityResetAttempt).filter_by(usuario_id=usuario.id).first()
    ahora = _utcnow()
    if intento and intento.locked_until and intento.locked_until > ahora:
        raise HTTPException(
            status_code=429,
            detail='Se alcanzó el máximo de intentos. Inténtalo nuevamente en 15 minutos.',
        )
    if intento and intento.locked_until and intento.locked_until <= ahora:
        intento.attempts = 0
        intento.locked_until = None

    if not _respuesta_seguridad_valida(usuario.respuesta_seguridad, body.respuesta_seguridad):
        if not intento:
            intento = SecurityResetAttempt(usuario_id=usuario.id, attempts=0)
            db.add(intento)
        intento.attempts += 1
        if intento.attempts >= 5:
            intento.attempts = 0
            intento.locked_until = ahora + timedelta(minutes=15)
        db.commit()
        raise HTTPException(status_code=400, detail='La respuesta no es válida o debes usar la recuperación por correo.')

    usuario.contrasena_hash = hash_password(body.nueva_contrasena)
    usuario.token_version += 1
    usuario.requiere_cambio_contrasena = False
    usuario.respuesta_seguridad = AuthService.hash_respuesta_seguridad(
        body.respuesta_seguridad,
    )
    if intento:
        db.delete(intento)
    db.query(PasswordResetCode).filter_by(usuario_id=usuario.id).delete(
        synchronize_session=False,
    )
    db.commit()
    return {'mensaje': '✅ Contraseña actualizada exitosamente'}


@router.get('/me')
def me(usuario: Usuario = Depends(obtener_usuario_actual)):
    return {'usuario': _usuario_publico(usuario)}
