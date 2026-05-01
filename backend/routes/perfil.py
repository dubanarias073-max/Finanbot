# routes/perfil.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db, bcrypt
from models import Usuario

perfil_bp = Blueprint('perfil', __name__)

@perfil_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_perfil():
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        return jsonify({'mensaje': 'Usuario no encontrado'}), 404

    return jsonify({
        'id': usuario.id,
        'nombre': usuario.nombre,
        'correo': usuario.correo,
        'ingreso_mensual': float(usuario.ingreso_mensual or 0),
        'meta_ahorro': float(usuario.meta_ahorro or 0),
        'fecha_registro': usuario.fecha_registro.strftime('%d/%m/%Y'),
        'onboarding_completado': usuario.onboarding_completado
    }), 200


@perfil_bp.route('/', methods=['PUT'])
@jwt_required()
def actualizar_perfil():
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get(usuario_id)
    data = request.get_json()

    if not usuario:
        return jsonify({'mensaje': 'Usuario no encontrado'}), 404

    if data.get('nombre'):
        usuario.nombre = data['nombre']

    if data.get('ingreso_mensual') is not None:
        usuario.ingreso_mensual = float(data['ingreso_mensual'])

    if data.get('meta_ahorro') is not None:
        usuario.meta_ahorro = float(data['meta_ahorro'])

    if data.get('nueva_contrasena'):
        usuario.contrasena_hash = bcrypt.generate_password_hash(
            data['nueva_contrasena']
        ).decode('utf-8')

    if data.get('onboarding_completado') is not None:
        usuario.onboarding_completado = data['onboarding_completado']

    db.session.commit()

    return jsonify({'mensaje': '✅ Perfil actualizado!'}), 200