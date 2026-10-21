# FinanBot

**FinanBot** es una plataforma web modular diseñada para la gestión de finanzas personales. Integra un **asistente inteligente con IA**, simuladores financieros avanzados, calendarios de pagos y herramientas de exportación de reportes.

La fecha y hora de negocio de la aplicación usan `America/Bogota` (UTC−5, sin horario de verano), independientemente de la zona horaria del servidor o del navegador. Las expiraciones de seguridad se calculan en UTC.

La arquitectura sigue un enfoque de **monolito modular por capas** orientado a MVC, donde un backend en **FastAPI** sirve tanto una API REST como pantallas legadas (`/legacy`), complementado por un frontend moderno en **React + Vite**.

---

## 🚀 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:
* **Python 3.10** o superior.
* **Node.js 18** o superior (con npm).
* **Visual Studio Code**.

Elige uno de los dos siguientes entornos para preparar tu base de datos antes de inicializar los servidores.

---

## 🐳 Entorno A: Docker Desktop + HeidiSQL 

Esta opción automatiza la creación del servidor de base de datos en un contenedor aislado, evitando conflictos de puertos en tu sistema operativo.

### 1. Levantar el contenedor de MySQL
Ejecuta el siguiente comando en tu terminal de PowerShell. Este comando descargará la imagen oficial, configurará el usuario `root`, asignará la contraseña `123456` y **creará automáticamente la base de datos** vacía llamada `finanbot_db`:

```powershell
docker run --name mi-mysql -e MYSQL_ROOT_PASSWORD=123456 -e MYSQL_DATABASE=finanbot_db -p 3306:3306 -d mysql:latest
```

### 2. Importar las tablas con HeidiSQL
1. Abre **HeidiSQL** y haz clic en el botón **Nuevo** (abajo a la izquierda) para crear una sesión.
2. Configura los siguientes parámetros en la pestaña *Settings*:
   * **Tipo de red / Network type:** `MariaDB or MySQL (TCP/IP)`
   * **Host / IP:** `127.0.0.1`
   * **Usuario / User:** `root`
   * **Contraseña / Password:** `123456`
   * **Puerto / Port:** `3306`
3. Haz clic en **Abrir** (Open). Verás la base de datos `finanbot_db` en el árbol de la izquierda.
4. Selecciónala, ve a la pestaña **Consulta** (Query), copia y pega el contenido del archivo `Mysql(base de datos)/finanbot_db.sql` y presiona **F9** para ejecutar el script.

### 3. Archivo de entorno `.env` para Docker
En la raíz de la carpeta `backend/`, crea un archivo llamado `.env` apuntando a tu puerto local con la contraseña configurada:

```env
SECRET_KEY="finanbot_super_secret_key_2026_production_ready"
JWT_SECRET_KEY="finanbot_jwt_token_secret_generation_2026"

# URL activa para el contenedor Docker
DATABASE_URL="mysql+pymysql://root:123456@127.0.0.1:3306/finanbot_db?charset=utf8mb4"

# FinanBot IA 2 (opcional, ver sección "Activar FinanBot IA 2")
GEMINI_API_KEY="PEGA_AQUI_TU_CLAVE"
```

---

## 🛠️ Entorno B: XAMPP + MySQL Workbench (Tradicional)

Usa esta opción si prefieres administrar los servicios de forma local directamente sobre tu máquina mediante herramientas tradicionales.

### 1. Iniciar los servicios locales
1. Abre el panel de control de **XAMPP**.
2. Haz clic en el botón **Start** de los módulos **Apache** y **MySQL**. Asegúrate de que los indicadores cambien a color verde.

### 2. Importar las tablas con MySQL Workbench
1. Abre **MySQL Workbench** y abre tu conexión local (usualmente llamada *Local Instance 3306*).
2. Ve al menú superior y selecciona **File > Open SQL Script...**
3. Busca y abre el archivo `Mysql(base de datos)/finanbot_db.sql`.
4. Haz clic en el icono del **rayo** en la barra de herramientas para ejecutar todo el script. Esto creará la base de datos y todas las tablas del sistema.



### 3. Archivo de entorno `.env` para XAMPP
En la raíz de la carpeta `backend/`, crea un archivo llamado `.env` sin contraseña en la cadena de conexión (configuración por defecto de XAMPP):

```env
SECRET_KEY="finanbot_super_secret_key_2026_production_ready"
JWT_SECRET_KEY="finanbot_jwt_token_secret_generation_2026"

# URL activa para XAMPP (sin contraseña)
DATABASE_URL="mysql+pymysql://root:@127.0.0.1:3306/finanbot_db?charset=utf8mb4"

# FinanBot IA 2 (opcional, ver sección "Activar FinanBot IA 2")
GEMINI_API_KEY="PEGA_AQUI_TU_CLAVE"
```

---


## ⚙️ Inicialización del Proyecto

Una vez que tu base de datos esté lista con cualquiera de las dos opciones anteriores, sigue estos pasos:

### Paso 1: Levantar el Backend (FastAPI)
Abre una terminal en la carpeta `backend/` y ejecuta:

```powershell
# 1. Crear el entorno virtual
python -m venv venv

# 2. Activar el entorno virtual
.\venv\Scripts\Activate

# 3. Instalar dependencias del proyecto
pip install -r requirements.txt

# 4. Iniciar el servidor en modo desarrollo
fastapi dev app.py
```
> El backend estará disponible en `http://127.0.0.1:8000` con documentación interactiva en `/docs`. También puedes usar `uvicorn app:app --reload`.

### Paso 2: Levantar el Frontend (React + Vite)
El backend no sirve la interfaz de usuario de forma directa de manera nativa. En una **nueva terminal**, navega a la carpeta `frontend/`:

```powershell
# 1. Instalar dependencias de Node
npm install

# 2. Levantar el servidor de desarrollo de Vite
npm run dev -- --host
```
Abre la dirección `Network` que muestra Vite (por ejemplo, `http://192.168.1.10:5173`) desde otro dispositivo conectado a la misma red Wi-Fi. Vite redirige automáticamente las peticiones de `/api`, `/legacy` e `/images` al backend local en el puerto `8000`; deja el backend ejecutándose y permite el acceso de Node.js/Vite en el firewall de Windows si aparece una solicitud.

---

## 📧 Registro con Gmail y recuperación por correo

Para que FinanBot pueda enviar códigos de recuperación y avisos de inicio de sesión, configura una cuenta emisora que controles. Esta dirección puede ser una cuenta dedicada al proyecto; no tiene que ser la misma dirección que usan los clientes. En `backend/.env`, agrega tus propios valores (**cada variable en su propia línea**):

```env
SMTP_PORT="587"
SMTP_USERNAME="finanbot.sena@gmail.com"
SMTP_APP_PASSWORD="inqlxalpizdplvgo"
SMTP_FROM="finanbot.sena@gmail.com"

GOOGLE_CLIENT_ID="315416890012-ffvd56diopltc438ev5e8bgrqd2q931m.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET=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ASSWORD_RESET_URL="http://(tu ip):8000/legacy/pages/login.html"
PUBLIC_BASE_URL=http://TU_IP_DE_RED:5173
```

Los correos de recuperación contienen un código de 6 dígitos y un enlace directo para establecer una contraseña nueva. Si reportas un inicio de sesión con “No fui yo”, se cierran las sesiones y aparece el formulario para cambiar la contraseña inmediatamente en esa misma página.


---

## 🌐 Acceso desde otros dispositivos y enlaces del correo (guía de configuración)

El enlace que llega por correo (recuperar contraseña, "Sí, fui yo" / "No fui yo") se construye con `PUBLIC_BASE_URL`. Si esa dirección no es válida o no es alcanzable desde el dispositivo donde se abre el correo, el enlace no carga (`ERR_CONNECTION_TIMED_OUT`) o la app muestra *"Configura PUBLIC_BASE_URL con una dirección accesible..."*.

### Archivos que se modificaron para que funcione

| Archivo | Cambio | Por qué |
|---|---|---|
| `backend/.env` | Corregir `PUBLIC_BASE_URL` (sin espacios, sin comillas raras, sin caracteres sueltos al final) y poner **cada variable en su propia línea** | Con un espacio dentro de las comillas o `GOOGLE_CLIENT_SECRET` pegado a la línea siguiente, el backend rechaza la URL como inválida y el secret de Google se lee mal |
| `backend/.env` | Poner en `PUBLIC_BASE_URL` la IP actual de red (o la URL del túnel) | La IP del Wi-Fi cambia según la red; una IP vieja da *timeout* |
| `frontend/vite.config.js` | Agregar `allowedHosts` dentro de `server` | Vite 6+ bloquea dominios desconocidos (como el del túnel) con "Blocked request" |
| Regla de firewall de Windows | Permitir entrada TCP al puerto 5173 | Windows bloquea por defecto las conexiones entrantes desde otros dispositivos |
| *(opcional)* `backend/routes/auth.py` | Que `solicitar_recuperacion` y `reenviar_codigo_recuperacion` reciban `request: Request` y usen `_base_url_publica(request)` | Así el enlace usa la URL desde la que se entra a la app aunque `PUBLIC_BASE_URL` no esté bien. Hay que ajustar los tests que llaman estas funciones |

### 1. `frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true, // o ['.trycloudflare.com'] para limitarlo al túnel
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/legacy': 'http://127.0.0.1:8000',
      '/images': 'http://127.0.0.1:8000',
    },
  },
})
```

Vite no recarga en caliente los cambios de `server`: reinícialo (`Ctrl + C` y `npm run dev`).

### 2. `PUBLIC_BASE_URL` en `backend/.env`

Reglas: debe empezar por `http://` o `https://`, ser solo host y puerto (sin ruta como `/api`), sin espacios, sin comillas internas y **nunca** `localhost` ni `127.0.0.1`.

```env
# Red local (usa la IP de la línea "Network ... Wi-Fi" que muestra Vite)
PUBLIC_BASE_URL=http://(tu ip):5173

# O con túnel público
PUBLIC_BASE_URL=https://tu-subdominio.trycloudflare.com

RECORDAR: poner el dominio en https://console.cloud.google.com/apis/credentials?project=finanbot-512414 y editar (cliente web 1 de finanbot.sena@gmail.com) solo el url ej: https://tu-subdominio.trycloudflare.com

```

Reinicia el backend después de editar el `.env`.

### 3. Firewall de Windows (PowerShell como administrador)

```powershell
New-NetFirewallRule -DisplayName "Vite 5173" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow -Profile Any
```

### 4. Túnel público con Cloudflare (funciona desde cualquier red)

Útil cuando la red tiene *aislamiento de clientes* (común en redes institucionales como la del SENA), cuando la IP cambia seguido o cuando el dispositivo que abre el correo no está en el mismo Wi-Fi.

```powershell
# Instalar (una sola vez) y reabrir PowerShell
winget install --id Cloudflare.cloudflared

# Abrir el túnel (deja esta ventana abierta mientras pruebas)
cloudflared tunnel --url http://localhost:5173

Si sigue sin reconocerlo, actualiza el PATH de la sesión actual sin cerrar nada y vuelve a ejecutar el de arriba :

powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cloudflared tunnel --url http://localhost:5173
```

1. Copia la URL `https://....trycloudflare.com` que muestra la terminal.
2. Ponla en `PUBLIC_BASE_URL` del `backend/.env`.
3. Verifica `allowedHosts` en `vite.config.js` y reinicia Vite y el backend.
4. Abre la app **desde la URL del túnel** (no desde `localhost`), pide el código de recuperación y abre el correo desde cualquier dispositivo.


> La URL del túnel gratuito **cambia cada vez que reinicias `cloudflared`**: hay que actualizar `PUBLIC_BASE_URL` y reiniciar el backend. Mientras el túnel esté abierto, la app es accesible desde internet; ciérralo cuando termines de probar.

### Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ERR_CONNECTION_TIMED_OUT` al abrir el enlace del correo | La IP de `PUBLIC_BASE_URL` ya no es la del equipo (cambió de red) o hay firewall/aislamiento de clientes | Revisa la IP en la línea `Network` de Vite o con `ipconfig`, actualiza `.env`, abre el firewall o usa el túnel |
| "Configura PUBLIC_BASE_URL con una dirección accesible..." | `PUBLIC_BASE_URL` vacío, con `localhost`, sin `http://`, con espacios o con ruta | Corrige el valor y reinicia el backend |
| "Blocked request. This host is not allowed" | Falta `allowedHosts` o no se reinició Vite | Agrégalo en `vite.config.js` y reinicia Vite |
| El enlace carga en tu PC pero no en el celular | Firewall de Windows o aislamiento de clientes del Wi-Fi | Regla de firewall, hotspot del celular o túnel |
| Error 502 / 1033 en la URL del túnel | El túnel aún se propaga o Vite no está corriendo | Espera unos segundos y confirma que `npm run dev` está activo |
| "El enlace no es válido o ya venció" | Los enlaces y códigos duran 10 minutos y son de un solo uso | Solicita uno nuevo |
| El inicio con Google falla | `GOOGLE_CLIENT_SECRET` pegado a la línea siguiente en el `.env` | Una variable por línea |

**Alternativa sin correo ni URL:** el botón **"Recuperar con pregunta de seguridad"** permite cambiar la contraseña sin depender de `PUBLIC_BASE_URL`. El código de 6 dígitos del correo también funciona sin abrir el enlace.

---

## 🤖 Activar FinanBot IA 2 (Gemini, gratis)

El chat tiene dos cerebros:

* **FinanBot (reglas):** registra, edita y borra movimientos, metas, IVA, descuentos y reportes. Funciona siempre, sin internet ni claves.
* **FinanBot IA 2:** responde las preguntas libres ("¿cómo voy este mes?", "¿me alcanza para viajar en diciembre?") usando los datos reales del usuario y propone botones con el siguiente paso. **Necesita una clave de Gemini.** Sin clave, el chat sigue funcionando solo con las reglas.

### 1. Crear tu clave (cada integrante crea la suya)
1. Entra a [aistudio.google.com/apikey](https://aistudio.google.com/apikey) con tu cuenta de Google.
2. Clic en **Crear clave de API** → acepta el proyecto por defecto. Queda en **Nivel gratuito** (no pide tarjeta).
3. Copia la clave (empieza por `AIza...`).

> Cada quien debe usar **su propia clave**: el cupo gratis es por clave, y si todos comparten una se agota más rápido.

### 2. Ponerla en el `.env`
En `backend/.env` agrega (o completa) la línea:

```env
GEMINI_API_KEY="AIza...tu_clave"
```



### 3. Reiniciar y probar
Reinicia el backend y escribe en el chat algo libre, por ejemplo *"¿cómo voy este mes y qué me recomiendas?"*. En la terminal debe aparecer:

```text
[FinanBot IA 2] Usando modelo Gemini: gemini-3.1-flash-lite
```

### Mensajes en la terminal

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `Usando modelo Gemini: ...` | La IA 2 está activa | Nada 🎉 |
| `no respondió (HTTP 404)` | Google retiró ese modelo | Nada, prueba el siguiente solo |
| `no respondió (HTTP 429)` | Se agotó el cupo gratis de ese modelo | Nada, prueba otro; si se agotan todos, usa reglas 60 s |
| `no respondió (HTTP 503)` | Google está saturado | Nada, prueba otro modelo |
| `tardó demasiado` | Ese modelo está lento (más de 12 s) | Nada, prueba otro modelo |
| `HTTP Error 400` / `API key not valid` | Clave mal copiada | Revisa `GEMINI_API_KEY` en el `.env` |
| No aparece ningún mensaje `[FinanBot IA 2]` | No está leyendo la clave | Revisa el paso 3 y reinicia |

> ⚠️ **Nunca subas el `.env` a GitHub** (contiene tu clave y las claves JWT). Verifica que `.env` esté en el `.gitignore`.

### Alternativas a Gemini (opcional)
Se usa el primer proveedor que tenga clave en el `.env`:

```env
# Groq (también gratis: console.groq.com)
GROQ_API_KEY="gsk_..."

# Ollama, sin clave y sin internet (requiere instalar Ollama y: ollama pull llama3.1)
FINANBOT_IA2_BASE_URL="http://localhost:11434/v1"
FINANBOT_IA2_MODEL="llama3.1"
```

---

## 📐 Arquitectura del Proyecto

El proyecto está segmentado de forma monolítica pero modular por capas:

```text
backend/
├── application/services/   # Lógica de negocio encapsulada (auth_service, etc.)
├── presentation/api.py     # Configuración central de FastAPI, Middlewares y ruteo legacy
├── routes/                 # Endpoints REST organizados por dominios financieros
├── tests/                  # Suite de pruebas unitarias e integración (Pytest)
├── app.py                  # Punto de entrada de la aplicación
├── config.py               # Lector de variables de entorno y configuraciones
├── database.py             # Instanciación y gestión del ciclo de vida de SQLAlchemy
├── finanbot_ia.py          # Orquestador del chat (reglas: registrar, editar, metas, IVA…)
├── finanbot_ia_2.py        # FinanBot IA 2: conversación libre con Gemini/Groq/Ollama
└── models.py               # Declaración de modelos y mapas relacionales ORM

frontend/
├── src/                    # Componentes core de React y estilos globales
├── pages/                  # Vistas HTML estáticas servidas en la ruta /legacy
└── vite.config.js          # Configuración del servidor de desarrollo y Proxies de API

images/                     # Assets compartidos del ecosistema
Mysql(base de datos)/       # Scripts de respaldo y migraciones SQL
```

### 🔄 Funcionamiento de Rutas y Páginas Legadas
Las vistas interactivas residen en `frontend/pages/` y son servidas por FastAPI en `/legacy/pages/<archivo>.html`. 

La aplicación React actúa como el **enrutador inicial** para determinar la vista de entrada. Tras el renderizado inicial, la navegación ocurre directamente entre las páginas HTML mediante hipervínculos nativos. Al recargar la página (`F5`), el navegador conserva el estado de la vista legada actual en la URL de forma transparente.

---

## 🧪 Validaciones y Pruebas Unitarias

Para comprobar el correcto funcionamiento de los algoritmos del Chatbot y las conexiones, puedes correr los tests integrados:

```powershell
# Ejecutar pruebas del motor de IA
pytest -q tests/test_finanbot_ia.py

# Ejecutar la suite completa de pruebas del backend
pytest -q tests
```

⚠️ **Advertencia de desarrollo:** Si todo no responde  correctamente o devuelve respuestas genéricas vacías, se debe a una pérdida de sincronía con la base de datos tras un reinicio del servidor de FastAPI. Detén el proceso (`Ctrl + C`) y levanta el backend nuevamente con `fastapi dev app.py`.