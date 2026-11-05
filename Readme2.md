# Finanbot - Guía de Acceso y Clonación en Data-Center

Esta guía detalla los pasos secuenciales para establecer la conexión al entorno virtual del proyecto **Finanbot** en el entorno institucional.

---

## 1. Acceso a la Plataforma DataSENA

1. Ingrese al portal web oficial: `https://datasena.com/`
2. Diríjase a la esquina inferior derecha y seleccione la opción **Prácticas**.
3. Autentíquese utilizando las credenciales asignadas para su entorno:
   - **Usuario:** `Aprendiz01@datasena.local`
   - **Contraseña:** `Data2025+`
4. El sistema abrirá automáticamente la sesión en **Citrix Workspace** (si no cuenta con el software, deberá descargarlo e instalarlo previamente). Vuelva a introducir sus datos si el cliente lo solicita para desplegar el servidor virtual.

---

## 2. Configuración de Conexión SSH en VS Code

1. Abra **Visual Studio Code** e ingrese al panel de extensiones (`Ctrl + Shift + X`).
2. Busque e instale la extensión oficial **Remote - SSH** de Microsoft.
3. En la esquina inferior izquierda de la ventana, haga clic en el botón de Entornos Remotos **`><`**.
4. Seleccione la opción **Connect to Host...** del menú desplegable.
5. Seleccione **Add New SSH Host...** e introduzca la siguiente cadena de conexión:
   ```bash
   ssh sofianieto@10.12.19.82
   ```
6. Complete el flujo seleccionando su archivo de configuración por defecto. El entorno de desarrollo remoto se inicializará.

---

## 3. Clonación del Repositorio mediante PowerShell

1. Abra una terminal de **PowerShell** en su máquina local para verificar el estado de la red y acceder al entorno:
   ```powershell
   # Validar conectividad con el servidor remoto
   ping 10.12.19.82

   # Establecer sesión remota segura
   ssh sofianieto@10.12.19.82
   ```
2. Una vez autenticado dentro de la terminal del servidor remoto, ejecute la clonación del repositorio de Git:
   ```powershell
   git clone https://github.com/dubanarias073-max/Finanbot.git
   ```
3. Al finalizar la descarga, diríjase al menú superior de VS Code conectado por SSH, seleccione **File > Open Folder...** y abra el directorio raíz llamado `Finanbot`.

## 4. Configuración de la Base de Datos en Docker (Linux / SSH)

Para desplegar el servidor de base de datos MySQL de forma limpia e importar su estructura inicial:

1. Limpiar y Levantar el Contenedor de MySQL
Ejecute los siguientes comandos en orden. El primero asegurará la eliminación de cualquier contenedor previo con el mismo nombre para evitar conflictos, y el segundo creará la instancia limpia:

```bash
# Eliminar el contenedor existente si ya existe(borrara la base de datos)
sudo docker rm -f mi-mysql

# Crear y levantar el nuevo contenedor de MySQL
sudo docker run --name mi-mysql -e MYSQL_ROOT_PASSWORD=123456 -e MYSQL_DATABASE=finanbot_db -p 3306:3306 -d mysql:latest
```
*(Nota: Si la terminal se lo solicita, introduzca la contraseña de la máquina virtual: `12345`)*

2. Importación del Esquema Inicial sin Interfaz Gráfica
Inyecte las tablas del proyecto directamente al contenedor ejecutando este comando desde la raíz de la carpeta `Finanbot`:

```bash
sudo docker exec -i mi-mysql mysql -u root -p123456 finanbot_db < "Mysql(base de datos)/finanbot_db.sql"
```
## 5. Inicialización del Backend (FastAPI)

Navegue a la carpeta del proyecto e inicie el backend de la siguiente manera:

1. Activar el Entorno Virtual y Dependencias
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Configurar Variables de Entorno (`.env`)
Cree un archivo `.env` en la carpeta `backend/` con los siguientes parámetros de conexión hacia Docker:

```env
SECRET_KEY="finanbot_super_secret_key_2026_production_ready"
JWT_SECRET_KEY="finanbot_jwt_token_secret_generation_2026"

# URL activa para el contenedor Docker (con contraseña)
DATABASE_URL="mysql+pymysql://root:123456@127.0.0.1:3306/finanbot_db?charset=utf8mb4"

# FinanBot IA 2
GEMINI_API_KEY="Tu_API_KEY_DE_GEMINI"

SMTP_PORT="587"
SMTP_USERNAME="finanbot.sena@gmail.com"
SMTP_APP_PASSWORD="contraseña de aplicacion( se ve en la cuenta finanbot)"
SMTP_FROM="finanbot.sena@gmail.com"

GOOGLE_CLIENT_ID="315416890012-ffvd56diopltc438ev5e8bgrqd2q931m.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET=GOCSPX-KGKeGYtQTEHJrPACG90VSPDN85w
GOOGLE_CLIENT_ID="315416890012-ffvd56diopltc438ev5e8bgrqd2q931m.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET=GOCSPX-KGKeGYtQTEHJrPACG90VSPDN85w
PASSWORD_RESET_URL="http://192.168.0.10:8000/legacy/pages/login.html"
PUBLIC_BASE_URL=https://finanbot.taila41f89.ts.net
```

3. Ejecutar el Servidor
```bash
fastapi dev app.py
```

## 6. Inicialización del Frontend y Configuración del Túnel Público

Navegue a la carpeta del frontend e inicie la interfaz de usuario junto con el túnel de comunicación:

 1. Instalar Dependencias de Node.js
Asegúrese de estar en otra terminal  y ejecute la instalación de los paquetes requeridos:
```bash
cd frontend
npm install
```

 2. Levantar el Servidor de Desarrollo de Vite
Inicie el servidor web exponiendo la aplicación para que el túnel pueda escuchar el puerto local:
```bash
npm run dev -- --host
```

## 7. Acceso por Escritorio Remoto (mstsc)

Esta sección explica cómo entrar al escritorio gráfico de la máquina virtual de Finanbot desde Windows, como alternativa a SSH en VS Code.

### 7.1 Requisito previo: red interna habilitada

1. Abra **Citrix Secure Access** (ícono del candado en la barra de tareas) e inicie sesión en `access.datasena.com` con las credenciales asignadas.
2. Pulse **Página de inicio** y, en Citrix Gateway, seleccione **Acceso de red** (Citrix Gateway Plug-in). Instale el plug-in si el sistema lo solicita.
3. Verifique en la ventana de estado que aparezca **Dirección de red interna: Habilitada**. Sin este paso, la IP `10.12.19.82` no será alcanzable desde su equipo.

### 7.2 Abrir Conexión a Escritorio remoto

1. Presione `Win + R`, escriba `mstsc` y pulse **Enter**.
2. En el campo **Equipo**, escriba:

```text
10.12.19.82
```

3. Haga clic en **Mostrar opciones** y, en **Nombre de usuario**, escriba:

```text
sofianieto
```

4. Pulse **Conectar**.

### 7.3 Aceptar el certificado

Windows mostrará la advertencia *"No puedes comprobarse la identidad del equipo remoto"*. Es normal: el equipo usa un certificado propio. Compruebe que el nombre en el certificado sea `adso3407184` y pulse **Sí**. Si lo desea, marque *"No volver a preguntarme sobre conexiones a este equipo"*.

### 7.4 Iniciar sesión en la VM

Introduzca la contraseña de la máquina virtual indicada en su documento de credenciales. Se abrirá el escritorio de **Ubuntu Server 24.04 (XFCE)**.

### 7.5 Abrir la terminal

Dentro del escritorio remoto, presione `Ctrl + Alt + T` (o use el menú de aplicaciones > *Terminal*) para ejecutar los comandos de las secciones anteriores.

### 7.6 Cerrar la conexión

1. Cierre la ventana de Escritorio remoto. La sesión y los procesos de la VM siguen activos.
2. Cuando termine de trabajar, pulse **Cerrar sesión** en Citrix Secure Access para que su internet vuelva a la normalidad.

### 7.7 Solución de problemas

| Mensaje o síntoma | Causa probable | Solución |
|---|---|---|
| *No se puede conectar al equipo remoto* | La red interna no está habilitada | Repita el punto 7.1 y elija **Acceso de red** |
| Tiempo de espera agotado | IP incorrecta | Verifique que sea `10.12.19.82` |
| *Credenciales incorrectas* | Usuario o contraseña erróneos | Revise `sofianieto` y la contraseña de la VM |
| Sin internet al usar Citrix | La VPN enruta todo el tráfico por la red del SENA | Cierre sesión en Citrix al terminar |

> Nota: Si Tailscale está instalado en su equipo con la misma cuenta, también puede conectarse a la IP de Tailscale de la VM (`tailscale ip -4` en la VM) sin necesidad de Citrix.


## 8. Visualización de las Bases de Datos de FinanBot (Linux / SSH)

Esta sección explica cómo consultar las bases de datos y tablas del contenedor MySQL ya desplegado.

### 8.1 Verificar que el contenedor esté activo

```bash
sudo docker ps
```

Debe aparecer `mi-mysql` con estado `Up`. Si no aparece, revise todos los contenedores con `sudo docker ps -a` y, si está detenido, inícielo con:

```bash
sudo docker start mi-mysql
```

*(Si la terminal lo solicita, introduzca la contraseña de la máquina virtual.)*

### 8.2 Entrar al cliente de MySQL

```bash
sudo docker exec -it mi-mysql mysql -u root -p123456
```

Al conectarse aparecerá el prompt `mysql>`.

> Nota: Si aparece `ERROR 2002 (HY000): Can't connect to local MySQL server`, el servidor aún está iniciando. Espere unos 30 segundos y repita el comando.

### 8.3 Listar las bases de datos

```sql
SHOW DATABASES;
```

Debe aparecer `finanbot_db` junto con las bases del sistema (`information_schema`, `mysql`, `performance_schema` y `sys`), que no deben modificarse.

### 8.4 Seleccionar la base de datos del proyecto

```sql
USE finanbot_db;
```

### 8.5 Listar las tablas

```sql
SHOW TABLES;
```

Si el resultado es `Empty set`, la importación del esquema no se ejecutó correctamente. Repita el paso de importación de la sección 4.

### 8.6 Ver la estructura de una tabla

```sql
DESCRIBE nombre_tabla;
```

### 8.7 Consultar los registros de una tabla

```sql
SELECT * FROM nombre_tabla LIMIT 10;
```

Reemplace `nombre_tabla` por el nombre real de la tabla obtenido en el paso 5.5.

### 8.8 Salir del cliente de MySQL

```sql
EXIT;
```

### 8.9 Consulta rápida sin entrar al cliente

Para ver las tablas directamente desde la terminal de Linux:

```bash
sudo docker exec -i mi-mysql mysql -u root -p123456 -e "USE finanbot_db; SHOW TABLES;"
```

> Nota: El aviso `Using a password on the command line interface can be insecure` es normal y puede ignorarse.