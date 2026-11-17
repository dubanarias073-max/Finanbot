# config.py - Configuración de FinanBot
import json
import os
import secrets
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
# Claves generadas automáticamente cuando no vienen en el .env (no se sube a git)
_ARCHIVO_CLAVES_LOCALES = _BACKEND_DIR / '.claves_locales.json'
# Valores que estaban escritos en el código: cualquiera que lea el repositorio los conoce
_CLAVES_INSEGURAS = {'finanbot_secret_key_2026', 'finanbot_jwt_secret_2026', '', 'changeme'}


def _clave_secreta(nombre: str) -> str:
    """Lee la clave del entorno. Si no está (o es una clave conocida), usa una
    aleatoria guardada en .claves_locales.json para que no cambie al reiniciar.
    Con FINANBOT_ENV=produccion se exige que venga en el entorno."""
    valor = os.getenv(nombre, '')
    if valor and valor not in _CLAVES_INSEGURAS and len(valor) >= 16:
        return valor
    if os.getenv('FINANBOT_ENV', '').lower() in ('produccion', 'production', 'prod'):
        raise RuntimeError(
            f'Falta {nombre} en el entorno (mínimo 16 caracteres). '
            f'Genera una con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    try:
        guardadas = json.loads(_ARCHIVO_CLAVES_LOCALES.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        guardadas = {}
    if not guardadas.get(nombre):
        guardadas[nombre] = secrets.token_urlsafe(48)
        try:
            _ARCHIVO_CLAVES_LOCALES.write_text(json.dumps(guardadas, indent=2), encoding='utf-8')
        except OSError:
            pass
        print(f'[FinanBot] {nombre} no estaba en el .env: se generó una clave local aleatoria.')
    return guardadas[nombre]


def _lista_env(nombre: str, por_defecto: list[str]) -> list[str]:
    valor = os.getenv(nombre)
    if not valor:
        return por_defecto
    return [x.strip().rstrip('/') for x in valor.split(',') if x.strip()]


class Settings:
    # Claves secretas (JWT y firma de respuestas de seguridad). Nunca con valores fijos.
    SECRET_KEY = _clave_secreta('SECRET_KEY')
    JWT_SECRET_KEY = _clave_secreta('JWT_SECRET_KEY')

    # Conexión con MySQL sin contraseña (utf8mb4 para los emojis)
    DATABASE_URL = (os.getenv('DATABASE_URL')
                    or 'mysql+pymysql://root:@localhost/finanbot_db?charset=utf8mb4')

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT') or 587)
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_APP_PASSWORD = os.getenv('SMTP_APP_PASSWORD', '').replace(' ', '')
    SMTP_FROM = os.getenv('SMTP_FROM', '')
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
    # Orígenes que pueden llamar la API desde otro dominio (separados por coma).
    # El frontend usa el proxy de Vite (/api), así que normalmente basta con localhost.
    CORS_ORIGINS = _lista_env('CORS_ORIGINS', [
        'http://localhost:5173', 'http://127.0.0.1:5173',
        'http://localhost:8000', 'http://127.0.0.1:8000',
    ]) + ([PUBLIC_BASE_URL] if PUBLIC_BASE_URL else [])
    # Login: intentos fallidos permitidos antes de bloquear y minutos de bloqueo
    LOGIN_MAX_INTENTOS = int(os.getenv('LOGIN_MAX_INTENTOS') or 5)
    LOGIN_BLOQUEO_MIN = int(os.getenv('LOGIN_BLOQUEO_MIN') or 15)
    UPLOADS_DIR = Path(
        os.getenv('FINANBOT_UPLOADS_DIR') or str(Path(__file__).resolve().parent / 'uploads')
    )

    # Roles = perfil elegido en el onboarding (usuarios.rol)
    ROLES = ('estudiante', 'empleado', 'independiente', 'emprendedor')


settings = Settings()
