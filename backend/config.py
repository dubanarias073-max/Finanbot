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

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_APP_PASSWORD = os.getenv('SMTP_APP_PASSWORD', '').replace(' ', '')
    SMTP_FROM = os.getenv('SMTP_FROM', '')
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')

    # Roles = perfil elegido en el onboarding (usuarios.rol)
    ROLES = ('estudiante', 'empleado', 'independiente', 'emprendedor')


settings = Settings()
