# routes/chat_historial.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Chat, Conversacion

router = APIRouter()


# =========================================================
# ESQUEMAS
# =========================================================

class ConversacionCreate(BaseModel):
    titulo: Optional[str] = 'Nueva conversación'

class TituloUpdate(BaseModel):
    titulo: Optional[str] = None

class MensajeCreate(BaseModel):
    mensaje: str
    respuesta: str


# ============================================
# CONVERSACIONES
# ============================================

@router.get('/conversaciones')
def obtener_conversaciones(
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conversaciones = (db.query(Conversacion).filter_by(usuario_id=uid)
                       .order_by(Conversacion.fecha_actualizacion.desc()).all())

    resultado = []
    for c in conversaciones:
        ultimo_mensaje = (db.query(Chat).filter_by(conversacion_id=c.id)
                           .order_by(Chat.fecha.desc()).first())

        resultado.append({
            'id': c.id,
            'titulo': c.titulo,
            'fecha': c.fecha_actualizacion.strftime('%d/%m/%Y'),
            'ultimo_mensaje': (
                ultimo_mensaje.mensaje[:50] + '...'
                if ultimo_mensaje and len(ultimo_mensaje.mensaje) > 50
                else (ultimo_mensaje.mensaje if ultimo_mensaje else '')
            ),
        })

    return resultado


@router.post('/conversaciones', status_code=201)
def crear_conversacion(
    body: ConversacionCreate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)

    nueva = Conversacion(usuario_id=uid, titulo=body.titulo)

    db.add(nueva)
    db.commit()

    return {'id': nueva.id, 'titulo': nueva.titulo}


@router.delete('/conversaciones/{id}')
def eliminar_conversacion(
    id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv = db.query(Conversacion).filter_by(id=id, usuario_id=uid).first()

    if not conv:
        raise HTTPException(status_code=404, detail='No encontrada')

    db.query(Chat).filter_by(conversacion_id=id).delete()
    db.delete(conv)
    db.commit()

    return {'mensaje': '✅ Conversación eliminada'}


@router.put('/conversaciones/{id}/titulo')
def actualizar_titulo(
    id: int,
    body: TituloUpdate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv = db.query(Conversacion).filter_by(id=id, usuario_id=uid).first()

    if not conv:
        raise HTTPException(status_code=404, detail='No encontrada')

    conv.titulo = body.titulo or conv.titulo
    db.commit()

    return {'mensaje': '✅ Título actualizado'}


# ============================================
# MENSAJES
# ============================================

@router.get('/mensajes/{conv_id}')
def obtener_mensajes(
    conv_id: int,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv = db.query(Conversacion).filter_by(id=conv_id, usuario_id=uid).first()

    if not conv:
        raise HTTPException(status_code=404, detail='No encontrada')

    mensajes = (db.query(Chat).filter_by(conversacion_id=conv_id)
                .order_by(Chat.fecha.asc()).all())

    return [{
        'id': m.id,
        'mensaje': m.mensaje,
        'respuesta': m.respuesta,
        'hora': m.fecha.strftime('%I:%M %p')
    } for m in mensajes]


@router.post('/mensajes/{conv_id}', status_code=201)
def guardar_mensaje(
    conv_id: int,
    body: MensajeCreate,
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    conv = db.query(Conversacion).filter_by(id=conv_id, usuario_id=uid).first()

    if not conv:
        raise HTTPException(status_code=404, detail='Conversación no encontrada')

    nuevo = Chat(
        usuario_id=uid,
        conversacion_id=conv_id,
        mensaje=body.mensaje,
        respuesta=body.respuesta,
        es_invitado=False
    )

    conv.fecha_actualizacion = datetime.utcnow()

    if conv.titulo == 'Nueva conversación':
        titulo = body.mensaje[:40]
        conv.titulo = titulo + '...' if len(body.mensaje) > 40 else titulo

    db.add(nuevo)
    db.commit()

    return {'mensaje': '✅ Guardado!'}