# FinanBot

FinanBot es un proyecto web para gestionar finanzas personales con un asistente inteligente, simulaciones financieras y registro de transacciones.

## Requisitos previos

- Python 3.10 o superior
- Node.js 18 o superior (para el frontend con Vite)
- XAMPP con MySQL activo
- MySQL Workbench
- Visual Studio Code
- Extensión Live Server (opcional, solo para abrir pantallas sueltas de `frontend/pages`)

## 1. Preparar la base de datos

1. Abre la carpeta `Mysql(base de datos)` del proyecto.
2. Abre el archivo `finanbot_db.sql` en MySQL Workbench.
3. Copia su contenido y ejecútalo en una conexión activa de MySQL para crear la base de datos.

> Si usas XAMPP, asegúrate de iniciar Apache y MySQL desde el panel de control.

## 2. Crear el entorno virtual

Abre una terminal en la carpeta `backend` del proyecto y ejecuta:

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate
```

## 3. Instalar dependencias del backend

Dentro del entorno virtual, instala las dependencias con:

```powershell
pip install -r requirements.txt
```

## 4. Ejecutar el backend

Una vez instaladas las dependencias, inicia el servidor con:

```powershell
fastapi dev app.py
```

Si prefieres usar Uvicorn directamente:

```powershell
uvicorn app:app --reload
```

El backend queda disponible en `http://127.0.0.1:8000` (documentación interactiva en `/docs`).

> **ADVERTENCIA:** si el chatbot se vuelve tonto es porque creaste la base de datos y reiniciaste el servidor de FastAPI. Entonces `Ctrl + C` y vuelve a colocar `fastapi dev app.py` o `uvicorn app:app --reload`.

## 5. Ejecutar el frontend (React + Vite)

El backend por sí solo **no sirve la interfaz**; el frontend corre con su propio servidor de desarrollo. En otra terminal, desde `frontend`:

```powershell
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Vite redirige `/api`, `/legacy` e `/images` al backend de FastAPI en `http://127.0.0.1:8000`, así que el backend debe estar corriendo (paso 4) para que el login, los datos y las imágenes funcionen.

Scripts disponibles (no existe `npm start`, es un proyecto Vite):

```powershell
npm run dev       # servidor de desarrollo (recarga en caliente)
npm run build     # genera la versión de producción en frontend/dist
npm run preview   # sirve localmente el build de producción
```

## Arquitectura

FinanBot usa un monolito modular por capas orientado a MVC:

```text
backend/
	application/
		services/
			auth_service.py       # lógica de autenticación (hash, tokens)
	presentation/
		api.py                     # ensamblado de FastAPI, middleware, mounts /legacy e /images
	routes/                        # endpoints por dominio (auth, transacciones, metas, chat,
	                                #   recomendaciones, simulaciones, perfil, calendario,
	                                #   exportar/excel, aprende, chat-historial, reporte mensual)
	tests/                         # pruebas con pytest
	venv/                          # entorno virtual (no se versiona)
	app.py                         # punto de entrada FastAPI
	config.py                      # configuración/variables de entorno
	database.py                    # conexión SQLAlchemy a MySQL
	extensions.py                  # utilidades compartidas (hash_password, auth, etc.)
	finanbot_ia.py                 # motor del asistente / chatbot
	models.py                      # entidades y relaciones SQLAlchemy
	requirements.txt

frontend/
	node_modules/                  # dependencias (no se versiona, generado por npm install)
	src/                            # código de la app React (App.jsx, main.jsx, estilos)
	pages/                          # pantallas HTML originales, servidas por el backend en /legacy
	index.html                      # punto de entrada real de Vite (no abrir con doble clic)
	package.json / package-lock.json
	vite.config.js

images/                           # logo.png y assets compartidos entre frontend/pages y el backend (/images)
Mysql(base de datos)/             # script(s) SQL para crear la base de datos
```

`frontend/pages` contiene las pantallas originales (dashboard, chat, finanzas, calendario, etc.), servidas por el backend en `/legacy/pages/<archivo>.html`. La app React solo decide **qué pantalla mostrar primero** según la ruta con la que entras (`/`, `/dashboard`, `/chat`, ...); a partir de ahí, cada pantalla navega directamente a la siguiente (login → dashboard → chat, menú lateral, cerrar sesión) sin depender de React, así que recargar la página (F5) siempre te deja en la misma pantalla en la que estabas — la URL cambiará a algo como `http://localhost:5173/legacy/pages/dashboard.html`, y eso es normal.

Rutas de entrada que reconoce la app React:

```text
/             Landing pública (antiguo index.html, ahora frontend/pages/index-legacy.html)
/dashboard    Dashboard
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

### Abrir una pantalla legada de forma independiente (opcional)

Para revisar o editar una pantalla suelta sin pasar por React, puedes abrir cualquier archivo de `frontend/pages` con Live Server. Los enlaces entre pantallas y las rutas a `images/` funcionan igual, siempre que el backend (paso 4) esté corriendo para las llamadas a la API.

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

O correr toda la suite de pruebas:

```powershell
cd backend
pytest -q tests
```