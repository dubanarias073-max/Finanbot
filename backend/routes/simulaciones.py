# routes/simulaciones.py

from flask import Blueprint, request, jsonify

simulaciones_bp = Blueprint('simulaciones', __name__)


@simulaciones_bp.route('/calcular', methods=['POST'])
def calcular_simulacion():

    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'mensaje': 'No se recibieron datos'
        }), 400

    # ─────────────────────────────────────────
    # Validación
    # ─────────────────────────────────────────

    campos = [
        'capital_inicial',
        'tasa_retorno',
        'plazo_meses'
    ]

    for campo in campos:
        if campo not in data:
            return jsonify({
                'success': False,
                'mensaje': f'Falta el campo: {campo}'
            }), 400

    try:
        capital = float(data['capital_inicial'])
        tasa = float(data['tasa_retorno'])
        plazo = int(data['plazo_meses'])
        aporte_mensual = float(data.get('aporte_mensual', 0))
        nombre_tipo = str(
            data.get(
                'nombre_tipo',
                'Inversión'
            )
        )

    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'mensaje': 'Los valores deben ser numéricos'
        }), 400

    # ─────────────────────────────────────────
    # Reglas
    # ─────────────────────────────────────────

    if capital <= 0:
        return jsonify({
            'success': False,
            'mensaje': 'El capital debe ser mayor a 0'
        }), 400

    if tasa <= 0:
        return jsonify({
            'success': False,
            'mensaje': 'La tasa debe ser mayor a 0'
        }), 400

    if plazo <= 0:
        return jsonify({
            'success': False,
            'mensaje': 'El plazo debe ser mayor a 0'
        }), 400

    # ─────────────────────────────────────────
    # Cálculo interés compuesto
    # ─────────────────────────────────────────

    tasa_mensual = tasa / 100 / 12

    total_invertido = capital + (
        aporte_mensual * plazo
    )

    balance = capital

    proyeccion = []

    for mes in range(plazo + 1):

        capital_acumulado = capital + (
            aporte_mensual * mes
        )

        intereses = max(
            round(
                balance - capital_acumulado,
                2
            ),
            0
        )

        proyeccion.append({
            'mes': mes,
            'periodo': (
                'Inicio'
                if mes == 0
                else f'Mes {mes}'
            ),
            'valor': round(balance, 2),
            'capital': round(capital_acumulado, 2),
            'intereses': intereses
        })

        if mes < plazo:
            balance = (
                balance *
                (1 + tasa_mensual)
            ) + aporte_mensual

    valor_final = round(balance, 2)

    ganancia = round(
        valor_final - total_invertido,
        2
    )

    ganancia = max(ganancia, 0)

    retencion = round(
        ganancia * 0.04,
        2
    )

    saldo_neto = round(
        valor_final - retencion,
        2
    )

    rentabilidad = round(
        (
            (valor_final / capital) - 1
        ) * 100,
        2
    )

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
            b = (
                b *
                (1 + tm)
            ) + aporte_mensual

        b = round(b, 2)

        escenarios.append({
            'nombre': nombre,
            'tasa': tasa_escenario,
            'valor_final': b,
            'ganancia': round(
                max(
                    b - total_invertido,
                    0
                ),
                2
            ),
            'rentabilidad': round(
                (
                    (b / capital) - 1
                ) * 100,
                2
            )
        })

    # ─────────────────────────────────────────
    # Texto plazo
    # ─────────────────────────────────────────

    if plazo < 12:
        plazo_texto = (
            f"{plazo} mes"
            if plazo == 1
            else f"{plazo} meses"
        )

    elif plazo % 12 == 0:

        años = plazo // 12

        plazo_texto = (
            f"{años} año"
            if años == 1
            else f"{años} años"
        )

    else:

        años = plazo // 12
        meses = plazo % 12

        plazo_texto = (
            f"{años} años y {meses} meses"
        )

    # ─────────────────────────────────────────
    # Respuesta
    # ─────────────────────────────────────────

    return jsonify({

        'success': True,

        'nombre_tipo': nombre_tipo,

        'capital_inicial': capital,

        'aporte_mensual': aporte_mensual,

        'tasa_retorno': tasa,

        'tasa_mensual': round(
            tasa / 12,
            4
        ),

        'plazo_meses': plazo,

        'plazo_texto': plazo_texto,

        'total_invertido': round(
            total_invertido,
            2
        ),

        'valor_final': valor_final,

        'ganancia': ganancia,

        'retencion': retencion,

        'saldo_neto': saldo_neto,

        'rentabilidad': rentabilidad,

        'aportes_totales': round(
            aporte_mensual * plazo,
            2
        ),

        'proyeccion': proyeccion,

        'escenarios': escenarios

    }), 200


@simulaciones_bp.route('/health', methods=['GET'])
def health():

    return jsonify({
        'success': True,
        'modulo': 'simulaciones',
        'estado': 'activo'
    }), 200