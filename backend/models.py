# models.py
from datetime import datetime
from extensions import db

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(150), nullable=False, unique=True)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    ingreso_mensual = db.Column(db.Numeric(10, 2), default=0.00)
    meta_ahorro = db.Column(db.Numeric(10, 2), default=0.00)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    transacciones = db.relationship('Transaccion', backref='usuario', lazy=True)
    metas = db.relationship('MetaAhorro', backref='usuario', lazy=True)
    simulaciones = db.relationship('Simulacion', backref='usuario', lazy=True)
    chats = db.relationship('Chat', backref='usuario', lazy=True)
    conversaciones = db.relationship('Conversacion', backref='usuario', lazy=True)

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    tipo = db.Column(db.Enum('gasto', 'ingreso'), nullable=False)
    icono = db.Column(db.String(50))
    transacciones = db.relationship('Transaccion', backref='categoria', lazy=True)

class Transaccion(db.Model):
    __tablename__ = 'transacciones'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    tipo = db.Column(db.Enum('gasto', 'ingreso'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    descripcion = db.Column(db.String(255))
    fecha = db.Column(db.Date, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

class MetaAhorro(db.Model):
    __tablename__ = 'metas_ahorro'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    monto_objetivo = db.Column(db.Numeric(10, 2), nullable=False)
    monto_actual = db.Column(db.Numeric(10, 2), default=0.00)
    fecha_limite = db.Column(db.Date)
    completada = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Simulacion(db.Model):
    __tablename__ = 'simulaciones'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    capital_inicial = db.Column(db.Numeric(12, 2), nullable=False)
    tasa_retorno = db.Column(db.Numeric(5, 2), nullable=False)
    plazo_meses = db.Column(db.Integer, nullable=False)
    resultado_final = db.Column(db.Numeric(14, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Conversacion(db.Model):
    __tablename__ = 'conversaciones'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False, default='Nueva conversación')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)
    mensajes = db.relationship('Chat', backref='conversacion', lazy=True)

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey('conversaciones.id'), nullable=True)
    mensaje = db.Column(db.Text, nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    es_invitado = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)