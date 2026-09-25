from sqlalchemy.orm import Session

from extensions import create_access_token, hash_password, verify_password
from models import Usuario


class AuthService:
    """Casos de uso de autenticacion, independiente del controlador HTTP."""

    @staticmethod
    def usuario_publico(usuario: Usuario) -> dict:
        return {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'rol': usuario.rol,
            'ingreso_mensual': float(usuario.ingreso_mensual or 0),
            'meta_ahorro': float(usuario.meta_ahorro or 0),
            'onboarding_completado': usuario.onboarding_completado,
        }

    @staticmethod
    def registrar(db: Session, *, nombre: str, correo: str, contrasena: str,
                  pregunta_seguridad: str | None = None,
                  respuesta_seguridad: str = '') -> Usuario:
        usuario_existente = db.query(Usuario).filter_by(correo=correo).first()
        if usuario_existente:
            raise ValueError('El correo ya esta registrado')

        usuario = Usuario(
            nombre=nombre,
            correo=correo,
            contrasena_hash=hash_password(contrasena),
            pregunta_seguridad=pregunta_seguridad,
            respuesta_seguridad=respuesta_seguridad.lower().strip(),
            onboarding_completado=False,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def autenticar(db: Session, *, correo: str, contrasena: str) -> Usuario | None:
        usuario = db.query(Usuario).filter_by(correo=correo).first()
        if not usuario or not verify_password(contrasena, usuario.contrasena_hash):
            return None
        return usuario

    @staticmethod
    def token(usuario: Usuario) -> str:
        return create_access_token({
            'sub': str(usuario.id),
            'user_id': usuario.id,
            'rol': usuario.rol,
        })
