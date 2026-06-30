# routes/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from extensions import hash_password, verify_password, create_access_token
from models import Usuario

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
    nueva_contrasena: str


# =========================================================
# REGISTRO
# =========================================================

@router.post('/registro', status_code=201)
def registro(body: RegistroSchema, db: Session = Depends(get_db)):

    usuario_existente = db.query(Usuario).filter_by(correo=body.correo).first()

    if usuario_existente:
        raise HTTPException(status_code=409, detail='El correo ya está registrado')

    contrasena_hash = hash_password(body.contrasena)

    nuevo_usuario = Usuario(
        nombre=body.nombre,
        correo=body.correo,
        contrasena_hash=contrasena_hash,
        pregunta_seguridad=body.pregunta_seguridad,
        respuesta_seguridad=(body.respuesta_seguridad or '').lower().strip(),
        onboarding_completado=False
    )

    db.add(nuevo_usuario)
    db.commit()

    return {'mensaje': '✅ Usuario registrado exitosamente!'}


# =========================================================
# LOGIN
# =========================================================

@router.post('/login')
def login(body: LoginSchema, db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter_by(correo=body.correo).first()

    if not usuario:
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')

    if not verify_password(body.contrasena, usuario.contrasena_hash):
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')

    token = create_access_token({"sub": str(usuario.id)})

    return {
        'mensaje': '✅ Inicio de sesión exitoso!',
        'token': token,
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'ingreso_mensual': float(usuario.ingreso_mensual or 0),
            'meta_ahorro': float(usuario.meta_ahorro or 0),
            'onboarding_completado': usuario.onboarding_completado
        }
    }


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

    usuario.contrasena_hash = hash_password(body.nueva_contrasena)
    db.commit()

    return {'mensaje': '✅ Contraseña actualizada exitosamente'}