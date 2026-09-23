# config.py - Configuración de FinanBot
import os


class Settings:
    # Clave secreta para JWT (se puede sobrescribir con variables de entorno)
    SECRET_KEY = os.getenv('SECRET_KEY', 'finanbot_secret_key_2026')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'finanbot_jwt_secret_2026')

    # Conexión con MySQL sin contraseña (utf8mb4 para los emojis)
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:@localhost/finanbot_db?charset=utf8mb4',
    )

    # Roles = perfil elegido en el onboarding (usuarios.rol)
    ROLES = ('estudiante', 'empleado', 'independiente', 'emprendedor')


settings = Settings()
