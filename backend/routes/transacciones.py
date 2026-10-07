# routes/transacciones.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import extract

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Transaccion, CATEGORIAS, normalizar_categoria, icono_categoria

router = APIRouter()


# =========================================================
# ESQUEMAS
# =========================================================

class TransaccionCreate(BaseModel):
    tipo: str
    categoria: str          # una de models.CATEGORIAS
    monto: float
    fecha: str
    descripcion: Optional[str] = ''
    icono: Optional[str] = None   # se ignora: el icono sale de la categoría
    # Ubicación opcional (dónde se hizo el gasto/ingreso)
    ubicacion_nombre: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class TransaccionUpdate(BaseModel):
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    monto: Optional[float] = None
    descripcion: Optional[str] = None
    fecha: Optional[str] = None
    icono: Optional[str] = None   # se ignora: el icono sale de la categoría
    ubicacion_nombre: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    quitar_ubicacion: Optional[bool] = False   # True = borrar la ubicación guardada


def _validar_tipo(tipo: str):
    if tipo not in ('gasto', 'ingreso'):
        raise HTTPException(status_code=400, detail="tipo debe ser 'gasto' o 'ingreso'")


def _validar_categoria(nombre: str) -> str:
    cat = next((c for c in CATEGORIAS if c.lower() == (nombre or '').strip().lower()), None)
    if not cat:
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Opciones: {', '.join(CATEGORIAS)}")
    return cat


def _validar_ubicacion(lat, lng, nombre):
    """Devuelve (nombre, lat, lng) validados, o (None, None, None) si no
    se envió ubicación. Latitud y longitud deben ir juntas."""
    if lat is None and lng is None:
        return None, None, None
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail='Envía latitud y longitud juntas')
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail='Coordenadas fuera de rango')
    nombre = (nombre or '').strip()[:255] or None
    return nombre, round(lat, 7), round(lng, 7)


def _transaccion_dict(t: Transaccion) -> dict:
    return {
        'id': t.id,
        'tipo': t.tipo,
        'categoria': t.categoria,
        'icono': icono_categoria(t.categoria, t.tipo),
        'monto': float(t.monto),
        'descripcion': t.descripcion or '',
        'fecha': str(t.fecha),
        'ubicacion_nombre': t.ubicacion_nombre,
        'latitud': float(t.latitud) if t.latitud is not None else None,
        'longitud': float(t.longitud) if t.longitud is not None else None,
    }


@router.get('/categorias')
def listar_categorias():
    """Lista fija de categorías (para llenar selects en el frontend)."""
    from models import CATEGORIAS_GASTO, CATEGORIAS_INGRESO
    return {
        'gasto':   [{'nombre': c, 'icono': icono_categoria(c, 'gasto')} for c in CATEGORIAS_GASTO],
        'ingreso': [{'nombre': c, 'icono': icono_categoria(c, 'ingreso')} for c in CATEGORIAS_INGRESO],
    }


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

    return [_transaccion_dict(t) for t in transacciones]


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

    _validar_tipo(body.tipo)
    categoria = _validar_categoria(body.categoria)
    if body.monto == 0:
        raise HTTPException(status_code=400, detail='El monto no puede ser cero')
    try:
        fecha = datetime.strptime(body.fecha, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail='Formato de fecha inválido. Usa YYYY-MM-DD')

    ubic_nombre, lat, lng = _validar_ubicacion(body.latitud, body.longitud, body.ubicacion_nombre)

    nueva = Transaccion(
        usuario_id=uid,
        categoria=categoria,
        tipo=body.tipo,
        monto=body.monto,
        descripcion=body.descripcion,
        fecha=fecha,
        ubicacion_nombre=ubic_nombre,
        latitud=lat,
        longitud=lng,
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
        _validar_tipo(body.tipo)
        transaccion.tipo = body.tipo

    if body.categoria is not None:
        transaccion.categoria = _validar_categoria(body.categoria)

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

    if body.quitar_ubicacion:
        transaccion.ubicacion_nombre = None
        transaccion.latitud = None
        transaccion.longitud = None
    elif body.latitud is not None or body.longitud is not None:
        nombre, lat, lng = _validar_ubicacion(body.latitud, body.longitud, body.ubicacion_nombre)
        transaccion.ubicacion_nombre = nombre
        transaccion.latitud = lat
        transaccion.longitud = lng

    db.commit()

    return {'mensaje': '✅ Transacción actualizada!', **_transaccion_dict(transaccion)}


# =========================================================
# UBICACIONES — solo los movimientos que tienen coordenadas,
# para pintarlos en el mapa (tipo Google Maps).
# Debe ir ANTES de '/{id}' para que FastAPI no lo confunda.
# =========================================================

@router.get('/ubicaciones')
def obtener_ubicaciones(
    tipo: Optional[str] = None,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    q = (db.query(Transaccion)
         .filter(Transaccion.usuario_id == uid)
         .filter(Transaccion.latitud.isnot(None))
         .filter(Transaccion.longitud.isnot(None)))
    if tipo:
        _validar_tipo(tipo)
        q = q.filter(Transaccion.tipo == tipo)
    return [_transaccion_dict(t) for t in q.order_by(Transaccion.fecha.desc()).all()]


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