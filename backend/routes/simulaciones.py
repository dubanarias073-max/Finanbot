# routes/simulaciones.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Simulacion
from datetime import datetime

simulaciones_bp = Blueprint('simulaciones', __name__)


# ─────────────────────────────────────────────────────────
#  GET — Obtener simulaciones del usuario
# ─────────────────────────────────────────────────────────
@simulaciones_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_simulaciones():
    usuario_id = int(get_jwt_identity())

    simulaciones = Simulacion.query.filter_by(
        usuario_id=usuario_id
    ).order_by(Simulacion.fecha.desc()).limit(20).all()

    resultado = []
    for s in simulaciones:
        capital    = float(s.capital_inicial)
        resultado_f = float(s.resultado_final)
        tasa        = float(s.tasa_retorno)
        plazo       = int(s.plazo_meses)
        ganancia    = resultado_f - capital
        retencion   = round(max(ganancia, 0) * 0.04, 2)
        saldo_neto  = round(resultado_f - retencion, 2)
        rentabilidad = round(((resultado_f / capital) - 1) * 100, 2) if capital > 0 else 0

        # Texto descriptivo del tipo de inversión
        if tasa <= 5:
            tipo_texto = 'CDT Básico'
        elif tasa <= 8:
            tipo_texto = 'CDT Premium'
        elif tasa <= 10:
            tipo_texto = 'Fondo de inversión'
        elif tasa <= 15:
            tipo_texto = 'Acciones BVC'
        elif tasa <= 20:
            tipo_texto = 'Startups'
        else:
            tipo_texto = f'Personalizada ({tasa}%)'

        # Texto del plazo
        if plazo < 12:
            plazo_texto = f'{plazo} mes{"es" if plazo > 1 else ""}'
        elif plazo == 12:
            plazo_texto = '1 año'
        elif plazo % 12 == 0:
            anos = plazo // 12
            plazo_texto = f'{anos} año{"s" if anos > 1 else ""}'
        else:
            anos = plazo // 12
            meses_r = plazo % 12
            plazo_texto = f'{anos} año{"s" if anos > 1 else ""} y {meses_r} mes{"es" if meses_r > 1 else ""}'

        resultado.append({
            'id':              s.id,
            'capital_inicial': capital,
            'tasa_retorno':    tasa,
            'plazo_meses':     plazo,
            'resultado_final': resultado_f,
            'ganancia':        round(ganancia, 2),
            'retencion':       retencion,
            'saldo_neto':      saldo_neto,
            'rentabilidad':    rentabilidad,
            'tipo_texto':      tipo_texto,
            'plazo_texto':     plazo_texto,
            'fecha':           s.fecha.strftime('%d/%m/%Y') if s.fecha else '',
            'fecha_iso':       s.fecha.strftime('%Y-%m-%d') if s.fecha else '',
        })

    return jsonify(resultado), 200


# ─────────────────────────────────────────────────────────
#  POST — Guardar nueva simulación
# ─────────────────────────────────────────────────────────
@simulaciones_bp.route('/', methods=['POST'])
@jwt_required()
def guardar_simulacion():
    usuario_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({'mensaje': '❌ No se recibieron datos'}), 400

    # Validar campos obligatorios
    campos = ['capital_inicial', 'tasa_retorno', 'plazo_meses', 'resultado_final']
    for campo in campos:
        if data.get(campo) is None:
            return jsonify({'mensaje': f'❌ Falta el campo: {campo}'}), 400

    try:
        capital     = float(data['capital_inicial'])
        tasa        = float(data['tasa_retorno'])
        plazo       = int(data['plazo_meses'])
        resultado   = float(data['resultado_final'])
    except (ValueError, TypeError):
        return jsonify({'mensaje': '❌ Los valores deben ser numéricos'}), 400

    # Validaciones de rango
    if capital <= 0:
        return jsonify({'mensaje': '❌ El capital debe ser mayor a 0'}), 400
    if tasa <= 0 or tasa > 200:
        return jsonify({'mensaje': '❌ La tasa debe estar entre 0.1% y 200%'}), 400
    if plazo < 1 or plazo > 600:
        return jsonify({'mensaje': '❌ El plazo debe estar entre 1 y 600 meses'}), 400
    if resultado <= 0:
        return jsonify({'mensaje': '❌ El resultado debe ser mayor a 0'}), 400

    ganancia   = resultado - capital
    retencion  = round(max(ganancia, 0) * 0.04, 2)
    saldo_neto = round(resultado - retencion, 2)

    nueva = Simulacion(
        usuario_id     = usuario_id,
        capital_inicial = capital,
        tasa_retorno   = tasa,
        plazo_meses    = plazo,
        resultado_final = resultado,
        fecha          = datetime.now().date()
    )

    db.session.add(nueva)
    db.session.commit()

    return jsonify({
        'mensaje':    '✅ Simulación guardada correctamente',
        'id':         nueva.id,
        'ganancia':   round(ganancia, 2),
        'retencion':  retencion,
        'saldo_neto': saldo_neto,
    }), 201


# ─────────────────────────────────────────────────────────
#  DELETE /<id> — Eliminar una simulación específica
# ─────────────────────────────────────────────────────────
@simulaciones_bp.route('/<int:sim_id>', methods=['DELETE'])
@jwt_required()
def eliminar_simulacion(sim_id):
    usuario_id = int(get_jwt_identity())

    sim = Simulacion.query.filter_by(id=sim_id, usuario_id=usuario_id).first()
    if not sim:
        return jsonify({'mensaje': '❌ Simulación no encontrada'}), 404

    try:
        db.session.delete(sim)
        db.session.commit()
        return jsonify({'mensaje': '✅ Simulación eliminada'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'mensaje': f'❌ Error al eliminar: {str(e)}'}), 500


# ─────────────────────────────────────────────────────────
#  DELETE / — Eliminar todas las simulaciones del usuario
# ─────────────────────────────────────────────────────────
@simulaciones_bp.route('/', methods=['DELETE'])
@jwt_required()
def eliminar_todas_simulaciones():
    usuario_id = int(get_jwt_identity())
    try:
        eliminadas = Simulacion.query.filter_by(usuario_id=usuario_id).delete()
        db.session.commit()
        return jsonify({
            'mensaje':    f'✅ {eliminadas} simulación(es) eliminada(s)',
            'eliminadas': eliminadas
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'mensaje': f'❌ Error: {str(e)}'}), 500


# ─────────────────────────────────────────────────────────
#  GET /resumen — Resumen estadístico de simulaciones
# ─────────────────────────────────────────────────────────
@simulaciones_bp.route('/resumen', methods=['GET'])
@jwt_required()
def resumen_simulaciones():
    usuario_id = int(get_jwt_identity())

    simulaciones = Simulacion.query.filter_by(usuario_id=usuario_id).all()

    if not simulaciones:
        return jsonify({
            'total':            0,
            'capital_total':    0,
            'ganancia_total':   0,
            'mejor_ganancia':   0,
            'tasa_promedio':    0,
            'plazo_promedio':   0,
        }), 200

    capitales  = [float(s.capital_inicial) for s in simulaciones]
    resultados = [float(s.resultado_final) for s in simulaciones]
    ganancias  = [r - c for r, c in zip(resultados, capitales)]
    tasas      = [float(s.tasa_retorno) for s in simulaciones]
    plazos     = [int(s.plazo_meses) for s in simulaciones]

    return jsonify({
        'total':           len(simulaciones),
        'capital_total':   round(sum(capitales), 2),
        'ganancia_total':  round(sum(ganancias), 2),
        'mejor_ganancia':  round(max(ganancias), 2),
        'tasa_promedio':   round(sum(tasas) / len(tasas), 2),
        'plazo_promedio':  round(sum(plazos) / len(plazos)),
    }), 200