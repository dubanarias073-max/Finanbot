# routes/metas.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import MetaAhorro

router = APIRouter()


# =========================================================
# ESQUEMAS
# =========================================================

class MetaCreate(BaseModel):
    nombre: str
    monto_objetivo: float
    monto_actual: Optional[float] = 0
    fecha_limite: Optional[str] = None

class MetaUpdate(BaseModel):
    nombre: Optional[str] = None
    monto_actual: Optional[float] = None


# =========================================================
# OBTENER TODAS
# =========================================================

@router.get('/')
def obtener_metas(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    metas = db.query(MetaAhorro).filter_by(usuario_id=uid).all()

    resultado = []
    for m in metas:
        porcentaje = min(round((float(m.monto_actual) / float(m.monto_objetivo)) * 100), 100) if m.monto_objetivo > 0 else 0
        resultado.append({
            'id': m.id,
            'nombre': m.nombre,
            'monto_objetivo': float(m.monto_objetivo),
            'monto_actual': float(m.monto_actual),
            'porcentaje': porcentaje,
            'completada': m.completada,
            'fecha_limite': str(m.fecha_limite) if m.fecha_limite else None
        })

    return resultado


# =========================================================
# CREAR
# =========================================================

@router.post('/', status_code=201)
def crear_meta(
    body: MetaCreate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)

    nueva = MetaAhorro(
        usuario_id=uid,
        nombre=body.nombre,
        monto_objetivo=body.monto_objetivo,
        monto_actual=body.monto_actual,
        fecha_limite=datetime.strptime(body.fecha_limite, '%Y-%m-%d').date() if body.fecha_limite else None
    )

    db.add(nueva)
    db.commit()

    return {'mensaje': '✅ Meta creada!', 'id': nueva.id}


# =========================================================
# ACTUALIZAR
# =========================================================

@router.put('/{id}')
def actualizar_meta(
    id: int,
    body: MetaUpdate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    meta = db.query(MetaAhorro).filter_by(id=id, usuario_id=uid).first()

    if not meta:
        raise HTTPException(status_code=404, detail='Meta no encontrada')

    if body.monto_actual is not None:
        meta.monto_actual = body.monto_actual
        if meta.monto_actual >= float(meta.monto_objetivo):
            meta.completada = True

    if body.nombre:
        meta.nombre = body.nombre

    db.commit()
    return {'mensaje': '✅ Meta actualizada!'}


# =========================================================
# ELIMINAR
# =========================================================

@router.delete('/{id}')
def eliminar_meta(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    meta = db.query(MetaAhorro).filter_by(id=id, usuario_id=uid).first()

    if not meta:
        raise HTTPException(status_code=404, detail='Meta no encontrada')

    db.delete(meta)
    db.commit()
    return {'mensaje': '✅ Meta eliminada!'}