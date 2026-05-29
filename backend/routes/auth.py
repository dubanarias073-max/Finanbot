
# routes/auth.py

import os

from flask import Blueprint, request, jsonify

from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)

from extensions import db, bcrypt
from models import Usuario

auth = Blueprint('auth', __name__)

# =========================================================
# FOTO DE PERFIL
# =========================================================

@auth.route('/update_profile_pic', methods=['POST'])
@jwt_required()
def update_profile_pic():

    if 'foto' not in request.files:

        return jsonify({
            "error": "No hay archivo en la petición"
        }), 400

    archivo = request.files['foto']

    if archivo.filename == '':

        return jsonify({
            "error": "No se seleccionó ningún archivo"
        }), 400

    usuario_id = get_jwt_identity()

    usuario = Usuario.query.get(usuario_id)

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    upload_folder = os.path.join(
        'static',
        'uploads',
        'perfiles'
    )

    if not os.path.exists(upload_folder):

        os.makedirs(upload_folder)

    extension = archivo.filename.rsplit('.', 1)[1].lower()

    nombre_archivo = f"perfil_{usuario_id}.{extension}"

    ruta_completa = os.path.join(
        upload_folder,
        nombre_archivo
    )

    archivo.save(ruta_completa)

    usuario.foto_perfil = (
        f"/static/uploads/perfiles/{nombre_archivo}"
    )

    db.session.commit()

    return jsonify({

        "mensaje": "✅ Foto actualizada",

        "url": usuario.foto_perfil

    }), 200


# =========================================================
# REGISTRO
# =========================================================

@auth.route('/registro', methods=['POST'])
def registro():

    data = request.get_json()

    nombre = data.get('nombre')
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    if not nombre or not correo or not contrasena:

        return jsonify({
            'mensaje':
            'Todos los campos son obligatorios'
        }), 400

    usuario_existente = Usuario.query.filter_by(
        correo=correo
    ).first()

    if usuario_existente:

        return jsonify({
            'mensaje':
            'El correo ya está registrado'
        }), 409

    contrasena_hash = bcrypt.generate_password_hash(
        contrasena
    ).decode('utf-8')

    nuevo_usuario = Usuario(

        nombre=nombre,

        correo=correo,

        contrasena_hash=contrasena_hash,

        pregunta_seguridad=data.get(
            'pregunta_seguridad'
        ),

        respuesta_seguridad=data.get(
            'respuesta_seguridad',
            ''
        ).lower().strip(),

        # ✅ IMPORTANTE
        onboarding_completado=False
    )

    db.session.add(nuevo_usuario)

    db.session.commit()

    return jsonify({

        'mensaje':
        '✅ Usuario registrado exitosamente!'

    }), 201


# =========================================================
# LOGIN
# =========================================================

@auth.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    correo = data.get('correo')
    contrasena = data.get('contrasena')

    if not correo or not contrasena:

        return jsonify({
            'mensaje':
            'Correo y contraseña son obligatorios'
        }), 400

    usuario = Usuario.query.filter_by(
        correo=correo
    ).first()

    if not usuario:

        return jsonify({
            'mensaje':
            'Correo o contraseña incorrectos'
        }), 401

    password_correcta = bcrypt.check_password_hash(
        usuario.contrasena_hash,
        contrasena
    )

    if not password_correcta:

        return jsonify({
            'mensaje':
            'Correo o contraseña incorrectos'
        }), 401

    token = create_access_token(
        identity=str(usuario.id)
    )

    return jsonify({

        'mensaje':
        '✅ Inicio de sesión exitoso!',

        'token': token,

        'usuario': {

            'id':
            usuario.id,

            'nombre':
            usuario.nombre,

            'correo':
            usuario.correo,

            'foto_perfil':
            usuario.foto_perfil,

            'ingreso_mensual':
            float(usuario.ingreso_mensual or 0),

            'meta_ahorro':
            float(usuario.meta_ahorro or 0),

            # ✅ CLAVE PARA EL ONBOARDING
            'onboarding_completado':
            usuario.onboarding_completado
        }

    }), 200


# =========================================================
# OBTENER PREGUNTA
# =========================================================

@auth.route('/obtener-pregunta', methods=['POST'])
def obtener_pregunta():

    data = request.get_json()

    correo = data.get('correo')

    if not correo:

        return jsonify({
            'mensaje':
            'Correo es obligatorio'
        }), 400

    usuario = Usuario.query.filter_by(
        correo=correo
    ).first()

    if not usuario:

        return jsonify({
            'mensaje':
            'No existe una cuenta con ese correo'
        }), 404

    if not usuario.pregunta_seguridad:

        return jsonify({
            'mensaje':
            'Esta cuenta no tiene pregunta de seguridad'
        }), 400

    return jsonify({

        'pregunta':
        usuario.pregunta_seguridad

    }), 200


# =========================================================
# VERIFICAR RESPUESTA
# =========================================================

@auth.route('/verificar-seguridad', methods=['POST'])
def verificar_seguridad():

    data = request.get_json()

    correo = data.get('correo')

    respuesta = data.get(
        'respuesta',
        ''
    ).lower().strip()

    usuario = Usuario.query.filter_by(
        correo=correo
    ).first()

    if not usuario:

        return jsonify({
            'mensaje':
            'Usuario no encontrado'
        }), 404

    if usuario.respuesta_seguridad != respuesta:

        return jsonify({
            'mensaje':
            'Respuesta incorrecta'
        }), 401

    return jsonify({

        'mensaje':
        '✅ Verificación exitosa'

    }), 200


# =========================================================
# RESETEAR CONTRASEÑA
# =========================================================

@auth.route('/resetear-contrasena', methods=['POST'])
def resetear_contrasena():

    data = request.get_json()

    correo = data.get('correo')

    nueva_contrasena = data.get(
        'nueva_contrasena'
    )

    usuario = Usuario.query.filter_by(
        correo=correo
    ).first()

    if not usuario:

        return jsonify({
            'mensaje':
            'Usuario no encontrado'
        }), 404

    if not nueva_contrasena:

        return jsonify({
            'mensaje':
            'Nueva contraseña requerida'
        }), 400

    nueva_hash = bcrypt.generate_password_hash(
        nueva_contrasena
    ).decode('utf-8')

    usuario.contrasena_hash = nueva_hash

    db.session.commit()

    return jsonify({

        'mensaje':
        '✅ Contraseña actualizada exitosamente'

    }), 200
