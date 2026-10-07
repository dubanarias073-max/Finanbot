# FinanBot

**FinanBot** es una plataforma web modular diseñada para la gestión de finanzas personales. Integra un **asistente inteligente con IA**, simuladores financieros avanzados, calendarios de pagos y herramientas de exportación de reportes.

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
npm run dev
```
Abre `http://localhost:5173` en tu navegador. Vite redirige automáticamente las peticiones de `/api`, `/legacy` e `/images` hacia el backend en el puerto `8000`.

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
├── finanbot_ia.py          # Orquestador del modelo de Inteligencia Artificial
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

⚠️ **Advertencia de desarrollo:** Si el chatbot no responde correctamente o devuelve respuestas genéricas vacías, se debe a una pérdida de sincronía con la base de datos tras un reinicio del servidor de FastAPI. Detén el proceso (`Ctrl + C`) y levanta el backend nuevamente con `fastapi dev app.py`.
