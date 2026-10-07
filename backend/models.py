# models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text,
    ForeignKey, Enum, UniqueConstraint, func,
)
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
    tiendas = relationship('Tienda', back_populates='usuario')
    metas = relationship('MetaAhorro', back_populates='usuario')
    chats = relationship('Chat', back_populates='usuario')


# =========================================================
# CATEGORÍAS: tabla catálogo `categorias`, unida a
# transacciones.categoria por FOREIGN KEY (categorias.nombre).
# Las constantes de abajo se conservan porque otros módulos
# (finanbot_ia, reportes, rutas) las usan, y sirven para
# sembrar la tabla si está vacía.
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


class Categoria(Base):
    __tablename__ = 'categorias'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False, unique=True)
    tipo = Column(Enum('gasto', 'ingreso', 'meta', name='tipo_categoria_enum'), nullable=False)
    icono = Column(String(10), nullable=False)

    transacciones = relationship('Transaccion', back_populates='categoria_rel')


class CategoriaUsuario(Base):
    """Categorías de cada usuario:
    - personalizada=True  → la creó el usuario (ej. '☕ Café'). Su nombre
      también existe en `categorias` para que la FK de transacciones funcione.
    - personalizada=False → es una categoría por defecto que el usuario
      decidió ocultar o eliminar de sus listas."""
    __tablename__ = 'categorias_usuario'

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, index=True)
    nombre = Column(String(50), ForeignKey('categorias.nombre', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    tipo = Column(Enum('gasto', 'ingreso', name='tipo_categoria_usuario_enum'), nullable=False)
    icono = Column(String(10), nullable=False, default='🏷️')
    personalizada = Column(Boolean, nullable=False, default=True)
    oculta = Column(Boolean, nullable=False, default=False)
    eliminada = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('usuario_id', 'nombre', name='uq_categoria_usuario_nombre'),
    )


def _tipo_de_categoria(nombre: str) -> str:
    if nombre in CATEGORIAS_GASTO:
        return 'gasto'
    if nombre in CATEGORIAS_INGRESO:
        return 'ingreso'
    return 'meta'


def sembrar_categorias(db) -> None:
    """Inserta las categorías que falten (útil si las tablas se crearon con
    create_all y no con el script SQL). Es seguro llamarla en cada arranque."""
    existentes = {n for (n,) in db.query(Categoria.nombre).all()}
    nuevas = [
        Categoria(nombre=n, tipo=_tipo_de_categoria(n), icono=ICONOS_CATEGORIA.get(n, '💸'))
        for n in CATEGORIAS if n not in existentes
    ]
    if nuevas:
        db.add_all(nuevas)
        db.commit()


def normalizar_categoria(nombre, tipo: str) -> str:
    """Devuelve una categoría válida del catálogo (sin importar mayúsculas/tildes
    exactas); si no coincide con ninguna, 'Otros gastos' / 'Otros ingresos'."""
    texto = (nombre or '').strip().lower()
    for cat in CATEGORIAS:
        if cat.lower() == texto:
            return cat
    return 'Otros gastos' if tipo == 'gasto' else 'Otros ingresos'


def icono_categoria(nombre, tipo: str = 'gasto', icono_db: str | None = None) -> str:
    """Icono de una categoría. `icono_db` es el de la tabla `categorias`
    (sirve para las categorías personalizadas)."""
    return ICONOS_CATEGORIA.get(nombre) or icono_db or ('💸' if tipo == 'gasto' else '💰')


# =========================================================
# TIENDAS: lugares donde el usuario hace movimientos.
# La tabla se llena sola por triggers de MySQL cuando una
# transacción trae ubicacion_nombre + latitud + longitud.
# =========================================================

class Tienda(Base):
    __tablename__ = 'tiendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    nombre = Column(String(255), nullable=False)
    latitud = Column(Numeric(10, 7), nullable=False)
    longitud = Column(Numeric(10, 7), nullable=False)
    fecha_creacion = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('usuario_id', 'nombre', name='uq_tienda_usuario_nombre'),
    )

    usuario = relationship('Usuario', back_populates='tiendas')
    transacciones = relationship('Transaccion', back_populates='tienda')


class Transaccion(Base):
    __tablename__ = 'transacciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    # Unida a categorias.nombre (FK); sigue siendo el texto de siempre
    categoria = Column(
        String(50),
        ForeignKey('categorias.nombre', onupdate='CASCADE', ondelete='RESTRICT'),
        nullable=False,
    )
    tipo = Column(Enum('gasto', 'ingreso', name='tipo_transaccion_enum'), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    descripcion = Column(String(255))
    fecha = Column(Date, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    # Ubicación donde se hizo el gasto/ingreso (opcional).
    # DECIMAL(10,7) da precisión de ~1 cm, suficiente para un mapa.
    ubicacion_nombre = Column(String(255), nullable=True)
    latitud = Column(Numeric(10, 7), nullable=True)
    longitud = Column(Numeric(10, 7), nullable=True)
    # Lo asigna el trigger de MySQL a partir de ubicacion_nombre/latitud/longitud;
    # el backend no necesita escribirlo.
    tienda_id = Column(Integer, ForeignKey('tiendas.id', ondelete='SET NULL'), nullable=True)

    usuario = relationship('Usuario', back_populates='transacciones')
    categoria_rel = relationship('Categoria', back_populates='transacciones')
    tienda = relationship('Tienda', back_populates='transacciones')

    @property
    def icono(self):
        if self.categoria in ICONOS_CATEGORIA:
            return ICONOS_CATEGORIA[self.categoria]
        # categoría personalizada: el icono está en la tabla `categorias`
        return icono_categoria(self.categoria, self.tipo,
                               self.categoria_rel.icono if self.categoria_rel else None)


def eliminar_tiendas_sin_transacciones(db, tienda_ids) -> None:
    """Elimina tiendas afectadas por un borrado solo si ya no tienen movimientos."""
    ids = {tienda_id for tienda_id in tienda_ids if tienda_id is not None}
    if not ids:
        return

    usadas = {
        tienda_id
        for (tienda_id,) in (
            db.query(Transaccion.tienda_id)
            .filter(Transaccion.tienda_id.in_(ids))
            .all()
        )
    }
    huerfanas = ids - usadas
    if huerfanas:
        db.query(Tienda).filter(Tienda.id.in_(huerfanas)).delete(synchronize_session=False)


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