# routes/chat_historial.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Chat, Conversacion
from datetime import datetime

chat_historial_bp = Blueprint('chat_historial', __name__)

# ============================================
# CONVERSACIONES
# ============================================

@chat_historial_bp.route('/conversaciones', methods=['GET'])
@jwt_required()
def obtener_conversaciones():
    usuario_id = int(get_jwt_identity())
    conversaciones = Conversacion.query.filter_by(
        usuario_id=usuario_id
    ).order_by(Conversacion.fecha_actualizacion.desc()).all()

    resultado = []
    for c in conversaciones:
        ultimo_mensaje = Chat.query.filter_by(
            conversacion_id=c.id
        ).order_by(Chat.fecha.desc()).first()

        resultado.append({
            'id': c.id,
            'titulo': c.titulo,
            'fecha': c.fecha_actualizacion.strftime('%d/%m/%Y'),
            'ultimo_mensaje': ultimo_mensaje.mensaje[:50] + '...' if ultimo_mensaje and len(ultimo_mensaje.mensaje) > 50 else (ultimo_mensaje.mensaje if ultimo_mensaje else ''),
        })

    return jsonify(resultado), 200


@chat_historial_bp.route('/conversaciones', methods=['POST'])
@jwt_required()
def crear_conversacion():
    usuario_id = int(get_jwt_identity())
    data = request.get_json()

    nueva = Conversacion(
        usuario_id=usuario_id,
        titulo=data.get('titulo', 'Nueva conversación')
    )

    db.session.add(nueva)
    db.session.commit()

    return jsonify({'id': nueva.id, 'titulo': nueva.titulo}), 201


@chat_historial_bp.route('/conversaciones/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_conversacion(id):
    usuario_id = int(get_jwt_identity())
    conv = Conversacion.query.filter_by(id=id, usuario_id=usuario_id).first()

    if not conv:
        return jsonify({'error': 'No encontrada'}), 404

    Chat.query.filter_by(conversacion_id=id).delete()
    db.session.delete(conv)
    db.session.commit()

    return jsonify({'mensaje': '✅ Conversación eliminada'}), 200


@chat_historial_bp.route('/conversaciones/<int:id>/titulo', methods=['PUT'])
@jwt_required()
def actualizar_titulo(id):
    usuario_id = int(get_jwt_identity())
    conv = Conversacion.query.filter_by(id=id, usuario_id=usuario_id).first()
    data = request.get_json()

    if not conv:
        return jsonify({'error': 'No encontrada'}), 404

    conv.titulo = data.get('titulo', conv.titulo)
    db.session.commit()

    return jsonify({'mensaje': '✅ Título actualizado'}), 200


# ============================================
# MENSAJES
# ============================================

@chat_historial_bp.route('/mensajes/<int:conv_id>', methods=['GET'])
@jwt_required()
def obtener_mensajes(conv_id):
    usuario_id = int(get_jwt_identity())
    conv = Conversacion.query.filter_by(id=conv_id, usuario_id=usuario_id).first()

    if not conv:
        return jsonify({'error': 'No encontrada'}), 404

    mensajes = Chat.query.filter_by(
        conversacion_id=conv_id
    ).order_by(Chat.fecha.asc()).all()

    resultado = [{
        'id': m.id,
        'mensaje': m.mensaje,
        'respuesta': m.respuesta,
        'hora': m.fecha.strftime('%I:%M %p')
    } for m in mensajes]

    return jsonify(resultado), 200


@chat_historial_bp.route('/mensajes/<int:conv_id>', methods=['POST'])
@jwt_required()
def guardar_mensaje(conv_id):
    usuario_id = int(get_jwt_identity())
    conv = Conversacion.query.filter_by(id=conv_id, usuario_id=usuario_id).first()

    if not conv:
        return jsonify({'error': 'Conversación no encontrada'}), 404

    data = request.get_json()

    nuevo = Chat(
        usuario_id=usuario_id,
        conversacion_id=conv_id,
        mensaje=data['mensaje'],
        respuesta=data['respuesta'],
        es_invitado=False
    )

    # Actualizar fecha de conversación
    conv.fecha_actualizacion = datetime.utcnow()

    # Actualizar título con primer mensaje si es nueva
    if conv.titulo == 'Nueva conversación':
        titulo = data['mensaje'][:40]
        conv.titulo = titulo + '...' if len(data['mensaje']) > 40 else titulo

    db.session.add(nuevo)
    db.session.commit()

    return jsonify({'mensaje': '✅ Guardado!'}), 201