Despues de que pongas la carpeta del proyecto en documentos sigue estos pasos:

1. abre la carpeta Mysql(base de datos ) deberas tener xampp instalado y workbench
2. abre el archivo finanbot_db.sql y te abrira en workbench copia su contenido
3. luego abre  xampp  y luego workbench  y al entrar en un servidor pega el contenido y lo ejecutas , creando la base de datos 
4. luego abre la carpeta del proyecto  en vs code, abre la terminal  y coloca este codigo :
python -m venv venv
generara una carpeta llamada venv significando  que se creo el entorno virtual de flask
5. luego coloca estos codigos uno por uno dado ENTER:
cd backend
..\venv\Scripts\Activate.ps1
pip install flask
pip install flask-cors python-dotenv
pip install flask-sqlalchemy flask-bcrypt flask-jwt-extended
pip install pymysql
python app.py
6. al hacer todo lo anterior abre  frontend/index.html y pon Go live  (si no tienes isntalado en vs code live server no aparecera)