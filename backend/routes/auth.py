# routes/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from extensions import obtener_usuario_actual, hash_password
from models import Usuario
from application.services.auth_service import AuthService

router = APIRouter()


# =========================================================
# ESQUEMAS (reemplazan request.get_json() con validación)
# =========================================================

class RegistroSchema(BaseModel):
    nombre: str
    correo: str
    contrasena: str
    pregunta_seguridad: Optional[str] = None
    respuesta_seguridad: Optional[str] = ""

class LoginSchema(BaseModel):
    correo: str
    contrasena: str

class CorreoSchema(BaseModel):
    correo: str

class VerificarSeguridadSchema(BaseModel):
    correo: str
    respuesta: Optional[str] = ""

class ResetearContrasenaSchema(BaseModel):
    correo: str
    respuesta: str          # se vuelve a validar aquí: sin esto cualquiera cambia la clave con solo el correo
    nueva_contrasena: str


# =========================================================
# HELPERS
# =========================================================

_usuario_publico = AuthService.usuario_publico


# =========================================================
# REGISTRO
# =========================================================

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


# =========================================================
# LOGIN
# =========================================================

@router.post('/login')
def login(body: LoginSchema, db: Session = Depends(get_db)):

    usuario = AuthService.autenticar(db, correo=body.correo, contrasena=body.contrasena)
    if not usuario:
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')

    token = AuthService.token(usuario)

    return {
        'mensaje': '✅ Inicio de sesión exitoso!',
        'token': token,
        'usuario': _usuario_publico(usuario),
    }


# =========================================================
# USUARIO ACTUAL (para que el frontend consulte su rol)
# =========================================================

@router.get('/me')
def me(usuario: Usuario = Depends(obtener_usuario_actual)):
    return {'usuario': _usuario_publico(usuario)}


# =========================================================
# OBTENER PREGUNTA
# =========================================================

@router.post('/obtener-pregunta')
def obtener_pregunta(body: CorreoSchema, db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter_by(correo=body.correo).first()

    if not usuario:
        raise HTTPException(status_code=404, detail='No existe una cuenta con ese correo')

    if not usuario.pregunta_seguridad:
        raise HTTPException(status_code=400, detail='Esta cuenta no tiene pregunta de seguridad')

    return {'pregunta': usuario.pregunta_seguridad}


# =========================================================
# VERIFICAR RESPUESTA
# =========================================================

@router.post('/verificar-seguridad')
def verificar_seguridad(body: VerificarSeguridadSchema, db: Session = Depends(get_db)):

    respuesta = (body.respuesta or '').lower().strip()

    usuario = db.query(Usuario).filter_by(correo=body.correo).first()

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    if usuario.respuesta_seguridad != respuesta:
        raise HTTPException(status_code=401, detail='Respuesta incorrecta')

    return {'mensaje': '✅ Verificación exitosa'}


# =========================================================
# RESETEAR CONTRASEÑA
# =========================================================

@router.post('/resetear-contrasena')
def resetear_contrasena(body: ResetearContrasenaSchema, db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter_by(correo=body.correo).first()

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    if not usuario.respuesta_seguridad or usuario.respuesta_seguridad != (body.respuesta or '').lower().strip():
        raise HTTPException(status_code=401, detail='Respuesta de seguridad incorrecta')

    if len(body.nueva_contrasena) < 6:
        raise HTTPException(status_code=400, detail='La contraseña debe tener mínimo 6 caracteres')

    usuario.contrasena_hash = hash_password(body.nueva_contrasena)
    db.commit()

    return {'mensaje': '✅ Contraseña actualizada exitosamente'}