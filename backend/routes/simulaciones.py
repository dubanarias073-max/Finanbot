# routes/simulaciones.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Simulacion

simulaciones_bp = Blueprint('simulaciones', __name__)

@simulaciones_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_simulaciones():
    usuario_id = int(get_jwt_identity())
    simulaciones = Simulacion.query.filter_by(
        usuario_id=usuario_id
    ).order_by(Simulacion.fecha.desc()).limit(10).all()

    resultado = []
    for s in simulaciones:
        resultado.append({
            'id': s.id,
            'capital_inicial': float(s.capital_inicial),
            'tasa_retorno': float(s.tasa_retorno),
            'plazo_meses': s.plazo_meses,
            'resultado_final': float(s.resultado_final),
            'ganancia': float(s.resultado_final) - float(s.capital_inicial),
            'fecha': s.fecha.strftime('%d/%m/%Y')
        })

    return jsonify(resultado), 200


@simulaciones_bp.route('/', methods=['POST'])
@jwt_required()
def guardar_simulacion():
    usuario_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get('capital_inicial') or not data.get('tasa_retorno') or not data.get('plazo_meses') or not data.get('resultado_final'):
        return jsonify({'mensaje': 'Faltan campos obligatorios'}), 400

    nueva = Simulacion(
        usuario_id=usuario_id,
        capital_inicial=float(data['capital_inicial']),
        tasa_retorno=float(data['tasa_retorno']),
        plazo_meses=int(data['plazo_meses']),
        resultado_final=float(data['resultado_final'])
    )

    db.session.add(nueva)
    db.session.commit()

    return jsonify({'mensaje': '✅ Simulación guardada!', 'id': nueva.id}), 201