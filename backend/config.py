# config.py - Configuración de FinanBot

class Settings:
    # Clave secreta para JWT
    SECRET_KEY = 'finanbot_secret_key_2026'
    JWT_SECRET_KEY = 'finanbot_jwt_secret_2026'

    # Conexión con MySQL sin contraseña
    DATABASE_URL = 'mysql+pymysql://root:@localhost/finanbot_db'


settings = Settings()