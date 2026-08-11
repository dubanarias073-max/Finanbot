# routes/chat_route.py
import re, ast, operator
from datetime import date, datetime
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from database import get_db
from extensions import obtener_usuario_id_opcional
from finanbot_ia import FinanBotIA
from models import Transaccion, MetaAhorro, Usuario, Categoria, Simulacion, Conversacion, Chat


def obtener_o_crear_categoria(db: Session, nombre: str, tipo: str, icono: str | None = None):
    nombre_limpio = (nombre or '').strip()
    if not nombre_limpio:
        nombre_limpio = 'Otros gastos' if tipo == 'gasto' else 'Otros ingresos'

    categoria = db.query(Categoria).filter(Categoria.nombre.ilike(nombre_limpio), Categoria.tipo == tipo).first()
    if categoria:
        return categoria

    categoria = db.query(Categoria).filter(Categoria.nombre.ilike(f'%{nombre_limpio}%'), Categoria.tipo == tipo).first()
    if categoria:
        return categoria

    categoria = Categoria(nombre=nombre_limpio, tipo=tipo, icono=icono or ('💸' if tipo == 'gasto' else '💰'))
    db.add(categoria)
    db.flush()
    return categoria

router = APIRouter()
sesiones   = {}
_contextos = {}

# ══════════════════════════════════════════════════════════════════
#  NORMALIZACIÓN DE TEXTO (sin cambios — es Python puro)
# ══════════════════════════════════════════════════════════════════
_TYPOS = {
    r'\blataza\b': 'la tasa', r'\blatsa\b': 'la tasa', r'\blatasa\b': 'la tasa',
    r'\bel plazo\b': 'el plazo', r'\belplazo\b': 'el plazo', r'\belmonto\b': 'el monto',
    r'\bmesos\b': 'meses', r'\bmese\b': 'meses', r'\bañoss\b': 'años',
    r'\bsimulacion\b': 'simulación', r'\binversion\b': 'inversión',
    r'\btarjeta\b': 'tarjeta', r'\bregistra\b': 'registra', r'\bregistar\b': 'registra',
    r'\bborrar\b': 'borra', r'\bporcierto\b': 'por ciento', r'\bporciento\b': 'por ciento',
    r'\bdescuento\b': 'descuento', r'\biva\b': 'iva',
}

def _normalizar(texto: str) -> str:
    t = texto
    for patron, reemplazo in _TYPOS.items():
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    return t


# ══════════════════════════════════════════════════════════════════
#  TIPOS QUE SE RESPONDEN LOCALMENTE (sin pasar por FinanBotIA)
#  Son las preguntas de ayuda y los "¿cuál de estos?" que necesitan
#  texto exacto ligado a los datos que ya extrajimos aquí.
# ══════════════════════════════════════════════════════════════════
_TIPOS_RESPUESTA_LOCAL = {
    'ayuda_accion', 'pide_categoria', 'pide_nombre_meta',
    'confirmar_editar_gasto', 'confirmar_editar_ingreso', 'confirmar_editar_meta',
}

def _fmt(monto) -> str:
    try:
        return f"${int(monto):,}".replace(',', '.')
    except (TypeError, ValueError):
        return str(monto)

def _texto_ayuda(entidad: str, accion: str) -> str:
    nombre_entidad = {'gasto': 'un gasto', 'ingreso': 'un ingreso', 'meta': 'una meta'}[entidad]

    if accion == 'crear':
        if entidad == 'meta':
            return (
                "Para crear una meta de ahorro dime:\n\n"
                "• 🎯 **Nombre** de la meta (ej. \"viaje\", \"tecnología\")\n"
                "• 💰 **Monto objetivo**\n"
                "• Si la quieres **automática**, dime también el aporte mensual y el día del mes\n\n"
                "Ejemplo: _\"crea una meta para viajar de $2.000.000\"_.\n"
                "Si te falta algún dato, yo te lo pregunto."
            )
        ejemplo = '"gasté $50.000 en comida"' if entidad == 'gasto' else '"recibí $1.200.000 de freelance"'
        cats = ('Alimentación, Transporte, Arriendo, Salud, Entretenimiento, Educación, Ropa, '
                'Servicios, Mascotas, Regalos, Viajes u Otros gastos') if entidad == 'gasto' else \
               'Salario, Freelance, Inversión, Negocio, Regalo u Otros ingresos'
        return (
            f"Para registrar {nombre_entidad} dime:\n\n"
            "• 💰 **Monto** (obligatorio)\n"
            f"• 🏷️ **Categoría** — una de: {cats} (si no la menciono, te la pregunto)\n"
            "• 📝 **Descripción** (opcional, solo si quieres)\n\n"
            f"Ejemplo: _{ejemplo}_"
        )

    if accion == 'editar':
        if entidad == 'meta':
            return (
                "Para editar una meta dime el nombre y el nuevo monto.\n\n"
                "Ejemplo: _\"cambia el monto de mi meta viaje a $500.000\"_.\n"
                "Si solo quieres sumar (sin reemplazar el total), usa \"abona\" en vez de \"cambia\"."
            )
        ejemplo = '"cambia mi gasto de comida a $30.000"' if entidad == 'gasto' else '"cambia mi ingreso de salario a $1.500.000"'
        return (
            f"Para editar {nombre_entidad} dime la categoría y el nuevo monto.\n\n"
            f"Ejemplo: _{ejemplo}_.\n"
            "Si tengo varios que coinciden, te pregunto cuál es antes de cambiarlo."
        )

    # eliminar
    if entidad == 'meta':
        return "Para eliminar una meta dime su nombre.\n\nEjemplo: _\"elimina mi meta de viaje\"_"
    ejemplo = '"elimina mi gasto de comida"' if entidad == 'gasto' else '"elimina mi ingreso de freelance"'
    return (
        f"Para eliminar {nombre_entidad} dime el monto o la categoría.\n\n"
        f"Ejemplo: _{ejemplo}_.\n"
        "Si no encuentro uno exacto, te muestro los últimos para que elijas."
    )

def _texto_respuesta_local(accion: dict) -> str:
    tipo = accion.get('tipo')

    if tipo == 'ayuda_accion':
        return _texto_ayuda(accion['entidad'], accion['accion'])

    if tipo == 'pide_categoria':
        entidad = accion.get('contexto')
        sujeto = 'ese gasto' if entidad == 'gasto' else 'ese ingreso'
        opciones = ('Alimentación, Transporte, Arriendo, Salud, Entretenimiento, Educación, '
                    'Ropa, Servicios, Mascotas, Regalos, Viajes u Otros gastos') if entidad == 'gasto' else \
                   'Salario, Freelance, Inversión, Negocio, Regalo u Otros ingresos'
        return (f"¡Listo, {_fmt(accion.get('monto'))}! ¿En qué categoría va {sujeto}?\n\n"
                f"Puede ser: {opciones}.")

    if tipo == 'pide_nombre_meta':
        return f"¡Perfecto, {_fmt(accion.get('monto'))}! ¿Cómo quieres llamar esta meta?"

    if tipo in ('confirmar_editar_gasto', 'confirmar_editar_ingreso'):
        entidad = 'gasto' if tipo == 'confirmar_editar_gasto' else 'ingreso'
        lista = accion.get('gastos') or accion.get('ingresos') or []
        if not lista:
            return f"No encontré {entidad}s para editar."
        opciones = '\n'.join(f"• {t['categoria']} — {_fmt(t['monto'])}" for t in lista)
        return f"Tengo varios {entidad}s recientes, ¿cuál quieres editar?\n\n{opciones}"

    if tipo == 'confirmar_editar_meta':
        metas = accion.get('metas', [])
        if not metas:
            return "No encontré metas para editar."
        opciones = '\n'.join(f"• {m['nombre']} — {_fmt(m['objetivo'])}" for m in metas)
        return f"Tienes varias metas, ¿cuál quieres editar?\n\n{opciones}"

    return "¿Puedes darme un poco más de información?"


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT
# ══════════════════════════════════════════════════════════════════

@router.post('/mensaje')
def mensaje(
    body: dict = Body(...),
    usuario_id: Optional[str] = Depends(obtener_usuario_id_opcional),
    db: Session = Depends(get_db),
):
    if not body or not body.get('mensaje'):
        return {'error': 'Mensaje vacío'}

    msg_original = body['mensaje'].strip()
    if len(msg_original) > 1000:
        return {'error': 'Mensaje demasiado largo'}

    msg_usuario = _normalizar(msg_original)

    session_key = usuario_id or 'invitado'
    if session_key not in sesiones:
        sesiones[session_key] = FinanBotIA()
    bot = sesiones[session_key]

    ctx = _cargar_contexto(int(usuario_id), db) if usuario_id else None
    uid = int(usuario_id) if usuario_id else None
    accion = None

    if uid and ctx:
        accion = _resolver_contexto(msg_usuario, uid, ctx, session_key, db)

    if accion is None and uid and ctx:
        accion = ejecutar_accion(msg_usuario, uid, ctx, db)

    if uid:
        _actualizar_contexto(session_key, accion, msg_usuario)

    if accion and accion.get('tipo') in _TIPOS_RESPUESTA_LOCAL:
        # Preguntas de ayuda y "¿cuál de estos?" se responden aquí mismo,
        # con el texto exacto ligado a los datos que ya extrajimos —
        # no dependen de FinanBotIA.
        respuesta = _texto_respuesta_local(accion)
        acciones_ui = []
    else:
        respuesta, acciones_ui = bot.responder_con_acciones(msg_usuario, ctx, accion)
        respuesta = _agregar_disclaimers_si_necesario(respuesta, msg_usuario)

    if uid:
        try:
            conv = (db.query(Conversacion).filter_by(usuario_id=uid).order_by(Conversacion.fecha_actualizacion.desc()).first())
            if conv is None:
                conv = Conversacion(usuario_id=uid, titulo=msg_usuario[:40] or 'Nueva conversación')
                db.add(conv)
                db.flush()
            conv.fecha_actualizacion = datetime.utcnow()
            db.add(Chat(usuario_id=uid, conversacion_id=conv.id, mensaje=msg_original, respuesta=respuesta, es_invitado=False))
            db.commit()
        except Exception as e:
            print(f'[FinanBot] Error guardar conversación: {e}')

    return {
        'respuesta': respuesta,
        'acciones': acciones_ui,
        'accion_ejecutada': accion,
        'estado': 'ok',
        'es_ia': True,
    }


def _agregar_disclaimers_si_necesario(respuesta: str, mensaje: str) -> str:
    msg = mensaje.lower()
    if any(x in msg for x in ['inverti', 'cdt', 'criptomoneda', 'bolsa', 'fondo', 'renta variable']):
        if '⚠️' not in respuesta and 'asesor' not in respuesta.lower():
            respuesta += "\n\n_🤖 Recuerda: Soy una IA. Para decisiones de inversión grandes, consulta con un asesor financiero profesional._"
    if any(x in msg for x in ['deuda', 'embargo', 'cobranza']):
        if '⚠️' not in respuesta:
            respuesta += "\n\n_⚠️ Si estás en crisis de deuda, busca asesoría legal o contacta a Asobancaria Colombia._"
    if any(x in msg for x in ['préstamo gota a gota', 'prestamo gota a gota', 'usura']):
        respuesta += "\n\n_🚨 Los préstamos de gota a gota son ILEGALES. Denúncialos a la policía._"
    return respuesta


# ══════════════════════════════════════════════════════════════════
#  CONTEXTO CONVERSACIONAL
# ══════════════════════════════════════════════════════════════════

def _actualizar_contexto(session_key: str, accion, msg: str):
    ctx_actual = _contextos.get(session_key, {})
    if accion is None:
        return
    tipo = accion.get('tipo', '')

    if tipo == 'pide_monto':
        _contextos[session_key] = {
            'esperando': 'monto',
            'accion_pendiente': accion.get('contexto', ''),
            'datos': {
                **ctx_actual.get('datos', {}),
                'id_objetivo': accion.get('id_objetivo'),
                'categoria_objetivo': accion.get('categoria_objetivo'),
            },
        }
    elif tipo == 'pide_categoria':
        _contextos[session_key] = {
            'esperando': 'categoria',
            'accion_pendiente': accion.get('contexto', ''),
            'datos': {'monto': accion.get('monto'), 'descripcion': accion.get('descripcion')},
        }
    elif tipo == 'pide_nombre_meta':
        _contextos[session_key] = {
            'esperando': 'nombre_meta',
            'accion_pendiente': 'meta',
            'datos': {
                'monto': accion.get('monto'), 'modo': accion.get('modo'),
                'monto_automatico': accion.get('monto_automatico'),
                'dia_automatico': accion.get('dia_automatico'),
            },
        }
    elif tipo in ('confirmar_eliminar_gasto', 'confirmar_eliminar_ingreso'):
        entidad = 'gasto' if tipo == 'confirmar_eliminar_gasto' else 'ingreso'
        lista = accion.get('gastos') if entidad == 'gasto' else accion.get('ingresos')
        _contextos[session_key] = {
            'esperando': 'cual_transaccion',
            'accion_pendiente': f'{entidad}_eliminar',
            'datos': {'candidatos': lista or []},
        }
    elif tipo == 'confirmar_eliminar_meta':
        _contextos[session_key] = {
            'esperando': 'cual_meta',
            'accion_pendiente': 'meta_eliminar',
            'datos': {'candidatos': accion.get('metas', [])},
        }
    elif tipo in ('confirmar_editar_gasto', 'confirmar_editar_ingreso'):
        entidad = 'gasto' if tipo == 'confirmar_editar_gasto' else 'ingreso'
        lista = accion.get('gastos') if entidad == 'gasto' else accion.get('ingresos')
        _contextos[session_key] = {
            'esperando': 'cual_transaccion',
            'accion_pendiente': f'{entidad}_editar',
            'datos': {'candidatos': lista or [], 'monto': accion.get('monto')},
        }
    elif tipo == 'confirmar_editar_meta':
        _contextos[session_key] = {
            'esperando': 'cual_meta',
            'accion_pendiente': 'meta_editar',
            'datos': {'candidatos': accion.get('metas', []), 'monto': accion.get('monto')},
        }
    elif tipo == 'simulacion_realizada':
        _contextos[session_key] = {
            'esperando': None, 'ultimo_tipo': 'simulacion',
            'datos': {'monto': accion.get('capital'), 'tasa': accion.get('tasa'), 'plazo': accion.get('plazo')}
        }
    elif tipo == 'meta_creada':
        _contextos[session_key] = {
            'esperando': None, 'ultimo_tipo': 'meta',
            'datos': {'nombre': accion.get('nombre'), 'monto': accion.get('monto')}
        }
    elif tipo in ('gasto_registrado', 'ingreso_registrado'):
        _contextos[session_key] = {
            'esperando': None, 'ultimo_tipo': tipo,
            'datos': {'monto': accion.get('monto'), 'categoria': accion.get('categoria')}
        }
    else:
        _contextos[session_key] = {'esperando': None, 'ultimo_tipo': tipo, 'datos': {}}


def _resolver_contexto(msg: str, uid: int, ctx: dict, session_key: str, db: Session):
    conv = _contextos.get(session_key, {})
    if not conv:
        return None

    esperando        = conv.get('esperando')
    accion_pendiente = conv.get('accion_pendiente', '')
    datos_previos    = conv.get('datos', {})
    ultimo_tipo      = conv.get('ultimo_tipo', '')
    msg_l            = msg.lower().strip()

    if any(p in msg_l for p in ['sí', 'si', 'ok', 'dale', 'claro', 'exacto',
                                  'ese mismo', 'eso', 'correcto', 'listo', 'bueno']):
        if ultimo_tipo == 'simulacion':
            return {'tipo': 'pide_monto', 'contexto': 'simulacion'}
        if ultimo_tipo == 'meta':
            return {'tipo': 'consulta_metas', 'metas': ctx.get('metas', [])}
        return None

    # ── El usuario acaba de decir la CATEGORÍA de un gasto/ingreso que
    # ya tenía monto y descripción listos, esperando solo esto. ───────
    if esperando == 'categoria' and accion_pendiente in ('gasto', 'ingreso'):
        monto = datos_previos.get('monto')
        desc  = datos_previos.get('descripcion')
        cat_texto = re.sub(
            r'^(es|en|la categoria es|la categoría es|ser[ií]a|sería|de)\s+',
            '', msg.strip(), flags=re.IGNORECASE
        ).strip()
        # Preferir siempre una de las categorías reales del selector de la
        # app (GASTO_CATS/ING_CATS) antes que crear una categoría nueva
        # con el texto tal cual lo escribió el usuario.
        cats_reales = GASTO_CATS if accion_pendiente == 'gasto' else ING_CATS
        cat_normalizada = next(
            (nombre for nombre in cats_reales if nombre.lower() == cat_texto.lower()),
            None
        ) or _detectar_categoria(cat_texto, accion_pendiente)
        if cat_normalizada:
            cat_texto = cat_normalizada
        if monto and monto > 0 and cat_texto:
            try:
                icono = '🍔' if accion_pendiente == 'gasto' else '💰'
                c = obtener_o_crear_categoria(db, cat_texto, accion_pendiente, icono)
                t = Transaccion(usuario_id=uid, categoria_id=c.id, tipo=accion_pendiente, monto=monto,
                                 descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                db.add(t); db.commit()
                _contextos[session_key] = {
                    'esperando': None, 'ultimo_tipo': f'{accion_pendiente}_registrado',
                    'datos': {'monto': monto, 'categoria': c.nombre}
                }
                return {'tipo': f'{accion_pendiente}_registrado', 'monto': monto, 'categoria': c.nombre, 'id': t.id}
            except Exception as e:
                print(f'[FinanBot] {accion_pendiente} categoria contexto: {e}')
        return None

    # ── El usuario acaba de decir el NOMBRE de la meta que ya tenía
    # monto (y modo automático, si aplica) listos. ───────────────────
    if esperando == 'nombre_meta' and accion_pendiente == 'meta':
        nombre = msg.strip()[:50]
        monto  = datos_previos.get('monto')
        if nombre and monto and monto > 0:
            try:
                modo       = datos_previos.get('modo') or 'manual'
                monto_auto = datos_previos.get('monto_automatico')
                dia_auto   = datos_previos.get('dia_automatico')
                m = MetaAhorro(usuario_id=uid, nombre=nombre.capitalize(), monto_objetivo=monto, monto_actual=0,
                                modo=modo,
                                monto_automatico=monto_auto if modo == 'automatico' else None,
                                dia_automatico=dia_auto if modo == 'automatico' else None)
                db.add(m); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'meta',
                                            'datos': {'nombre': m.nombre, 'monto': monto}}
                return {'tipo': 'meta_creada', 'nombre': m.nombre, 'monto': monto, 'id': m.id,
                        'modo': modo, 'monto_automatico': monto_auto, 'dia_automatico': dia_auto}
            except Exception as e:
                print(f'[FinanBot] Meta nombre contexto: {e}')
        return None

    # ── El usuario ya eligió CUÁL gasto/ingreso quiere editar/eliminar
    # de la lista que se le mostró. ──────────────────────────────────
    if esperando == 'cual_transaccion' and accion_pendiente in (
        'gasto_eliminar', 'ingreso_eliminar', 'gasto_editar', 'ingreso_editar'
    ):
        entidad, sub = accion_pendiente.split('_')
        candidatos = datos_previos.get('candidatos', [])
        elegido = _buscar_trans(msg_l, candidatos, extraer_monto(msg), tipo_cat=entidad)
        if not elegido:
            pos = _extraer_ordinal(msg_l)
            if pos is not None and pos < len(candidatos):
                elegido = candidatos[pos]
        if not elegido:
            return None
        try:
            t = db.query(Transaccion).get(elegido['id'])
            if not t or t.usuario_id != uid:
                return None
            if sub == 'eliminar':
                db.delete(t); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': f'{entidad}_eliminado', 'datos': {}}
                return {'tipo': f'{entidad}_eliminado', 'monto': elegido['monto'], 'categoria': elegido['categoria']}
            else:
                nuevo_monto = extraer_monto(msg) or datos_previos.get('monto')
                if not (nuevo_monto and nuevo_monto > 0):
                    return None
                anterior = float(t.monto)
                t.monto = nuevo_monto
                db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': f'{entidad}_editado', 'datos': {}}
                return {'tipo': f'{entidad}_editado', 'categoria': elegido['categoria'],
                        'monto': nuevo_monto, 'monto_anterior': anterior, 'id': t.id}
        except Exception as e:
            print(f'[FinanBot] {accion_pendiente} contexto: {e}')
        return None

    # ── El usuario ya eligió CUÁL meta quiere editar/eliminar. ───────
    if esperando == 'cual_meta' and accion_pendiente in ('meta_eliminar', 'meta_editar'):
        candidatos = datos_previos.get('candidatos', [])
        elegida = _buscar_meta(msg_l, candidatos)
        if not elegida:
            pos = _extraer_ordinal(msg_l)
            if pos is not None and pos < len(candidatos):
                elegida = candidatos[pos]
        if not elegida:
            return None
        try:
            m = db.query(MetaAhorro).get(elegida['id'])
            if not m or m.usuario_id != uid:
                return None
            if accion_pendiente == 'meta_eliminar':
                nombre_m = m.nombre
                db.delete(m); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'meta_eliminada', 'datos': {}}
                return {'tipo': 'meta_eliminada', 'nombre': nombre_m}
            else:
                nuevo_monto = extraer_monto(msg) or datos_previos.get('monto')
                if not (nuevo_monto and nuevo_monto > 0):
                    return None
                m.monto_actual = nuevo_monto
                if nuevo_monto >= float(m.monto_objetivo):
                    m.completada = True
                db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'meta', 'datos': {}}
                return {'tipo': 'meta_actualizada', 'nombre': elegida['nombre'], 'nuevo_monto': nuevo_monto}
        except Exception as e:
            print(f'[FinanBot] meta contexto: {e}')
        return None

    # ── Está esperando el MONTO para terminar de editar un gasto/ingreso
    # puntual ya identificado (id_objetivo guardado). ────────────────
    if esperando == 'monto' and accion_pendiente in ('gasto_editar', 'ingreso_editar'):
        entidad = accion_pendiente.split('_')[0]
        nuevo_monto = extraer_monto(msg)
        id_obj = datos_previos.get('id_objetivo')
        if nuevo_monto and nuevo_monto > 0 and id_obj:
            try:
                t = db.query(Transaccion).get(id_obj)
                if t and t.usuario_id == uid:
                    anterior = float(t.monto)
                    t.monto = nuevo_monto
                    db.commit()
                    _contextos[session_key] = {'esperando': None, 'ultimo_tipo': f'{entidad}_editado', 'datos': {}}
                    return {'tipo': f'{entidad}_editado', 'categoria': datos_previos.get('categoria_objetivo', ''),
                            'monto': nuevo_monto, 'monto_anterior': anterior, 'id': t.id}
            except Exception as e:
                print(f'[FinanBot] {entidad} editar contexto: {e}')
        return None

    if esperando == 'monto' and accion_pendiente == 'simulacion':
        datos = dict(datos_previos)
        monto = extraer_monto(msg) or datos.get('monto')
        tasa  = extraer_tasa(msg)  or datos.get('tasa')
        plazo = extraer_plazo(msg) or datos.get('plazo')
        if monto: datos['monto'] = monto
        if tasa:  datos['tasa']  = tasa
        if plazo: datos['plazo'] = plazo

        if datos.get('monto'):
            tasa_f  = datos.get('tasa')  or 8.0
            plazo_f = datos.get('plazo') or 12
            tm      = tasa_f / 100 / 12
            bal     = datos['monto']
            for _ in range(plazo_f):
                bal *= (1 + tm)
            gan = bal - datos['monto']
            try:
                db.add(Simulacion(usuario_id=uid, capital_inicial=datos['monto'],
                                   tasa_retorno=tasa_f, plazo_meses=plazo_f, resultado_final=round(bal)))
                db.commit()
            except Exception as e:
                print(f'[FinanBot] Sim contexto: {e}')

            _contextos[session_key] = {
                'esperando': None, 'ultimo_tipo': 'simulacion',
                'datos': {'monto': datos['monto'], 'tasa': tasa_f, 'plazo': plazo_f}
            }
            return {'tipo': 'simulacion_realizada', 'capital': datos['monto'],
                    'tasa': tasa_f, 'plazo': plazo_f, 'resultado': round(bal), 'ganancia': round(gan)}
        else:
            _contextos[session_key]['datos'] = datos
            return {'tipo': 'pide_monto', 'contexto': 'simulacion'}

    if esperando == 'monto' and accion_pendiente == 'meta':
        montos = extraer_todos_montos(msg)
        monto  = (montos[0] if montos else extraer_monto(msg))
        nombre = extraer_nombre_meta(msg) or datos_previos.get('nombre')
        if monto and monto > 0:
            es_automatica = _t(msg_l, AUTOMATICA_KW)
            dia_auto   = extraer_dia_mes(msg) if es_automatica else None
            monto_auto = montos[1] if (es_automatica and len(montos) > 1) else None
            modo = 'automatico' if (es_automatica and monto_auto and dia_auto) else 'manual'
            if not nombre:
                _contextos[session_key] = {
                    'esperando': 'nombre_meta', 'accion_pendiente': 'meta',
                    'datos': {'monto': monto, 'modo': modo, 'monto_automatico': monto_auto, 'dia_automatico': dia_auto}
                }
                return {'tipo': 'pide_nombre_meta', 'monto': monto}
            try:
                m = MetaAhorro(usuario_id=uid, nombre=nombre or '🎯 Meta de ahorro',
                                monto_objetivo=monto, monto_actual=0,
                                modo=modo,
                                monto_automatico=monto_auto if modo == 'automatico' else None,
                                dia_automatico=dia_auto if modo == 'automatico' else None)
                db.add(m); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'meta',
                                            'datos': {'nombre': m.nombre, 'monto': monto}}
                return {'tipo': 'meta_creada', 'nombre': m.nombre, 'monto': monto, 'id': m.id,
                        'modo': modo, 'monto_automatico': monto_auto, 'dia_automatico': dia_auto}
            except Exception as e:
                print(f'[FinanBot] Meta contexto: {e}')

    if esperando == 'monto' and accion_pendiente == 'gasto':
        monto = extraer_monto(msg)
        if monto and monto > 0:
            desc = extraer_descripcion(msg)
            cat  = _detectar_categoria(msg, 'gasto')
            if not cat:
                _contextos[session_key] = {
                    'esperando': 'categoria', 'accion_pendiente': 'gasto',
                    'datos': {'monto': monto, 'descripcion': desc}
                }
                return {'tipo': 'pide_categoria', 'contexto': 'gasto', 'monto': monto, 'descripcion': desc}
            try:
                c = obtener_o_crear_categoria(db, cat, 'gasto', '🍔')
                t = Transaccion(usuario_id=uid, categoria_id=c.id, tipo='gasto', monto=monto,
                                 descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                db.add(t); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'gasto_registrado', 'datos': {}}
                return {'tipo': 'gasto_registrado', 'monto': monto, 'categoria': c.nombre, 'id': t.id}
            except Exception as e:
                print(f'[FinanBot] Gasto contexto: {e}')

    if esperando == 'monto' and accion_pendiente == 'ingreso':
        monto = extraer_monto(msg)
        if monto and monto > 0:
            desc = extraer_descripcion(msg)
            cat  = _detectar_categoria(msg, 'ingreso')
            if not cat:
                _contextos[session_key] = {
                    'esperando': 'categoria', 'accion_pendiente': 'ingreso',
                    'datos': {'monto': monto, 'descripcion': desc}
                }
                return {'tipo': 'pide_categoria', 'contexto': 'ingreso', 'monto': monto, 'descripcion': desc}
            try:
                c = obtener_o_crear_categoria(db, cat, 'ingreso', '💰')
                t = Transaccion(usuario_id=uid, categoria_id=c.id, tipo='ingreso', monto=monto,
                                 descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                db.add(t); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'ingreso_registrado', 'datos': {}}
                return {'tipo': 'ingreso_registrado', 'monto': monto, 'categoria': c.nombre, 'id': t.id}
            except Exception as e:
                print(f'[FinanBot] Ingreso contexto: {e}')

    if ultimo_tipo in ('simulacion', None) or esperando == 'monto':
        monto = extraer_monto(msg) or datos_previos.get('monto')
        tasa  = extraer_tasa(msg)  or datos_previos.get('tasa')
        plazo = extraer_plazo(msg) or datos_previos.get('plazo')

        if monto and (extraer_tasa(msg) or extraer_plazo(msg)):
            tasa_f  = tasa  or 8.0
            plazo_f = plazo or 12
            tm      = tasa_f / 100 / 12
            bal     = monto
            for _ in range(plazo_f):
                bal *= (1 + tm)
            gan = bal - monto
            try:
                db.add(Simulacion(usuario_id=uid, capital_inicial=monto, tasa_retorno=tasa_f,
                                   plazo_meses=plazo_f, resultado_final=round(bal)))
                db.commit()
            except Exception as e:
                print(f'[FinanBot] Sim ctx2: {e}')

            _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'simulacion',
                                        'datos': {'monto': monto, 'tasa': tasa_f, 'plazo': plazo_f}}
            return {'tipo': 'simulacion_realizada', 'capital': monto, 'tasa': tasa_f,
                    'plazo': plazo_f, 'resultado': round(bal), 'ganancia': round(gan)}

    return None


def _cargar_contexto(uid: int, db: Session):
    try:
        transacciones = db.query(Transaccion).filter_by(usuario_id=uid).all()
        metas         = db.query(MetaAhorro).filter_by(usuario_id=uid).all()
        sims          = (db.query(Simulacion).filter_by(usuario_id=uid)
                         .order_by(Simulacion.fecha.desc()).limit(5).all())
        usuario       = db.query(Usuario).get(uid)

        total_ing = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
        total_gas = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')

        cats = defaultdict(float)
        for t in transacciones:
            if t.tipo == 'gasto':
                cats[t.categoria.nombre if t.categoria else 'Otros'] += float(t.monto)

        cat_mayor = max(cats, key=cats.get) if cats else None

        return {
            'nombre': usuario.nombre if usuario else 'Usuario',
            'correo': usuario.correo if usuario else '',
            'total_ingresos': total_ing, 'total_gastos': total_gas, 'balance': total_ing - total_gas,
            'num_transacciones': len(transacciones),
            'num_gastos':   sum(1 for t in transacciones if t.tipo == 'gasto'),
            'num_ingresos': sum(1 for t in transacciones if t.tipo == 'ingreso'),
            'num_metas': len(metas),
            'categoria_mayor_gasto': cat_mayor,
            'monto_mayor_gasto': cats[cat_mayor] if cat_mayor else 0,
            'gastos_por_categoria': dict(cats),
            'metas': [{
                'id': m.id, 'nombre': m.nombre, 'objetivo': float(m.monto_objetivo),
                'actual': float(m.monto_actual),
                'porcentaje': min(round(float(m.monto_actual)/float(m.monto_objetivo)*100), 100) if m.monto_objetivo > 0 else 0,
                'completada': m.completada,
                'modo': getattr(m, 'modo', 'manual') or 'manual',
                'monto_automatico': float(m.monto_automatico) if getattr(m, 'monto_automatico', None) is not None else None,
                'dia_automatico': getattr(m, 'dia_automatico', None),
            } for m in metas],
            'transacciones_recientes': [{
                'id': t.id, 'tipo': t.tipo, 'monto': float(t.monto),
                'categoria': t.categoria.nombre if t.categoria else 'Otros',
                'descripcion': t.descripcion, 'fecha': str(t.fecha),
            } for t in sorted(transacciones, key=lambda x: x.fecha, reverse=True)[:10]],
            'simulaciones': [{
                'capital': float(s.capital_inicial), 'tasa': float(s.tasa_retorno),
                'plazo': s.plazo_meses, 'resultado': float(s.resultado_final),
            } for s in sims],
            'ingreso_mensual': float(usuario.ingreso_mensual or 0),
            'meta_ahorro_mensual': float(usuario.meta_ahorro or 0),
            'usuario_id': uid, 'usuario_obj': usuario,
        }
    except Exception as e:
        print(f'[FinanBot] Error contexto: {e}')
        return None


# ══════════════════════════════════════════════════════════════════
#  PALABRAS CLAVE  (idénticas + nuevas para editar/abonar/ayuda)
# ══════════════════════════════════════════════════════════════════
CREAR = ['crea','crear','agrega','agregar','añade','añadir','añademe','agregame','hazme','haz',
         'ponme','pon','registra','registrar','registrame','nueva','nuevo','generame','genera','ingresa','ingresame']
ELIMINAR = ['elimina','eliminar','borra','borrar','eliminame','quita','quitar','quitame','suprime',
            'suprimir','remueve','remover','bota','botar','bórralo','bórrala']
ACTUALIZAR = ['actualiza','actualizar','cambia','cambiar','modifica','modificar','edita','editar',
              'cambiame','actualizame','modificame','pon que','ahora es','ahora son','ya es','ya son',
              'corrige','corregir','cambia a','cambiar a','ponme de','llámame','llamame',
              'mi nombre es','mi correo es']
# Palabras que indican SOLO SUMAR a una meta (nunca reemplazan el total).
# Antes estaban mezcladas con ACTUALIZAR — se separan porque "editar el
# monto" (reemplaza, puede bajar) y "abonar/añadir" (solo suma) son
# acciones distintas desde que perfil.html las diferencia.
ABONAR_KW = ['añade','añadir','agrega','agregar','suma','sumar','abona','abonar']
# Frases que indican que en realidad se está pidiendo CREAR una meta
# nueva, aunque el mensaje use alguna palabra de ABONAR_KW (ej. "agrega
# una meta de $500.000" no es un abono, es una meta nueva).
META_NUEVA_KW = ['una meta', 'la meta', 'meta nueva', 'nueva meta', 'crea', 'crear']
# Indica que la meta que se está creando debe quedar en modo automático.
AUTOMATICA_KW = ['automática', 'automatica', 'automático', 'automatico']
CONSULTAR = ['cuantos','cuántos','cuanto','cuánto','revisa','revisar','revisame','muestra','mostrar',
             'muestrame','dime','cual','cuál','ver','verifica','verifique','hay','tengo','lista','listar',
             'detalle','detalles','muéstrame']
META_KW      = ['meta','metas','objetivo','objetivos']
GASTO_KW     = ['gasto','gastos','gaste','gasté','compré','compre','pagué','pague','egreso','egresé']
INGRESO_KW   = ['ingreso','ingresos','salario','sueldo','cobré','cobre','gané','gane','recibí','recibi','quincena']
SIMULADOR_KW = ['simula','simulacion','simulación','simulador','simular']
PERFIL_KW    = ['nombre','correo','email','mi nombre','mi correo','llámame','llamame','salario mensual',
                'ingreso mensual','meta mensual','meta_ahorro']
REPORTE_KW   = ['reporte','informe','exportar','descargar reporte','descargar informe','hazme un reporte',
                'genera un reporte','quiero el reporte','pdf','excel']
CALCULO_KW   = ['suma','resta','multiplica','divide','calcula','cuanto es','cuánto es','cuanto son',
                'cuánto son','cuanto vale','cuánto vale']
DESCUENTO_KW = ['descuento','rebaja','oferta','promocion','promoción','rebajado','con descuento','dto']
IVA_KW       = ['iva','con iva','más iva','mas iva','incluido iva','sin iva','impuesto']
REPARTO_KW   = ['dividir entre','dividido entre','repartir','repartimos','cuanto le toca','cuánto le toca',
                'cuanto paga cada','cuánto paga cada']
AUMENTO_KW   = ['aumento','incremento','subio','subió','aumenta','incrementa']
PORCENTAJE_KW= ['que porcentaje','qué porcentaje','cuanto representa','cuánto representa','porcentaje de']
INTERES_KW   = ['interes','interés','cuanto gano','cuánto gano','cuanto genera','cuánto genera','rendimiento']
SALDO_KW     = ['cuanto me queda','cuánto me queda','me queda','que sobra','qué sobra','cuanto sobra','cuánto sobra']
BIENVENIDA_KW= ['hola','buenos dias','buenos días','buenas tardes','buenas noches','buenas','hey','saludos',
                'que puedes hacer','qué puedes hacer','ayuda','como me ayudas','cómo me ayudas','que haces',
                'qué haces','inicio','comenzar','empezar','para que sirves','para qué sirves']
BALANCE_KW   = ['balance','resumen','estado financiero','como estoy','cómo estoy','cuanto tengo','cuánto tengo',
                'mis finanzas','como van mis','cómo van mis']

# Verbos en primera persona ("cómo elimino...", "cómo edito...") usados
# SOLO para detectar preguntas de ayuda — no se mezclan con CREAR/
# ACTUALIZAR/ELIMINAR porque esas listas están afinadas para órdenes
# directas ("elimina", "edita"), no para preguntas.
AYUDA_CREAR_KW    = ['creo', 'crear', 'registro', 'registrar', 'agrego', 'agregar',
                      'añado', 'añadir', 'pongo', 'hago']
AYUDA_EDITAR_KW   = ['edito', 'editar', 'cambio', 'cambiar', 'modifico', 'modificar',
                      'actualizo', 'actualizar']
AYUDA_ELIMINAR_KW = ['elimino', 'eliminar', 'borro', 'borrar', 'quito', 'quitar',
                      'remuevo', 'remover']


def _t(msg: str, lista: list) -> bool:
    return any(p in msg for p in lista)

def _crear_implicito(msg: str) -> bool:
    if _t(msg, CREAR):
        return True
    return bool(re.search(r'(gast[eé]|compr[eé]|pagu[eé]|cobr[eé]|gan[eé]|recib[ií])\b', msg))

def _detectar_ayuda(msg: str) -> dict | None:
    """Detecta preguntas tipo '¿cómo creo/edito/elimino un gasto/ingreso/
    meta?' para responder con una explicación en vez de intentar
    ejecutar la acción. Las preguntas genéricas ('¿qué puedes hacer?')
    ya las cubre BIENVENIDA_KW."""
    if not msg.startswith(('como', 'cómo', 'de que forma', 'de qué forma', 'de que manera', 'de qué manera')):
        return None
    if not _t(msg, META_KW + GASTO_KW + INGRESO_KW):
        return None

    entidad = 'meta' if _t(msg, META_KW) else ('gasto' if _t(msg, GASTO_KW) else 'ingreso')

    if _t(msg, AYUDA_ELIMINAR_KW):
        accion = 'eliminar'
    elif _t(msg, AYUDA_EDITAR_KW):
        accion = 'editar'
    elif _t(msg, AYUDA_CREAR_KW):
        accion = 'crear'
    else:
        return None

    return {'entidad': entidad, 'accion': accion}

_ORDINALES = {
    'primero': 0, 'primera': 0, 'uno': 0, '1': 0,
    'segundo': 1, 'segunda': 1, 'dos': 1, '2': 1,
    'tercero': 2, 'tercera': 2, 'tres': 2, '3': 2,
    'cuarto': 3, 'cuarta': 3, 'cuatro': 3, '4': 3,
    'quinto': 4, 'quinta': 4, 'cinco': 4, '5': 4,
}

def _extraer_ordinal(msg: str) -> int | None:
    for palabra, pos in _ORDINALES.items():
        if re.search(rf'\b{palabra}\b', msg):
            return pos
    return None


# ══════════════════════════════════════════════════════════════════
#  ORQUESTADOR
# ══════════════════════════════════════════════════════════════════

def ejecutar_accion(mensaje: str, uid: int, ctx: dict, db: Session):
    msg = mensaje.lower().strip()

    ayuda = _detectar_ayuda(msg)
    if ayuda:
        return {'tipo': 'ayuda_accion', **ayuda}

    if _t(msg, BIENVENIDA_KW):
        return {'tipo': 'bienvenida', 'nombre': ctx.get('nombre', 'Usuario'),
                'resumen': {'balance': ctx.get('balance', 0), 'total_ingresos': ctx.get('total_ingresos', 0),
                            'total_gastos': ctx.get('total_gastos', 0), 'num_metas': ctx.get('num_metas', 0),
                            'num_transacciones': ctx.get('num_transacciones', 0)}}

    if _t(msg, REPORTE_KW):
        tipo_rep = 'excel' if any(p in msg for p in ['excel', 'xlsx']) else 'pdf'
        return {'tipo': 'reporte', 'formato': tipo_rep}

    res = _resolver_financiero(mensaje, msg)
    if res:
        return res

    if _t(msg, CALCULO_KW) or re.search(r'\d+\s*[\+\-\*\/x]\s*\d+', msg):
        r = calcular_operacion(mensaje)
        if r is not None:
            return {'tipo': 'calculo', 'resultado': r, 'operacion': mensaje}

    if _t(msg, BALANCE_KW):
        return {'tipo': 'consulta_resumen', 'balance': ctx.get('balance', 0),
                'total_ingresos': ctx.get('total_ingresos', 0), 'total_gastos': ctx.get('total_gastos', 0),
                'num_metas': ctx.get('num_metas', 0), 'num_transacciones': ctx.get('num_transacciones', 0),
                'gastos_por_categoria': ctx.get('gastos_por_categoria', {}),
                'categoria_mayor_gasto': ctx.get('categoria_mayor_gasto')}

    if _t(msg, SIMULADOR_KW):
        monto = extraer_monto(mensaje)
        tasa  = extraer_tasa(mensaje)
        plazo = extraer_plazo(mensaje)
        if monto and monto > 0:
            tasa  = tasa  or 8.0
            plazo = plazo or 12
            tm    = tasa / 100 / 12
            bal   = monto
            for _ in range(plazo):
                bal *= (1 + tm)
            gan = bal - monto
            try:
                db.add(Simulacion(usuario_id=uid, capital_inicial=monto, tasa_retorno=tasa,
                                   plazo_meses=plazo, resultado_final=round(bal)))
                db.commit()
            except Exception as e:
                print(f'[FinanBot] Sim: {e}')
            return {'tipo': 'simulacion_realizada', 'capital': monto, 'tasa': tasa, 'plazo': plazo,
                    'resultado': round(bal), 'ganancia': round(gan)}
        return {'tipo': 'pide_monto', 'contexto': 'simulacion'}

    if _t(msg, ACTUALIZAR) and _t(msg, PERFIL_KW):
        u = ctx.get('usuario_obj')
        if u:
            nombre = extraer_nombre_usuario(mensaje)
            correo = extraer_email(mensaje)
            monto  = extraer_monto(mensaje)

            if nombre and any(p in msg for p in ['nombre', 'llámame', 'llamame', 'mi nombre']):
                try:
                    u.nombre = nombre; db.commit()
                    return {'tipo': 'perfil_actualizado', 'campo': 'nombre', 'valor': nombre}
                except Exception as e: print(f'[FinanBot] Perfil nombre: {e}')

            if correo and any(p in msg for p in ['correo', 'email']):
                try:
                    u.correo = correo; db.commit()
                    return {'tipo': 'perfil_actualizado', 'campo': 'correo', 'valor': correo}
                except Exception as e: print(f'[FinanBot] Perfil correo: {e}')

            if monto and any(p in msg for p in ['salario', 'sueldo', 'ingreso mensual']):
                try:
                    u.ingreso_mensual = monto; db.commit()
                    return {'tipo': 'salario_actualizado', 'nuevo_salario': monto}
                except Exception as e: print(f'[FinanBot] Salario: {e}')

            if monto and any(p in msg for p in ['meta mensual', 'meta_ahorro', 'meta de ahorro mensual']):
                try:
                    u.meta_ahorro = monto; db.commit()
                    return {'tipo': 'meta_mensual_actualizada', 'nuevo_monto': monto}
                except Exception as e: print(f'[FinanBot] Meta mensual: {e}')

    # ── METAS ────────────────────────────────────────────────────
    if _t(msg, META_KW):
        parece_creacion = _t(msg, META_NUEVA_KW)

        # 1) ABONAR (solo suma) — se revisa ANTES que crear/actualizar,
        # porque "añade"/"agrega" también aparecen en CREAR y había
        # ambigüedad: "añade $50.000 a mi meta de viajes" es un abono,
        # no una meta nueva.
        if _t(msg, ABONAR_KW) and not parece_creacion:
            metas = ctx.get('metas', [])
            if not metas:
                return {'tipo': 'sin_datos', 'contexto': 'metas'}
            monto = extraer_monto(mensaje)
            if monto and monto > 0:
                meta = _buscar_meta(msg, metas) or metas[0]
                try:
                    m = db.query(MetaAhorro).get(meta['id'])
                    if m and m.usuario_id == uid:
                        nuevo_total = float(m.monto_actual) + monto
                        m.monto_actual = nuevo_total
                        if nuevo_total >= float(m.monto_objetivo):
                            m.completada = True
                        db.commit()
                        return {'tipo': 'meta_abonada', 'nombre': meta['nombre'],
                                'monto_abonado': monto, 'nuevo_total': nuevo_total, 'id': m.id}
                except Exception as e:
                    print(f'[FinanBot] Meta abonar: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'meta'}

        # 2) CREAR (manual o automática) — si falta el nombre, se
        # pregunta antes de crear (no se usa el nombre genérico salvo
        # que el usuario, al preguntársele, no dé uno usable).
        if _t(msg, CREAR):
            montos = extraer_todos_montos(mensaje)
            monto  = montos[0] if montos else extraer_monto(mensaje)
            nombre = extraer_nombre_meta(mensaje)
            es_automatica = _t(msg, AUTOMATICA_KW)
            dia_auto   = extraer_dia_mes(mensaje) if es_automatica else None
            # El "aporte mensual" es un segundo monto distinto al objetivo
            # total — ej. "meta automática de $2.000.000 ... $200.000 el
            # día 5". Si el usuario solo dio un monto, no hay suficiente
            # información para el modo automático y se crea manual.
            monto_auto = montos[1] if (es_automatica and len(montos) > 1) else None
            modo = 'automatico' if (es_automatica and monto_auto and dia_auto) else 'manual'

            if monto and monto > 0:
                if not nombre:
                    return {'tipo': 'pide_nombre_meta', 'monto': monto, 'modo': modo,
                            'monto_automatico': monto_auto, 'dia_automatico': dia_auto}
                try:
                    m = MetaAhorro(usuario_id=uid, nombre=nombre or '🎯 Meta de ahorro',
                                    monto_objetivo=monto, monto_actual=0,
                                    modo=modo,
                                    monto_automatico=monto_auto if modo == 'automatico' else None,
                                    dia_automatico=dia_auto if modo == 'automatico' else None)
                    db.add(m); db.commit()
                    return {'tipo': 'meta_creada', 'nombre': m.nombre, 'monto': monto, 'id': m.id,
                            'modo': modo, 'monto_automatico': monto_auto, 'dia_automatico': dia_auto}
                except Exception as e:
                    print(f'[FinanBot] Meta crear: {e}')
                    return {'tipo': 'error', 'mensaje': 'No pude crear la meta.'}
            return {'tipo': 'pide_monto', 'contexto': 'meta'}

        # 3) ELIMINAR
        if _t(msg, ELIMINAR):
            metas = ctx.get('metas', [])
            if not metas:
                return {'tipo': 'sin_datos', 'contexto': 'metas'}
            encontrada = _buscar_meta(msg, metas)
            if not encontrada:
                return {'tipo': 'confirmar_eliminar_meta', 'mensaje': 'No encontré esa meta. ¿Cuál quieres eliminar?', 'metas': metas}
            try:
                m = db.query(MetaAhorro).get(encontrada['id'])
                if m and m.usuario_id == uid:
                    nombre_m = m.nombre
                    db.delete(m); db.commit()
                    return {'tipo': 'meta_eliminada', 'nombre': nombre_m}
            except Exception as e:
                print(f'[FinanBot] Meta eliminar: {e}')

        # 4) ACTUALIZAR (reemplaza el total — puede subir o bajar). Si
        # hay más de una meta y no se identifica cuál, se pregunta en
        # vez de asumir la primera.
        if _t(msg, ACTUALIZAR):
            monto = extraer_monto(mensaje)
            metas = ctx.get('metas', [])
            if monto and metas:
                meta = _buscar_meta(msg, metas)
                if not meta:
                    if len(metas) == 1:
                        meta = metas[0]
                    else:
                        return {'tipo': 'confirmar_editar_meta', 'metas': metas, 'monto': monto}
                try:
                    m = db.query(MetaAhorro).get(meta['id'])
                    if m and m.usuario_id == uid:
                        m.monto_actual = monto
                        if monto >= meta['objetivo']:
                            m.completada = True
                        db.commit()
                        return {'tipo': 'meta_actualizada', 'nombre': meta['nombre'], 'nuevo_monto': monto}
                except Exception as e:
                    print(f'[FinanBot] Meta update: {e}')

        # 5) CONSULTAR
        if _t(msg, CONSULTAR):
            return {'tipo': 'consulta_metas', 'metas': ctx.get('metas', [])}

    # ── GASTOS ───────────────────────────────────────────────────
    if _t(msg, GASTO_KW):
        # Editar se revisa ANTES de crear: "pon" (crear) y "ponme de"
        # (editar) se pisaban entre sí; ahora "cambia/edita/actualiza"
        # siempre gana si aparece. Si hay más de un gasto y no se
        # identifica cuál, se pregunta en vez de tomar el primero.
        if _t(msg, ACTUALIZAR):
            gastos = [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'gasto']
            if not gastos:
                return {'tipo': 'sin_datos', 'contexto': 'gastos'}
            nuevo_monto = extraer_monto(mensaje)
            g = _buscar_trans(msg, gastos, None, tipo_cat='gasto')
            if not g:
                if len(gastos) == 1:
                    g = gastos[0]
                else:
                    return {'tipo': 'confirmar_editar_gasto', 'gastos': gastos[:5], 'monto': nuevo_monto}
            if nuevo_monto and nuevo_monto > 0:
                try:
                    t = db.query(Transaccion).get(g['id'])
                    if t and t.usuario_id == uid:
                        anterior = float(t.monto)
                        t.monto = nuevo_monto
                        db.commit()
                        return {'tipo': 'gasto_editado', 'categoria': g['categoria'],
                                'monto': nuevo_monto, 'monto_anterior': anterior, 'id': t.id}
                except Exception as e:
                    print(f'[FinanBot] Gasto editar: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'gasto_editar',
                    'id_objetivo': g['id'], 'categoria_objetivo': g['categoria']}

        if _crear_implicito(msg):
            monto = extraer_monto(mensaje)
            desc  = extraer_descripcion(mensaje)
            if monto and monto > 0:
                cat = _detectar_categoria(mensaje, 'gasto')
                if not cat:
                    return {'tipo': 'pide_categoria', 'contexto': 'gasto', 'monto': monto, 'descripcion': desc}
                try:
                    c = obtener_o_crear_categoria(db, cat, 'gasto', '🍔')
                    t = Transaccion(usuario_id=uid, categoria_id=c.id, tipo='gasto', monto=monto,
                                     descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                    db.add(t); db.commit()
                    return {'tipo': 'gasto_registrado', 'monto': monto, 'categoria': c.nombre, 'id': t.id}
                except Exception as e:
                    print(f'[FinanBot] Gasto crear: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'gasto'}

        if _t(msg, ELIMINAR):
            gastos = [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'gasto']
            if not gastos:
                return {'tipo': 'sin_datos', 'contexto': 'gastos'}
            g = _buscar_trans(msg, gastos, extraer_monto(mensaje), tipo_cat='gasto')
            if not g:
                return {'tipo': 'confirmar_eliminar_gasto', 'mensaje': 'No encontré ese gasto. ¿Elimino el más reciente?', 'gastos': gastos[:5]}
            try:
                t = db.query(Transaccion).get(g['id'])
                if t and t.usuario_id == uid:
                    db.delete(t); db.commit()
                    return {'tipo': 'gasto_eliminado', 'monto': g['monto'], 'categoria': g['categoria']}
            except Exception as e:
                print(f'[FinanBot] Gasto eliminar: {e}')

        if _t(msg, CONSULTAR):
            return {'tipo': 'consulta_gastos', 'num_gastos': ctx.get('num_gastos', 0),
                    'total_gastos': ctx.get('total_gastos', 0),
                    'gastos_por_categoria': ctx.get('gastos_por_categoria', {}),
                    'recientes': [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'gasto'][:5]}

    # ── INGRESOS ─────────────────────────────────────────────────
    if _t(msg, INGRESO_KW):
        if _t(msg, ACTUALIZAR):
            ingresos = [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'ingreso']
            if not ingresos:
                return {'tipo': 'sin_datos', 'contexto': 'ingresos'}
            nuevo_monto = extraer_monto(mensaje)
            i = _buscar_trans(msg, ingresos, None, tipo_cat='ingreso')
            if not i:
                if len(ingresos) == 1:
                    i = ingresos[0]
                else:
                    return {'tipo': 'confirmar_editar_ingreso', 'ingresos': ingresos[:5], 'monto': nuevo_monto}
            if nuevo_monto and nuevo_monto > 0:
                try:
                    t = db.query(Transaccion).get(i['id'])
                    if t and t.usuario_id == uid:
                        anterior = float(t.monto)
                        t.monto = nuevo_monto
                        db.commit()
                        return {'tipo': 'ingreso_editado', 'categoria': i['categoria'],
                                'monto': nuevo_monto, 'monto_anterior': anterior, 'id': t.id}
                except Exception as e:
                    print(f'[FinanBot] Ingreso editar: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'ingreso_editar',
                    'id_objetivo': i['id'], 'categoria_objetivo': i['categoria']}

        if _crear_implicito(msg):
            monto = extraer_monto(mensaje)
            desc  = extraer_descripcion(mensaje)
            if monto and monto > 0:
                cat = _detectar_categoria(mensaje, 'ingreso')
                if not cat:
                    return {'tipo': 'pide_categoria', 'contexto': 'ingreso', 'monto': monto, 'descripcion': desc}
                try:
                    c = obtener_o_crear_categoria(db, cat, 'ingreso', '💰')
                    t = Transaccion(usuario_id=uid, categoria_id=c.id, tipo='ingreso', monto=monto,
                                     descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                    db.add(t); db.commit()
                    return {'tipo': 'ingreso_registrado', 'monto': monto, 'categoria': c.nombre, 'id': t.id}
                except Exception as e:
                    print(f'[FinanBot] Ingreso crear: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'ingreso'}

        if _t(msg, ELIMINAR):
            ingresos = [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'ingreso']
            if not ingresos:
                return {'tipo': 'sin_datos', 'contexto': 'ingresos'}
            i = _buscar_trans(msg, ingresos, extraer_monto(mensaje), tipo_cat='ingreso')
            if not i:
                return {'tipo': 'confirmar_eliminar_ingreso', 'mensaje': 'No encontré ese ingreso. ¿Elimino el más reciente?', 'ingresos': ingresos[:5]}
            try:
                t = db.query(Transaccion).get(i['id'])
                if t and t.usuario_id == uid:
                    db.delete(t); db.commit()
                    return {'tipo': 'ingreso_eliminado', 'monto': i['monto'], 'categoria': i['categoria']}
            except Exception as e:
                print(f'[FinanBot] Ingreso eliminar: {e}')

        if _t(msg, CONSULTAR):
            return {'tipo': 'consulta_ingresos', 'num_ingresos': ctx.get('num_ingresos', 0),
                    'total_ingresos': ctx.get('total_ingresos', 0),
                    'recientes': [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'ingreso'][:5]}

    return None

# ══════════════════════════════════════════════════════════════════
#  CALCULADORA FINANCIERA COTIDIANA
# ══════════════════════════════════════════════════════════════════

def _resolver_financiero(mensaje: str, msg: str) -> dict | None:
    valor = extraer_monto(mensaje)
    pct   = extraer_porcentaje(mensaje)

    if _t(msg, DESCUENTO_KW) and valor and pct is not None:
        desc = round(valor * pct / 100, 2)
        return {'tipo': 'descuento', 'precio_original': valor,
                'porcentaje': pct, 'valor_descuento': desc,
                'precio_final': round(valor - desc, 2)}

    if _t(msg, IVA_KW) and valor:
        quitar = any(p in msg for p in ['sin iva', 'sin el iva', 'quitar iva', 'antes de iva'])
        tasa   = pct or 19.0
        if quitar:
            base = round(valor / (1 + tasa / 100), 2)
            return {'tipo': 'iva_descontado', 'valor_con_iva': valor,
                    'tasa_iva': tasa, 'base_sin_iva': base,
                    'valor_iva': round(valor - base, 2)}
        iva = round(valor * tasa / 100, 2)
        return {'tipo': 'iva_sumado', 'base': valor, 'tasa_iva': tasa,
                'valor_iva': iva, 'total': round(valor + iva, 2)}

    if _t(msg, ['propina', 'tip']) and valor and pct is not None:
        prop = round(valor * pct / 100, 2)
        return {'tipo': 'propina', 'cuenta': valor, 'porcentaje': pct,
                'propina': prop, 'total': round(valor + prop, 2)}

    if _t(msg, AUMENTO_KW) and valor and pct is not None:
        aum = round(valor * pct / 100, 2)
        return {'tipo': 'aumento', 'valor_original': valor, 'porcentaje': pct,
                'valor_aumento': aum, 'valor_nuevo': round(valor + aum, 2)}

    if _t(msg, REPARTO_KW) and valor:
        pers = extraer_personas(mensaje)
        if pers and pers > 1:
            return {'tipo': 'reparto', 'total': valor, 'personas': pers,
                    'por_persona': round(valor / pers, 2)}

    if _t(msg, PORCENTAJE_KW):
        vals = extraer_dos_valores(mensaje)
        if vals:
            parte, total = vals
            if total > 0:
                return {'tipo': 'porcentaje_de', 'parte': parte,
                        'total': total, 'porcentaje': round(parte / total * 100, 2)}

    if _t(msg, INTERES_KW) and valor and pct is not None:
        plazo = extraer_plazo(mensaje) or 12
        if 'compuesto' in msg:
            tasa_mensual = pct / 100 / 12
            valor_final = round(valor * ((1 + tasa_mensual) ** plazo), 2)
            ganancia = round(valor_final - valor, 2)
            return {'tipo': 'interes_compuesto', 'capital': valor, 'tasa_anual': pct,
                    'plazo_meses': plazo, 'valor_final': valor_final,
                    'ganancia': ganancia}
        interes = round(valor * (pct / 100) * (plazo / 12), 2)
        return {'tipo': 'interes_simple', 'capital': valor, 'tasa_anual': pct,
                'plazo_meses': plazo, 'interes_ganado': interes,
                'total': round(valor + interes, 2)}

    if _t(msg, SALDO_KW):
        vals = extraer_dos_valores(mensaje)
        if vals:
            mayor, menor = sorted(vals, reverse=True)
            return {'tipo': 'saldo_restante', 'total': mayor,
                    'gasto': menor, 'restante': round(mayor - menor, 2)}

    return None


# ══════════════════════════════════════════════════════════════════
#  HELPERS DE BÚSQUEDA
# ══════════════════════════════════════════════════════════════════

_RE_EMOJI = re.compile(
    r'[\U00010000-\U0010ffff\u2600-\u27BF\U0001F300-\U0001F9FF]',
    flags=re.UNICODE,
)

def _buscar_meta(msg: str, metas: list) -> dict | None:
    for m in metas:
        limpio = _RE_EMOJI.sub('', m['nombre']).lower().strip()
        if any(p in msg for p in limpio.split() if len(p) > 3):
            return m
    return None

def _buscar_trans(msg: str, lista: list, monto: int | None, tipo_cat: str | None = None) -> dict | None:
    # 1) match exacto por monto (útil para borrar, donde el usuario suele
    # dar el monto original)
    if monto:
        for t in lista:
            if abs(t['monto'] - monto) < 1:
                return t
    # 2) match por categoría DETECTADA a partir de palabras clave del
    # mensaje (ej. "comida" -> Alimentación) — más confiable que buscar
    # el nombre exacto de la categoría dentro del texto, que casi nunca
    # coincide literalmente.
    if tipo_cat:
        cat = extraer_categoria(msg, tipo_cat)
        coincidencias = [t for t in lista if t['categoria'] == cat]
        if coincidencias:
            return coincidencias[0]
    # 3) fallback: nombre literal de la categoría dentro del mensaje
    for t in lista:
        if t['categoria'].lower() in msg:
            return t
    return None


# ══════════════════════════════════════════════════════════════════
#  EXTRACCIÓN
# ══════════════════════════════════════════════════════════════════

def extraer_monto(texto: str) -> int | None:
    n = re.sub(r'(\d)[\.,](\d{3})\b', r'\1\2', texto)
    for patron, mult in [
        (r'\$\s*(\d+(?:\.\d+)?)', None),
        (r'(\d+(?:\.\d+)?)\s*millones?', 1_000_000),
        (r'(\d+(?:\.\d+)?)\s*mil\b', 1_000),
        (r'\b(\d+(?:\.\d+)?)\s*k\b', 1_000),
        (r'\b(\d{5,})\b', 1),
    ]:
        m = re.search(patron, n, re.IGNORECASE)
        if m:
            v = float(m.group(1))
            if mult:
                return int(v * mult)
            t = texto.lower()
            if 'millon' in t and v < 1_000:  return int(v * 1_000_000)
            if 'mil'    in t and v < 10_000: return int(v * 1_000)
            return int(v)
    return None

def extraer_todos_montos(texto: str) -> list:
    """Devuelve TODOS los montos en pesos mencionados en el texto, en el
    orden en que aparecen (a diferencia de extraer_monto, que solo da
    uno). Se usa para metas automáticas, donde el mensaje trae DOS
    montos: el objetivo total y el aporte mensual — ej. 'meta
    automática de $2.000.000 ... $200.000 el día 5' → [2000000, 200000].
    """
    n = re.sub(r'(\d)[\.,](\d{3})\b', r'\1\2', texto)
    montos = []
    for m in re.finditer(r'\$\s*(\d+(?:\.\d+)?)\s*(millones?|mil|k)?', n, re.IGNORECASE):
        v = float(m.group(1))
        suf = (m.group(2) or '').lower()
        if 'millon' in suf:
            v *= 1_000_000
        elif suf in ('mil', 'k'):
            v *= 1_000
        montos.append(int(v))
    if not montos:
        solo = extraer_monto(texto)
        if solo:
            montos = [solo]
    return montos

def extraer_dia_mes(texto: str) -> int | None:
    """Extrae un día del mes (1-31) de frases como 'el día 5', 'día 20
    de cada mes'. Se usa para el aporte automático de una meta."""
    m = re.search(r'd[ií]a\s+(\d{1,2})', texto, re.IGNORECASE)
    if m:
        d = int(m.group(1))
        return d if 1 <= d <= 31 else None
    return None

def extraer_porcentaje(texto: str) -> float | None:
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:%|por\s*ciento)', texto, re.IGNORECASE)
    return float(m.group(1).replace(',', '.')) if m else None

def extraer_tasa(texto: str) -> float | None:
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*%', texto)
    return float(m.group(1).replace(',', '.')) if m else None

def extraer_plazo(texto: str) -> int | None:
    m = re.search(r'(\d+)\s*(mes(?:es)?|año(?:s)?)', texto.lower())
    if m:
        v = int(m.group(1))
        return v * 12 if 'año' in m.group(2) else v
    return None

def extraer_personas(texto: str) -> int | None:
    m = re.search(
        r'(?:entre|para|por)\s+(\d+)\s*(?:personas?|gente|amigos?|partes?)?',
        texto, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return n if 2 <= n <= 500 else None
    m = re.search(r'somos\s+(\d+)', texto, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return n if 2 <= n <= 500 else None
    return None

def extraer_dos_valores(texto: str) -> tuple | None:
    n = re.sub(r'(\d)[\.,](\d{3})\b', r'\1\2', texto)
    nums = re.findall(r'\b(\d+(?:\.\d+)?)\b', n)
    montos = []
    for x in nums:
        v = float(x)
        if v > 10 and v not in montos:
            montos.append(v)
        if len(montos) == 2:
            break
    return tuple(montos) if len(montos) == 2 else None

def extraer_nombre_meta(texto: str) -> str | None:
    patrones = [
        r'(?:para|llamada?|de|sobre)\s+([a-záéíóúüñA-ZÁÉÍÓÚÜÑ][a-záéíóúüñA-ZÁÉÍÓÚÜÑ\s]{2,40}?)(?:\s+de\s+\$|\s+\d|\s*$)',
        r'meta\s+(?:de\s+)?([a-záéíóúüñA-ZÁÉÍÓÚÜÑ][a-záéíóúüñA-ZÁÉÍÓÚÜÑ\s]{2,40}?)(?:\s+de\s+\$|\s+\d|\s*$)',
    ]
    for p in patrones:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            nombre = re.sub(r'\$?\d+[\.,]?\d*\s*(?:pesos|mil|millones)?', '', m.group(1)).strip()
            if len(nombre) > 2:
                return nombre[:50].capitalize()
    return None

def extraer_nombre_usuario(texto: str) -> str | None:
    m = re.search(
        r'(?:ll[aá]mame|mi nombre es|cambia(?:r)? mi nombre a|ponme de nombre|nombre es|nombre a)\s+'
        r'([A-Za-zÁÉÍÓÚÑáéíóúñ\s]{2,40})',
        texto, re.IGNORECASE)
    if m:
        n = m.group(1).strip().rstrip('.').title()
        if len(n) >= 2:
            return n
    return None

def extraer_email(texto: str) -> str | None:
    m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', texto)
    return m.group(0) if m else None

def extraer_descripcion(texto: str) -> str | None:
    m = re.search(
        r'\d[\d.,]*\s*(?:pesos|mil|millones|k)?\s+(?:en|para|por)\s+(.{3,80})',
        texto, re.IGNORECASE)
    if m:
        return m.group(1).strip()[:100]
    m = re.search(r'\b(?:en|para)\s+([a-záéíóúüñA-ZÁÉÍÓÚÜÑ][^$\d]{3,60})', texto, re.IGNORECASE)
    return m.group(1).strip()[:100] if m else None

# Diccionarios de categorías a nivel de módulo (antes vivían dentro de
# extraer_categoria) para poder reutilizarlos desde _detectar_categoria
# sin duplicar las palabras clave. Las categorías (nombres y orden)
# coinciden EXACTO con el selector "Selecciona categoría..." de
# finanzas.html/perfil.html, para que el chat nunca invente una
# categoría distinta a las que ya existen en el desplegable.
GASTO_CATS = {
    'Alimentación':  ['comida','aliment','almuerzo','desayuno','cena','restaurante',
                      'mercado','supermercado','frutas','snack','café','cafe','tinto','empanada'],
    'Transporte':    ['bus','taxi','uber','gasolina','transporte','metro','transmilenio',
                      'pasaje','moto','carro','sitp','peaje'],
    'Arriendo':      ['arriendo','arrendo','alquiler','canon','renta del apartamento',
                      'renta de la casa','arriendo del apto'],
    'Salud':         ['médico','medico','farmacia','medicina','salud','doctor',
                      'clinica','hospital','pastilla','examen','eps','odontólogo'],
    'Entretenimiento': ['cine','netflix','spotify','juego','salida','fiesta','bar',
                        'concierto','streaming','disney','prime'],
    'Educación':     ['curso','libro','educacion','estudio','universidad','colegio',
                      'clase','capacitacion','sena','matricula'],
    'Ropa':          ['ropa','zapatos','vestido','camisa','pantalon','tenis',
                      'zapatillas','jean','chaqueta'],
    'Servicios':     ['luz','agua','gas','internet','telefono','teléfono','wifi',
                      'celular','epm','codensa','claro','tigo','movistar'],
    'Mascotas':      ['mascota','mascotas','perro','gato','alimento para mascota','veterinario'],
    'Regalos':       ['regalo','regalos','cumpleaños','aniversario','navidad'],
    'Viajes':        ['viaje','viajes','hotel','pasaje aéreo','pasaje aereo','vuelo','tour'],
    'Otros gastos':  [],
}
ING_CATS = {
    'Salario':       ['salario','sueldo','pago','pagaron','quincena','nomina'],
    'Freelance':     ['freelance','trabajo extra','proyecto','cliente','contrato','honorarios'],
    'Inversión':     ['invert','inversion','inversión','cdt','acciones','dividendos',
                      'rendimiento de mi inversion','fondo de inversion'],
    'Negocio':       ['negocio','ventas','venta','emprendimiento','mi negocio','clientes del negocio'],
    'Regalo':        ['me regalaron','regalo','obsequio'],
    'Otros ingresos': [],
}

def _detectar_categoria(texto: str, tipo: str) -> str | None:
    """Igual que extraer_categoria pero devuelve None cuando no hay
    ninguna palabra clave reconocida, en vez de forzar 'Otros gastos' /
    'Otros ingresos'. Se usa para decidir si hay que PREGUNTARLE la
    categoría al usuario en vez de asumirla."""
    cats  = GASTO_CATS if tipo == 'gasto' else ING_CATS
    t     = texto.lower()
    score = defaultdict(int)
    for cat, kws in cats.items():
        for kw in kws:
            if kw in t:
                score[cat] += 1
    return max(score, key=score.get) if score else None

def extraer_categoria(texto: str, tipo: str) -> str:
    return _detectar_categoria(texto, tipo) or ('Otros gastos' if tipo == 'gasto' else 'Otros ingresos')


# ══════════════════════════════════════════════════════════════════
#  CALCULADORA SEGURA (ast, sin eval)
# ══════════════════════════════════════════════════════════════════

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow,  ast.USub: operator.neg}

def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        l, r = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Div) and r == 0:
            raise ZeroDivisionError()
        return _OPS[type(node.op)](l, r)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError()

def calcular_operacion(texto: str) -> float | None:
    e = texto.lower()
    e = re.sub(r'\b(más|mas)\b', '+', e)
    e = re.sub(r'\b(menos)\b',   '-', e)
    e = re.sub(r'\b(por|x)\b',   '*', e)
    e = re.sub(r'\b(dividido|entre)\b', '/', e)
    e = re.sub(r'([\+\-\*\/\(\)])', r' \1 ', e)
    e = re.sub(r'[^\d\+\-\*\/\.\(\)\s]', ' ', e)
    e = re.sub(r'\s+', ' ', e).strip()
    e = re.sub(r'(\d)\s+(\d)', r'\1\2', e)
    try:
        return round(float(_eval(ast.parse(e, mode='eval').body)), 2)
    except Exception:
        pass
    for pat, op in [
        (r'(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)', operator.add),
        (r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',  operator.sub),
        (r'(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)', operator.mul),
        (r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)',  operator.truediv),
    ]:
        m = re.search(pat, e)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            if op is operator.truediv and b == 0: return None
            return round(op(a, b), 2)
    return None