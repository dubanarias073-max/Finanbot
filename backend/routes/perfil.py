# routes/perfil.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from extensions import obtener_usuario_id_requerido, verify_password, hash_password
from config import settings
from models import Usuario

router = APIRouter()


# =========================================================
# ESQUEMA
# rol = perfil elegido en el onboarding:
#  'estudiante' | 'empleado' | 'independiente' | 'emprendedor'
# =========================================================

class PerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    ingreso_mensual: Optional[float] = None
    meta_ahorro: Optional[float] = None
    fecha_salario: Optional[str] = None
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
    usuario = db.get(Usuario, int(usuario_id))

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    return {
        'id': usuario.id,
        'nombre': usuario.nombre,
        'correo': usuario.correo,
        'rol': usuario.rol,
        'ingreso_mensual': float(usuario.ingreso_mensual or 0),
        'meta_ahorro': float(usuario.meta_ahorro or 0),
        'fecha_salario': usuario.fecha_salario.strftime('%Y-%m-%d') if usuario.fecha_salario else None,
        'fecha_registro': usuario.fecha_registro.strftime('%d/%m/%Y') if usuario.fecha_registro else None,
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
    usuario = db.get(Usuario, int(usuario_id))

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    if body.nombre:
        usuario.nombre = body.nombre

    if body.rol is not None:
        if body.rol not in settings.ROLES:
            raise HTTPException(status_code=400, detail=f"❌ Rol inválido. Opciones: {', '.join(settings.ROLES)}")
        usuario.rol = body.rol

    if body.ingreso_mensual is not None:
        usuario.ingreso_mensual = body.ingreso_mensual

    if body.meta_ahorro is not None:
        usuario.meta_ahorro = body.meta_ahorro

    if body.fecha_salario is not None:
        try:
            usuario.fecha_salario = (
                datetime.strptime(body.fecha_salario, '%Y-%m-%d').date() if body.fecha_salario else None
            )
        except ValueError:
            raise HTTPException(status_code=400, detail='❌ fecha_salario debe tener formato AAAA-MM-DD.')

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
