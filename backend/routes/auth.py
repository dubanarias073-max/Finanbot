# routes/auth.py
from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import Usuario
from flask_jwt_extended import create_access_token

auth = Blueprint('auth', __name__)

@auth.route('/registro', methods=['POST'])
def registro():
    data = request.get_json()

    if not data.get('nombre') or not data.get('correo') or not data.get('contrasena'):
        return jsonify({'mensaje': 'Todos los campos son obligatorios'}), 400

    if Usuario.query.filter_by(correo=data['correo']).first():
        return jsonify({'mensaje': 'El correo ya está registrado'}), 409

    contrasena_hash = bcrypt.generate_password_hash(data['contrasena']).decode('utf-8')

    nuevo_usuario = Usuario(
        nombre=data['nombre'],
        correo=data['correo'],
        contrasena_hash=contrasena_hash
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({'mensaje': '✅ Usuario registrado exitosamente!'}), 201


@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data.get('correo') or not data.get('contrasena'):
        return jsonify({'mensaje': 'Correo y contraseña son obligatorios'}), 400

    usuario = Usuario.query.filter_by(correo=data['correo']).first()

    if not usuario:
        return jsonify({'mensaje': 'Correo o contraseña incorrectos'}), 401

    if not bcrypt.check_password_hash(usuario.contrasena_hash, data['contrasena']):
        return jsonify({'mensaje': 'Correo o contraseña incorrectos'}), 401

    token = create_access_token(identity=str(usuario.id))

    return jsonify({
        'mensaje': '✅ Inicio de sesión exitoso!',
        'token': token,
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo
        }
    }), 200