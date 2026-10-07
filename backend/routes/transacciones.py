# routes/transacciones.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import extract, func
import json
import time
import threading
import urllib.parse
import urllib.request

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import (
    Transaccion, Categoria, CategoriaUsuario, Tienda, eliminar_tiendas_sin_transacciones,
    CATEGORIAS, CATEGORIAS_GASTO, CATEGORIAS_INGRESO, ICONOS_CATEGORIA,
    normalizar_categoria, icono_categoria,
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


def _validar_categoria(nombre: str, db: Session, uid: int) -> str:
    """Valida contra la tabla `categorias` y devuelve el nombre exacto del
    catálogo (MySQL compara sin importar mayúsculas ni tildes)."""
    texto = (nombre or '').strip()
    cat = db.query(Categoria).filter(Categoria.nombre == texto).first() if texto else None
    if not cat:
        opciones = [n for (n,) in db.query(Categoria.nombre).order_by(Categoria.id).all()] or list(CATEGORIAS)
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Opciones: {', '.join(opciones)}")
    eliminada = db.query(CategoriaUsuario.id).filter_by(
        usuario_id=uid, nombre=cat.nombre, eliminada=True,
    ).first()
    if eliminada:
        raise HTTPException(status_code=400, detail=f'La categoría "{cat.nombre}" fue eliminada')
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
        'icono': t.icono,
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

class CategoriaCrear(BaseModel):
    nombre: str
    tipo: str                      # 'gasto' | 'ingreso'
    icono: Optional[str] = None


class CategoriaCambiar(BaseModel):
    oculta: Optional[bool] = None  # ocultar / mostrar
    icono: Optional[str] = None    # solo para las personalizadas


_DEFECTO = {'gasto': CATEGORIAS_GASTO, 'ingreso': CATEGORIAS_INGRESO}
_OTROS = {'gasto': 'Otros gastos', 'ingreso': 'Otros ingresos'}


def _limpiar_nombre(nombre: str) -> str:
    n = ' '.join((nombre or '').split())[:50]
    if len(n) < 2:
        raise HTTPException(status_code=400, detail='El nombre debe tener al menos 2 letras')
    return n[:1].upper() + n[1:]


def _limpiar_icono(icono, tipo) -> str:
    ic = (icono or '').strip()
    return ic[:10] if ic else ('🏷️' if tipo == 'gasto' else '💰')


def _mis_categorias(uid: int, db: Session) -> dict:
    """Categorías del usuario: por defecto (marcando las ocultas) + personalizadas."""
    propias = db.query(CategoriaUsuario).filter_by(usuario_id=uid).all()
    ocultas = {c.nombre for c in propias if c.oculta}
    eliminadas = {c.nombre for c in propias if c.eliminada}
    usos = dict(
        db.query(Transaccion.categoria, func.count(Transaccion.id))
        .filter(Transaccion.usuario_id == uid).group_by(Transaccion.categoria).all()
    )
    resultado = {'gasto': [], 'ingreso': []}
    for tipo, nombres in _DEFECTO.items():
        for n in nombres:
            if n in eliminadas:
                continue
            resultado[tipo].append({
                'nombre': n, 'icono': ICONOS_CATEGORIA.get(n, '💸'), 'tipo': tipo,
                'personalizada': False, 'oculta': n in ocultas,
                'protegida': n == _OTROS[tipo],          # "Otros" no se puede ocultar
                'movimientos': usos.get(n, 0),
            })
    for c in sorted((c for c in propias if c.personalizada), key=lambda c: c.id):
        item = {'nombre': c.nombre, 'icono': c.icono, 'tipo': c.tipo, 'personalizada': True,
                'oculta': bool(c.oculta), 'protegida': False, 'movimientos': usos.get(c.nombre, 0)}
        # va antes de "Otros …" para que ese quede siempre de último
        lista = resultado[c.tipo]
        lista.insert(len(lista) - 1, item)
    return resultado


# URL: GET /api/transacciones/categorias/mias
@router.get('/categorias/mias')
def listar_mis_categorias(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    return _mis_categorias(int(usuario_id), db)


# URL: POST /api/transacciones/categorias/mias
@router.post('/categorias/mias', status_code=201)
def crear_mi_categoria(
    body: CategoriaCrear,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    _validar_tipo(body.tipo)
    nombre = _limpiar_nombre(body.nombre)
    icono = _limpiar_icono(body.icono, body.tipo)

    # ¿Ya existe ese nombre en el catálogo? (MySQL compara sin mayúsculas/tildes)
    existente = db.query(Categoria).filter(Categoria.nombre == nombre).first()
    if existente:
        nombre = existente.nombre
        if nombre in CATEGORIAS:
            # Las categorías predeterminadas se pueden restaurar al agregarlas de nuevo.
            fila = db.query(CategoriaUsuario).filter_by(usuario_id=uid, nombre=nombre).first()
            if fila and fila.eliminada and existente.tipo == body.tipo:
                fila.eliminada = False
                fila.oculta = False
                db.commit()
                return {'mensaje': f'"{nombre}" ya existía y la restauré', 'nombre': nombre}
            if fila and fila.oculta and existente.tipo == body.tipo:
                db.delete(fila)
                db.commit()
                return {'mensaje': f'"{nombre}" ya existía y la volví a mostrar', 'nombre': nombre}
            raise HTTPException(status_code=400, detail=f'"{nombre}" ya es una categoría de FinanBot')
        if existente.tipo != body.tipo:
            raise HTTPException(status_code=400,
                                detail=f'Ya existe "{nombre}" como categoría de {existente.tipo}. Usa otro nombre.')
    else:
        db.add(Categoria(nombre=nombre, tipo=body.tipo, icono=icono))
        db.flush()

    fila = db.query(CategoriaUsuario).filter_by(usuario_id=uid, nombre=nombre).first()
    if fila:
        if not fila.oculta:
            raise HTTPException(status_code=400, detail=f'Ya tienes la categoría "{nombre}"')
        fila.oculta = False
        fila.icono = icono
    else:
        db.add(CategoriaUsuario(usuario_id=uid, nombre=nombre, tipo=body.tipo,
                                icono=icono, personalizada=True, oculta=False))
    _commit(db)
    return {'mensaje': f'✅ Categoría "{nombre}" creada', 'nombre': nombre, 'icono': icono}


# URL: PATCH /api/transacciones/categorias/mias/{nombre}
@router.patch('/categorias/mias/{nombre}')
def cambiar_mi_categoria(
    nombre: str,
    body: CategoriaCambiar,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    fila = db.query(CategoriaUsuario).filter_by(usuario_id=uid, nombre=nombre).first()

    if nombre in CATEGORIAS_GASTO or nombre in CATEGORIAS_INGRESO:
        tipo = 'gasto' if nombre in CATEGORIAS_GASTO else 'ingreso'
        if body.oculta is not None:
            if nombre == _OTROS[tipo] and body.oculta:
                raise HTTPException(status_code=400, detail=f'"{nombre}" no se puede ocultar')
            if body.oculta and not fila:
                db.add(CategoriaUsuario(usuario_id=uid, nombre=nombre, tipo=tipo,
                                        icono=ICONOS_CATEGORIA.get(nombre, '💸'),
                                        personalizada=False, oculta=True))
            elif not body.oculta and fila:
                db.delete(fila)
    else:
        if not fila or not fila.personalizada:
            raise HTTPException(status_code=404, detail='Categoría no encontrada')
        if body.oculta is not None:
            fila.oculta = body.oculta
        if body.icono:
            fila.icono = _limpiar_icono(body.icono, fila.tipo)
    _commit(db)
    return {'mensaje': '✅ Categoría actualizada'}


# URL: DELETE /api/transacciones/categorias/mias/{nombre}
@router.delete('/categorias/mias/{nombre}')
def eliminar_mi_categoria(
    nombre: str,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    """Elimina una categoría para el usuario y conserva sus movimientos en Otros."""
    uid = int(usuario_id)
    fila = db.query(CategoriaUsuario).filter_by(usuario_id=uid, nombre=nombre).first()
    es_predeterminada = nombre in CATEGORIAS_GASTO or nombre in CATEGORIAS_INGRESO
    if fila and fila.personalizada:
        destino = _OTROS[fila.tipo]
        movidos = (db.query(Transaccion)
                   .filter(Transaccion.usuario_id == uid, Transaccion.categoria == fila.nombre)
                   .update({Transaccion.categoria: destino}, synchronize_session=False))
        db.delete(fila)
        db.flush()

        # Si nadie más la usa, se borra también del catálogo.
        otros_usuarios = db.query(CategoriaUsuario).filter(CategoriaUsuario.nombre == nombre).count()
        con_movs = db.query(Transaccion).filter(Transaccion.categoria == nombre).count()
        if not otros_usuarios and not con_movs:
            db.query(Categoria).filter(Categoria.nombre == nombre).delete(synchronize_session=False)
    elif es_predeterminada:
        tipo = 'gasto' if nombre in CATEGORIAS_GASTO else 'ingreso'
        if nombre == _OTROS[tipo]:
            raise HTTPException(status_code=400, detail=f'"{nombre}" no se puede eliminar')
        if fila and fila.eliminada:
            raise HTTPException(status_code=404, detail='Categoría no encontrada')

        destino = _OTROS[tipo]
        movidos = (db.query(Transaccion)
                   .filter(Transaccion.usuario_id == uid, Transaccion.categoria == nombre)
                   .update({Transaccion.categoria: destino}, synchronize_session=False))
        if fila:
            fila.oculta = True
            fila.eliminada = True
        else:
            db.add(CategoriaUsuario(
                usuario_id=uid, nombre=nombre, tipo=tipo,
                icono=ICONOS_CATEGORIA.get(nombre, '💸'),
                personalizada=False, oculta=True, eliminada=True,
            ))
    else:
        raise HTTPException(status_code=404, detail='Categoría no encontrada')

    _commit(db)
    return {'mensaje': f'🗑️ Categoría "{nombre}" eliminada', 'movidos': movidos, 'destino': destino}

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
# LUGARES CERCANOS — tiendas, restaurantes, bancos, farmacias…
# reales de la zona visible del mapa (como los íconos de Google
# Maps). Los datos salen de OpenStreetMap vía Overpass API:
# gratis y sin API key. Se guardan en caché unos minutos para no
# repetir consultas al mover el mapa.
# URL: GET /api/transacciones/lugares-cercanos?s=&w=&n=&e=
# =========================================================

OVERPASS_URLS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
]
_LUGARES_CACHE: dict = {}
_LUGARES_LOCK = threading.Lock()
_LUGARES_TTL = 30 * 60          # 30 minutos
_LUGARES_MAX_CACHE = 300
_LUGARES_MAX_SPAN = 0.08        # grados (~9 km): más grande = demasiados lugares
_LUGARES_MAX_RESULTADOS = 400

# etiqueta OSM -> (nombre legible, emoji, grupo de color, categoría FinanBot sugerida)
_TIPOS_SHOP = {
    'supermarket':      ('Supermercado', '🛒', 'compras', 'Alimentación'),
    'convenience':      ('Tienda', '🏪', 'compras', 'Alimentación'),
    'bakery':           ('Panadería', '🥖', 'comida', 'Alimentación'),
    'butcher':          ('Carnicería', '🥩', 'compras', 'Alimentación'),
    'greengrocer':      ('Fruver', '🥬', 'compras', 'Alimentación'),
    'beverages':        ('Licorera', '🍾', 'compras', 'Alimentación'),
    'alcohol':          ('Licorera', '🍾', 'compras', 'Alimentación'),
    'mall':             ('Centro comercial', '🛍️', 'compras', 'Otros gastos'),
    'department_store': ('Almacén', '🛍️', 'compras', 'Otros gastos'),
    'clothes':          ('Ropa', '👕', 'compras', 'Ropa'),
    'shoes':            ('Zapatos', '👟', 'compras', 'Ropa'),
    'electronics':      ('Electrónica', '📱', 'compras', 'Otros gastos'),
    'mobile_phone':     ('Celulares', '📱', 'compras', 'Otros gastos'),
    'computer':         ('Computadores', '💻', 'compras', 'Otros gastos'),
    'hardware':         ('Ferretería', '🔧', 'compras', 'Otros gastos'),
    'doityourself':     ('Ferretería', '🔧', 'compras', 'Otros gastos'),
    'pet':              ('Mascotas', '🐾', 'compras', 'Mascotas'),
    'beauty':           ('Belleza', '💅', 'compras', 'Otros gastos'),
    'hairdresser':      ('Peluquería', '💇', 'compras', 'Otros gastos'),
    'books':            ('Librería', '📚', 'educacion', 'Educación'),
    'stationery':       ('Papelería', '✏️', 'educacion', 'Educación'),
    'optician':         ('Óptica', '👓', 'salud', 'Salud'),
    'chemist':          ('Droguería', '💊', 'salud', 'Salud'),
    'gift':             ('Regalos', '🎁', 'compras', 'Regalos'),
    'toys':             ('Juguetería', '🧸', 'compras', 'Regalos'),
    'furniture':        ('Muebles', '🛋️', 'compras', 'Otros gastos'),
    'car_repair':       ('Taller', '🔧', 'transporte', 'Transporte'),
    'bicycle':          ('Bicicletas', '🚲', 'transporte', 'Transporte'),
}
_TIPOS_AMENITY = {
    'restaurant':  ('Restaurante', '🍽️', 'comida', 'Alimentación'),
    'fast_food':   ('Comida rápida', '🍔', 'comida', 'Alimentación'),
    'cafe':        ('Café', '☕', 'comida', 'Alimentación'),
    'ice_cream':   ('Heladería', '🍦', 'comida', 'Alimentación'),
    'bar':         ('Bar', '🍺', 'ocio', 'Entretenimiento'),
    'pub':         ('Bar', '🍺', 'ocio', 'Entretenimiento'),
    'nightclub':   ('Discoteca', '🪩', 'ocio', 'Entretenimiento'),
    'cinema':      ('Cine', '🎬', 'ocio', 'Entretenimiento'),
    'theatre':     ('Teatro', '🎭', 'ocio', 'Entretenimiento'),
    'bank':        ('Banco', '🏦', 'dinero', 'Otros gastos'),
    'atm':         ('Cajero', '🏧', 'dinero', 'Otros gastos'),
    'bureau_de_change': ('Casa de cambio', '💱', 'dinero', 'Otros gastos'),
    'pharmacy':    ('Farmacia', '💊', 'salud', 'Salud'),
    'hospital':    ('Hospital', '🏥', 'salud', 'Salud'),
    'clinic':      ('Clínica', '🏥', 'salud', 'Salud'),
    'doctors':     ('Consultorio', '🩺', 'salud', 'Salud'),
    'dentist':     ('Odontología', '🦷', 'salud', 'Salud'),
    'veterinary':  ('Veterinaria', '🐾', 'salud', 'Mascotas'),
    'fuel':        ('Gasolinera', '⛽', 'transporte', 'Transporte'),
    'bus_station': ('Estación', '🚌', 'transporte', 'Transporte'),
    'parking':     ('Parqueadero', '🅿️', 'transporte', 'Transporte'),
    'school':      ('Colegio', '🏫', 'educacion', 'Educación'),
    'college':     ('Instituto', '🎓', 'educacion', 'Educación'),
    'university':  ('Universidad', '🎓', 'educacion', 'Educación'),
    'marketplace': ('Plaza de mercado', '🧺', 'compras', 'Alimentación'),
    'post_office': ('Correo', '📮', 'servicios', 'Servicios'),
}
_TIPOS_TOURISM = {
    'hotel':  ('Hotel', '🏨', 'ocio', 'Viajes'),
    'hostel': ('Hostal', '🏨', 'ocio', 'Viajes'),
    'museum': ('Museo', '🏛️', 'ocio', 'Entretenimiento'),
}


def _consultar_overpass(s: float, w: float, n: float, e: float) -> list:
    bbox = f'{s},{w},{n},{e}'
    amenities = '|'.join(_TIPOS_AMENITY)
    query = f"""
[out:json][timeout:20];
(
  nwr["shop"]["name"]({bbox});
  nwr["amenity"~"^({amenities})$"]["name"]({bbox});
  nwr["tourism"~"^(hotel|hostel|museum)$"]["name"]({bbox});
);
out center {_LUGARES_MAX_RESULTADOS * 2};
"""
    datos = urllib.parse.urlencode({'data': query}).encode()
    ultimo_error = None
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(url, data=datos, headers={
                'User-Agent': 'FinanBot/1.0 (proyecto educativo SENA)',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode('utf-8')).get('elements', [])
        except Exception as err:      # se prueba el siguiente servidor
            ultimo_error = err
    raise HTTPException(status_code=503, detail=f'No se pudieron cargar los lugares del mapa ({ultimo_error})')


def _formatear_lugar(el: dict):
    tags = el.get('tags') or {}
    nombre = (tags.get('name') or '').strip()
    lat = el.get('lat') or (el.get('center') or {}).get('lat')
    lng = el.get('lon') or (el.get('center') or {}).get('lon')
    if not nombre or lat is None or lng is None:
        return None

    if tags.get('amenity') in _TIPOS_AMENITY:
        etiqueta, emoji, grupo, cat = _TIPOS_AMENITY[tags['amenity']]
    elif tags.get('tourism') in _TIPOS_TOURISM:
        etiqueta, emoji, grupo, cat = _TIPOS_TOURISM[tags['tourism']]
    elif 'shop' in tags:
        etiqueta, emoji, grupo, cat = _TIPOS_SHOP.get(tags['shop'], ('Tienda', '🛍️', 'compras', 'Otros gastos'))
    else:
        return None

    calle = tags.get('addr:street') or ''
    numero = tags.get('addr:housenumber') or ''
    direccion = f'{calle} # {numero}'.strip(' #') if calle else (tags.get('addr:full') or '')

    return {
        'id': f"{el.get('type', 'n')[0]}{el.get('id')}",
        'nombre': nombre[:120],
        'latitud': round(float(lat), 7),
        'longitud': round(float(lng), 7),
        'tipo': etiqueta,
        'emoji': emoji,
        'grupo': grupo,                     # comida | compras | salud | dinero | transporte | ocio | educacion | servicios
        'categoria_sugerida': cat,          # categoría de gasto de FinanBot
        'direccion': direccion,
        'horario': tags.get('opening_hours') or '',
        'telefono': tags.get('phone') or tags.get('contact:phone') or '',
        'web': tags.get('website') or tags.get('contact:website') or '',
        'marca': tags.get('brand') or '',
    }


@router.get('/lugares-cercanos')
def lugares_cercanos(
    s: float, w: float, n: float, e: float,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
):
    """Lugares con nombre (tiendas, restaurantes, bancos, farmacias,
    gasolineras…) dentro del rectángulo visible del mapa."""
    if not (-90 <= s < n <= 90) or not (-180 <= w < e <= 180):
        raise HTTPException(status_code=400, detail='Rectángulo de mapa inválido')
    if (n - s) > _LUGARES_MAX_SPAN or (e - w) > _LUGARES_MAX_SPAN:
        raise HTTPException(status_code=400, detail='Acércate más al mapa para ver los lugares')

    # Se redondea el rectángulo para que pequeños movimientos del mapa
    # reutilicen la misma consulta guardada en caché.
    s_r, w_r = round(s - 0.002, 3), round(w - 0.002, 3)
    n_r, e_r = round(n + 0.002, 3), round(e + 0.002, 3)
    clave = (s_r, w_r, n_r, e_r)
    ahora = time.time()

    with _LUGARES_LOCK:
        guardado = _LUGARES_CACHE.get(clave)
        if guardado and ahora - guardado[0] < _LUGARES_TTL:
            return guardado[1]

    vistos, lugares = set(), []
    for el in _consultar_overpass(s_r, w_r, n_r, e_r):
        lugar = _formatear_lugar(el)
        if not lugar or lugar['id'] in vistos:
            continue
        vistos.add(lugar['id'])
        lugares.append(lugar)
        if len(lugares) >= _LUGARES_MAX_RESULTADOS:
            break

    with _LUGARES_LOCK:
        if len(_LUGARES_CACHE) >= _LUGARES_MAX_CACHE:
            for k in sorted(_LUGARES_CACHE, key=lambda k: _LUGARES_CACHE[k][0])[:50]:
                _LUGARES_CACHE.pop(k, None)
        _LUGARES_CACHE[clave] = (ahora, lugares)

    return lugares


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
    categoria = _validar_categoria(body.categoria, db, uid)
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
        transaccion.categoria = _validar_categoria(body.categoria, db, uid)

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