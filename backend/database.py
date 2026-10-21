# database.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

# La URL vive en config.py (incluye charset=utf8mb4 para los emojis)
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)


@event.listens_for(engine, 'connect')
def _set_mysql_timezone(connection, _connection_record):
    if engine.dialect.name != 'mysql':
        return
    cursor = connection.cursor()
    try:
        cursor.execute("SET time_zone = '-05:00'")
    finally:
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependencia para inyectar la sesión de DB en cada endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
