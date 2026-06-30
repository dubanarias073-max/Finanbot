# models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship

from database import Base


class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), nullable=False, unique=True)
    contrasena_hash = Column(String(255), nullable=False)
    ingreso_mensual = Column(Numeric(10, 2), default=0.00)
    meta_ahorro = Column(Numeric(10, 2), default=0.00)
    pregunta_seguridad = Column(String(255), nullable=True)
    respuesta_seguridad = Column(String(255), nullable=True)
    onboarding_completado = Column(Boolean, default=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    transacciones = relationship('Transaccion', back_populates='usuario')
    metas = relationship('MetaAhorro', back_populates='usuario')
    simulaciones = relationship('Simulacion', back_populates='usuario')
    chats = relationship('Chat', back_populates='usuario')
    conversaciones = relationship('Conversacion', back_populates='usuario')


class Categoria(Base):
    __tablename__ = 'categorias'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    tipo = Column(Enum('gasto', 'ingreso', name='tipo_categoria_enum'), nullable=False)
    icono = Column(String(50))

    transacciones = relationship('Transaccion', back_populates='categoria')


class Transaccion(Base):
    __tablename__ = 'transacciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    tipo = Column(Enum('gasto', 'ingreso', name='tipo_transaccion_enum'), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    descripcion = Column(String(255))
    fecha = Column(Date, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='transacciones')
    categoria = relationship('Categoria', back_populates='transacciones')


class MetaAhorro(Base):
    __tablename__ = 'metas_ahorro'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    nombre = Column(String(100), nullable=False)
    monto_objetivo = Column(Numeric(10, 2), nullable=False)
    monto_actual = Column(Numeric(10, 2), default=0.00)
    fecha_limite = Column(Date)
    completada = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='metas')


class Simulacion(Base):
    __tablename__ = 'simulaciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    capital_inicial = Column(Numeric(12, 2), nullable=False)
    tasa_retorno = Column(Numeric(5, 2), nullable=False)
    plazo_meses = Column(Integer, nullable=False)
    resultado_final = Column(Numeric(14, 2), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='simulaciones')


class Conversacion(Base):
    __tablename__ = 'conversaciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    titulo = Column(String(100), nullable=False, default='Nueva conversación')
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='conversaciones')
    mensajes = relationship('Chat', back_populates='conversacion')


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    conversacion_id = Column(Integer, ForeignKey('conversaciones.id'), nullable=True)
    mensaje = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    es_invitado = Column(Boolean, default=False)
    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='chats')
    conversacion = relationship('Conversacion', back_populates='mensajes')