# routes/metas.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, timedelta
from sqlalchemy import func, or_

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import MetaAhorro, Transaccion
from timezone import bogota_today
from application.services import metas_service
from application.services.metas_service import MetaError

router = APIRouter()


def obtener_metas_calculadas(usuario_id: int, db: Session, hoy: Optional[date] = None):
    hoy = hoy or bogota_today()
    metas = db.query(MetaAhorro).filter_by(usuario_id=usuario_id).all()
    resultado = []
    for meta in metas:
        monto_actual = float(meta.monto_actual or 0)
        periodo = None
        if meta.tipo in ('gasto_mensual', 'gasto_anual'):
            if meta.tipo == 'gasto_mensual':
                inicio = hoy.replace(day=1)
                fin = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
                periodo = hoy.strftime('%Y-%m')
            else:
                inicio = hoy.replace(month=1, day=1)
                fin = hoy.replace(year=hoy.year + 1, month=1, day=1)
                periodo = str(hoy.year)
            monto_actual = float(
                db.query(func.coalesce(func.sum(Transaccion.monto), 0))
                .filter(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.tipo == 'gasto',
                    Transaccion.fecha >= inicio,
                    Transaccion.fecha < fin,
                    Transaccion.fecha <= hoy,
                    or_(
                        Transaccion.descripcion.is_(None),
                        ~Transaccion.descripcion.like(
                            r'\_\_%\_meta\_%\_\_', escape='\\'
                        ),
                    ),
                )
                .scalar()
            )
        objetivo = float(meta.monto_objetivo)
        porcentaje = round((monto_actual / objetivo) * 100) if objetivo > 0 else 0
        if meta.tipo == 'ahorro':
            porcentaje = min(porcentaje, 100)
        excedida = meta.tipo in ('gasto_mensual', 'gasto_anual') and monto_actual >= objetivo
        resultado.append({
            'id': meta.id,
            'nombre': meta.nombre,
            'tipo': meta.tipo or 'ahorro',
            'monto_objetivo': objetivo,
            'monto_actual': monto_actual,
            'porcentaje': porcentaje,
            'excedida': excedida,
            'disponible': objetivo - monto_actual if meta.tipo in ('gasto_mensual', 'gasto_anual') else None,
            'completada': (
                bool(meta.completada) or monto_actual >= objetivo
                if meta.tipo == 'ahorro' else False
            ),
            'periodo': periodo,
            'fecha_limite': str(meta.fecha_limite) if meta.fecha_limite else None,
            'modo': meta.modo or 'manual',
            'monto_automatico': float(meta.monto_automatico) if meta.monto_automatico is not None else None,
            'dia_automatico': meta.dia_automatico,
            'icono': meta.icono,
            'categoria': meta.categoria,
            'prioridad': meta.prioridad or 'media',
            'fecha_creacion': meta.fecha_creacion.isoformat() if meta.fecha_creacion else None,
        })
    return resultado


# =========================================================
# ESQUEMAS
# =========================================================

class MetaCreate(BaseModel):
    model_config = {'json_schema_extra': {'examples': [{"nombre": "🏖️ Viaje a Cartagena", "monto_objetivo": 2000000, "tipo": "ahorro", "monto_actual": 0, "fecha_limite": "2027-06-30", "modo": "automatico", "monto_automatico": 200000, "dia_automatico": 5, "icono": "🏖️", "categoria": "viaje", "prioridad": "alta"}]}}
    nombre: str
    monto_objetivo: float
    tipo: Optional[str] = 'ahorro'
    monto_actual: Optional[float] = 0
    fecha_limite: Optional[str] = None
    modo: Optional[str] = 'manual'                 # 'manual' o 'automatico'
    monto_automatico: Optional[float] = None        # aporte mensual (solo si modo='automatico')
    dia_automatico: Optional[int] = None             # día del mes 1-31 (solo si modo='automatico')
    icono: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: Optional[str] = 'media'

class MetaUpdate(BaseModel):
    model_config = {'json_schema_extra': {'examples': [{"nombre": "🏖️ Viaje a San Andrés", "monto_objetivo": 3000000, "fecha_limite": "2027-12-15", "prioridad": "media"}]}}
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    monto_objetivo: Optional[float] = None
    monto_actual: Optional[float] = None
    fecha_limite: Optional[str] = None             # enviar null o '' para quitarla
    modo: Optional[str] = None
    monto_automatico: Optional[float] = None
    dia_automatico: Optional[int] = None
    icono: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: Optional[str] = None


# =========================================================
# OBTENER TODAS
# =========================================================

@router.get('/')
def obtener_metas(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    # aplica en el servidor el salario y los aportes automáticos pendientes del mes
    metas_service.procesar_automaticos(db, uid)
    return obtener_metas_calculadas(uid, db)


# =========================================================
# MOVIMIENTOS DE DINERO (atómicos, calculados en el servidor)
# =========================================================

class MontoBody(BaseModel):
    model_config = {'json_schema_extra': {'examples': [{"monto": 50000}]}}
    monto: float


class TotalBody(BaseModel):
    model_config = {'json_schema_extra': {'examples': [{"nuevo_total": 300000}]}}
    nuevo_total: float


def _meta_o_error(db, uid, id):
    try:
        return metas_service.obtener_meta(db, uid, id)
    except MetaError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/{id}/abonar')
def abonar_meta(
    id: int,
    body: MontoBody,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    """Suma dinero a la meta y lo descuenta del balance (gasto 'Aporte manual a meta')."""
    uid = int(usuario_id)
    meta = _meta_o_error(db, uid, id)
    try:
        return {'mensaje': '✅ Abono registrado', **metas_service.abonar(db, uid, meta, body.monto)}
    except MetaError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/{id}/ajustar')
def ajustar_meta(
    id: int,
    body: TotalBody,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    """Reemplaza el total ahorrado. Si baja, el dinero vuelve al balance."""
    uid = int(usuario_id)
    meta = _meta_o_error(db, uid, id)
    try:
        return {'mensaje': '✅ Monto actualizado', **metas_service.ajustar_total(db, uid, meta, body.nuevo_total)}
    except MetaError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/{id}/retirar')
def retirar_meta(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    """Meta completada: devuelve todo lo ahorrado al balance y la elimina."""
    uid = int(usuario_id)
    meta = _meta_o_error(db, uid, id)
    if (meta.tipo or 'ahorro') != 'ahorro' or not (
            meta.completada or float(meta.monto_actual or 0) >= float(meta.monto_objetivo)):
        raise HTTPException(status_code=400, detail='Solo puedes retirar el dinero de una meta completada.')
    return {'mensaje': '✅ Dinero retirado y meta eliminada', **metas_service.eliminar(db, uid, meta)}


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

    tipo = body.tipo or 'ahorro'
    if tipo not in ('ahorro', 'gasto_mensual', 'gasto_anual'):
        raise HTTPException(
            status_code=400,
            detail="tipo debe ser 'ahorro', 'gasto_mensual' o 'gasto_anual'",
        )
    if not body.nombre.strip():
        raise HTTPException(status_code=400, detail='El nombre de la meta es obligatorio.')
    if body.monto_objetivo <= 0:
        raise HTTPException(status_code=400, detail='El monto objetivo debe ser mayor que cero.')
    if (body.monto_actual or 0) < 0:
        raise HTTPException(status_code=400, detail='Lo ya ahorrado no puede ser negativo.')
    if body.prioridad not in (None, 'baja', 'media', 'alta'):
        raise HTTPException(status_code=400, detail="prioridad debe ser 'baja', 'media' o 'alta'")
    if body.icono and len(body.icono) > 10:
        raise HTTPException(status_code=400, detail='El icono debe tener máximo 10 caracteres.')
    if body.categoria and len(body.categoria) > 50:
        raise HTTPException(status_code=400, detail='La categoría debe tener máximo 50 caracteres.')

    modo = body.modo if body.modo in ('manual', 'automatico') else 'manual'
    if tipo != 'ahorro':
        modo = 'manual'
    monto_automatico = body.monto_automatico if modo == 'automatico' else None
    dia_automatico = body.dia_automatico if modo == 'automatico' else None
    monto_actual = (body.monto_actual or 0) if tipo == 'ahorro' else 0

    # Validación básica del modo automático
    if modo == 'automatico':
        if not monto_automatico or monto_automatico <= 0:
            raise HTTPException(status_code=400, detail='Indica un aporte mensual válido para el modo automático.')
        if not dia_automatico or dia_automatico < 1 or dia_automatico > 31:
            raise HTTPException(status_code=400, detail='Indica un día del mes válido (1-31) para el modo automático.')

    nueva = MetaAhorro(
        usuario_id=uid,
        nombre=body.nombre,
        monto_objetivo=body.monto_objetivo,
        monto_actual=monto_actual,
        fecha_limite=datetime.strptime(body.fecha_limite, '%Y-%m-%d').date() if body.fecha_limite else None,
        tipo=tipo,
        modo=modo,
        monto_automatico=monto_automatico,
        dia_automatico=dia_automatico,
        icono=body.icono,
        categoria=body.categoria,
        prioridad=body.prioridad or 'media',
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

    if body.tipo is not None:
        if body.tipo not in ('ahorro', 'gasto_mensual', 'gasto_anual'):
            raise HTTPException(
                status_code=400,
                detail="tipo debe ser 'ahorro', 'gasto_mensual' o 'gasto_anual'",
            )
        meta.tipo = body.tipo
        if body.tipo != 'ahorro':
            meta.fecha_limite = None
            meta.monto_actual = 0
            meta.completada = False
            meta.modo = 'manual'
            meta.monto_automatico = None
            meta.dia_automatico = None

    if body.monto_objetivo is not None:
        if body.monto_objetivo <= 0:
            raise HTTPException(status_code=400, detail='El monto objetivo debe ser mayor que cero.')
        meta.monto_objetivo = body.monto_objetivo
        if meta.tipo == 'ahorro':
            # Si se sube el objetivo por encima de lo ahorrado, la meta vuelve a estar activa
            meta.completada = float(meta.monto_actual or 0) >= body.monto_objetivo

    if 'fecha_limite' in body.model_fields_set:
        if body.fecha_limite:
            try:
                meta.fecha_limite = datetime.strptime(body.fecha_limite, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail='fecha_limite debe tener formato AAAA-MM-DD')
        else:
            meta.fecha_limite = None

    nuevo_total = None
    if body.monto_actual is not None:
        if meta.tipo != 'ahorro':
            raise HTTPException(status_code=400, detail='Los límites de gasto se calculan desde tus movimientos.')
        if body.monto_actual < 0:
            raise HTTPException(status_code=400, detail='El monto ahorrado no puede ser negativo.')
        nuevo_total = body.monto_actual        # se aplica al final, con sus movimientos

    if body.nombre is not None:
        if not body.nombre.strip():
            raise HTTPException(status_code=400, detail='El nombre de la meta es obligatorio.')
        meta.nombre = body.nombre.strip()

    if body.icono is not None:
        meta.icono = body.icono
    if body.categoria is not None:
        meta.categoria = body.categoria
    if body.prioridad is not None:
        if body.prioridad not in ('baja', 'media', 'alta'):
            raise HTTPException(status_code=400, detail="prioridad debe ser 'baja', 'media' o 'alta'")
        meta.prioridad = body.prioridad
    if body.icono and len(body.icono) > 10:
        raise HTTPException(status_code=400, detail='El icono debe tener máximo 10 caracteres.')
    if body.categoria and len(body.categoria) > 50:
        raise HTTPException(status_code=400, detail='La categoría debe tener máximo 50 caracteres.')

    if body.modo is not None:
        if meta.tipo != 'ahorro' and body.modo == 'automatico':
            raise HTTPException(status_code=400, detail='El modo automático solo aplica a metas de ahorro.')
        if body.modo not in ('manual', 'automatico'):
            raise HTTPException(status_code=400, detail="modo debe ser 'manual' o 'automatico'")
        meta.modo = body.modo
        if body.modo == 'manual':
            # Al pasar a manual, se limpian los datos de automatización
            meta.monto_automatico = None
            meta.dia_automatico = None

    if body.monto_automatico is not None:
        if body.monto_automatico <= 0:
            raise HTTPException(status_code=400, detail='El aporte mensual debe ser mayor que cero.')
        meta.monto_automatico = body.monto_automatico

    if body.dia_automatico is not None:
        if body.dia_automatico < 1 or body.dia_automatico > 31:
            raise HTTPException(status_code=400, detail='dia_automatico debe estar entre 1 y 31')
        meta.dia_automatico = body.dia_automatico

    if meta.modo == 'automatico' and (not meta.monto_automatico or meta.monto_automatico <= 0
                                      or not meta.dia_automatico):
        db.rollback()
        raise HTTPException(status_code=400, detail='El modo automático necesita un aporte mensual y un día válidos.')

    if nuevo_total is not None:
        try:
            metas_service.ajustar_total(db, uid, meta, nuevo_total)   # hace commit
        except MetaError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    else:
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

    # borra también sus aportes/ajustes: ese dinero vuelve al balance
    resultado = metas_service.eliminar(db, uid, meta)
    return {'mensaje': '✅ Meta eliminada!', **resultado}