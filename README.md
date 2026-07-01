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

```powershell
cd backend
fastapi dev app.py
```

Si prefieres usar Uvicorn directamente:

```powershell
uvicorn app:app --reload
```

## 5. Abrir la interfaz

Abre la carpeta frontend y ejecuta el archivo index.html.

Si tienes Live Server instalado en VS Code, puedes hacer clic en “Go Live” para abrir la interfaz en el navegador.

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
