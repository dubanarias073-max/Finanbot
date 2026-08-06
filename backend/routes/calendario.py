# calendario.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import extract

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Transaccion, Categoria, PeriodoFinanciero, TransaccionPeriodo, Usuario

from .reporte_mensual import (
    generar_reporte_pdf_mensual,
    generar_reporte_excel_mensual,
    MESES_ES,
)

router = APIRouter(tags=["Calendario"])


def _transacciones_del_mes(db: Session, usuario_id: int, anio: int, mes: int):
    return (
        db.query(Transaccion)
        .filter(Transaccion.usuario_id == usuario_id)
        .filter(extract('year', Transaccion.fecha) == anio)
        .filter(extract('month', Transaccion.fecha) == mes)
        .order_by(Transaccion.fecha.asc())
        .all()
    )


# ══════════════════════════════════════════════════════════════════
#  GET /api/calendario/{anio}/{mes}
#  Datos de un mes para pintar el calendario grande: cada día marcado
#  y el listado de movimientos, para el panel lateral al hacer clic.
# ══════════════════════════════════════════════════════════════════
@router.get("/{anio}/{mes}")
def obtener_mes(
    anio: int,
    mes: int,
    db: Session = Depends(get_db),
    usuario_id: str = Depends(obtener_usuario_id_requerido),
):
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mes inválido (1-12).")

    trans = _transacciones_del_mes(db, int(usuario_id), anio, mes)
    ingresos = [t for t in trans if t.tipo == 'ingreso']
    gastos   = [t for t in trans if t.tipo == 'gasto']

    return {
        "anio": anio,
        "mes": mes,
        "nombre_mes": MESES_ES[mes],
        "hay_transacciones": len(trans) > 0,
        "total_ingresos": sum(t.monto for t in ingresos),
        "total_gastos": sum(t.monto for t in gastos),
        "balance": sum(t.monto for t in ingresos) - sum(t.monto for t in gastos),
        "num_movimientos": len(trans),
        "movimientos": [
            {
                "id": t.id,
                "fecha": t.fecha.strftime('%Y-%m-%d') if hasattr(t.fecha, 'strftime') else str(t.fecha),
                "tipo": t.tipo,
                "categoria": t.categoria,
                "icono": getattr(t, 'icono', None),
                "descripcion": t.descripcion,
                "monto": t.monto,
            }
            for t in trans
        ],
    }


# ══════════════════════════════════════════════════════════════════
#  GET /api/calendario/disponibles/{anio}
#  Para cada mes del año, indica si tiene o no transacciones — útil
#  para pintar de una vez en el calendario grande qué meses ya tienen
#  reporte disponible, sin consultar mes por mes desde el frontend.
# ══════════════════════════════════════════════════════════════════
@router.get("/disponibles/{anio}")
def meses_con_datos(
    anio: int,
    db: Session = Depends(get_db),
    usuario_id: str = Depends(obtener_usuario_id_requerido),
):
    uid = int(usuario_id)
    resultado = []
    for mes in range(1, 13):
        trans = _transacciones_del_mes(db, uid, anio, mes)
        resultado.append({
            "mes": mes,
            "nombre_mes": MESES_ES[mes],
            "hay_transacciones": len(trans) > 0,
            "num_movimientos": len(trans),
        })
    return resultado


# ══════════════════════════════════════════════════════════════════
#  GET /api/calendario/reporte/{anio}/{mes}?formato=pdf|excel
#  Descarga el reporte del mes indicado, en el formato que el usuario
#  elija. Si el mes no tiene transacciones, responde 404 con un
#  mensaje claro para que el frontend muestre el aviso correspondiente
#  en vez de intentar descargar un archivo vacío.
# ══════════════════════════════════════════════════════════════════
@router.get("/reporte/{anio}/{mes}")
def descargar_reporte_mensual(
    anio: int,
    mes: int,
    formato: str = "pdf",
    db: Session = Depends(get_db),
    usuario_id: str = Depends(obtener_usuario_id_requerido),
):
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mes inválido (1-12).")
    if formato not in ("pdf", "excel"):
        raise HTTPException(status_code=400, detail="Formato inválido. Usa 'pdf' o 'excel'.")

    uid = int(usuario_id)
    trans = _transacciones_del_mes(db, uid, anio, mes)

    if not trans:
        raise HTTPException(
            status_code=404,
            detail=f"No hay transacciones registradas en {MESES_ES[mes]} {anio}.",
        )

    # El reporte necesita el nombre del usuario -> se busca el objeto completo
    usuario = db.query(Usuario).filter(Usuario.id == uid).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    nombre_mes = MESES_ES[mes]

    if formato == "pdf":
        buffer = generar_reporte_pdf_mensual(usuario, trans, anio, mes)
        filename = f"FinanBot_{nombre_mes}_{anio}.pdf"
        media_type = "application/pdf"
    else:
        buffer = generar_reporte_excel_mensual(usuario, trans, anio, mes)
        filename = f"FinanBot_{nombre_mes}_{anio}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )