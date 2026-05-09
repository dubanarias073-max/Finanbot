# routes/chat_route.py
import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from finanbot_ia import FinanBotIA
from models import Transaccion, MetaAhorro, Usuario, Categoria, Simulacion
from extensions import db
from collections import defaultdict
from datetime import datetime, date

chat_bp = Blueprint('chat_bp', __name__)
sesiones = {}

@chat_bp.route('/mensaje', methods=['POST'])
def mensaje():
    usuario_id = None
    try:
        verify_jwt_in_request(optional=True)
        from flask_jwt_extended import get_jwt_identity
        usuario_id = get_jwt_identity()
    except:
        pass

    data = request.get_json()
    if not data or not data.get('mensaje'):
        return jsonify({'error': 'Mensaje vacío'}), 400

    mensaje_usuario = data['mensaje'].strip()

    session_key = usuario_id or 'invitado'
    if session_key not in sesiones:
        sesiones[session_key] = FinanBotIA()

    bot = sesiones[session_key]

    contexto_financiero = None
    if usuario_id:
        try:
            transacciones = Transaccion.query.filter_by(usuario_id=int(usuario_id)).all()
            metas = MetaAhorro.query.filter_by(usuario_id=int(usuario_id)).all()
            simulaciones = Simulacion.query.filter_by(usuario_id=int(usuario_id)).order_by(Simulacion.fecha.desc()).limit(5).all()
            usuario = Usuario.query.get(int(usuario_id))

            total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
            total_gastos = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')

            gastos_cat = defaultdict(float)
            for t in transacciones:
                if t.tipo == 'gasto':
                    gastos_cat[t.categoria.nombre if t.categoria else 'Otros'] += float(t.monto)

            cat_mayor = max(gastos_cat, key=gastos_cat.get) if gastos_cat else None

            metas_lista = [{
                'id': m.id,
                'nombre': m.nombre,
                'objetivo': float(m.monto_objetivo),
                'actual': float(m.monto_actual),
                'porcentaje': min(round((float(m.monto_actual)/float(m.monto_objetivo))*100), 100) if m.monto_objetivo > 0 else 0,
                'completada': m.completada
            } for m in metas]

            trans_recientes = sorted(transacciones, key=lambda x: x.fecha, reverse=True)[:10]

            gastos_lista = [t for t in transacciones if t.tipo == 'gasto']
            ingresos_lista = [t for t in transacciones if t.tipo == 'ingreso']

            contexto_financiero = {
                'nombre': usuario.nombre if usuario else 'Usuario',
                'total_ingresos': total_ingresos,
                'total_gastos': total_gastos,
                'balance': total_ingresos - total_gastos,
                'num_transacciones': len(transacciones),
                'num_gastos': len(gastos_lista),
                'num_ingresos': len(ingresos_lista),
                'num_metas': len(metas),
                'categoria_mayor_gasto': cat_mayor,
                'monto_mayor_gasto': gastos_cat[cat_mayor] if cat_mayor else 0,
                'gastos_por_categoria': dict(gastos_cat),
                'metas': metas_lista,
                'transacciones_recientes': [{
                    'id': t.id,
                    'tipo': t.tipo,
                    'monto': float(t.monto),
                    'categoria': t.categoria.nombre if t.categoria else 'Otros',
                    'descripcion': t.descripcion,
                    'fecha': str(t.fecha)
                } for t in trans_recientes],
                'simulaciones': [{
                    'capital': float(s.capital_inicial),
                    'tasa': float(s.tasa_retorno),
                    'plazo': s.plazo_meses,
                    'resultado': float(s.resultado_final)
                } for s in simulaciones],
                'ingreso_mensual': float(usuario.ingreso_mensual or 0),
                'meta_ahorro_mensual': float(usuario.meta_ahorro or 0),
                'usuario_id': int(usuario_id),
                'usuario_obj': usuario
            }
        except Exception as e:
            print(f"Error cargando contexto: {e}")

    accion_ejecutada = None
    if usuario_id and contexto_financiero:
        accion_ejecutada = ejecutar_accion(mensaje_usuario, int(usuario_id), contexto_financiero)

    respuesta, acciones = bot.responder_con_acciones(mensaje_usuario, contexto_financiero, accion_ejecutada)

    return jsonify({
        'respuesta': respuesta,
        'acciones': acciones,
        'accion_ejecutada': accion_ejecutada,
        'estado': 'ok'
    }), 200


# ============================================
# PALABRAS CLAVE GENERALIZADAS
# ============================================
CREAR = ['crea', 'crear', 'cre', 'agrega', 'agregar', 'añade', 'añadir', 'añademe', 'agregame',
         'hazme', 'haz', 'ponme', 'pon', 'registra', 'registrar', 'registrame', 'nueva',
         'nuevo', 'quiero', 'necesito', 'haber', 'hacer', 'dame', 'generame', 'genera']

ELIMINAR = ['elimina', 'eliminar', 'borra', 'borrar', 'borrarne', 'eliminame', 'quita',
            'quitar', 'quitame', 'suprime', 'suprimir', 'remueve', 'remover', 'bota', 'botar']

ACTUALIZAR = ['actualiza', 'actualizar', 'cambia', 'cambiar', 'modifica', 'modificar',
              'edita', 'editar', 'cambiame', 'actualizame', 'modificame', 'pon que',
              'ahora es', 'ahora son', 'ya es', 'ya son', 'corrige', 'corregir']

CONSULTAR = ['cuantos', 'cuántos', 'cuanto', 'cuánto', 'revisa', 'revisar', 'revisame',
             'muestra', 'mostrar', 'muestrame', 'dime', 'cual', 'cuál', 'ver', 'verifique',
             'verifica', 'dame', 'hay', 'tengo', 'lista', 'listar', 'detalle', 'detalles']

META_KW = ['meta', 'metas', 'objetivo', 'objetivos', 'ahorro', 'ahorrar']
GASTO_KW = ['gasto', 'gastos', 'gaste', 'gasté', 'compré', 'compre', 'pagué', 'pague', 'egreso']
INGRESO_KW = ['ingreso', 'ingresos', 'salario', 'sueldo', 'cobré', 'cobre', 'gané', 'gane', 'recibí', 'recibi']
SIMULADOR_KW = ['simula', 'simulacion', 'simulación', 'simulador', 'inversión', 'inversion', 'cdt', 'fondo']
PERFIL_KW = ['perfil', 'nombre', 'correo', 'contraseña', 'salario mensual', 'ingreso mensual', 'meta mensual']
CALCULO_KW = ['suma', 'resta', 'multiplica', 'divide', 'calcula', 'cuanto es', 'cuánto es', 'cuanto son', 'cuánto son']


def tiene_palabra(msg, lista):
    return any(p in msg for p in lista)


def ejecutar_accion(mensaje, usuario_id, ctx):
    msg = mensaje.lower().strip()

    # ============================================
    # CÁLCULOS MATEMÁTICOS
    # ============================================
    if tiene_palabra(msg, CALCULO_KW) or re.search(r'\d+\s*[\+\-\*\/x]\s*\d+', msg):
        resultado = calcular_operacion(mensaje)
        if resultado is not None:
            return {'tipo': 'calculo', 'resultado': resultado, 'operacion': mensaje}

    # ============================================
    # CREAR META
    # ============================================
    if tiene_palabra(msg, CREAR) and tiene_palabra(msg, META_KW):
        monto = extraer_monto(mensaje)
        nombre = extraer_nombre_meta(mensaje)
        if monto and monto > 0:
            try:
                nueva = MetaAhorro(
                    usuario_id=usuario_id,
                    nombre=nombre or '🎯 Meta de ahorro',
                    monto_objetivo=monto,
                    monto_actual=0
                )
                db.session.add(nueva)
                db.session.commit()
                return {'tipo': 'meta_creada', 'nombre': nueva.nombre, 'monto': monto, 'id': nueva.id}
            except Exception as e:
                print(f"Error creando meta: {e}")
                return {'tipo': 'error', 'mensaje': 'No pude crear la meta. Intenta de nuevo.'}
        else:
            return {'tipo': 'pide_monto', 'contexto': 'meta'}

    # ============================================
    # ELIMINAR META
    # ============================================
    if tiene_palabra(msg, ELIMINAR) and tiene_palabra(msg, META_KW):
        metas = ctx.get('metas', [])
        if not metas:
            return {'tipo': 'sin_datos', 'contexto': 'metas'}

        meta_encontrada = None
        for meta in metas:
            palabras_meta = meta['nombre'].lower().replace('🎯', '').replace('✈️', '').replace('🏠', '').strip().split()
            if any(p in msg for p in palabras_meta if len(p) > 3):
                meta_encontrada = meta
                break

        if not meta_encontrada:
            meta_encontrada = metas[0]

        try:
            m = MetaAhorro.query.get(meta_encontrada['id'])
            if m and m.usuario_id == usuario_id:
                nombre = m.nombre
                db.session.delete(m)
                db.session.commit()
                return {'tipo': 'meta_eliminada', 'nombre': nombre}
        except Exception as e:
            print(f"Error eliminando meta: {e}")

    # ============================================
    # ACTUALIZAR META (abonar)
    # ============================================
    if tiene_palabra(msg, ACTUALIZAR) and tiene_palabra(msg, META_KW):
        monto = extraer_monto(mensaje)
        metas = ctx.get('metas', [])
        if monto and metas:
            meta = metas[0]
            for m in metas:
                palabras = m['nombre'].lower().split()
                if any(p in msg for p in palabras if len(p) > 3):
                    meta = m
                    break
            try:
                m_obj = MetaAhorro.query.get(meta['id'])
                if m_obj and m_obj.usuario_id == usuario_id:
                    m_obj.monto_actual = monto
                    if monto >= meta['objetivo']:
                        m_obj.completada = True
                    db.session.commit()
                    return {'tipo': 'meta_actualizada', 'nombre': meta['nombre'], 'nuevo_monto': monto}
            except Exception as e:
                print(f"Error actualizando meta: {e}")

    # ============================================
    # CONSULTAR METAS
    # ============================================
    if tiene_palabra(msg, CONSULTAR) and tiene_palabra(msg, META_KW):
        metas = ctx.get('metas', [])
        return {'tipo': 'consulta_metas', 'metas': metas}

    # ============================================
    # CREAR GASTO
    # ============================================
    if tiene_palabra(msg, CREAR) and tiene_palabra(msg, GASTO_KW):
        monto = extraer_monto(mensaje)
        categoria_nombre = extraer_categoria(mensaje, 'gasto')
        descripcion = extraer_descripcion(mensaje)

        if monto and monto > 0:
            try:
                categoria = Categoria.query.filter(
                    Categoria.nombre.ilike(f'%{categoria_nombre}%'),
                    Categoria.tipo == 'gasto'
                ).first() or Categoria.query.filter_by(tipo='gasto').first()

                nueva = Transaccion(
                    usuario_id=usuario_id,
                    categoria_id=categoria.id if categoria else 1,
                    tipo='gasto',
                    monto=monto,
                    descripcion=descripcion or 'Registrado por FinanBot',
                    fecha=date.today()
                )
                db.session.add(nueva)
                db.session.commit()
                return {'tipo': 'gasto_registrado', 'monto': monto, 'categoria': categoria.nombre if categoria else 'Otros', 'id': nueva.id}
            except Exception as e:
                print(f"Error registrando gasto: {e}")
        else:
            return {'tipo': 'pide_monto', 'contexto': 'gasto'}

    # ============================================
    # ELIMINAR GASTO
    # ============================================
    if tiene_palabra(msg, ELIMINAR) and tiene_palabra(msg, GASTO_KW):
        trans = ctx.get('transacciones_recientes', [])
        gastos = [t for t in trans if t['tipo'] == 'gasto']
        if not gastos:
            return {'tipo': 'sin_datos', 'contexto': 'gastos'}

        gasto = None
        monto = extraer_monto(mensaje)
        if monto:
            for g in gastos:
                if abs(g['monto'] - monto) < 1:
                    gasto = g
                    break

        if not gasto:
            for g in gastos:
                if g['categoria'].lower() in msg:
                    gasto = g
                    break

        if not gasto:
            gasto = gastos[0]

        try:
            t = Transaccion.query.get(gasto['id'])
            if t and t.usuario_id == usuario_id:
                db.session.delete(t)
                db.session.commit()
                return {'tipo': 'gasto_eliminado', 'monto': gasto['monto'], 'categoria': gasto['categoria']}
        except Exception as e:
            print(f"Error eliminando gasto: {e}")

    # ============================================
    # CREAR INGRESO
    # ============================================
    if tiene_palabra(msg, CREAR) and tiene_palabra(msg, INGRESO_KW):
        monto = extraer_monto(mensaje)
        categoria_nombre = extraer_categoria(mensaje, 'ingreso')
        descripcion = extraer_descripcion(mensaje)

        if monto and monto > 0:
            try:
                categoria = Categoria.query.filter(
                    Categoria.nombre.ilike(f'%{categoria_nombre}%'),
                    Categoria.tipo == 'ingreso'
                ).first() or Categoria.query.filter_by(tipo='ingreso').first()

                nueva = Transaccion(
                    usuario_id=usuario_id,
                    categoria_id=categoria.id if categoria else 1,
                    tipo='ingreso',
                    monto=monto,
                    descripcion=descripcion or 'Registrado por FinanBot',
                    fecha=date.today()
                )
                db.session.add(nueva)
                db.session.commit()
                return {'tipo': 'ingreso_registrado', 'monto': monto, 'categoria': categoria.nombre if categoria else 'Salario', 'id': nueva.id}
            except Exception as e:
                print(f"Error registrando ingreso: {e}")
        else:
            return {'tipo': 'pide_monto', 'contexto': 'ingreso'}

    # ============================================
    # ELIMINAR INGRESO
    # ============================================
    if tiene_palabra(msg, ELIMINAR) and tiene_palabra(msg, INGRESO_KW):
        trans = ctx.get('transacciones_recientes', [])
        ingresos = [t for t in trans if t['tipo'] == 'ingreso']
        if not ingresos:
            return {'tipo': 'sin_datos', 'contexto': 'ingresos'}

        ingreso = None
        monto = extraer_monto(mensaje)
        if monto:
            for i in ingresos:
                if abs(i['monto'] - monto) < 1:
                    ingreso = i
                    break

        if not ingreso:
            ingreso = ingresos[0]

        try:
            t = Transaccion.query.get(ingreso['id'])
            if t and t.usuario_id == usuario_id:
                db.session.delete(t)
                db.session.commit()
                return {'tipo': 'ingreso_eliminado', 'monto': ingreso['monto'], 'categoria': ingreso['categoria']}
        except Exception as e:
            print(f"Error eliminando ingreso: {e}")

    # ============================================
    # CONSULTAR GASTOS
    # ============================================
    if tiene_palabra(msg, CONSULTAR) and tiene_palabra(msg, GASTO_KW):
        return {
            'tipo': 'consulta_gastos',
            'num_gastos': ctx.get('num_gastos', 0),
            'total_gastos': ctx.get('total_gastos', 0),
            'gastos_por_categoria': ctx.get('gastos_por_categoria', {}),
            'recientes': [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'gasto'][:5]
        }

    # ============================================
    # CONSULTAR INGRESOS
    # ============================================
    if tiene_palabra(msg, CONSULTAR) and tiene_palabra(msg, INGRESO_KW):
        return {
            'tipo': 'consulta_ingresos',
            'num_ingresos': ctx.get('num_ingresos', 0),
            'total_ingresos': ctx.get('total_ingresos', 0),
            'recientes': [t for t in ctx.get('transacciones_recientes', []) if t['tipo'] == 'ingreso'][:5]
        }

    # ============================================
    # ACTUALIZAR SALARIO / PERFIL
    # ============================================
    if tiene_palabra(msg, ACTUALIZAR) and any(p in msg for p in ['salario', 'sueldo', 'ingreso mensual', 'ingreso_mensual']):
        monto = extraer_monto(mensaje)
        if monto:
            try:
                usuario = ctx.get('usuario_obj')
                if usuario:
                    usuario.ingreso_mensual = monto
                    db.session.commit()
                    return {'tipo': 'salario_actualizado', 'nuevo_salario': monto}
            except Exception as e:
                print(f"Error actualizando salario: {e}")

    # ============================================
    # ACTUALIZAR META AHORRO MENSUAL
    # ============================================
    if tiene_palabra(msg, ACTUALIZAR) and any(p in msg for p in ['meta mensual', 'meta de ahorro mensual', 'meta_ahorro']):
        monto = extraer_monto(mensaje)
        if monto:
            try:
                usuario = ctx.get('usuario_obj')
                if usuario:
                    usuario.meta_ahorro = monto
                    db.session.commit()
                    return {'tipo': 'meta_mensual_actualizada', 'nuevo_monto': monto}
            except Exception as e:
                print(f"Error actualizando meta mensual: {e}")

    # ============================================
    # SIMULADOR
    # ============================================
    if tiene_palabra(msg, CREAR + SIMULADOR_KW) and tiene_palabra(msg, SIMULADOR_KW):
        monto = extraer_monto(mensaje)
        tasa = extraer_tasa(mensaje)
        plazo = extraer_plazo(mensaje)

        if monto:
            if not tasa:
                tasa = 8.0
            if not plazo:
                plazo = 12

            tasa_mensual = tasa / 100 / 12
            balance = monto
            for i in range(plazo):
                balance = balance * (1 + tasa_mensual)

            ganancia = balance - monto

            try:
                sim = Simulacion(
                    usuario_id=usuario_id,
                    capital_inicial=monto,
                    tasa_retorno=tasa,
                    plazo_meses=plazo,
                    resultado_final=round(balance)
                )
                db.session.add(sim)
                db.session.commit()
            except Exception as e:
                print(f"Error guardando simulación: {e}")

            return {
                'tipo': 'simulacion_realizada',
                'capital': monto,
                'tasa': tasa,
                'plazo': plazo,
                'resultado': round(balance),
                'ganancia': round(ganancia)
            }

    # ============================================
    # CONSULTAR BALANCE / RESUMEN
    # ============================================
    if any(p in msg for p in ['balance', 'resumen', 'finanzas', 'estado', 'como estoy', 'cómo estoy', 'cuanto tengo', 'cuánto tengo']):
        return {
            'tipo': 'consulta_resumen',
            'balance': ctx.get('balance', 0),
            'total_ingresos': ctx.get('total_ingresos', 0),
            'total_gastos': ctx.get('total_gastos', 0),
            'num_metas': ctx.get('num_metas', 0),
            'num_transacciones': ctx.get('num_transacciones', 0)
        }

    return None


# ============================================
# FUNCIONES DE EXTRACCIÓN
# ============================================
def extraer_monto(texto):
    texto_limpio = texto.replace(',', '').replace('.', '')
    patrones = [
        r'\$\s*(\d+)',
        r'(\d+)\s*pesos',
        r'(\d+)\s*millones',
        r'(\d+)\s*mil',
        r'de\s+(\d+)',
        r'por\s+(\d+)',
        r'(\d{4,})',
        r'(\d{1,3})\s*k\b',
    ]
    for patron in patrones:
        match = re.search(patron, texto_limpio.lower())
        if match:
            valor = int(match.group(1))
            if 'millones' in texto.lower() and valor < 1000:
                valor *= 1000000
            elif 'mil' in texto.lower() and valor < 10000:
                valor *= 1000
            elif texto.lower().endswith('k') or f'{valor}k' in texto.lower():
                valor *= 1000
            if valor > 0:
                return valor
    return None


def extraer_tasa(texto):
    match = re.search(r'(\d+(?:\.\d+)?)\s*%', texto)
    if match:
        return float(match.group(1))
    return None


def extraer_plazo(texto):
    match = re.search(r'(\d+)\s*(mes|meses|año|años)', texto.lower())
    if match:
        valor = int(match.group(1))
        unidad = match.group(2)
        if 'año' in unidad:
            valor *= 12
        return valor
    return None


def extraer_nombre_meta(texto):
    patrones = [
        r'(?:para|llamada?|de|sobre)\s+([a-záéíóúñA-ZÁÉÍÓÚÑ\s]+?)(?:\s+de\s+\$|\s+por\s+|\s+\d|\s*$)',
        r'meta\s+(?:de\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ\s]+?)(?:\s+de\s+\$|\s+\d|\s*$)',
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            nombre = re.sub(r'\$?\d+[\.,]?\d*\s*(pesos|mil|millones)?', '', nombre).strip()
            if len(nombre) > 2:
                return nombre[:50].capitalize()
    return None


def extraer_descripcion(texto):
    for kw in ['para', 'de', 'por', 'en']:
        idx = texto.lower().find(kw)
        if idx != -1:
            parte = texto[idx+len(kw):].strip()
            parte = re.sub(r'\$?\d+[\.,]?\d*\s*(pesos|mil|millones)?', '', parte).strip()
            if len(parte) > 2:
                return parte[:100]
    return None


def extraer_categoria(texto, tipo):
    categorias_gasto = {
        'Alimentación': ['comida', 'aliment', 'almuerzo', 'desayuno', 'cena', 'restaurante', 'mercado', 'supermercado', 'frutas', 'snack', 'cafe', 'café'],
        'Transporte': ['bus', 'taxi', 'uber', 'gasolina', 'transport', 'metro', 'transmilenio', 'pasaje', 'moto', 'carro'],
        'Entretenimiento': ['cine', 'netflix', 'spotify', 'juego', 'entreteni', 'salida', 'fiesta', 'bar', 'concierto', 'streaming'],
        'Salud': ['médico', 'medico', 'farmacia', 'medicina', 'salud', 'doctor', 'clinica', 'hospital', 'droga', 'pastilla'],
        'Educación': ['curso', 'libro', 'educac', 'estudio', 'universidad', 'colegio', 'clase', 'capacitacion'],
        'Servicios públicos': ['luz', 'agua', 'gas', 'internet', 'servicio', 'telefono', 'teléfono', 'wifi', 'celular'],
        'Ropa': ['ropa', 'zapatos', 'vestido', 'camisa', 'pantalon', 'tenis', 'zapatillas', 'jean'],
        'Otros gastos': ['otro', 'varios', 'misc', 'diverso'],
    }
    categorias_ingreso = {
        'Salario': ['salario', 'sueldo', 'pago', 'pagaron', 'quincena', 'mensual', 'trabajo'],
        'Freelance': ['freelance', 'trabajo extra', 'proyecto', 'cliente', 'contrato'],
        'Otros ingresos': ['bono', 'regalo', 'extra', 'otro', 'venta', 'vendí', 'vendi'],
    }

    cats = categorias_gasto if tipo == 'gasto' else categorias_ingreso
    texto_lower = texto.lower()

    for cat, palabras in cats.items():
        for palabra in palabras:
            if palabra in texto_lower:
                return cat

    return 'Otros gastos' if tipo == 'gasto' else 'Otros ingresos'


def calcular_operacion(texto):
    try:
        expr = re.sub(r'[^\d\+\-\*\/\.\(\)x]', ' ', texto.lower())
        expr = expr.replace('x', '*').strip()
        expr = re.sub(r'\s+', '', expr)
        if re.match(r'^[\d\+\-\*\/\.\(\)]+$', expr):
            resultado = eval(expr)
            return round(resultado, 2)
    except:
        pass

    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:más|mas|\+)\s*(\d+(?:\.\d+)?)', texto.lower())
    if match:
        return round(float(match.group(1)) + float(match.group(2)), 2)

    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:menos|\-)\s*(\d+(?:\.\d+)?)', texto.lower())
    if match:
        return round(float(match.group(1)) - float(match.group(2)), 2)

    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:por|x|\*)\s*(\d+(?:\.\d+)?)', texto.lower())
    if match:
        return round(float(match.group(1)) * float(match.group(2)), 2)

    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:dividido|entre|\/)\s*(\d+(?:\.\d+)?)', texto.lower())
    if match:
        b = float(match.group(2))
        if b != 0:
            return round(float(match.group(1)) / b, 2)

    return None