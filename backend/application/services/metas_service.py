# application/services/metas_service.py
# ══════════════════════════════════════════════════════════════════
#  Movimientos de dinero de las metas y procesos automáticos.
#
#  Antes el navegador hacía estos pasos con varias peticiones seguidas
#  (actualizar la meta, crear el gasto, borrar transacciones…). Si una
#  fallaba a la mitad, el saldo quedaba descuadrado, y cualquiera podía
#  mandar el total que quisiera. Ahora todo pasa aquí, en el servidor y
#  en una sola transacción de base de datos.
#
#  Lo usan: routes/metas.py (la web), routes/chat_route.py (reglas del
#  chat) y finanbot_tools.py (herramientas de la IA).
# ══════════════════════════════════════════════════════════════════
from __future__ import annotations

import calendar
import threading
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import CategoriaUsuario, MetaAhorro, Transaccion, Usuario
from timezone import bogota_today

TAG_SALARIO = '__auto_salario__'
MONTO_MAX = 10 ** 9            # el modelo guarda Numeric(10, 2)


def tag_auto(meta_id: int) -> str:
    return f'__auto_meta_{meta_id}__'


def tag_manual(meta_id: int) -> str:
    return f'__manual_meta_{meta_id}__'


def tag_ajuste(meta_id: int) -> str:
    return f'__ajuste_meta_{meta_id}__'


def tags_de_meta(meta_id: int) -> tuple[str, str, str]:
    return tag_auto(meta_id), tag_manual(meta_id), tag_ajuste(meta_id)


def es_tag_reservado(descripcion: str | None) -> bool:
    """Etiquetas internas que solo crea el servidor (no se aceptan desde la web)."""
    d = descripcion or ''
    return TAG_SALARIO in d or ('__' in d and '_meta_' in d)


class MetaError(ValueError):
    """Error de validación con un mensaje listo para mostrar a la persona."""


# ── utilidades ───────────────────────────────────────────────────

def _monto_valido(valor, *, permitir_cero: bool = False) -> float:
    try:
        monto = round(float(valor), 2)
    except (TypeError, ValueError):
        raise MetaError('El monto no es un número válido.')
    if monto < 0 or (monto == 0 and not permitir_cero):
        raise MetaError('El monto debe ser mayor que cero.')
    if monto > MONTO_MAX:
        raise MetaError('El monto es demasiado grande.')
    return monto


def _mes(hoy: date) -> tuple[date, date]:
    inicio = hoy.replace(day=1)
    fin = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    return inicio, fin


def dia_en_mes(anio: int, mes: int, dia: int) -> int:
    """Ajusta el día al último del mes (ej. día 31 en noviembre → 30)."""
    return min(max(1, int(dia)), calendar.monthrange(anio, mes)[1])


def _transacciones_de_meta(db: Session, uid: int, meta_id: int):
    return db.query(Transaccion).filter(
        Transaccion.usuario_id == uid,
        or_(*[Transaccion.descripcion == t for t in tags_de_meta(meta_id)]),
    )


def _crear_movimiento(db: Session, uid: int, tipo: str, categoria: str, monto: float,
                      descripcion: str, fecha: date) -> Transaccion:
    t = Transaccion(usuario_id=uid, tipo=tipo, categoria=categoria, monto=monto,
                    descripcion=descripcion, fecha=fecha)
    db.add(t)
    return t


def obtener_meta(db: Session, uid: int, meta_id: int) -> MetaAhorro:
    meta = db.get(MetaAhorro, int(meta_id))
    if not meta or meta.usuario_id != uid:
        raise MetaError('Meta no encontrada.')
    return meta


def _solo_ahorro(meta: MetaAhorro) -> None:
    if (meta.tipo or 'ahorro') != 'ahorro':
        raise MetaError('Los límites de gasto se calculan desde tus movimientos.')


def _actualizar_completada(meta: MetaAhorro) -> None:
    meta.completada = float(meta.monto_actual or 0) >= float(meta.monto_objetivo)


# ── operaciones de la persona ────────────────────────────────────

def abonar(db: Session, uid: int, meta: MetaAhorro, monto, hoy: date | None = None) -> dict:
    """Suma dinero a la meta y lo registra como gasto ('Aporte manual a meta')."""
    _solo_ahorro(meta)
    monto = _monto_valido(monto)
    hoy = hoy or bogota_today()
    meta.monto_actual = float(meta.monto_actual or 0) + monto
    _actualizar_completada(meta)
    _crear_movimiento(db, uid, 'gasto', 'Aporte manual a meta', monto, tag_manual(meta.id), hoy)
    db.commit()
    return {'nombre': meta.nombre, 'abonado': monto, 'nuevo_total': float(meta.monto_actual),
            'completada': bool(meta.completada), 'id': meta.id}


def calcular_retiro(db: Session, uid: int, meta_id: int, monto_retiro: float,
                    hoy: date | None = None) -> tuple[float, float]:
    """Divide un retiro en (parte aportada ESTE mes, parte de meses anteriores).

    Lo aportado este mes se deshace restando de Gastos; lo de meses ya
    cerrados se registra como Ingreso de este mes ('Retiro de ahorro')."""
    hoy = hoy or bogota_today()
    inicio, fin = _mes(hoy)
    aportado = retirado = 0.0
    for t in _transacciones_de_meta(db, uid, meta_id).filter(
            Transaccion.fecha >= inicio, Transaccion.fecha < fin):
        monto = float(t.monto)
        if t.tipo == 'ingreso':
            retirado += monto
        elif monto >= 0:
            aportado += monto
        else:
            retirado += -monto
    este_mes = min(monto_retiro, max(0.0, aportado - retirado))
    return round(este_mes, 2), round(monto_retiro - este_mes, 2)


def ajustar_total(db: Session, uid: int, meta: MetaAhorro, nuevo_total, hoy: date | None = None) -> dict:
    """Reemplaza el total ahorrado (puede subir o bajar) y registra la diferencia."""
    _solo_ahorro(meta)
    nuevo_total = _monto_valido(nuevo_total, permitir_cero=True)
    hoy = hoy or bogota_today()
    anterior = float(meta.monto_actual or 0)
    diferencia = round(nuevo_total - anterior, 2)
    este_mes = anteriores = 0.0

    if diferencia > 0:
        _crear_movimiento(db, uid, 'gasto', 'Ajuste de meta', diferencia, tag_ajuste(meta.id), hoy)
    elif diferencia < 0:
        este_mes, anteriores = calcular_retiro(db, uid, meta.id, -diferencia, hoy)
        if este_mes > 0:
            # gasto negativo interno: deshace aportes de este mes sin tocar Ingresos
            _crear_movimiento(db, uid, 'gasto', 'Ajuste de meta', -este_mes, tag_ajuste(meta.id), hoy)
        if anteriores > 0:
            _crear_movimiento(db, uid, 'ingreso', 'Retiro de ahorro', anteriores, tag_ajuste(meta.id), hoy)

    meta.monto_actual = nuevo_total
    _actualizar_completada(meta)
    db.commit()
    return {'nombre': meta.nombre, 'nuevo_monto': nuevo_total, 'diferencia': diferencia,
            'devuelto_este_mes': este_mes, 'devuelto_meses_anteriores': anteriores,
            'completada': bool(meta.completada), 'id': meta.id}


def eliminar(db: Session, uid: int, meta: MetaAhorro) -> dict:
    """Borra la meta y sus movimientos internos: el dinero vuelve al balance."""
    devuelto = float(meta.monto_actual or 0) if (meta.tipo or 'ahorro') == 'ahorro' else 0.0
    nombre = meta.nombre
    _transacciones_de_meta(db, uid, meta.id).delete(synchronize_session=False)
    db.delete(meta)
    db.commit()
    return {'nombre': nombre, 'devuelto': devuelto}


# ── procesos automáticos (salario y aportes mensuales) ───────────

_candados: dict[int, threading.Lock] = {}
_candados_lock = threading.Lock()


def _candado(uid: int) -> threading.Lock:
    with _candados_lock:
        return _candados.setdefault(uid, threading.Lock())


def _categoria_salario(db: Session, uid: int) -> str:
    oculta = db.query(CategoriaUsuario).filter_by(
        usuario_id=uid, nombre='Salario', personalizada=False).first()
    return 'Otros ingresos' if oculta else 'Salario'


def _procesar_salario(db: Session, uid: int, hoy: date) -> bool:
    usuario = db.get(Usuario, uid)
    if not usuario:
        return False
    inicio, fin = _mes(hoy)
    cambios = False
    # nunca se adelanta el salario de meses futuros (limpia restos de versiones viejas)
    futuros = db.query(Transaccion).filter(
        Transaccion.usuario_id == uid, Transaccion.descripcion == TAG_SALARIO,
        Transaccion.fecha >= fin)
    if futuros.count():
        futuros.delete(synchronize_session=False)
        cambios = True

    ingreso = float(usuario.ingreso_mensual or 0)
    if ingreso <= 0 or not usuario.fecha_salario:
        return cambios
    del_mes = db.query(Transaccion).filter(
        Transaccion.usuario_id == uid, Transaccion.descripcion == TAG_SALARIO,
        Transaccion.fecha >= inicio, Transaccion.fecha < fin).order_by(Transaccion.id).all()
    if len(del_mes) > 1:                         # duplicados de versiones anteriores
        for t in del_mes[1:]:
            db.delete(t)
        cambios = True
    if del_mes:
        return cambios
    dia = dia_en_mes(hoy.year, hoy.month, usuario.fecha_salario.day)
    if hoy.day < dia:
        return cambios                           # aún no llega el día de pago
    _crear_movimiento(db, uid, 'ingreso', _categoria_salario(db, uid), ingreso,
                      TAG_SALARIO, hoy.replace(day=dia))
    return True


def _procesar_aportes(db: Session, uid: int, hoy: date) -> list[dict]:
    inicio, fin = _mes(hoy)
    aplicados = []
    metas = db.query(MetaAhorro).filter(
        MetaAhorro.usuario_id == uid, MetaAhorro.modo == 'automatico',
        or_(MetaAhorro.tipo == 'ahorro', MetaAhorro.tipo.is_(None))).all()
    for meta in metas:
        if meta.completada or not meta.monto_automatico or not meta.dia_automatico:
            continue
        dia = dia_en_mes(hoy.year, hoy.month, meta.dia_automatico)
        if hoy.day < dia:
            continue
        creada = meta.fecha_creacion.date() if meta.fecha_creacion else None
        # si se creó este mes después de su día, el primer aporte es el mes siguiente
        if creada and creada >= inicio and creada.day > dia:
            continue
        ya = db.query(Transaccion.id).filter(
            Transaccion.usuario_id == uid, Transaccion.descripcion == tag_auto(meta.id),
            Transaccion.fecha >= inicio, Transaccion.fecha < fin).first()
        if ya:
            continue
        faltante = float(meta.monto_objetivo) - float(meta.monto_actual or 0)
        aporte = round(min(float(meta.monto_automatico), faltante), 2)
        if aporte <= 0:
            continue
        _crear_movimiento(db, uid, 'gasto', 'Ahorro automático', aporte, tag_auto(meta.id),
                          hoy.replace(day=dia))
        meta.monto_actual = float(meta.monto_actual or 0) + aporte
        _actualizar_completada(meta)
        aplicados.append({'meta_id': meta.id, 'nombre': meta.nombre, 'aporte': aporte})
    return aplicados


def procesar_automaticos(db: Session, uid: int, hoy: date | None = None) -> dict:
    """Aplica el salario y los aportes automáticos pendientes del MES ACTUAL.

    Es idempotente: se puede llamar en cada petición y nunca duplica nada.
    Nunca toca meses pasados."""
    hoy = hoy or bogota_today()
    with _candado(uid):
        try:
            salario = _procesar_salario(db, uid, hoy)
            aportes = _procesar_aportes(db, uid, hoy)
            if salario or aportes:
                db.commit()
            return {'salario': salario, 'aportes': aportes}
        except Exception as error:
            db.rollback()
            print(f'[FinanBot] No se pudieron aplicar los automáticos de {uid}: {error}')
            return {'salario': False, 'aportes': [], 'error': str(error)}
