Despues de que pongas la carpeta del proyecto en documentos sigue estos pasos:

1. abre la carpeta Mysql(base de datos ) deberas tener xampp instalado y workbench
2. abre el archivo finanbot_db.sql y te abrira en workbench copia su contenido
3. luego abre  xampp  y luego workbench  y al entrar en un servidor pega el contenido y lo ejecutas , creando la base de datos 
4. luego abre la carpeta del proyecto , y abre la terminal de git bash y coloca este codigo:
cd backend
python -m venv venv
source venv/Scripts/activate

generara una carpeta llamada venv significando  que se creo el entorno virtual de flask
5. luego coloca estos codigos uno por uno dado ENTER en la terminal de powershell:
cd backend
venv\Scripts\Activate
pip install flask
pip install flask-cors python-dotenv
pip install flask-sqlalchemy flask-bcrypt flask-jwt-extended
pip install pymysql
pip install reportlab --break-system-packages
python app.py
6. al hacer todo lo anterior abre  frontend/index.html y pon Go live  (si no tienes isntalado en vs code live server no aparecera)