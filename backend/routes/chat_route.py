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
            'datos': ctx_actual.get('datos', {}),
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
        monto  = extraer_monto(msg)
        nombre = extraer_nombre_meta(msg) or datos_previos.get('nombre')
        if monto and monto > 0:
            try:
                m = MetaAhorro(usuario_id=uid, nombre=nombre or '🎯 Meta de ahorro',
                                monto_objetivo=monto, monto_actual=0)
                db.add(m); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'meta',
                                            'datos': {'nombre': m.nombre, 'monto': monto}}
                return {'tipo': 'meta_creada', 'nombre': m.nombre, 'monto': monto, 'id': m.id}
            except Exception as e:
                print(f'[FinanBot] Meta contexto: {e}')

    if esperando == 'monto' and accion_pendiente == 'gasto':
        monto = extraer_monto(msg)
        if monto and monto > 0:
            cat  = extraer_categoria(msg, 'gasto')
            desc = extraer_descripcion(msg)
            try:
                c = (db.query(Categoria).filter(Categoria.nombre.ilike(f'%{cat}%'), Categoria.tipo == 'gasto').first()
                     or db.query(Categoria).filter_by(tipo='gasto').first())
                t = Transaccion(usuario_id=uid, categoria_id=c.id if c else 1, tipo='gasto', monto=monto,
                                 descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                db.add(t); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'gasto_registrado', 'datos': {}}
                return {'tipo': 'gasto_registrado', 'monto': monto, 'categoria': c.nombre if c else 'Otros', 'id': t.id}
            except Exception as e:
                print(f'[FinanBot] Gasto contexto: {e}')

    if esperando == 'monto' and accion_pendiente == 'ingreso':
        monto = extraer_monto(msg)
        if monto and monto > 0:
            cat  = extraer_categoria(msg, 'ingreso')
            desc = extraer_descripcion(msg)
            try:
                c = (db.query(Categoria).filter(Categoria.nombre.ilike(f'%{cat}%'), Categoria.tipo == 'ingreso').first()
                     or db.query(Categoria).filter_by(tipo='ingreso').first())
                t = Transaccion(usuario_id=uid, categoria_id=c.id if c else 1, tipo='ingreso', monto=monto,
                                 descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                db.add(t); db.commit()
                _contextos[session_key] = {'esperando': None, 'ultimo_tipo': 'ingreso_registrado', 'datos': {}}
                return {'tipo': 'ingreso_registrado', 'monto': monto, 'categoria': c.nombre if c else 'Salario', 'id': t.id}
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
#  PALABRAS CLAVE  (idénticas, sin cambios)
# ══════════════════════════════════════════════════════════════════
CREAR = ['crea','crear','agrega','agregar','añade','añadir','añademe','agregame','hazme','haz',
         'ponme','pon','registra','registrar','registrame','nueva','nuevo','generame','genera','ingresa','ingresame']
ELIMINAR = ['elimina','eliminar','borra','borrar','eliminame','quita','quitar','quitame','suprime',
            'suprimir','remueve','remover','bota','botar','bórralo','bórrala']
ACTUALIZAR = ['actualiza','actualizar','cambia','cambiar','modifica','modificar','edita','editar',
              'cambiame','actualizame','modificame','pon que','ahora es','ahora son','ya es','ya son',
              'corrige','corregir','abona','abonar','cambia a','cambiar a','ponme de','llámame','llamame',
              'mi nombre es','mi correo es']
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


def _t(msg: str, lista: list) -> bool:
    return any(p in msg for p in lista)

def _crear_implicito(msg: str) -> bool:
    if _t(msg, CREAR):
        return True
    return bool(re.search(r'(gast[eé]|compr[eé]|pagu[eé]|cobr[eé]|gan[eé]|recib[ií])\b', msg))


# ══════════════════════════════════════════════════════════════════
#  ORQUESTADOR
# ══════════════════════════════════════════════════════════════════

def ejecutar_accion(mensaje: str, uid: int, ctx: dict, db: Session):
    msg = mensaje.lower().strip()

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

    if _t(msg, META_KW):
        if _t(msg, CREAR):
            monto  = extraer_monto(mensaje)
            nombre = extraer_nombre_meta(mensaje)
            if monto and monto > 0:
                try:
                    m = MetaAhorro(usuario_id=uid, nombre=nombre or '🎯 Meta de ahorro',
                                    monto_objetivo=monto, monto_actual=0)
                    db.add(m); db.commit()
                    return {'tipo': 'meta_creada', 'nombre': m.nombre, 'monto': monto, 'id': m.id}
                except Exception as e:
                    print(f'[FinanBot] Meta crear: {e}')
                    return {'tipo': 'error', 'mensaje': 'No pude crear la meta.'}
            return {'tipo': 'pide_monto', 'contexto': 'meta'}

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

        if _t(msg, ACTUALIZAR):
            monto = extraer_monto(mensaje)
            metas = ctx.get('metas', [])
            if monto and metas:
                meta = _buscar_meta(msg, metas) or metas[0]
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

        if _t(msg, CONSULTAR):
            return {'tipo': 'consulta_metas', 'metas': ctx.get('metas', [])}

    if _t(msg, GASTO_KW):
        if _crear_implicito(msg):
            monto = extraer_monto(mensaje)
            cat   = extraer_categoria(mensaje, 'gasto')
            desc  = extraer_descripcion(mensaje)
            if monto and monto > 0:
                try:
                    c = (db.query(Categoria).filter(Categoria.nombre.ilike(f'%{cat}%'), Categoria.tipo == 'gasto').first()
                         or db.query(Categoria).filter_by(tipo='gasto').first())
                    t = Transaccion(usuario_id=uid, categoria_id=c.id if c else 1, tipo='gasto', monto=monto,
                                     descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                    db.add(t); db.commit()
                    return {'tipo': 'gasto_registrado', 'monto': monto, 'categoria': c.nombre if c else 'Otros', 'id': t.id}
                except Exception as e:
                    print(f'[FinanBot] Gasto crear: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'gasto'}

        if _t(msg, ELIMINAR):
            gastos = [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'gasto']
            if not gastos:
                return {'tipo': 'sin_datos', 'contexto': 'gastos'}
            g = _buscar_trans(msg, gastos, extraer_monto(mensaje))
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

    if _t(msg, INGRESO_KW):
        if _crear_implicito(msg):
            monto = extraer_monto(mensaje)
            cat   = extraer_categoria(mensaje, 'ingreso')
            desc  = extraer_descripcion(mensaje)
            if monto and monto > 0:
                try:
                    c = (db.query(Categoria).filter(Categoria.nombre.ilike(f'%{cat}%'), Categoria.tipo == 'ingreso').first()
                         or db.query(Categoria).filter_by(tipo='ingreso').first())
                    t = Transaccion(usuario_id=uid, categoria_id=c.id if c else 1, tipo='ingreso', monto=monto,
                                     descripcion=desc or 'Registrado por FinanBot', fecha=date.today())
                    db.add(t); db.commit()
                    return {'tipo': 'ingreso_registrado', 'monto': monto, 'categoria': c.nombre if c else 'Salario', 'id': t.id}
                except Exception as e:
                    print(f'[FinanBot] Ingreso crear: {e}')
            return {'tipo': 'pide_monto', 'contexto': 'ingreso'}

        if _t(msg, ELIMINAR):
            ingresos = [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'ingreso']
            if not ingresos:
                return {'tipo': 'sin_datos', 'contexto': 'ingresos'}
            i = _buscar_trans(msg, ingresos, extraer_monto(mensaje))
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

def _buscar_trans(msg: str, lista: list, monto: int | None) -> dict | None:
    if monto:
        for t in lista:
            if abs(t['monto'] - monto) < 1:
                return t
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

def extraer_categoria(texto: str, tipo: str) -> str:
    GASTO_CATS = {
        'Alimentación':  ['comida','aliment','almuerzo','desayuno','cena','restaurante',
                          'mercado','supermercado','frutas','snack','café','cafe','tinto','empanada'],
        'Transporte':    ['bus','taxi','uber','gasolina','transporte','metro','transmilenio',
                          'pasaje','moto','carro','sitp','peaje'],
        'Entretenimiento': ['cine','netflix','spotify','juego','salida','fiesta','bar',
                            'concierto','streaming','disney','prime'],
        'Salud':         ['médico','medico','farmacia','medicina','salud','doctor',
                          'clinica','hospital','pastilla','examen','eps','odontólogo'],
        'Educación':     ['curso','libro','educacion','estudio','universidad','colegio',
                          'clase','capacitacion','sena','matricula'],
        'Servicios':     ['luz','agua','gas','internet','telefono','teléfono','wifi',
                          'celular','epm','codensa','claro','tigo','movistar'],
        'Ropa':          ['ropa','zapatos','vestido','camisa','pantalon','tenis',
                          'zapatillas','jean','chaqueta'],
        'Otros gastos':  [],
    }
    ING_CATS = {
        'Salario':       ['salario','sueldo','pago','pagaron','quincena','trabajo','nomina'],
        'Freelance':     ['freelance','trabajo extra','proyecto','cliente','contrato','honorarios'],
        'Otros ingresos': [],
    }
    cats  = GASTO_CATS if tipo == 'gasto' else ING_CATS
    t     = texto.lower()
    score = defaultdict(int)
    for cat, kws in cats.items():
        for kw in kws:
            if kw in t:
                score[cat] += 1
    if score:
        return max(score, key=score.get)
    return 'Otros gastos' if tipo == 'gasto' else 'Otros ingresos'


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