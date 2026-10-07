from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, engine, SessionLocal


def _register_routers(app: FastAPI) -> None:
    from routes.aprende import router as aprende_router
    from routes.auth import router as auth_router
    from routes.calendario import router as calendario_router
    from routes.chat_historial import router as chat_historial_router
    from routes.chat_route import router as chat_router
    from routes.excel import router as excel_router
    from routes.excel_simulaciones import router as excel_sim_router
    from routes.exportar import router as exportar_router
    from routes.metas import router as metas_router
    from routes.perfil import router as perfil_router
    from routes.recomendaciones import router as recomendaciones_router
    from routes.simulaciones import router as simulaciones_router
    from routes.transacciones import router as transacciones_router

    routers = (
        (auth_router, '/api/auth'),
        (excel_sim_router, '/api/simulaciones'),
        (chat_router, '/api/chat'),
        (transacciones_router, '/api/transacciones'),
        (simulaciones_router, '/api/simulaciones'),
        (perfil_router, '/api/perfil'),
        (metas_router, '/api/metas'),
        (recomendaciones_router, '/api/recomendaciones'),
        (chat_historial_router, '/api/chat-historial'),
        (exportar_router, '/api/exportar'),
        (excel_router, '/api/exportar'),
        (aprende_router, '/api/aprende'),
        (calendario_router, '/api/calendario'),
    )
    for router, prefix in routers:
        app.include_router(router, prefix=prefix)


def _migrar_esquema() -> None:
    """Completa cambios incrementales que create_all() no aplica a tablas existentes."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    columnas = {c['name']: c for c in inspector.get_columns('transacciones')}
    columnas_categoria_usuario = {
        c['name'] for c in inspector.get_columns('categorias_usuario')
    }
    nuevas = {
        'ubicacion_nombre': 'VARCHAR(255) NULL',
        'latitud': 'DECIMAL(10,7) NULL',
        'longitud': 'DECIMAL(10,7) NULL',
        'tienda_id': 'INT NULL',
    }
    with engine.begin() as conn:
        for nombre, tipo in nuevas.items():
            if nombre not in columnas:
                conn.execute(text(f'ALTER TABLE transacciones ADD COLUMN {nombre} {tipo}'))
                print(f'Columna transacciones.{nombre} agregada')

        if 'eliminada' not in columnas_categoria_usuario:
            conn.execute(text(
                'ALTER TABLE categorias_usuario '
                'ADD COLUMN eliminada BOOLEAN NOT NULL DEFAULT FALSE'
            ))
            print('Columna categorias_usuario.eliminada agregada')

        if engine.dialect.name != 'mysql':
            return

        categoria = columnas.get('categoria')
        if categoria and 'enum' in str(categoria['type']).lower():
            conn.execute(text(
                'ALTER TABLE transacciones MODIFY COLUMN categoria VARCHAR(50) NOT NULL'
            ))

        relaciones = inspect(engine).get_foreign_keys('transacciones')
        if not any(
            fk.get('constrained_columns') == ['categoria']
            and fk.get('referred_table') == 'categorias'
            for fk in relaciones
        ):
            conn.execute(text(
                'ALTER TABLE transacciones '
                'ADD CONSTRAINT fk_transacciones_categoria '
                'FOREIGN KEY (categoria) REFERENCES categorias(nombre) '
                'ON UPDATE CASCADE ON DELETE RESTRICT'
            ))

        if not any(
            fk.get('constrained_columns') == ['tienda_id']
            and fk.get('referred_table') == 'tiendas'
            for fk in relaciones
        ):
            conn.execute(text(
                'ALTER TABLE transacciones '
                'ADD CONSTRAINT fk_transacciones_tienda '
                'FOREIGN KEY (tienda_id) REFERENCES tiendas(id) '
                'ON DELETE SET NULL'
            ))

        triggers = set(conn.execute(text(
            'SELECT TRIGGER_NAME FROM information_schema.TRIGGERS '
            'WHERE TRIGGER_SCHEMA = DATABASE() '
            'AND TRIGGER_NAME IN '
            "('trg_transacciones_tienda_ins', 'trg_transacciones_tienda_upd')"
        )).scalars())
        definiciones = {
            'trg_transacciones_tienda_ins': """
                CREATE TRIGGER trg_transacciones_tienda_ins
                BEFORE INSERT ON transacciones FOR EACH ROW
                BEGIN
                    DECLARE v_tienda INT;
                    IF NEW.ubicacion_nombre IS NOT NULL
                       AND TRIM(NEW.ubicacion_nombre) <> ''
                       AND NEW.latitud IS NOT NULL AND NEW.longitud IS NOT NULL THEN
                        INSERT IGNORE INTO tiendas (usuario_id, nombre, latitud, longitud)
                        VALUES (NEW.usuario_id, NEW.ubicacion_nombre, NEW.latitud, NEW.longitud);
                        SELECT id INTO v_tienda FROM tiendas
                        WHERE usuario_id = NEW.usuario_id AND nombre = NEW.ubicacion_nombre
                        LIMIT 1;
                        SET NEW.tienda_id = v_tienda;
                    END IF;
                END
            """,
            'trg_transacciones_tienda_upd': """
                CREATE TRIGGER trg_transacciones_tienda_upd
                BEFORE UPDATE ON transacciones FOR EACH ROW
                BEGIN
                    DECLARE v_tienda INT;
                    IF NEW.ubicacion_nombre IS NOT NULL
                       AND TRIM(NEW.ubicacion_nombre) <> ''
                       AND NEW.latitud IS NOT NULL AND NEW.longitud IS NOT NULL THEN
                        INSERT IGNORE INTO tiendas (usuario_id, nombre, latitud, longitud)
                        VALUES (NEW.usuario_id, NEW.ubicacion_nombre, NEW.latitud, NEW.longitud);
                        SELECT id INTO v_tienda FROM tiendas
                        WHERE usuario_id = NEW.usuario_id AND nombre = NEW.ubicacion_nombre
                        LIMIT 1;
                        SET NEW.tienda_id = v_tienda;
                    ELSE
                        SET NEW.tienda_id = NULL;
                    END IF;
                END
            """,
        }
        for nombre, definicion in definiciones.items():
            if nombre not in triggers:
                conn.execute(text(definicion))
                print(f'Trigger {nombre} agregado')


@asynccontextmanager
async def lifespan(app: FastAPI):
    from models import sembrar_categorias

    import models  # noqa: F401 - registra los modelos antes de crear tablas
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        sembrar_categorias(db)
    _migrar_esquema()
    print('Base de datos conectada correctamente!')
    yield


def create_app() -> FastAPI:
    app = FastAPI(title='FinanBot API', version='1.0.0', lifespan=lifespan)
    frontend_dir = Path(__file__).resolve().parents[2] / 'frontend'
    images_dir = frontend_dir.parent / 'images'
    if frontend_dir.exists():
        app.mount('/legacy', StaticFiles(directory=frontend_dir), name='legacy-frontend')
    if images_dir.exists():
        app.mount('/images', StaticFiles(directory=images_dir), name='frontend-images')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization'],
    )

    @app.middleware('http')
    async def add_no_cache_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    _register_routers(app)

    @app.get('/')
    def index():
        return {'message': 'FinanBot API funcionando!', 'architecture': 'monolito-por-capas-mvc'}

    return app
