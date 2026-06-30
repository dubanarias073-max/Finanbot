Después de que pongas la carpeta del proyecto en documentos sigue estos pasos:

1. Abre la carpeta MySQL (base de datos). Deberás tener XAMPP instalado y Workbench.
2. Abre el archivo finanbot_db.sql y te abrirá en Workbench, copia su contenido.
3. Luego abre XAMPP y luego Workbench, y al entrar en un servidor pega el contenido y lo ejecutas, creando la base de datos.
4. Luego abre la carpeta del proyecto, y abre la terminal de Git Bash y coloca este código:

cd backend
python -m venv venv
source venv/Scripts/activate

Generará una carpeta llamada venv significando que se creó el entorno virtual de FastAPI.

5. Luego coloca estos códigos uno por uno dando ENTER en la terminal de PowerShell:

cd backend
venv\Scripts\Activate
pip install "fastapi[standard]"
pip install "uvicorn[standard]"
pip install python-dotenv
pip install sqlalchemy pymysql
pip install python-jose[cryptography] passlib python-multipart
pip install "bcrypt==4.0.1"
pip install reportlab --break-system-packages
pip install openpyxl --break-system-packages
fastapi dev app.py
6. Al hacer todo lo anterior abre frontend/index.html y pon Go Live (si no tienes instalado en VS Code Live Server no aparecerá).
