# routes/transacciones.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import extract

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import (
    Transaccion, Categoria, Tienda, eliminar_tiendas_sin_transacciones,
    CATEGORIAS, normalizar_categoria, icono_categoria,
)

router = APIRouter()


# =========================================================
# ESQUEMAS
# =========================================================

class TransaccionCreate(BaseModel):
    tipo: str
    categoria: str          # nombre de una fila de la tabla categorias
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


def _validar_categoria(nombre: str, db: Session) -> str:
    """Valida contra la tabla `categorias` y devuelve el nombre exacto del
    catálogo (MySQL compara sin importar mayúsculas ni tildes)."""
    texto = (nombre or '').strip()
    cat = db.query(Categoria).filter(Categoria.nombre == texto).first() if texto else None
    if not cat:
        opciones = [n for (n,) in db.query(Categoria.nombre).order_by(Categoria.id).all()] or list(CATEGORIAS)
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Opciones: {', '.join(opciones)}")
    return cat.nombre


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


def _commit(db: Session):
    """Commit con mensaje claro si la FK de categoría o tienda falla."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail='Categoría no válida o dato inconsistente')


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
        'tienda_id': t.tienda_id,   # lo asigna el trigger de MySQL
    }


# =========================================================
# CATEGORÍAS (desde la tabla `categorias`)
# =========================================================

@router.get('/categorias')
def listar_categorias(db: Session = Depends(get_db)):
    """Catálogo de categorías agrupado por tipo (para llenar selects)."""
    filas = db.query(Categoria).order_by(Categoria.id).all()
    resultado = {'gasto': [], 'ingreso': [], 'meta': []}
    for c in filas:
        resultado[c.tipo].append({'id': c.id, 'nombre': c.nombre, 'icono': c.icono})
    return resultado


# =========================================================
# TIENDAS — lugares del usuario con sus totales (ranking del mapa).
# URL: GET /api/transacciones/tiendas
# =========================================================

@router.get('/tiendas')
def listar_tiendas(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    tiendas = db.query(Tienda).filter_by(usuario_id=uid).all()
    totales = {t.id: {'movimientos': 0, 'gastos': 0.0, 'ingresos': 0.0, 'ultimo': None} for t in tiendas}

    movs = (db.query(Transaccion)
            .filter(Transaccion.usuario_id == uid)
            .filter(Transaccion.tienda_id.isnot(None))
            .all())
    for m in movs:
        acc = totales.get(m.tienda_id)
        if acc is None:
            continue
        acc['movimientos'] += 1
        if m.tipo == 'gasto':
            acc['gastos'] += float(m.monto)
        else:
            acc['ingresos'] += float(m.monto)
        if acc['ultimo'] is None or m.fecha > acc['ultimo']:
            acc['ultimo'] = m.fecha

    salida = [{
        'id': t.id,
        'nombre': t.nombre,
        'latitud': float(t.latitud),
        'longitud': float(t.longitud),
        'total_movimientos': totales[t.id]['movimientos'],
        'total_gastos': totales[t.id]['gastos'],
        'total_ingresos': totales[t.id]['ingresos'],
        'ultimo_movimiento': str(totales[t.id]['ultimo']) if totales[t.id]['ultimo'] else None,
    } for t in tiendas]
    return sorted(salida, key=lambda x: x['total_gastos'] + x['total_ingresos'], reverse=True)


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
    categoria = _validar_categoria(body.categoria, db)
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
    _commit(db)
    db.refresh(nueva)   # trae el tienda_id que asignó el trigger

    return {'mensaje': '✅ Transacción guardada!', 'id': nueva.id, 'tienda_id': nueva.tienda_id}


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
        transaccion.categoria = _validar_categoria(body.categoria, db)

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

    _commit(db)
    db.refresh(transaccion)   # trae el tienda_id que asignó el trigger

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

    query = (
        db.query(Transaccion)
        .filter(Transaccion.usuario_id == uid)
        .filter(extract('year', Transaccion.fecha) == hoy.year)
        .filter(extract('month', Transaccion.fecha) == hoy.month)
    )
    tienda_ids = [tienda_id for (tienda_id,) in query.with_entities(Transaccion.tienda_id).all()]
    borradas = query.delete(synchronize_session=False)
    eliminar_tiendas_sin_transacciones(db, tienda_ids)
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

    query = (
        db.query(Transaccion)
        .filter(Transaccion.usuario_id == uid)
        .filter(extract('year', Transaccion.fecha) == anio)
        .filter(extract('month', Transaccion.fecha) == mes)
    )
    tienda_ids = [tienda_id for (tienda_id,) in query.with_entities(Transaccion.tienda_id).all()]
    borradas = query.delete(synchronize_session=False)
    if borradas == 0:
        raise HTTPException(status_code=404, detail='No hay movimientos en ese periodo')
    eliminar_tiendas_sin_transacciones(db, tienda_ids)
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

    tienda_id = transaccion.tienda_id
    db.delete(transaccion)
    eliminar_tiendas_sin_transacciones(db, [tienda_id])
    db.commit()

    return {'mensaje': '✅ Transacción eliminada!'}