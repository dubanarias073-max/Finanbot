# config.py - Configuración de FinanBot

class Config:
    # Clave secreta para JWT
    SECRET_KEY = 'finanbot_secret_key_2026'
    JWT_SECRET_KEY = 'finanbot_jwt_secret_2026'

    # Conexión con MySQL sin contraseña
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/finanbot_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False