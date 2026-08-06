# routes/transacciones.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Transaccion, Categoria, PeriodoFinanciero, TransaccionPeriodo

router = APIRouter()


def actualizar_totales_periodo(periodo: PeriodoFinanciero | None, db: Session):
    if not periodo:
        return

    if periodo.activo:
        registros = db.query(Transaccion).filter_by(usuario_id=periodo.usuario_id).all()
    else:
        registros = periodo.transacciones

    ingresos = sum(float(r.monto) for r in registros if getattr(r, 'tipo', None) == 'ingreso')
    gastos = sum(float(r.monto) for r in registros if getattr(r, 'tipo', None) == 'gasto')
    periodo.ingresos_total = ingresos
    periodo.gastos_total = gastos
    periodo.balance = ingresos - gastos


def gestionar_periodo_mensual(usuario_id: int, db: Session):
    hoy = datetime.now().date()
    periodo_actual = (
        db.query(PeriodoFinanciero)
        .filter_by(usuario_id=usuario_id, anio=hoy.year, mes=hoy.month, activo=True)
        .order_by(PeriodoFinanciero.id.desc())
        .first()
    )

    if periodo_actual:
        return periodo_actual

    periodos_abiertos = (
        db.query(PeriodoFinanciero)
        .filter_by(usuario_id=usuario_id, activo=True)
        .all()
    )

    if periodos_abiertos:
        for periodo in periodos_abiertos:
            transacciones = db.query(Transaccion).filter_by(usuario_id=usuario_id).all()
            if transacciones:
                for t in transacciones:
                    db.add(TransaccionPeriodo(
                        periodo_id=periodo.id,
                        tipo=t.tipo,
                        monto=t.monto,
                        categoria=t.categoria.nombre if t.categoria else 'Otros',
                        descripcion=t.descripcion,
                        fecha=t.fecha,
                    ))
                db.query(Transaccion).filter_by(usuario_id=usuario_id).delete(synchronize_session=False)

            periodo.activo = False
            periodo.fecha_cierre = datetime.utcnow()
            actualizar_totales_periodo(periodo, db)

    nuevo_periodo = PeriodoFinanciero(usuario_id=usuario_id, anio=hoy.year, mes=hoy.month, activo=True)
    db.add(nuevo_periodo)
    db.flush()
    return nuevo_periodo


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
# =========================================================

@router.get('/')
def obtener_transacciones(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    gestionar_periodo_mensual(uid, db)
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
    gestionar_periodo_mensual(uid, db)

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
    actualizar_totales_periodo(gestionar_periodo_mensual(uid, db), db)
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
    gestionar_periodo_mensual(uid, db)

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
    actualizar_totales_periodo(gestionar_periodo_mensual(uid, db), db)
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
# ELIMINAR
# =========================================================

@router.get('/periodos')
def obtener_periodos(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    gestionar_periodo_mensual(uid, db)

    periodos = (
        db.query(PeriodoFinanciero)
        .filter_by(usuario_id=uid)
        .order_by(PeriodoFinanciero.anio.desc(), PeriodoFinanciero.mes.desc())
        .all()
    )

    resultado = []
    for periodo in periodos:
        registros = []
        if periodo.activo:
            registros = [
                {
                    'id': t.id,
                    'tipo': t.tipo,
                    'categoria': t.categoria.nombre if t.categoria else 'Otros',
                    'monto': float(t.monto),
                    'descripcion': t.descripcion or '',
                    'fecha': str(t.fecha),
                }
                for t in db.query(Transaccion).filter_by(usuario_id=uid).order_by(Transaccion.fecha.desc()).all()
            ]
        else:
            registros = [
                {
                    'id': t.id,
                    'tipo': t.tipo,
                    'categoria': t.categoria,
                    'monto': float(t.monto),
                    'descripcion': t.descripcion or '',
                    'fecha': str(t.fecha),
                }
                for t in periodo.transacciones
            ]
        resultado.append({
            'id': periodo.id,
            'anio': periodo.anio,
            'mes': periodo.mes,
            'activo': periodo.activo,
            'label': f'{periodo.mes:02d}/{periodo.anio}',
            'ingresos_total': float(periodo.ingresos_total or 0),
            'gastos_total': float(periodo.gastos_total or 0),
            'balance': float(periodo.balance or 0),
            'transacciones': registros,
        })

    return resultado


@router.post('/periodos/reset')
def reset_periodo_actual(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    periodo = gestionar_periodo_mensual(uid, db)
    transacciones = db.query(Transaccion).filter_by(usuario_id=uid).all()
    for transaccion in transacciones:
        db.delete(transaccion)
    db.commit()
    actualizar_totales_periodo(periodo, db)
    db.commit()
    return {'mensaje': '✅ Mes reiniciado', 'periodo_id': periodo.id}


@router.delete('/periodos/{id}')
def eliminar_periodo(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    periodo = db.query(PeriodoFinanciero).filter_by(id=id, usuario_id=uid).first()
    if not periodo:
        raise HTTPException(status_code=404, detail='Periodo no encontrado')

    db.delete(periodo)
    db.commit()
    return {'mensaje': '✅ Periodo eliminado'}


@router.delete('/{id}')
def eliminar_transaccion(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    gestionar_periodo_mensual(uid, db)
    transaccion = db.query(Transaccion).filter_by(id=id, usuario_id=uid).first()

    if not transaccion:
        raise HTTPException(status_code=404, detail='Transacción no encontrada')

    db.delete(transaccion)
    db.commit()

    return {'mensaje': '✅ Transacción eliminada!'}