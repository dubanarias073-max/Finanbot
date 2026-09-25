# FinanBot

FinanBot es un proyecto web para gestionar finanzas personales con un asistente inteligente, simulaciones financieras y registro de transacciones.

## Requisitos previos

- Python 3.10 o superior
- XAMPP con MySQL activo
- MySQL Workbench
- Visual Studio Code
- Extensión Live Server (opcional, para abrir la interfaz web)

## 1. Preparar la base de datos

1. Abre la carpeta MySQL (base de datos) del proyecto.
2. Abre el archivo finanbot_db.sql en MySQL Workbench.
3. Copia su contenido y ejecútalo en una conexión activa de MySQL para crear la base de datos.

> Si usas XAMPP, asegúrate de iniciar Apache y MySQL desde el panel de control.

## 2. Crear el entorno virtual

Abre una terminal en la carpeta backend del proyecto y ejecuta:

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate
```

## 3. Instalar dependencias

Dentro del entorno virtual, instala las dependencias con:

```powershell
pip install -r requirements.txt
```

## 4. Ejecutar el backend

Una vez instaladas las dependencias, inicia el servidor con:

fastapi dev app.py


Si prefieres usar Uvicorn directamente:

```powershell
uvicorn app:app --reload
```

## ADVERTENCIA:
si el chatbot se vuelve tonto es porque creaste la base de datos y reiniciaste el servidor de FastAPI,
entonces control + c y vuelve a colocar :
fastapi dev app.py o uvicorn app:app --reload

## 5. Abrir la interfaz

Abre la carpeta frontend y ejecuta el archivo index.html.

Si tienes Live Server instalado en VS Code, puedes hacer clic en “Go Live” para abrir la interfaz en el navegador.

## Arquitectura

FinanBot usa un monolito modular por capas orientado a MVC:

```text
backend/
	presentation/             # ensamblado FastAPI, middleware y routers (Controller)
	application/services/     # casos de uso y reglas de aplicación (Service)
	models.py                 # entidades y relaciones SQLAlchemy (Model)
	database.py               # infraestructura de persistencia existente
	routes/                   # endpoints actuales, migrados gradualmente hacia Service
frontend/                   # interfaz HTML existente, compatible durante la transición
frontend-react/             # nueva interfaz React + Vite
```

La copia React incluye estas rutas:

```text
/             Dashboard / inicio
/login        Inicio de sesión
/registro     Registro de usuario
/onboarding   Configuración inicial
/chat         Chat con historial y modo invitado
/finanzas     Registro y consulta de movimientos
/calendario   Calendario financiero
/recomendaciones
/simulador
/aprende
/perfil
/exportar
```

Las pantallas HTML originales permanecen en `frontend/pages` como respaldo durante la transición. La nueva interfaz React conserva los endpoints existentes y puede migrarse módulo por módulo sin cambiar el backend.

### Ejecutar React

En otra terminal, desde `frontend-react`:

```powershell
npm install
npm run dev
```

Abre `http://localhost:5173`. Vite redirige `/api` al backend de FastAPI en
`http://127.0.0.1:8000`. Las páginas actuales siguen disponibles desde el
servidor de archivos o Live Server, por lo que la migración puede hacerse módulo a módulo.

Para generar una versión de producción:

```powershell
npm run build
```

El backend continúa iniciándose desde `backend` con `fastapi dev app.py`.

## 6. Funcionalidades principales

- Registro de ingresos y gastos
- Metas de ahorro
- Simulaciones financieras
- Chat con inteligencia artificial
- Exportación de reportes

## 7. Pruebas rápidas

Para validar el motor del chatbot puedes ejecutar:

```powershell
cd backend
pytest -q tests/test_finanbot_ia.py
```
