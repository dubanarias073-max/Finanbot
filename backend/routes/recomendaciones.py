
#Recomendaciones.py
# routes/recomendaciones.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Transaccion, MetaAhorro, Simulacion, Usuario
from extensions import db
from collections import defaultdict
from datetime import datetime, date, timedelta
 
recomendaciones_bp = Blueprint('recomendaciones', __name__)
 
 
# ─────────────────────────────────────────────────────────
#  GET — Obtener recomendaciones personalizadas
# ─────────────────────────────────────────────────────────
@recomendaciones_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_recomendaciones():
    usuario_id = int(get_jwt_identity())
 
    usuario       = Usuario.query.get(usuario_id)
    transacciones = Transaccion.query.filter_by(usuario_id=usuario_id).order_by(Transaccion.fecha.desc()).all()
    metas         = MetaAhorro.query.filter_by(usuario_id=usuario_id).all()
    simulaciones  = Simulacion.query.filter_by(usuario_id=usuario_id).all()
 
    if not usuario:
        return jsonify([]), 404
 
    recs = []
    rid  = 1
 
    def add(tipo, prioridad, icono, titulo, descripcion,
            beneficios, accion, link,
            ahorro_potencial=0, progreso=None, dato_clave=None,
            condicion_completada=False):
        """
        condicion_completada = True  →  la recomendación ya fue superada,
        se omite del listado (no se muestra).
        """
        nonlocal rid
        if condicion_completada:
            rid += 1
            return          # ← si ya se cumplió, simplemente no la agregamos
 
        r = {
            'id':              rid,
            'tipo':            tipo,
            'prioridad':       prioridad,
            'icono':           icono,
            'titulo':          titulo,
            'descripcion':     descripcion,
            'beneficios':      beneficios,
            'accion':          accion,
            'link':            link,
            'completada':      False,
            'ahorro_potencial': round(float(ahorro_potencial)),
        }
        if progreso is not None:
            r['progreso'] = min(int(progreso), 100)
        if dato_clave:
            r['dato_clave'] = dato_clave
        rid += 1
        recs.append(r)
 
    # ── MÉTRICAS ─────────────────────────────────────────
    total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
    total_gastos   = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')
    balance        = total_ingresos - total_gastos
    ing_mensual    = float(usuario.ingreso_mensual or 0)
    meta_mensual   = float(usuario.meta_ahorro     or 0)
    num_trans      = len(transacciones)
 
    # Categorías — t.categoria es string directo
    gastos_cat   = defaultdict(float)
    ingresos_cat = defaultdict(float)
    for t in transacciones:
        cat = t.categoria if isinstance(t.categoria, str) else (t.categoria.nombre if t.categoria else 'Otros')
        if t.tipo == 'gasto':
            gastos_cat[cat]   += float(t.monto)
        else:
            ingresos_cat[cat] += float(t.monto)
 
    cat_mayor        = max(gastos_cat, key=gastos_cat.get) if gastos_cat else None
    monto_cat_mayor  = gastos_cat[cat_mayor] if cat_mayor else 0
    pct_gastos       = round(total_gastos / total_ingresos * 100) if total_ingresos > 0 else 0
    pct_cat_mayor    = round(monto_cat_mayor / total_gastos * 100) if total_gastos > 0 else 0
 
    metas_completas = [m for m in metas if m.completada]
    metas_activas   = [m for m in metas if not m.completada]
    total_ahorrado  = sum(float(m.monto_actual)   for m in metas)
    total_meta_obj  = sum(float(m.monto_objetivo) for m in metas)
 
    hace_30         = date.today() - timedelta(days=30)
    dias_registro   = len(set(t.fecha for t in transacciones if t.fecha))
 
    # ── SIN DATOS ─────────────────────────────────────────
    if num_trans == 0:
        recs.append({
            'id': 1, 'tipo': 'info', 'prioridad': 'Alta',
            'icono': '📝',
            'titulo': 'Comienza registrando tus finanzas',
            'descripcion': (
                'FinanBot necesita al menos una transacción para darte '
                'recomendaciones personalizadas. '
                'Registra tu primer ingreso o gasto y el análisis se activa automáticamente.'
            ),
            'beneficios': [
                'Visibilidad total sobre tu dinero',
                'Recomendaciones ajustadas a tu realidad',
                'Detectar gastos que no notas día a día',
            ],
            'accion': 'Registrar primera transacción', 'link': 'finanzas.html',
            'completada': False, 'ahorro_potencial': 0,
            'dato_clave': '💡 Solo necesitas 5 minutos. Registra lo de hoy y FinanBot hace el resto.',
        })
        return jsonify(recs), 200
 
    # ═══════════════════════════════════════════════════════
    #  1 — BALANCE NEGATIVO
    #      Se va cuando balance >= 0
    # ═══════════════════════════════════════════════════════
    add(
        'alerta', 'Alta', '🚨',
        'Tus gastos superan tus ingresos',
        (
            f'Tu balance es -${abs(balance):,.0f}. '
            f'Cada mes que pasa sin corregirlo aumenta el déficit. '
            f'Identifica la categoría de mayor gasto y recórtala primero.'
        ),
        [
            f'Recortar {cat_mayor} un 20% = ${monto_cat_mayor * 0.2:,.0f} liberados' if cat_mayor else 'Revisar todos los gastos',
            'Pagar primero servicios básicos (arriendo, servicios, comida)',
            'Evitar gastos de entretenimiento hasta equilibrar el balance',
        ],
        'Ver mis gastos', 'finanzas.html',
        ahorro_potencial=abs(balance),
        progreso=max(0, min(100, round((1 - abs(balance) / max(total_ingresos, 1)) * 100))),
        dato_clave=f'🎯 Meta inmediata: reducir ${abs(balance):,.0f} en gastos para llegar a $0 de déficit.',
        condicion_completada=(balance >= 0),   # ← desaparece cuando se equilibra
    )
 
    # ═══════════════════════════════════════════════════════
    #  2 — SIN INGRESOS
    #      Se va cuando hay al menos 1 ingreso registrado
    # ═══════════════════════════════════════════════════════
    add(
        'advertencia', 'Alta', '💼',
        'No tienes ingresos registrados',
        (
            'Tienes gastos pero ningún ingreso. '
            'Sin esa información no podemos calcular tu balance real '
            'ni qué porcentaje de tus ingresos estás gastando.'
        ),
        [
            'Registra tu salario aunque sea una vez al mes',
            'Activa el análisis completo de balance',
            'Permite recomendaciones de ahorro personalizadas',
        ],
        'Registrar ingreso', 'finanzas.html',
        dato_clave='💡 Con un ingreso registrado, todas las métricas del dashboard se activan.',
        condicion_completada=(total_ingresos > 0),   # ← desaparece cuando hay ingresos
    )
 
    # ═══════════════════════════════════════════════════════
    #  3 — GASTOS > 90 %
    #      Se va cuando pct_gastos < 90
    # ═══════════════════════════════════════════════════════
    if total_ingresos > 0:
        add(
            'alerta', 'Alta', '⚡',
            f'Gastas el {pct_gastos}% de tus ingresos — zona de riesgo',
            (
                f'Solo te queda el {100 - pct_gastos}% libre. '
                f'Cualquier imprevisto te llevaría al déficit. '
                f'La regla de oro es no superar el 80% en gastos.'
            ),
            [
                f'Bajar al 80% libera ${total_ingresos * (pct_gastos/100 - 0.8):,.0f}/mes',
                'Revisar suscripciones automáticas que ya no usas',
                f'Limitar {cat_mayor} a ${monto_cat_mayor * 0.8:,.0f} el próximo mes' if cat_mayor else 'Revisar la categoría de mayor gasto',
            ],
            'Ver mis gastos', 'finanzas.html',
            ahorro_potencial=round(total_ingresos * (pct_gastos/100 - 0.8)),
            progreso=max(0, 100 - pct_gastos),
            dato_clave=f'🎯 Meta: reducir gastos a ${total_ingresos * 0.8:,.0f} (80% de ${total_ingresos:,.0f}).',
            condicion_completada=(pct_gastos < 90 or total_ingresos == 0),
        )
 
    # ═══════════════════════════════════════════════════════
    #  4 — GASTOS 70–90 % (aviso moderado)
    #      Se va cuando pct_gastos < 70 o >= 90 (ya cubre la alerta 3)
    # ═══════════════════════════════════════════════════════
    if total_ingresos > 0:
        add(
            'advertencia', 'Media', '⚠️',
            f'Usas el {pct_gastos}% de tus ingresos en gastos',
            (
                f'Estás dentro del rango, pero cerca del límite recomendado (80%). '
                f'Reducir aunque sea ${total_ingresos * 0.05:,.0f}/mes te da un colchón importante.'
            ),
            [
                f'Reducir al 70% libera ${total_ingresos * (pct_gastos/100 - 0.7):,.0f}/mes',
                'Aplica la regla 50/30/20 para estructurar tu presupuesto',
                'Revisa gastos recurrentes automáticos',
            ],
            'Aplicar regla 50/30/20', 'aprende.html',
            ahorro_potencial=round(total_ingresos * (pct_gastos/100 - 0.7)),
            progreso=round((1 - (pct_gastos - 70) / 20) * 100),
            dato_clave=f'📋 Meta: no superar ${total_ingresos * 0.7:,.0f}/mes en gastos.',
            condicion_completada=(pct_gastos < 70 or pct_gastos >= 90 or total_ingresos == 0),
        )
 
    # ═══════════════════════════════════════════════════════
    #  5 — SIN METAS DE AHORRO
    #      Se va cuando el usuario crea al menos 1 meta
    # ═══════════════════════════════════════════════════════
    add(
        'advertencia', 'Media', '🎯',
        'No tienes metas de ahorro definidas',
        (
            'Sin metas, el dinero que "sobra" tiende a gastarse sin rumbo. '
            'Una meta concreta (fondo de emergencia, viaje, tecnología) '
            'le da propósito a cada peso que guardas.'
        ),
        [
            'Crea un fondo de emergencia: 3 meses de gastos',
            'Define una meta de corto plazo alcanzable en 3-6 meses',
            'Las personas con metas ahorran 3x más que las que no las tienen',
        ],
        'Crear mi primera meta', 'perfil.html',
        ahorro_potencial=max(balance, 0) * 6,
        dato_clave=f'💡 Con tu balance actual puedes alcanzar ${max(balance,0)*6:,.0f} en 6 meses si ahorras consistente.',
        condicion_completada=(len(metas) > 0),   # ← desaparece al crear cualquier meta
    )
 
    # ═══════════════════════════════════════════════════════
    #  6 — CATEGORÍA DOMINANTE (> 40 %)
    #      Se va cuando esa categoría baja del 40 %
    # ═══════════════════════════════════════════════════════
    if cat_mayor and total_gastos > 0:
        add(
            'advertencia', 'Media', '📊',
            f'"{cat_mayor}" consume el {pct_cat_mayor}% de tus gastos',
            (
                f'Tienes ${monto_cat_mayor:,.0f} concentrados en {cat_mayor}. '
                f'Lo recomendado es que ninguna categoría supere el 35-40%. '
                f'Reducir un 15% aquí generaría ${monto_cat_mayor * 0.15:,.0f} libres al mes.'
            ),
            [
                f'Reducir 15% en {cat_mayor}: +${monto_cat_mayor * 0.15:,.0f}/mes',
                'Comparar precios antes de cada compra de esa categoría',
                'Establecer un límite fijo mensual para este rubro',
            ],
            'Ver mis gastos', 'finanzas.html',
            ahorro_potencial=round(monto_cat_mayor * 0.15),
            progreso=max(0, 100 - pct_cat_mayor),
            dato_clave=f'🔍 Revisa los últimos 5 gastos en {cat_mayor} — casi siempre hay al menos 1 evitable.',
            condicion_completada=(pct_cat_mayor <= 40),
        )
 
    # ═══════════════════════════════════════════════════════
    #  7 — POCOS REGISTROS (< 8)
    #      Se va cuando hay 8 o más transacciones
    # ═══════════════════════════════════════════════════════
    add(
        'info', 'Baja', '📅',
        f'Solo tienes {num_trans} transacción(es) — registra más',
        (
            'Con pocos datos las recomendaciones son generales. '
            'Con 2-3 semanas de registro diario FinanBot detecta patrones '
            'y te da un diagnóstico mucho más preciso y útil.'
        ),
        [
            'Detectar en qué días gastas más',
            'Identificar gastos repetitivos que no notas',
            'Pronóstico de balance para fin de mes',
        ],
        'Registrar transacciones', 'finanzas.html',
        progreso=round(num_trans / 8 * 100),
        dato_clave='📱 Tip: registra cada gasto en el momento, antes de que lo olvides.',
        condicion_completada=(num_trans >= 8),   # ← desaparece con 8+ transacciones
    )
 
    # ═══════════════════════════════════════════════════════
    #  8 — FONDO DE EMERGENCIA
    #      Se va cuando el balance cubre los 3 meses
    # ═══════════════════════════════════════════════════════
    if total_ingresos > 0 or ing_mensual > 0:
        fondo_obj     = (ing_mensual if ing_mensual > 0 else total_ingresos) * 3
        cobertura     = max(0, balance)
        pct_fondo     = min(100, round(cobertura / fondo_obj * 100)) if fondo_obj > 0 else 0
        tiene_fondo   = any('emergencia' in m.nombre.lower() or 'fondo' in m.nombre.lower() for m in metas)
 
        add(
            'info', 'Media', '🛡️',
            'Construye tu fondo de emergencia',
            (
                f'Un fondo de emergencia de ${fondo_obj:,.0f} (3 meses de ingresos) '
                f'es la base de cualquier plan financiero sólido. '
                f'Actualmente tu cobertura es del {pct_fondo}%.'
            ),
            [
                'Protección ante pérdida de empleo o enfermedad',
                'Evitar endeudarte en situaciones críticas',
                'Tomar decisiones financieras sin presión',
            ],
            'Crear meta de emergencia', 'perfil.html',
            ahorro_potencial=round(max(0, fondo_obj - cobertura)),
            progreso=pct_fondo,
            dato_clave=f'🎯 Meta: ${fondo_obj:,.0f} · Cobertura actual: {pct_fondo}% (${cobertura:,.0f}).',
            condicion_completada=(pct_fondo >= 100 or tiene_fondo),  # ← desaparece si ya tiene la meta o el fondo completo
        )
 
    # ═══════════════════════════════════════════════════════
    #  9 — REGLA 50/30/20
    #      Solo aparece si tiene ingreso mensual registrado
    #      Se va cuando el pct de gastos baja del 80 %
    # ═══════════════════════════════════════════════════════
    if ing_mensual > 0:
        n50 = ing_mensual * 0.5
        n30 = ing_mensual * 0.3
        n20 = ing_mensual * 0.2
        add(
            'info', 'Media', '📋',
            'Aplica la regla 50/30/20 a tu salario',
            (
                f'Con tu ingreso mensual de ${ing_mensual:,.0f} tienes una guía clara. '
                f'Esta regla equilibra necesidades, calidad de vida y futuro financiero.'
            ),
            [
                f'50% necesidades (${n50:,.0f}): arriendo, comida, transporte, salud',
                f'30% deseos (${n30:,.0f}): entretenimiento, ropa, salidas',
                f'20% ahorro e inversión (${n20:,.0f}): CDT, metas, pensión',
            ],
            'Ir al simulador', 'simulador.html',
            ahorro_potencial=round(n20 * 12),
            dato_clave=f'💰 Ahorrando ${n20:,.0f}/mes (20%), en 1 año tendrías ${n20*12:,.0f}.',
            condicion_completada=(pct_gastos <= 80 and total_ingresos > 0),
        )
 
    # ═══════════════════════════════════════════════════════
    #  10 — META DE AHORRO MENSUAL vs REALIDAD
    #       Se va cuando el ahorro real >= meta mensual
    # ═══════════════════════════════════════════════════════
    if meta_mensual > 0 and total_ingresos > 0:
        ahorro_real = max(0, balance)
        pct_meta    = min(100, round(ahorro_real / meta_mensual * 100))
        brecha      = max(0, meta_mensual - ahorro_real)
 
        add(
            'advertencia', 'Media', '🎯',
            f'Tu ahorro real está al {pct_meta}% de tu meta mensual',
            (
                f'Tu meta de ahorro mensual es ${meta_mensual:,.0f} '
                f'pero tu balance actual es ${ahorro_real:,.0f}. '
                f'Hay una brecha de ${brecha:,.0f} que debes cerrar.'
            ),
            [
                f'Reducir ${brecha:,.0f} en gastos cierra la brecha',
                'Transfiere el ahorro el mismo día que cobres',
                'Lo que no ves en cuenta corriente, no lo gastas',
            ],
            'Ajustar mis gastos', 'finanzas.html',
            ahorro_potencial=brecha,
            progreso=pct_meta,
            dato_clave=f'💡 Truco: el día de pago, transfiere ${meta_mensual:,.0f} a una cuenta separada antes de gastar.',
            condicion_completada=(ahorro_real >= meta_mensual),   # ← desaparece cuando cumple la meta
        )
 
    # ═══════════════════════════════════════════════════════
    #  11 — SIMULADOR NO USADO
    #       Se va cuando hace al menos 1 simulación
    # ═══════════════════════════════════════════════════════
    add(
        'info', 'Baja', '🔬',
        'Prueba el simulador de inversiones',
        (
            'El simulador te muestra cuánto crecería tu dinero con CDT, '
            'fondos o acciones — sin arriesgar un peso real. '
            'Es la forma más segura de aprender a invertir.'
        ),
        [
            'Simula CDT, fondos y acciones sin riesgo',
            'Compara distintas tasas y plazos en segundos',
            'Entiende el interés compuesto con tus propios números',
        ],
        'Ir al simulador', 'simulador.html',
        dato_clave='💡 Prueba: $1.000.000 al 10% por 24 meses. El resultado te sorprenderá.',
        condicion_completada=(len(simulaciones) > 0),   # ← desaparece al usar el simulador
    )
 
    # ═══════════════════════════════════════════════════════
    #  12 — INTERÉS COMPUESTO (solo si tiene balance positivo)
    #       Se va cuando ya invirtió (tiene simulaciones)
    # ═══════════════════════════════════════════════════════
    if balance > 0:
        capital_sug = round(balance * 0.5)
        r_1a  = round(capital_sug * (1.10 ** 1))
        r_5a  = round(capital_sug * (1.10 ** 5))
        r_10a = round(capital_sug * (1.10 ** 10))
        add(
            'info', 'Baja', '📈',
            'Tu balance puede generar dinero solo — Interés compuesto',
            (
                f'Si invirtieras ${capital_sug:,.0f} (50% de tu balance) '
                f'al 10% anual, ese dinero crece sin que hagas nada más. '
                f'El tiempo es tu mayor aliado.'
            ),
            [
                f'En 1 año: ${r_1a:,.0f} (ganancia ${r_1a - capital_sug:,.0f})',
                f'En 5 años: ${r_5a:,.0f} (ganancia ${r_5a - capital_sug:,.0f})',
                f'En 10 años: ${r_10a:,.0f} (ganancia ${r_10a - capital_sug:,.0f})',
            ],
            'Simular ahora', 'simulador.html',
            ahorro_potencial=r_5a - capital_sug,
            dato_clave=f'⏳ Quien empieza hoy con ${capital_sug:,.0f} tiene ventaja enorme sobre quien espera un año.',
            condicion_completada=(len(simulaciones) > 0),
        )
 
    # ═══════════════════════════════════════════════════════
    #  13 — INFLACIÓN: DINERO QUIETO PIERDE VALOR
    #       Se va cuando hace alguna simulación (invirtió)
    # ═══════════════════════════════════════════════════════
    if balance > 0:
        inflacion   = 9.28
        perdida_inf = round(balance * inflacion / 100)
        add(
            'info', 'Baja', '📉',
            'El dinero parado pierde valor — Protégete de la inflación',
            (
                f'Con inflación del {inflacion}% anual, '
                f'tu balance de ${balance:,.0f} pierde ${perdida_inf:,.0f} '
                f'de poder adquisitivo cada año si no lo inviertes.'
            ),
            [
                f'CDT 10-14% anual supera la inflación ({inflacion}%)',
                'Fondos de inversión: mayor rendimiento a largo plazo',
                'Cualquier rendimiento > inflación es ganancia real',
            ],
            'Simular protección', 'simulador.html',
            ahorro_potencial=perdida_inf,
            dato_clave=f'💸 No invertir hoy te cuesta ${perdida_inf:,.0f}/año en poder de compra perdido.',
            condicion_completada=(len(simulaciones) > 0),
        )
 
    # ═══════════════════════════════════════════════════════
    #  14 — PENSIÓN VOLUNTARIA (solo si ingreso >= 1.5 M)
    #       Siempre aparece (educativa)
    # ═══════════════════════════════════════════════════════
    if ing_mensual >= 1500000:
        aporte_pens   = round(ing_mensual * 0.1)
        beneficio_tri = round(aporte_pens * 0.19)
        add(
            'info', 'Baja', '👴',
            'Aportes voluntarios a pensión — Ahorra y paga menos impuestos',
            (
                f'Aportando el 10% de tu salario (${aporte_pens:,.0f}/mes) '
                f'a pensión voluntaria reduces tu base gravable y '
                f'ahorras ~${beneficio_tri:,.0f} en impuestos al mes.'
            ),
            [
                f'Ahorro en impuestos: ~${beneficio_tri:,.0f}/mes',
                f'Capital pensional anual adicional: ${aporte_pens * 12:,.0f}',
                'Deducible de renta (Art. 126-1, E.T. Colombia)',
            ],
            'Aprender más', 'aprende.html',
            ahorro_potencial=beneficio_tri * 12,
            dato_clave=f'📑 Con ${aporte_pens:,.0f}/mes en pensión voluntaria ahorras ${beneficio_tri * 12:,.0f}/año en impuestos.',
            condicion_completada=False,   # siempre visible si cumple el ingreso
        )
 
    # ═══════════════════════════════════════════════════════
    #  15 — DIVERSIFICACIÓN DE INGRESOS
    #       Se va cuando tiene 2+ categorías de ingresos
    # ═══════════════════════════════════════════════════════
    add(
        'info', 'Baja', '🌱',
        'Tienes una sola fuente de ingresos — diversifica',
        (
            'Depender de un solo ingreso es el mayor riesgo financiero personal. '
            'Si se corta (despido, enfermedad), tu flujo de caja desaparece. '
            'Una segunda fuente pequeña cambia completamente tu seguridad.'
        ),
        [
            'Freelance o consultoría en tu área',
            'Venta de productos digitales o físicos',
            'Inversiones que generen dividendos o intereses',
        ],
        'Explorar opciones', 'aprende.html',
        dato_clave='💡 Una segunda fuente de $300.000/mes cambia completamente tu seguridad financiera.',
        condicion_completada=(len(ingresos_cat) >= 2),   # ← desaparece con 2+ fuentes de ingreso
    )
 
    # ═══════════════════════════════════════════════════════
    #  ÉXITOS — Solo aparecen cuando realmente se logran
    # ═══════════════════════════════════════════════════════
 
    # Balance positivo y gastos < 70 %
    if balance > 0 and pct_gastos < 70 and total_ingresos > 0:
        ahorro_sug   = round(balance * 0.2)
        res_1a       = round(ahorro_sug * 12 * 1.10)
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '💰',
            'titulo': f'¡Excelente! Gastas solo el {pct_gastos}% — Momento de invertir',
            'descripcion': (
                f'Tu control financiero es sobresaliente. '
                f'Con balance positivo de ${balance:,.0f} y gastos controlados, '
                f'estás listo para hacer crecer tu dinero.'
            ),
            'beneficios': [
                f'CDT al 12% con ${ahorro_sug:,.0f} → ${round(ahorro_sug * 1.12):,.0f} en 1 año',
                f'En 1 año de aportes mensuales tendrías ~${res_1a:,.0f}',
                'Considera activos que generen ingreso pasivo',
            ],
            'accion': 'Simular inversión', 'link': 'simulador.html',
            'completada': False,
            'ahorro_potencial': round(balance * 0.2 * 12),
            'dato_clave': f'📈 Invirtiendo el 20% de tu balance (${ahorro_sug:,.0f}/mes), en 1 año tendrías ~${res_1a:,.0f}.',
        })
        rid += 1
 
    # Meta mensual cumplida
    if meta_mensual > 0 and max(0, balance) >= meta_mensual:
        excedente = max(0, balance) - meta_mensual
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '✅',
            'titulo': '¡Estás cumpliendo tu meta de ahorro mensual!',
            'descripcion': (
                f'Tu meta era ${meta_mensual:,.0f} y llevas ${max(0,balance):,.0f} ahorrados. '
                f'Estás ${excedente:,.0f} por encima de lo planeado. '
                f'Considera aumentar la meta o redirigir el excedente a inversión.'
            ),
            'beneficios': [
                f'Superaste la meta en ${excedente:,.0f}',
                f'Sube la meta a ${round(meta_mensual * 1.2):,.0f} (+20%) para crecer más rápido',
                'Redirige el excedente a un CDT o fondo de inversión',
            ],
            'accion': 'Actualizar mi meta', 'link': 'perfil.html',
            'completada': False,
            'ahorro_potencial': excedente * 12,
            'dato_clave': f'🚀 Sube tu meta a ${round(meta_mensual * 1.2):,.0f} (+20%) para acelerar tu progreso.',
            'progreso': 100,
        })
        rid += 1
 
    # Metas casi completadas
    for m in metas_activas:
        pct_m = round(float(m.monto_actual) / float(m.monto_objetivo) * 100) if m.monto_objetivo > 0 else 0
        if pct_m >= 75:
            faltante = float(m.monto_objetivo) - float(m.monto_actual)
            recs.append({
                'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
                'icono': '🚀',
                'titulo': f'¡Casi lo logras! "{m.nombre}" está al {pct_m}%',
                'descripcion': (
                    f'Solo faltan ${faltante:,.0f} para completar esta meta. '
                    f'Un aporte extra esta semana puede cerrarla antes de lo esperado.'
                ),
                'beneficios': [
                    f'Faltan ${faltante:,.0f} para completar la meta',
                    'Un aporte extra la cierra antes de lo previsto',
                    'Al completarla, crea una meta más ambiciosa',
                ],
                'accion': 'Ver mis metas', 'link': 'perfil.html',
                'completada': False,
                'ahorro_potencial': 0,
                'progreso': pct_m,
                'dato_clave': f'🏁 Con ${round(faltante/2):,.0f} en 2 abonos cierras esta meta.',
            })
            rid += 1
 
    # Metas completadas — celebrar
    if metas_completas:
        total_comp = sum(float(m.monto_objetivo) for m in metas_completas)
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '🏆',
            'titulo': f'¡{len(metas_completas)} meta(s) completada(s)! Sigue así',
            'descripcion': (
                f'Has demostrado disciplina real. '
                f'Llevas ${total_comp:,.0f} ahorrados en metas cumplidas. '
                f'Ese capital ahora puede ir a inversión o a una meta más grande.'
            ),
            'beneficios': [
                f'${total_comp:,.0f} ahorrados en metas cumplidas',
                'Reinvierte en una meta más ambiciosa',
                f'Siguiente reto: meta de ${total_comp * 1.5:,.0f} (50% más)',
            ],
            'accion': 'Crear nueva meta', 'link': 'perfil.html',
            'completada': False,
            'ahorro_potencial': 0,
            'progreso': 100,
            'dato_clave': f'🎯 Siguiente reto: una meta de ${total_comp * 1.5:,.0f} (50% más de lo que ya lograste).',
        })
        rid += 1
 
    # Simulador usado — siguiente nivel
    if len(simulaciones) > 0:
        ultima = simulaciones[-1]
        gan    = float(ultima.resultado_final) - float(ultima.capital_inicial)
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '🔬',
            'titulo': f'¡Usas el simulador! {len(simulaciones)} simulación(es)',
            'descripcion': (
                f'Tu última simulación proyectó una ganancia de ${gan:,.0f}. '
                f'El siguiente paso es convertir esa simulación en una inversión real.'
            ),
            'beneficios': [
                f'Última proyección: ganancia de ${gan:,.0f}',
                'CDT disponibles desde $100.000 en bancos colombianos',
                'Compara múltiples tasas antes de decidir',
            ],
            'accion': 'Nueva simulación', 'link': 'simulador.html',
            'completada': False,
            'ahorro_potencial': 0,
            'progreso': min(100, len(simulaciones) * 20),
            'dato_clave': f'📊 {len(simulaciones)} simulación(es). El próximo paso: abre un CDT real con ese capital.',
        })
        rid += 1
 
    # Buen ritmo de registro
    if dias_registro >= 7:
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '📋',
            'titulo': f'¡{dias_registro} días registrando! Gran hábito',
            'descripcion': (
                'Registrar consistentemente es uno de los hábitos más poderosos '
                'para mejorar la salud financiera. '
                'La mayoría de personas abandona en la primera semana — tú no.'
            ),
            'beneficios': [
                'Base de datos real para análisis precisos',
                'Patrones de gasto identificables',
                'Predicciones confiables para el futuro',
            ],
            'accion': 'Ver mis finanzas', 'link': 'finanzas.html',
            'completada': False,
            'ahorro_potencial': 0,
            'progreso': min(100, round(dias_registro / 30 * 100)),
            'dato_clave': f'📅 {dias_registro} días. La meta es 30 días continuos para consolidar el hábito.',
        })
        rid += 1
 
    # ── ORDENAR ───────────────────────────────────────────
    orden_tipo = {'alerta': 0, 'advertencia': 1, 'info': 2, 'exito': 3}
    orden_prio = {'Alta': 0, 'Media': 1, 'Baja': 2}
    recs.sort(key=lambda r: (
        orden_tipo.get(r['tipo'], 4),
        orden_prio.get(r['prioridad'], 3)
    ))
 
    return jsonify(recs), 200