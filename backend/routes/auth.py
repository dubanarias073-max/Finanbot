import os
from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import Usuario
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth = Blueprint('auth', __name__)

# --- RUTA PARA FOTO DE PERFIL ---
@auth.route('/update_profile_pic', methods=['POST'])
@jwt_required()
def update_profile_pic():
    if 'foto' not in request.files:
        return jsonify({"error": "No hay archivo en la petición"}), 400
    
    archivo = request.files['foto']
    if archivo.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    upload_folder = os.path.join('static', 'uploads', 'perfiles')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    extension = archivo.filename.rsplit('.', 1)[1].lower()
    nombre_archivo = f"perfil_{usuario_id}.{extension}"
    ruta_completa = os.path.join(upload_folder, nombre_archivo)
    
    archivo.save(ruta_completa)
    
    usuario.foto_perfil = f"/static/uploads/perfiles/{nombre_archivo}"
    db.session.commit()
    
    return jsonify({
        "mensaje": "✅ Foto actualizada", 
        "url": usuario.foto_perfil
    }), 200

# --- REGISTRO Y LOGIN ---
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
        contrasena_hash=contrasena_hash,
        pregunta_seguridad=data.get('pregunta_seguridad'),
        respuesta_seguridad=data.get('respuesta_seguridad', '').lower().strip()
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
    if not usuario or not bcrypt.check_password_hash(usuario.contrasena_hash, data['contrasena']):
        return jsonify({'mensaje': 'Correo o contraseña incorrectos'}), 401

    token = create_access_token(identity=str(usuario.id))
    return jsonify({
        'mensaje': '✅ Inicio de sesión exitoso!',
        'token': token,
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'foto_perfil': usuario.foto_perfil
        }
    }), 200

# --- RUTAS DE RECUPERACIÓN (LAS QUE TE DABAN 404) ---

@auth.route('/obtener-pregunta', methods=['POST'])
def obtener_pregunta():
    data = request.get_json()
    if not data.get('correo'):
        return jsonify({'mensaje': 'Correo es obligatorio'}), 400

    usuario = Usuario.query.filter_by(correo=data['correo']).first()
    if not usuario:
        return jsonify({'mensaje': 'No existe una cuenta con ese correo'}), 404

    if not usuario.pregunta_seguridad:
        return jsonify({'mensaje': 'Esta cuenta no tiene pregunta de seguridad'}), 400

    return jsonify({'pregunta': usuario.pregunta_seguridad}), 200

@auth.route('/verificar-seguridad', methods=['POST'])
def verificar_seguridad():
    data = request.get_json()
    usuario = Usuario.query.filter_by(correo=data.get('correo')).first()
    
    if not usuario or usuario.respuesta_seguridad != data.get('respuesta', '').lower().strip():
        return jsonify({'mensaje': 'Respuesta incorrecta'}), 401

    return jsonify({'mensaje': '✅ Verificación exitosa'}), 200

@auth.route('/resetear-contrasena', methods=['POST'])
def resetear_contrasena():
    data = request.get_json()
    usuario = Usuario.query.filter_by(correo=data.get('correo')).first()
    
    if not usuario:
        return jsonify({'mensaje': 'Error al procesar la solicitud'}), 404

    nueva_hash = bcrypt.generate_password_hash(data['nueva_contrasena']).decode('utf-8')
    usuario.contrasena_hash = nueva_hash
    db.session.commit()
    
    return jsonify({'mensaje': '✅ Contraseña actualizada exitosamente'}), 200
