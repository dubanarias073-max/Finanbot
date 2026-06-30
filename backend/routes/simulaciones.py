# routes/simulaciones.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# =========================================================
# ESQUEMA
# =========================================================

class SimulacionInput(BaseModel):
    capital_inicial: float
    tasa_retorno: float
    plazo_meses: int
    aporte_mensual: Optional[float] = 0
    nombre_tipo: Optional[str] = 'Inversión'


# =========================================================
# CALCULAR
# =========================================================

@router.post('/calcular')
def calcular_simulacion(body: SimulacionInput):

    capital        = body.capital_inicial
    tasa           = body.tasa_retorno
    plazo          = body.plazo_meses
    aporte_mensual = body.aporte_mensual
    nombre_tipo    = body.nombre_tipo

    # ─────────────────────────────────────────
    # Reglas
    # ─────────────────────────────────────────

    if capital <= 0:
        return {'success': False, 'mensaje': 'El capital debe ser mayor a 0'}

    if tasa <= 0:
        return {'success': False, 'mensaje': 'La tasa debe ser mayor a 0'}

    if plazo <= 0:
        return {'success': False, 'mensaje': 'El plazo debe ser mayor a 0'}

    # ─────────────────────────────────────────
    # Cálculo interés compuesto
    # ─────────────────────────────────────────

    tasa_mensual = tasa / 100 / 12
    total_invertido = capital + (aporte_mensual * plazo)
    balance = capital
    proyeccion = []

    for mes in range(plazo + 1):
        capital_acumulado = capital + (aporte_mensual * mes)
        intereses = max(round(balance - capital_acumulado, 2), 0)

        proyeccion.append({
            'mes': mes,
            'periodo': 'Inicio' if mes == 0 else f'Mes {mes}',
            'valor': round(balance, 2),
            'capital': round(capital_acumulado, 2),
            'intereses': intereses
        })

        if mes < plazo:
            balance = (balance * (1 + tasa_mensual)) + aporte_mensual

    valor_final = round(balance, 2)
    ganancia = round(valor_final - total_invertido, 2)
    ganancia = max(ganancia, 0)
    retencion = round(ganancia * 0.04, 2)
    saldo_neto = round(valor_final - retencion, 2)
    rentabilidad = round(((valor_final / capital) - 1) * 100, 2)

    # ─────────────────────────────────────────
    # Escenarios comparativos
    # ─────────────────────────────────────────

    escenarios = []
    escenarios_base = [
        (5, "🏦 CDT Básico"),
        (8, "💎 CDT Premium"),
        (10, "📊 Fondo de inversión"),
        (15, "📈 Acciones BVC"),
        (20, "🚀 Startups")
    ]

    for tasa_escenario, nombre in escenarios_base:
        tm = tasa_escenario / 100 / 12
        b = capital
        for _ in range(plazo):
            b = (b * (1 + tm)) + aporte_mensual
        b = round(b, 2)

        escenarios.append({
            'nombre': nombre,
            'tasa': tasa_escenario,
            'valor_final': b,
            'ganancia': round(max(b - total_invertido, 0), 2),
            'rentabilidad': round(((b / capital) - 1) * 100, 2)
        })

    # ─────────────────────────────────────────
    # Texto plazo
    # ─────────────────────────────────────────

    if plazo < 12:
        plazo_texto = f"{plazo} mes" if plazo == 1 else f"{plazo} meses"
    elif plazo % 12 == 0:
        años = plazo // 12
        plazo_texto = f"{años} año" if años == 1 else f"{años} años"
    else:
        años = plazo // 12
        meses = plazo % 12
        plazo_texto = f"{años} años y {meses} meses"

    # ─────────────────────────────────────────
    # Respuesta
    # ─────────────────────────────────────────

    return {
        'success': True,
        'nombre_tipo': nombre_tipo,
        'capital_inicial': capital,
        'aporte_mensual': aporte_mensual,
        'tasa_retorno': tasa,
        'tasa_mensual': round(tasa / 12, 4),
        'plazo_meses': plazo,
        'plazo_texto': plazo_texto,
        'total_invertido': round(total_invertido, 2),
        'valor_final': valor_final,
        'ganancia': ganancia,
        'retencion': retencion,
        'saldo_neto': saldo_neto,
        'rentabilidad': rentabilidad,
        'aportes_totales': round(aporte_mensual * plazo, 2),
        'proyeccion': proyeccion,
        'escenarios': escenarios
    }


@router.get('/health')
def health():
    return {'success': True, 'modulo': 'simulaciones', 'estado': 'activo'}