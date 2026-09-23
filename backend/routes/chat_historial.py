# routes/chat_historial.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Chat, nuevo_conversacion_id

router = APIRouter()

TITULO_POR_DEFECTO = 'Nueva conversación'


# =========================================================
# ESQUEMAS
# =========================================================

class ConversacionCreate(BaseModel):
    titulo: Optional[str] = TITULO_POR_DEFECTO

class TituloUpdate(BaseModel):
    titulo: Optional[str] = None

class MensajeCreate(BaseModel):
    mensaje: str
    respuesta: str
    titulo: Optional[str] = None  # opcional: título elegido al crear la conversación


# =========================================================
# HELPERS
# =========================================================

def _validar_conv_id(conv_id: str) -> str:
    try:
        return str(uuid.UUID(conv_id))
    except ValueError:
        raise HTTPException(status_code=400, detail='Id de conversación inválido')


def _mensajes_de(db: Session, conv_id: str, uid: int):
    return db.query(Chat).filter(Chat.conversacion_id == conv_id, Chat.usuario_id == uid)


def _conv_de_otro_usuario(db: Session, conv_id: str, uid: int) -> bool:
    return db.query(Chat.id).filter(Chat.conversacion_id == conv_id, Chat.usuario_id != uid).first() is not None


def _titulo_automatico(mensaje: str) -> str:
    titulo = mensaje[:40]
    return titulo + '...' if len(mensaje) > 40 else titulo


# ============================================
# CONVERSACIONES
# (una conversación = todas las filas de chats con el mismo conversacion_id)
# ============================================

@router.get('/conversaciones')
def obtener_conversaciones(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)

    conversaciones = (
        db.query(
            Chat.conversacion_id,
            func.max(Chat.titulo).label('titulo'),
            func.max(Chat.fecha).label('ultima_fecha'),
        )
        .filter(Chat.usuario_id == uid)
        .group_by(Chat.conversacion_id)
        .order_by(func.max(Chat.fecha).desc())
        .all()
    )

    resultado = []
    for c in conversaciones:
        ultimo = (_mensajes_de(db, c.conversacion_id, uid)
                  .order_by(Chat.fecha.desc(), Chat.id.desc()).first())
        texto = ultimo.mensaje if ultimo else ''

        resultado.append({
            'id': c.conversacion_id,
            'titulo': c.titulo,
            'fecha': c.ultima_fecha.strftime('%d/%m/%Y'),
            'ultimo_mensaje': texto[:50] + '...' if len(texto) > 50 else texto,
        })

    return resultado


@router.post('/conversaciones', status_code=201)
def crear_conversacion(
    body: ConversacionCreate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
):
    # Ya no hay tabla de conversaciones: solo se genera el id.
    # La conversación "existe" desde que se guarda su primer mensaje.
    return {'id': nuevo_conversacion_id(), 'titulo': body.titulo or TITULO_POR_DEFECTO}


@router.delete('/conversaciones/{id}')
def eliminar_conversacion(
    id: str,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv_id = _validar_conv_id(id)

    borrados = _mensajes_de(db, conv_id, uid).delete(synchronize_session=False)
    if not borrados:
        raise HTTPException(status_code=404, detail='No encontrada')

    db.commit()
    return {'mensaje': '✅ Conversación eliminada'}


@router.put('/conversaciones/{id}/titulo')
def actualizar_titulo(
    id: str,
    body: TituloUpdate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv_id = _validar_conv_id(id)

    if not body.titulo:
        return {'mensaje': '✅ Título actualizado'}

    actualizados = (_mensajes_de(db, conv_id, uid)
                    .update({Chat.titulo: body.titulo[:100]}, synchronize_session=False))
    if not actualizados:
        raise HTTPException(status_code=404, detail='No encontrada')

    db.commit()
    return {'mensaje': '✅ Título actualizado'}


# ============================================
# MENSAJES
# ============================================

@router.get('/mensajes/{conv_id}')
def obtener_mensajes(
    conv_id: str,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv_id = _validar_conv_id(conv_id)

    if _conv_de_otro_usuario(db, conv_id, uid):
        raise HTTPException(status_code=404, detail='No encontrada')

    # Una conversación recién creada (sin mensajes) devuelve lista vacía
    mensajes = _mensajes_de(db, conv_id, uid).order_by(Chat.fecha.asc(), Chat.id.asc()).all()

    return [{
        'id': m.id,
        'mensaje': m.mensaje,
        'respuesta': m.respuesta,
        'hora': m.fecha.strftime('%I:%M %p')
    } for m in mensajes]


@router.post('/mensajes/{conv_id}', status_code=201)
def guardar_mensaje(
    conv_id: str,
    body: MensajeCreate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv_id = _validar_conv_id(conv_id)

    if _conv_de_otro_usuario(db, conv_id, uid):
        raise HTTPException(status_code=404, detail='Conversación no encontrada')

    # Título: el que ya tiene la conversación; si es nueva o sigue con el
    # título por defecto, se usa el enviado o se genera del primer mensaje.
    previo = _mensajes_de(db, conv_id, uid).first()
    titulo = previo.titulo if previo else (body.titulo or TITULO_POR_DEFECTO)

    if titulo == TITULO_POR_DEFECTO:
        titulo = _titulo_automatico(body.mensaje)
        if previo:
            _mensajes_de(db, conv_id, uid).update({Chat.titulo: titulo}, synchronize_session=False)

    db.add(Chat(
        usuario_id=uid,
        conversacion_id=conv_id,
        titulo=titulo,
        mensaje=body.mensaje,
        respuesta=body.respuesta,
        es_invitado=False,
    ))
    db.commit()

    return {'mensaje': '✅ Guardado!', 'conversacion_id': conv_id, 'titulo': titulo}
