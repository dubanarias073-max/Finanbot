# routes/transacciones.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import extract

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Transaccion, Categoria

router = APIRouter()


# =========================================================
# ESQUEMAS
# =========================================================

class TransaccionCreate(BaseModel):
    tipo: str
    categoria: str
    monto: float
    fecha: str
    descripcion: Optional[str] = ''
    icono: Optional[str] = '💸'

class TransaccionUpdate(BaseModel):
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    monto: Optional[float] = None
    descripcion: Optional[str] = None
    fecha: Optional[str] = None
    icono: Optional[str] = '💸'


# =========================================================
# OBTENER TODAS
# Ya NO gestiona ni borra "períodos". Simplemente devuelve las
# transacciones del usuario. Cada mes existe solo porque tiene
# transacciones con esa fecha — nada se archiva ni se elimina
# automáticamente al cambiar de mes.
# =========================================================

@router.get('/')
def obtener_transacciones(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    transacciones = (db.query(Transaccion).filter_by(usuario_id=uid)
                      .order_by(Transaccion.fecha.desc()).all())

    resultado = []
    for t in transacciones:
        resultado.append({
            'id': t.id,
            'tipo': t.tipo,
            'categoria': t.categoria.nombre if t.categoria else '',
            'icono': t.categoria.icono if t.categoria else '💸',
            'monto': float(t.monto),
            'descripcion': t.descripcion or '',
            'fecha': str(t.fecha),
        })

    return resultado


# =========================================================
# CREAR
# =========================================================

@router.post('/', status_code=201)
def crear_transaccion(
    body: TransaccionCreate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)

    categoria = db.query(Categoria).filter_by(nombre=body.categoria).first()
    if not categoria:
        categoria = Categoria(nombre=body.categoria, tipo=body.tipo, icono=body.icono)
        db.add(categoria)
        db.flush()

    nueva = Transaccion(
        usuario_id=uid,
        categoria_id=categoria.id,
        tipo=body.tipo,
        monto=body.monto,
        descripcion=body.descripcion,
        fecha=datetime.strptime(body.fecha, '%Y-%m-%d').date()
    )

    db.add(nueva)
    db.commit()

    return {'mensaje': '✅ Transacción guardada!', 'id': nueva.id}


# =========================================================
# EDITAR
# =========================================================

@router.put('/{id}')
def editar_transaccion(
    id: int,
    body: TransaccionUpdate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)

    transaccion = db.query(Transaccion).filter_by(id=id, usuario_id=uid).first()
    if not transaccion:
        raise HTTPException(status_code=404, detail='Transacción no encontrada')

    if body.tipo is not None:
        transaccion.tipo = body.tipo

    if body.categoria is not None:
        tipo_para_cat = body.tipo or transaccion.tipo
        categoria = db.query(Categoria).filter_by(nombre=body.categoria).first()
        if not categoria:
            categoria = Categoria(nombre=body.categoria, tipo=tipo_para_cat, icono=body.icono)
            db.add(categoria)
            db.flush()
        transaccion.categoria_id = categoria.id

    if body.monto is not None:
        if body.monto <= 0:
            raise HTTPException(status_code=400, detail='El monto debe ser mayor a cero')
        transaccion.monto = body.monto

    if body.descripcion is not None:
        transaccion.descripcion = body.descripcion

    if body.fecha is not None:
        try:
            transaccion.fecha = datetime.strptime(body.fecha, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail='Formato de fecha inválido. Usa YYYY-MM-DD')

    db.commit()

    return {
        'mensaje': '✅ Transacción actualizada!',
        'id': transaccion.id,
        'tipo': transaccion.tipo,
        'categoria': transaccion.categoria.nombre if transaccion.categoria else '',
        'icono': transaccion.categoria.icono if transaccion.categoria else '💸',
        'monto': float(transaccion.monto),
        'descripcion': transaccion.descripcion or '',
        'fecha': str(transaccion.fecha),
    }


# =========================================================
# PERIODOS (Comparar meses) — calculados al vuelo desde
# Transaccion.fecha. Ya no se archiva ni se borra nada solo:
# un mes "existe" en esta lista porque tiene transacciones con
# esa fecha, punto. Ningún mes desaparece por sí solo.
# =========================================================

@router.get('/periodos')
def obtener_periodos(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    hoy = datetime.now().date()

    transacciones = db.query(Transaccion).filter_by(usuario_id=uid).all()

    buckets = {}
    for t in transacciones:
        key = (t.fecha.year, t.fecha.month)
        b = buckets.setdefault(key, {'ingresos': 0.0, 'gastos': 0.0})
        if t.tipo == 'ingreso':
            b['ingresos'] += float(t.monto)
        elif t.tipo == 'gasto':
            b['gastos'] += float(t.monto)

    resultado = []
    for (anio, mes), datos in sorted(buckets.items(), reverse=True):
        resultado.append({
            'id': anio * 100 + mes,  # identificador estable (ej. 202608)
            'anio': anio,
            'mes': mes,
            'activo': (anio == hoy.year and mes == hoy.month),
            'label': f'{mes:02d}/{anio}',
            'ingresos_total': datos['ingresos'],
            'gastos_total': datos['gastos'],
            'balance': datos['ingresos'] - datos['gastos'],
        })

    return resultado


@router.post('/periodos/reset')
def reset_periodo_actual(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    """Borra SOLO las transacciones del mes actual. Los meses pasados
    nunca se tocan."""
    uid = int(usuario_id)
    hoy = datetime.now().date()

    borradas = (
        db.query(Transaccion)
        .filter(Transaccion.usuario_id == uid)
        .filter(extract('year', Transaccion.fecha) == hoy.year)
        .filter(extract('month', Transaccion.fecha) == hoy.month)
        .delete(synchronize_session=False)
    )
    db.commit()

    return {'mensaje': f'✅ Mes actual reiniciado ({borradas} movimientos eliminados)'}


@router.delete('/periodos/{id}')
def eliminar_periodo(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    """id viene como anio*100+mes (ej. 202608 = agosto 2026). Borra
    SOLO las transacciones de ese año/mes puntual; el resto de meses
    queda intacto."""
    uid = int(usuario_id)
    anio, mes = divmod(id, 100)
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail='Identificador de periodo inválido')

    borradas = (
        db.query(Transaccion)
        .filter(Transaccion.usuario_id == uid)
        .filter(extract('year', Transaccion.fecha) == anio)
        .filter(extract('month', Transaccion.fecha) == mes)
        .delete(synchronize_session=False)
    )
    if borradas == 0:
        raise HTTPException(status_code=404, detail='No hay movimientos en ese periodo')
    db.commit()

    return {'mensaje': '✅ Periodo eliminado'}


# =========================================================
# ELIMINAR TRANSACCIÓN
# =========================================================

@router.delete('/{id}')
def eliminar_transaccion(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    transaccion = db.query(Transaccion).filter_by(id=id, usuario_id=uid).first()

    if not transaccion:
        raise HTTPException(status_code=404, detail='Transacción no encontrada')

    db.delete(transaccion)
    db.commit()

    return {'mensaje': '✅ Transacción eliminada!'}