from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, engine


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    import models  # noqa: F401 - registra los modelos antes de crear tablas

    Base.metadata.create_all(bind=engine)
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
