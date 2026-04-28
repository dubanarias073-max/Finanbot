# routes/metas.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import MetaAhorro
from datetime import datetime

metas_bp = Blueprint('metas', __name__)

@metas_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_metas():
    usuario_id = int(get_jwt_identity())
    metas = MetaAhorro.query.filter_by(usuario_id=usuario_id).all()

    resultado = []
    for m in metas:
        porcentaje = min(round((float(m.monto_actual) / float(m.monto_objetivo)) * 100), 100) if m.monto_objetivo > 0 else 0
        resultado.append({
            'id': m.id,
            'nombre': m.nombre,
            'monto_objetivo': float(m.monto_objetivo),
            'monto_actual': float(m.monto_actual),
            'porcentaje': porcentaje,
            'completada': m.completada,
            'fecha_limite': str(m.fecha_limite) if m.fecha_limite else None
        })

    return jsonify(resultado), 200


@metas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_meta():
    usuario_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get('nombre') or not data.get('monto_objetivo'):
        return jsonify({'mensaje': 'Nombre y monto objetivo son obligatorios'}), 400

    nueva = MetaAhorro(
        usuario_id=usuario_id,
        nombre=data['nombre'],
        monto_objetivo=float(data['monto_objetivo']),
        monto_actual=float(data.get('monto_actual', 0)),
        fecha_limite=datetime.strptime(data['fecha_limite'], '%Y-%m-%d').date() if data.get('fecha_limite') else None
    )

    db.session.add(nueva)
    db.session.commit()

    return jsonify({'mensaje': '✅ Meta creada!', 'id': nueva.id}), 201


@metas_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def actualizar_meta(id):
    usuario_id = int(get_jwt_identity())
    meta = MetaAhorro.query.filter_by(id=id, usuario_id=usuario_id).first()

    if not meta:
        return jsonify({'mensaje': 'Meta no encontrada'}), 404

    data = request.get_json()

    if data.get('monto_actual') is not None:
        meta.monto_actual = float(data['monto_actual'])
        if meta.monto_actual >= float(meta.monto_objetivo):
            meta.completada = True

    if data.get('nombre'):
        meta.nombre = data['nombre']

    db.session.commit()
    return jsonify({'mensaje': '✅ Meta actualizada!'}), 200


@metas_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_meta(id):
    usuario_id = int(get_jwt_identity())
    meta = MetaAhorro.query.filter_by(id=id, usuario_id=usuario_id).first()

    if not meta:
        return jsonify({'mensaje': 'Meta no encontrada'}), 404

    db.session.delete(meta)
    db.session.commit()
    return jsonify({'mensaje': '✅ Meta eliminada!'}), 200