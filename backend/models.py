# models.py
import uuid
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
    # Perfil elegido en el onboarding (NULL hasta completarlo)
    rol = Column(Enum('estudiante', 'empleado', 'independiente', 'emprendedor', name='rol_usuario_enum'), nullable=True)
    ingreso_mensual = Column(Numeric(10, 2), default=0.00)
    meta_ahorro = Column(Numeric(10, 2), default=0.00)
    fecha_salario = Column(Date, nullable=True)
    pregunta_seguridad = Column(String(255), nullable=True)
    respuesta_seguridad = Column(String(255), nullable=True)
    onboarding_completado = Column(Boolean, default=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    transacciones = relationship('Transaccion', back_populates='usuario')
    metas = relationship('MetaAhorro', back_populates='usuario')
    chats = relationship('Chat', back_populates='usuario')


# =========================================================
# CATEGORÍAS (ya no hay tabla: son valores fijos del ENUM
# transacciones.categoria, igual que usuarios.rol)
# =========================================================

CATEGORIAS_GASTO = (
    'Alimentación', 'Transporte', 'Arriendo', 'Salud', 'Entretenimiento', 'Educación',
    'Ropa', 'Servicios', 'Mascotas', 'Regalos', 'Viajes', 'Otros gastos',
)
CATEGORIAS_INGRESO = (
    'Salario', 'Freelance', 'Inversión', 'Negocio', 'Regalo', 'Otros ingresos',
)
# Movimientos que crea perfil.html al abonar/retirar de metas
CATEGORIAS_META = (
    'Ahorro automático', 'Aporte manual a meta', 'Ajuste de meta', 'Retiro de ahorro',
)
CATEGORIAS = CATEGORIAS_GASTO + CATEGORIAS_INGRESO + CATEGORIAS_META

ICONOS_CATEGORIA = {
    'Alimentación': '🍔', 'Transporte': '🚌', 'Arriendo': '🏠', 'Salud': '💊',
    'Entretenimiento': '🎬', 'Educación': '📚', 'Ropa': '👗', 'Servicios': '⚡',
    'Mascotas': '🐾', 'Regalos': '🎁', 'Viajes': '✈️', 'Otros gastos': '📦',
    'Salario': '💼', 'Freelance': '🧑‍💻', 'Inversión': '📈', 'Negocio': '🏪',
    'Regalo': '🎁', 'Otros ingresos': '💵',
    'Ahorro automático': '🎯', 'Aporte manual a meta': '🎯',
    'Ajuste de meta': '🎯', 'Retiro de ahorro': '↩️',
}


def normalizar_categoria(nombre, tipo: str) -> str:
    """Devuelve una categoría válida del ENUM (sin importar mayúsculas/tildes
    exactas); si no coincide con ninguna, 'Otros gastos' / 'Otros ingresos'."""
    texto = (nombre or '').strip().lower()
    for cat in CATEGORIAS:
        if cat.lower() == texto:
            return cat
    return 'Otros gastos' if tipo == 'gasto' else 'Otros ingresos'


def icono_categoria(nombre, tipo: str = 'gasto') -> str:
    return ICONOS_CATEGORIA.get(nombre, '💸' if tipo == 'gasto' else '💰')


class Transaccion(Base):
    __tablename__ = 'transacciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    categoria = Column(Enum(*CATEGORIAS, name='categoria_transaccion_enum'), nullable=False)
    tipo = Column(Enum('gasto', 'ingreso', name='tipo_transaccion_enum'), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    descripcion = Column(String(255))
    fecha = Column(Date, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='transacciones')

    @property
    def icono(self):
        return icono_categoria(self.categoria, self.tipo)


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
    # Modo de ahorro: 'manual' (el usuario abona cuando quiera) o
    # 'automatico' (FinanBot descuenta monto_automatico del sueldo cada
    # mes, el día dia_automatico, y lo suma solo a esta meta).
    modo = Column(Enum('manual', 'automatico', name='modo_meta_enum'), nullable=False, default='manual')
    monto_automatico = Column(Numeric(10, 2), nullable=True)
    dia_automatico = Column(Integer, nullable=True)

    usuario = relationship('Usuario', back_populates='metas')


def nuevo_conversacion_id():
    """Genera el id para una conversación nueva."""
    return str(uuid.uuid4())


class Chat(Base):
    """Chats y conversaciones unidos: cada fila es un mensaje y los
    mensajes de una misma conversación comparten conversacion_id y titulo."""
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    conversacion_id = Column(String(36), nullable=False, default=nuevo_conversacion_id, index=True)
    titulo = Column(String(100), nullable=False, default='Nueva conversación')
    mensaje = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    es_invitado = Column(Boolean, default=False)
    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship('Usuario', back_populates='chats')
