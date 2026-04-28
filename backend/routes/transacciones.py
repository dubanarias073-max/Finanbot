# routes/transacciones.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Transaccion, Categoria
from datetime import datetime

transacciones_bp = Blueprint('transacciones', __name__)

@transacciones_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_transacciones():
    usuario_id = int(get_jwt_identity())
    transacciones = Transaccion.query.filter_by(
        usuario_id=usuario_id
    ).order_by(Transaccion.fecha.desc()).all()

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

    return jsonify(resultado), 200


@transacciones_bp.route('/', methods=['POST'])
@jwt_required()
def crear_transaccion():
    usuario_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get('tipo') or not data.get('categoria') or not data.get('monto') or not data.get('fecha'):
        return jsonify({'mensaje': 'Faltan campos obligatorios'}), 400

    categoria = Categoria.query.filter_by(nombre=data['categoria']).first()
    if not categoria:
        categoria = Categoria(
            nombre=data['categoria'],
            tipo=data['tipo'],
            icono=data.get('icono', '💸')
        )
        db.session.add(categoria)
        db.session.flush()

    nueva = Transaccion(
        usuario_id=usuario_id,
        categoria_id=categoria.id,
        tipo=data['tipo'],
        monto=float(data['monto']),
        descripcion=data.get('descripcion', ''),
        fecha=datetime.strptime(data['fecha'], '%Y-%m-%d').date()
    )

    db.session.add(nueva)
    db.session.commit()

    return jsonify({'mensaje': '✅ Transacción guardada!', 'id': nueva.id}), 201


@transacciones_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_transaccion(id):
    usuario_id = int(get_jwt_identity())
    transaccion = Transaccion.query.filter_by(id=id, usuario_id=usuario_id).first()

    if not transaccion:
        return jsonify({'mensaje': 'Transacción no encontrada'}), 404

    db.session.delete(transaccion)
    db.session.commit()

    return jsonify({'mensaje': '✅ Transacción eliminada!'}), 200