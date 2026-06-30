# app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base

# ── LIFESPAN (reemplaza "with app.app_context(): db.create_all()") ────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Importa los modelos para que SQLAlchemy los registre antes de crear tablas
    import models
    Base.metadata.create_all(bind=engine)
    print('✅ Base de datos conectada correctamente!')
    yield
    # (código de cierre/limpieza, si lo necesitas en el futuro)

app = FastAPI(lifespan=lifespan)

# ── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── HEADERS DE RESPUESTA (reemplaza @app.after_request) ────
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ── ROUTERS (reemplaza Blueprints) ──────────────────────────
from routes.auth import router as auth_router
from routes.chat_route import router as chat_router
from routes.transacciones import router as transacciones_router
from routes.simulaciones import router as simulaciones_router
from routes.perfil import router as perfil_router
from routes.metas import router as metas_router
from routes.recomendaciones import router as recomendaciones_router
from routes.chat_historial import router as chat_historial_router
from routes.exportar import router as exportar_router
from routes.excel import router as excel_router
from routes.excel_simulaciones import router as excel_sim_router
from routes.aprende import router as aprende_router

app.include_router(auth_router,               prefix='/api/auth')
app.include_router(excel_sim_router,           prefix='/api/simulaciones')
app.include_router(chat_router,                prefix='/api/chat')
app.include_router(transacciones_router,       prefix='/api/transacciones')
app.include_router(simulaciones_router,        prefix='/api/simulaciones')
app.include_router(perfil_router,              prefix='/api/perfil')
app.include_router(metas_router,               prefix='/api/metas')
app.include_router(recomendaciones_router,     prefix='/api/recomendaciones')
app.include_router(chat_historial_router,      prefix='/api/chat-historial')
app.include_router(exportar_router,            prefix='/api/exportar')
app.include_router(excel_router,               prefix='/api/exportar')
app.include_router(aprende_router,             prefix='/api/aprende')

# ── RUTA RAÍZ ────────────────────────────────────────────────
@app.get('/')
def index():
    return {"message": "🤖 FinanBot API funcionando!"}