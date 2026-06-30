# routes/perfil.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from extensions import obtener_usuario_id_requerido, verify_password, hash_password
from models import Usuario

router = APIRouter()


# =========================================================
# ESQUEMA
# =========================================================

class PerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    ingreso_mensual: Optional[float] = None
    meta_ahorro: Optional[float] = None
    nueva_contrasena: Optional[str] = None
    contrasena_actual: Optional[str] = None
    onboarding_completado: Optional[bool] = None


# =========================================================
# OBTENER PERFIL
# =========================================================

@router.get('/')
def obtener_perfil(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    usuario = db.query(Usuario).get(uid)

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    return {
        'id': usuario.id,
        'nombre': usuario.nombre,
        'correo': usuario.correo,
        'ingreso_mensual': float(usuario.ingreso_mensual or 0),
        'meta_ahorro': float(usuario.meta_ahorro or 0),
        'fecha_registro': usuario.fecha_registro.strftime('%d/%m/%Y'),
        'onboarding_completado': usuario.onboarding_completado,
    }


# =========================================================
# ACTUALIZAR PERFIL
# =========================================================

@router.put('/')
def actualizar_perfil(
    body: PerfilUpdate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    usuario = db.query(Usuario).get(uid)

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    if body.nombre:
        usuario.nombre = body.nombre

    if body.ingreso_mensual is not None:
        usuario.ingreso_mensual = body.ingreso_mensual

    if body.meta_ahorro is not None:
        usuario.meta_ahorro = body.meta_ahorro

    # ── CONTRASEÑA: requiere la actual ──────────────────────────
    if body.nueva_contrasena:
        contrasena_actual = (body.contrasena_actual or '').strip()

        if not contrasena_actual:
            raise HTTPException(
                status_code=400,
                detail='❌ Debes ingresar tu contraseña actual para cambiarla.'
            )

        if not verify_password(contrasena_actual, usuario.contrasena_hash):
            raise HTTPException(
                status_code=400,
                detail='❌ La contraseña actual es incorrecta.'
            )

        usuario.contrasena_hash = hash_password(body.nueva_contrasena)
    # ────────────────────────────────────────────────────────────

    if body.onboarding_completado is not None:
        usuario.onboarding_completado = body.onboarding_completado

    db.commit()
    return {'mensaje': '✅ Perfil actualizado!'}