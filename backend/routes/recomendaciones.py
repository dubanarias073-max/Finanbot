
# routes/recomendaciones.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Transaccion, MetaAhorro, Simulacion, Usuario
from extensions import db
from collections import defaultdict
from datetime import date, timedelta

recomendaciones_bp = Blueprint('recomendaciones', __name__)


@recomendaciones_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_recomendaciones():
    usuario_id = int(get_jwt_identity())

    usuario      = Usuario.query.get(usuario_id)
    transacciones = Transaccion.query.filter_by(usuario_id=usuario_id)\
                                     .order_by(Transaccion.fecha.desc()).all()
    metas        = MetaAhorro.query.filter_by(usuario_id=usuario_id).all()
    simulaciones = Simulacion.query.filter_by(usuario_id=usuario_id).all()

    if not usuario:
        return jsonify([]), 404

    # ── MÉTRICAS BASE ─────────────────────────────────────
    total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
    total_gastos   = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')
    balance        = total_ingresos - total_gastos
    ing_mensual    = float(usuario.ingreso_mensual or 0)
    meta_mensual   = float(usuario.meta_ahorro or 0)
    num_trans      = len(transacciones)

    gastos_cat = defaultdict(float)
    ingresos_cat = defaultdict(float)
    for t in transacciones:
        cat = t.categoria if isinstance(t.categoria, str) else (
            t.categoria.nombre if t.categoria else 'Otros'
        )
        if t.tipo == 'gasto':
            gastos_cat[cat] += float(t.monto)
        else:
            ingresos_cat[cat] += float(t.monto)

    cat_mayor       = max(gastos_cat, key=gastos_cat.get) if gastos_cat else None
    monto_cat_mayor = gastos_cat[cat_mayor] if cat_mayor else 0
    pct_gastos      = round(total_gastos / total_ingresos * 100) if total_ingresos > 0 else 0
    pct_cat_mayor   = round(monto_cat_mayor / total_gastos * 100) if total_gastos > 0 else 0

    metas_activas   = [m for m in metas if not m.completada]
    metas_completas = [m for m in metas if m.completada]
    dias_registro   = len(set(t.fecha for t in transacciones if t.fecha))

    recs = []
    rid  = 1

    # ════════════════════════════════════════════════════════
    #  REGLA PRINCIPAL:
    #  Cada bloque decide si muestra UNA recomendación
    #  según el estado real del usuario.
    #  Máximo ~5-6 recomendaciones activas a la vez.
    # ════════════════════════════════════════════════════════

    # ── 1. SIN DATOS: solo esta, nada más ────────────────
    if num_trans == 0:
        return jsonify([{
            'id': 1, 'tipo': 'info', 'prioridad': 'Alta',
            'icono': '📝',
            'titulo': 'Registra tu primera transacción',
            'descripcion': (
                'Aún no tienes movimientos registrados. '
                'Con solo una transacción FinanBot empieza a analizar tus finanzas '
                'y a darte consejos reales.'
            ),
            'beneficios': [
                'Activa el análisis automático de tus finanzas',
                'Recibe recomendaciones personalizadas',
                'Ve cómo evoluciona tu balance en el dashboard',
            ],
            'accion': 'Ir a Mis Finanzas', 'link': 'finanzas.html',
            'completada': False, 'ahorro_potencial': 0,
            'dato_clave': '💡 Registra lo de hoy — solo toma 30 segundos.',
        }]), 200

    # ── 2. BALANCE NEGATIVO (prioridad máxima) ────────────
    #    Solo aparece si realmente hay déficit
    if balance < 0 and total_ingresos > 0:
        recs.append({
            'id': rid, 'tipo': 'alerta', 'prioridad': 'Alta',
            'icono': '🚨',
            'titulo': 'Tus gastos superan tus ingresos',
            'descripcion': (
                f'Tu balance es -${abs(balance):,.0f}. '
                f'La categoría que más pesa es "{cat_mayor}" '
                f'(${monto_cat_mayor:,.0f}). Recórtala primero.'
            ),
            'beneficios': [
                f'Reducir "{cat_mayor}" un 20% libera ${monto_cat_mayor * 0.2:,.0f}' if cat_mayor else 'Revisa tus gastos por categoría',
                'Prioriza arriendo, comida y servicios básicos',
                'Elimina gastos recurrentes que no usas',
            ],
            'accion': 'Ver mis gastos', 'link': 'finanzas.html',
            'completada': False,
            'ahorro_potencial': round(abs(balance)),
            'progreso': max(0, min(100, round((1 - abs(balance) / max(total_ingresos, 1)) * 100))),
            'dato_clave': f'🎯 Meta inmediata: recortar ${abs(balance):,.0f} para llegar a $0 de déficit.',
        })
        rid += 1

    # ── 3. GASTOS ELEVADOS (solo si > 85 % y balance >= 0) ─
    #    No aparece si ya mostró alerta de balance negativo
    elif total_ingresos > 0 and pct_gastos > 85:
        recs.append({
            'id': rid, 'tipo': 'advertencia', 'prioridad': 'Alta',
            'icono': '⚡',
            'titulo': f'Gastas el {pct_gastos}% de tus ingresos',
            'descripcion': (
                f'Solo te queda el {100 - pct_gastos}% libre al mes. '
                f'Un imprevisto pequeño podría ponerte en déficit. '
                f'Lo recomendado es no superar el 80%.'
            ),
            'beneficios': [
                f'Bajar al 80% libera ${round(total_ingresos * (pct_gastos/100 - 0.8)):,.0f}/mes',
                'Revisa suscripciones automáticas activas',
                f'Limita "{cat_mayor}" a ${round(monto_cat_mayor * 0.8):,.0f} este mes' if cat_mayor else 'Analiza tu categoría principal',
            ],
            'accion': 'Ver mis gastos', 'link': 'finanzas.html',
            'completada': False,
            'ahorro_potencial': round(total_ingresos * (pct_gastos / 100 - 0.8)),
            'progreso': max(0, 100 - pct_gastos),
            'dato_clave': f'🎯 Meta: no superar ${round(total_ingresos * 0.8):,.0f}/mes en gastos.',
        })
        rid += 1

    # ── 4. CATEGORÍA DOMINANTE (> 45 %, solo con 5+ trans) ─
    #    Aparece cuando hay datos suficientes para que sea real
    if cat_mayor and pct_cat_mayor > 45 and num_trans >= 5:
        recs.append({
            'id': rid, 'tipo': 'advertencia', 'prioridad': 'Media',
            'icono': '📊',
            'titulo': f'"{cat_mayor}" es el {pct_cat_mayor}% de tus gastos',
            'descripcion': (
                f'${monto_cat_mayor:,.0f} concentrados en una sola categoría. '
                f'Reducirla un 15% libera ${round(monto_cat_mayor * 0.15):,.0f} '
                f'sin cambiar drásticamente tu estilo de vida.'
            ),
            'beneficios': [
                f'Reducir 15%: +${round(monto_cat_mayor * 0.15):,.0f}/mes libres',
                f'Establece un tope fijo mensual para {cat_mayor}',
                'Compara precios antes de cada compra en esa categoría',
            ],
            'accion': 'Ver mis gastos', 'link': 'finanzas.html',
            'completada': False,
            'ahorro_potencial': round(monto_cat_mayor * 0.15),
            'progreso': max(0, 100 - pct_cat_mayor),
            'dato_clave': f'🔍 Revisa los últimos gastos en {cat_mayor} — casi siempre hay 1 evitable.',
        })
        rid += 1

    # ── 5. SIN METAS (solo si tiene 3+ transacciones) ─────
    #    No tiene sentido mostrarla al inicio, cuando aún no entiende la app
    if len(metas) == 0 and num_trans >= 3:
        recs.append({
            'id': rid, 'tipo': 'advertencia', 'prioridad': 'Media',
            'icono': '🎯',
            'titulo': 'Crea tu primera meta de ahorro',
            'descripcion': (
                'El dinero sin destino se gasta solo. '
                'Una meta concreta (fondo de emergencia, viaje, tecnología) '
                'le da propósito a cada peso que guardas.'
            ),
            'beneficios': [
                'Las personas con metas ahorran 3× más',
                'Define un objetivo alcanzable en 3-6 meses',
                'FinanBot te avisa cuando estés cerca de lograrlo',
            ],
            'accion': 'Crear mi primera meta', 'link': 'perfil.html',
            'completada': False,
            'ahorro_potencial': round(max(balance, 0) * 6),
            'dato_clave': f'💡 Con tu balance actual podrías acumular ${round(max(balance,0)*6):,.0f} en 6 meses.',
        })
        rid += 1

    # ── 6. META MENSUAL vs REALIDAD (solo si la tiene configurada) ─
    if meta_mensual > 0 and total_ingresos > 0:
        ahorro_real = max(0, balance)
        pct_meta    = min(100, round(ahorro_real / meta_mensual * 100))
        brecha      = max(0, meta_mensual - ahorro_real)
        if ahorro_real < meta_mensual:
            recs.append({
                'id': rid, 'tipo': 'advertencia', 'prioridad': 'Media',
                'icono': '🎯',
                'titulo': f'Vas al {pct_meta}% de tu meta mensual',
                'descripcion': (
                    f'Tu meta es ahorrar ${meta_mensual:,.0f}/mes '
                    f'pero tu balance actual es ${ahorro_real:,.0f}. '
                    f'Faltan ${brecha:,.0f} para cerrar la brecha.'
                ),
                'beneficios': [
                    f'Reducir ${brecha:,.0f} en gastos cierra la brecha',
                    'Transfiere el ahorro el mismo día que cobres',
                    'Lo que no ves en tu cuenta no lo gastas',
                ],
                'accion': 'Ajustar mis gastos', 'link': 'finanzas.html',
                'completada': False,
                'ahorro_potencial': brecha,
                'progreso': pct_meta,
                'dato_clave': f'💡 El día de pago, separa ${meta_mensual:,.0f} antes de gastar nada.',
            })
            rid += 1

    # ── 7. FONDO DE EMERGENCIA (solo si tiene 8+ trans y no tiene meta de fondo) ─
    #    Aparece cuando el usuario ya usa la app con regularidad
    if num_trans >= 8 and total_ingresos > 0:
        tiene_fondo = any(
            'emergencia' in m.nombre.lower() or 'fondo' in m.nombre.lower()
            for m in metas
        )
        if not tiene_fondo:
            base      = ing_mensual if ing_mensual > 0 else total_ingresos
            fondo_obj = base * 3
            recs.append({
                'id': rid, 'tipo': 'info', 'prioridad': 'Media',
                'icono': '🛡️',
                'titulo': 'Crea tu fondo de emergencia',
                'descripcion': (
                    f'Un fondo de ${fondo_obj:,.0f} (3 meses de ingresos) '
                    f'es la base de cualquier plan financiero sólido. '
                    f'Es lo primero que debes tener antes de invertir.'
                ),
                'beneficios': [
                    'Protección ante despido, enfermedad o imprevistos',
                    'Evitas endeudarte en momentos críticos',
                    'Tomas decisiones sin presión financiera',
                ],
                'accion': 'Crear meta de emergencia', 'link': 'perfil.html',
                'completada': False,
                'ahorro_potencial': round(fondo_obj),
                'dato_clave': f'🎯 Meta: ${fondo_obj:,.0f} · Empieza con ${round(fondo_obj/12):,.0f}/mes durante 1 año.',
            })
            rid += 1

    # ── 8. SIMULADOR (solo si balance > 0 y nunca ha simulado) ─
    #    Solo tiene sentido sugerirlo cuando hay dinero disponible
    if balance > 0 and len(simulaciones) == 0 and num_trans >= 5:
        capital_sug = round(balance * 0.5)
        recs.append({
            'id': rid, 'tipo': 'info', 'prioridad': 'Baja',
            'icono': '📈',
            'titulo': 'Tu balance puede generar dinero solo',
            'descripcion': (
                f'Tienes ${balance:,.0f} de balance positivo. '
                f'Si invirtieras ${capital_sug:,.0f} al 10% anual, '
                f'en 5 años tendrías ${round(capital_sug * 1.10**5):,.0f} sin hacer nada más.'
            ),
            'beneficios': [
                f'En 1 año: ${round(capital_sug * 1.10):,.0f} (+${round(capital_sug * 0.10):,.0f})',
                f'En 5 años: ${round(capital_sug * 1.10**5):,.0f} (+${round(capital_sug * (1.10**5-1)):,.0f})',
                'CDT, fondos o acciones desde $100.000 en Colombia',
            ],
            'accion': 'Ir al simulador', 'link': 'simulador.html',
            'completada': False,
            'ahorro_potencial': round(capital_sug * (1.10**5 - 1)),
            'dato_clave': f'⏳ Quien empieza hoy con ${capital_sug:,.0f} tiene ventaja enorme sobre quien espera un año.',
        })
        rid += 1

    # ── 9. REGLA 50/30/20 (solo si tiene ingreso mensual Y pct > 80) ─
    #    Educativa, aparece cuando hay contexto suficiente
    if ing_mensual > 0 and pct_gastos > 80 and num_trans >= 5:
        n20 = round(ing_mensual * 0.2)
        recs.append({
            'id': rid, 'tipo': 'info', 'prioridad': 'Baja',
            'icono': '📋',
            'titulo': 'Aplica la regla 50/30/20',
            'descripcion': (
                f'Con tu salario de ${ing_mensual:,.0f}: '
                f'50% para necesidades (${round(ing_mensual*0.5):,.0f}), '
                f'30% para deseos (${round(ing_mensual*0.3):,.0f}) '
                f'y 20% para ahorro (${n20:,.0f}).'
            ),
            'beneficios': [
                f'Ahorra ${n20:,.0f}/mes sin sacrificar calidad de vida',
                f'En 1 año de ahorro: ${n20*12:,.0f}',
                'Estructura clara sin hacer un presupuesto complicado',
            ],
            'accion': 'Aprender más', 'link': 'aprende.html',
            'completada': False,
            'ahorro_potencial': n20 * 12,
            'dato_clave': f'💰 Ahorrando ${n20:,.0f}/mes, en 1 año tendrías ${n20*12:,.0f}.',
        })
        rid += 1

    # ════════════════════════════════════════════════════════
    #  ÉXITOS — Aparecen cuando realmente se logran
    # ════════════════════════════════════════════════════════

    # Balance positivo y gastos controlados
    if balance > 0 and pct_gastos < 70 and total_ingresos > 0:
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '💰',
            'titulo': f'¡Excelente! Solo gastas el {pct_gastos}% — estás listo para invertir',
            'descripcion': (
                f'Balance positivo de ${balance:,.0f} y gastos bajo control. '
                f'Este es el momento ideal para hacer crecer tu dinero.'
            ),
            'beneficios': [
                f'CDT al 12%: ${round(balance*0.5*1.12):,.0f} en 1 año con ${round(balance*0.5):,.0f}',
                'Considera activos que generen ingreso pasivo',
                'Sube tu meta de ahorro mensual un 20%',
            ],
            'accion': 'Simular inversión', 'link': 'simulador.html',
            'completada': False,
            'ahorro_potencial': round(balance * 0.2 * 12),
            'dato_clave': f'📈 Invirtiendo el 20% de tu balance mensual, en 1 año acumulas ~${round(balance*0.2*12):,.0f}.',
        })
        rid += 1

    # Meta mensual cumplida
    if meta_mensual > 0 and max(0, balance) >= meta_mensual:
        excedente = max(0, balance) - meta_mensual
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '✅',
            'titulo': '¡Cumpliste tu meta de ahorro mensual!',
            'descripcion': (
                f'Meta: ${meta_mensual:,.0f} · Llevas: ${max(0,balance):,.0f}. '
                f'Estás ${excedente:,.0f} por encima. '
                f'Considera subir la meta o llevar el excedente a inversión.'
            ),
            'beneficios': [
                f'Superaste la meta en ${excedente:,.0f}',
                f'Sube la meta a ${round(meta_mensual*1.2):,.0f} (+20%)',
                'Redirige el excedente a un CDT o fondo',
            ],
            'accion': 'Actualizar mi meta', 'link': 'perfil.html',
            'completada': False,
            'ahorro_potencial': excedente * 12,
            'progreso': 100,
            'dato_clave': f'🚀 Sube tu meta a ${round(meta_mensual*1.2):,.0f} para seguir creciendo.',
        })
        rid += 1

    # Metas casi completadas (≥ 80 %)
    for m in metas_activas:
        if m.monto_objetivo <= 0:
            continue
        pct_m    = round(float(m.monto_actual) / float(m.monto_objetivo) * 100)
        faltante = float(m.monto_objetivo) - float(m.monto_actual)
        if pct_m >= 80:
            recs.append({
                'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
                'icono': '🚀',
                'titulo': f'¡Casi lo logras! "{m.nombre}" al {pct_m}%',
                'descripcion': (
                    f'Solo faltan ${faltante:,.0f} para completar esta meta. '
                    f'Un aporte extra esta semana puede cerrarla.'
                ),
                'beneficios': [
                    f'Faltan ${faltante:,.0f} — estás muy cerca',
                    'Un aporte extra la cierra antes de lo previsto',
                    'Al completarla, crea una meta más ambiciosa',
                ],
                'accion': 'Abonar a la meta', 'link': 'perfil.html',
                'completada': False,
                'ahorro_potencial': 0,
                'progreso': pct_m,
                'dato_clave': f'🏁 Con ${round(faltante/2):,.0f} en 2 abonos cierras esta meta.',
            })
            rid += 1

    # Metas completadas
    if metas_completas:
        total_comp = sum(float(m.monto_objetivo) for m in metas_completas)
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '🏆',
            'titulo': f'¡{len(metas_completas)} meta(s) completada(s)!',
            'descripcion': (
                f'Llevas ${total_comp:,.0f} ahorrados en metas cumplidas. '
                f'Esa disciplina es lo que separa a quienes logran sus metas de los que no.'
            ),
            'beneficios': [
                f'${total_comp:,.0f} ahorrados en metas cumplidas',
                'Reinvierte en una meta más ambiciosa',
                f'Siguiente reto: ${round(total_comp * 1.5):,.0f} (50% más)',
            ],
            'accion': 'Crear nueva meta', 'link': 'perfil.html',
            'completada': False, 'ahorro_potencial': 0, 'progreso': 100,
            'dato_clave': f'🎯 Siguiente reto: una meta de ${round(total_comp * 1.5):,.0f}.',
        })
        rid += 1

    # Simulador usado
    if len(simulaciones) > 0:
        ultima = simulaciones[-1]
        gan    = float(ultima.resultado_final) - float(ultima.capital_inicial)
        recs.append({
            'id': rid, 'tipo': 'exito', 'prioridad': 'Baja',
            'icono': '🔬',
            'titulo': f'¡Usas el simulador! {len(simulaciones)} simulación(es)',
            'descripcion': (
                f'Tu última simulación proyectó una ganancia de ${gan:,.0f}. '
                f'El siguiente paso es convertirla en una inversión real.'
            ),
            'beneficios': [
                f'Última proyección: +${gan:,.0f}',
                'CDT disponibles desde $100.000 en bancos colombianos',
                'Compara tasas antes de decidir',
            ],
            'accion': 'Nueva simulación', 'link': 'simulador.html',
            'completada': False, 'ahorro_potencial': 0,
            'progreso': min(100, len(simulaciones) * 25),
            'dato_clave': f'📊 {len(simulaciones)} simulación(es). Próximo paso: abre un CDT real con ese capital.',
        })
        rid += 1

    # ── ORDENAR: alertas primero, luego advertencias, info, éxitos ─
    orden_tipo = {'alerta': 0, 'advertencia': 1, 'info': 2, 'exito': 3}
    orden_prio = {'Alta': 0, 'Media': 1, 'Baja': 2}
    recs.sort(key=lambda r: (
        orden_tipo.get(r['tipo'], 4),
        orden_prio.get(r['prioridad'], 3)
    ))

    return jsonify(recs), 200