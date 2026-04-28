# app.py
from flask import Flask
from flask_cors import CORS
from extensions import db, bcrypt, jwt
from datetime import timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/finanbot_db'
app.config['SECRET_KEY'] = 'finanbot_secret_key_2026'
app.config['JWT_SECRET_KEY'] = 'finanbot_jwt_secret_2026'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)
CORS(app)

with app.app_context():
    from models import Usuario, Categoria, Transaccion, MetaAhorro, Simulacion, Chat
    db.create_all()
    print('✅ Base de datos conectada correctamente!')

from routes.auth import auth
from routes.chat_route import chat_bp
from routes.transacciones import transacciones_bp
from routes.simulaciones import simulaciones_bp
from routes.perfil import perfil_bp
from routes.metas import metas_bp
from routes.recomendaciones import recomendaciones_bp
from routes.chat_historial import chat_historial_bp

app.register_blueprint(auth, url_prefix='/api/auth')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(transacciones_bp, url_prefix='/api/transacciones')
app.register_blueprint(simulaciones_bp, url_prefix='/api/simulaciones')
app.register_blueprint(perfil_bp, url_prefix='/api/perfil')
app.register_blueprint(metas_bp, url_prefix='/api/metas')
app.register_blueprint(recomendaciones_bp, url_prefix='/api/recomendaciones')
app.register_blueprint(chat_historial_bp, url_prefix='/api/chat-historial')

@app.route('/')
def index():
    return '🤖 FinanBot API funcionando!'

if __name__ == '__main__':
    app.run(debug=True)