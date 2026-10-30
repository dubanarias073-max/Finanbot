# routes/perfil.py
from datetime import datetime
from io import BytesIO
import math
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
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
        'tiene_foto_perfil': bool(usuario.foto_perfil),
    }


@router.post('/foto')
async def actualizar_foto_perfil(
    archivo: UploadFile = File(...),
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    usuario = db.get(Usuario, int(usuario_id))
    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    contenido = await archivo.read(6 * 1024 * 1024 + 1)
    if len(contenido) > 6 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='La imagen no puede superar 6 MB.')
    try:
        imagen = Image.open(BytesIO(contenido))
        imagen.seek(0)
        if imagen.width > 8000 or imagen.height > 8000 or imagen.width * imagen.height > 25_000_000:
            raise HTTPException(status_code=400, detail='La imagen es demasiado grande en dimensiones.')
        imagen.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail='El archivo no contiene una imagen válida.')

    imagen.thumbnail((512, 512))
    if imagen.mode not in ('RGB',):
        imagen = imagen.convert('RGB')
    nombre_archivo = f'{uuid.uuid4().hex}.jpg'
    carpeta = settings.UPLOADS_DIR / 'perfiles' / str(usuario.id)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre_archivo
    imagen.save(destino, format='JPEG', quality=88, optimize=True)

    foto_anterior = usuario.foto_perfil
    usuario.foto_perfil = nombre_archivo
    try:
        db.commit()
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        raise
    if foto_anterior:
        anterior = carpeta / Path(foto_anterior).name
        if anterior.is_file():
            anterior.unlink()
    return {'mensaje': 'Foto de perfil actualizada.'}


@router.get('/foto')
def obtener_foto_perfil(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    usuario = db.get(Usuario, int(usuario_id))
    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    if not usuario.foto_perfil:
        raise HTTPException(status_code=404, detail='No hay foto de perfil.')
    carpeta = settings.UPLOADS_DIR / 'perfiles' / str(usuario.id)
    ruta = carpeta / Path(usuario.foto_perfil).name
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail='No se encontró la foto de perfil.')
    return FileResponse(ruta, media_type='image/jpeg')


@router.delete('/foto')
def eliminar_foto_perfil(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    usuario = db.get(Usuario, int(usuario_id))
    if not usuario:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    nombre_archivo = usuario.foto_perfil
    usuario.foto_perfil = None
    db.commit()
    if nombre_archivo:
        ruta = settings.UPLOADS_DIR / 'perfiles' / str(usuario.id) / Path(nombre_archivo).name
        if ruta.is_file():
            ruta.unlink()
    return {'mensaje': 'Foto de perfil eliminada.'}


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

    ingreso_mensual = (
        body.ingreso_mensual
        if body.ingreso_mensual is not None
        else float(usuario.ingreso_mensual or 0)
    )
    if body.ingreso_mensual is not None and (
        not math.isfinite(body.ingreso_mensual) or body.ingreso_mensual < 10000
    ):
        raise HTTPException(status_code=400, detail='El ingreso mensual debe ser de al menos $10.000.')
    if body.onboarding_completado is True and ingreso_mensual < 10000:
        raise HTTPException(status_code=400, detail='Debes ingresar un monto mensual de al menos $10.000 para completar el onboarding.')

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

    if 'fecha_salario' in body.model_fields_set:
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
