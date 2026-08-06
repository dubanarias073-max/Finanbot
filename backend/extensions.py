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
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def _resolver_usuario_id_desde_token(authorization: Optional[str], requerir_usuario: bool) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        if requerir_usuario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
        return None

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        if requerir_usuario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
        return None

    identificador = payload.get("sub")
    if not identificador:
        if requerir_usuario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
        return None

    if isinstance(identificador, str) and identificador.isdigit():
        return identificador

    db = next(get_db())
    try:
        usuario = db.query(Usuario).filter_by(correo=identificador).first()
    finally:
        db.close()

    if not usuario:
        if requerir_usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        return None

    return str(usuario.id)


def obtener_usuario_id_opcional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """Devuelve el ID del usuario si hay token válido, o None si no hay (invitado)."""
    return _resolver_usuario_id_desde_token(authorization, requerir_usuario=False)


def obtener_usuario_id_requerido(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """Igual que la versión opcional, pero EXIGE el token (como @jwt_required())."""
    return _resolver_usuario_id_desde_token(authorization, requerir_usuario=True) or ""