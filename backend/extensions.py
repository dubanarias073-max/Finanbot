# extensions.py
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from config import settings
from database import get_db
from models import Usuario

# ── BCRYPT (reemplaza flask_bcrypt) ────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ── JWT (reemplaza flask_jwt_extended) ─────────────────────
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(days=7)

def create_access_token(data: dict) -> str:
    """data debe incluir 'sub' (id del usuario). Opcionalmente 'rol'."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_token_para_usuario(usuario: Usuario) -> str:
    """Atajo para login/registro: mete id y rol en el token."""
    return create_access_token({"sub": str(usuario.id), "rol": usuario.rol})


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _resolver_usuario_desde_token(
    authorization: Optional[str],
    db: Session,
    requerir_usuario: bool,
) -> Optional[Usuario]:
    def _fallar(codigo: int, detalle: str):
        if requerir_usuario:
            raise HTTPException(status_code=codigo, detail=detalle)
        return None

    if not authorization or not authorization.startswith("Bearer "):
        return _fallar(status.HTTP_401_UNAUTHORIZED, "Token requerido")

    payload = decode_access_token(authorization.split(" ")[1])
    if not payload:
        return _fallar(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")

    identificador = payload.get("sub")
    if not identificador:
        return _fallar(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")

    # Tokens nuevos usan el id; los antiguos pueden traer el correo.
    if isinstance(identificador, str) and identificador.isdigit():
        usuario = db.get(Usuario, int(identificador))
    else:
        usuario = db.query(Usuario).filter_by(correo=identificador).first()

    if not usuario:
        return _fallar(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    return usuario


# ── Dependencias: ID (compatibles con el código existente) ─

def obtener_usuario_id_opcional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """Devuelve el ID del usuario si hay token válido, o None si no hay (invitado)."""
    usuario = _resolver_usuario_desde_token(authorization, db, requerir_usuario=False)
    return str(usuario.id) if usuario else None


def obtener_usuario_id_requerido(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """Igual que la versión opcional, pero EXIGE el token (como @jwt_required())."""
    usuario = _resolver_usuario_desde_token(authorization, db, requerir_usuario=True)
    return str(usuario.id)


# ── Dependencia: usuario completo (incluye su rol) ─────────

def obtener_usuario_actual(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Usuario:
    """Devuelve el objeto Usuario (con su rol). Exige token."""
    return _resolver_usuario_desde_token(authorization, db, requerir_usuario=True)
