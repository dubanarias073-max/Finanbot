# routes/recomendaciones.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Transaccion, Usuario
from collections import defaultdict

recomendaciones_bp = Blueprint('recomendaciones', __name__)

@recomendaciones_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_recomendaciones():
    usuario_id = int(get_jwt_identity())
    transacciones = Transaccion.query.filter_by(usuario_id=usuario_id).all()
    usuario = Usuario.query.get(usuario_id)

    recomendaciones = []

    if not transacciones:
        recomendaciones.append({
            'id': 1,
            'tipo': 'info',
            'prioridad': 'Alta',
            'icono': '📝',
            'titulo': 'Empieza a registrar tus finanzas',
            'descripcion': 'Aún no tienes transacciones registradas. Comienza registrando tus ingresos y gastos para recibir recomendaciones personalizadas.',
            'beneficios': ['Análisis personalizado', 'Recomendaciones inteligentes', 'Mejor control financiero'],
            'accion': 'Ir a Mis Finanzas',
            'link': 'finanzas.html',
            'completada': False,
            'progreso': 0,
            'ahorro_potencial': 0
        })
        return jsonify(recomendaciones), 200

    # Calcular totales
    total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
    total_gastos = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')
    balance = total_ingresos - total_gastos

    # Gastos por categoría
    gastos_categoria = defaultdict(float)
    for t in transacciones:
        if t.tipo == 'gasto':
            nombre_cat = t.categoria.nombre if t.categoria else 'Otros'
            gastos_categoria[nombre_cat] += float(t.monto)

    # ============================================
    # RECOMENDACIONES BASADAS EN DATOS
    # ============================================

    # 1. Balance negativo
    if balance < 0:
        recomendaciones.append({
            'id': 2,
            'tipo': 'alerta',
            'prioridad': 'Alta',
            'icono': '🚨',
            'titulo': 'Tu balance es negativo',
            'descripcion': f'Estás gastando más de lo que ingresas. Tu balance actual es -${abs(balance):,.0f}. Revisa tus gastos y busca reducir los no esenciales.',
            'beneficios': ['Mejorar balance mensual', 'Evitar deudas innecesarias', 'Estabilidad financiera'],
            'accion': 'Ver mis finanzas',
            'link': 'finanzas.html',
            'completada': False,
            'progreso': 0,
            'ahorro_potencial': abs(balance) * 0.3
        })

    # 2. Balance positivo — sugerir ahorro
    if balance > 0:
        ahorro_sugerido = balance * 0.20
        recomendaciones.append({
            'id': 3,
            'tipo': 'exito',
            'prioridad': 'Media',
            'icono': '💰',
            'titulo': '¡Tienes balance positivo!',
            'descripcion': f'Tu balance es ${balance:,.0f}. Podrías ahorrar el 20% de tu excedente, es decir ${ahorro_sugerido:,.0f} mensuales.',
            'beneficios': ['Construir patrimonio', 'Preparación para emergencias', 'Libertad financiera'],
            'accion': 'Crear meta de ahorro',
            'link': 'perfil.html',
            'completada': False,
            'progreso': 0,
            'ahorro_potencial': ahorro_sugerido
        })

    # 3. Categoría con más gastos
    if gastos_categoria:
        cat_mayor = max(gastos_categoria, key=gastos_categoria.get)
        monto_mayor = gastos_categoria[cat_mayor]
        porcentaje = (monto_mayor / total_gastos * 100) if total_gastos > 0 else 0
        if porcentaje > 30:
            ahorro_potencial = monto_mayor * 0.15
            recomendaciones.append({
                'id': 4,
                'tipo': 'advertencia',
                'prioridad': 'Media',
                'icono': '📊',
                'titulo': f'Alto gasto en {cat_mayor}',
                'descripcion': f'El {porcentaje:.0f}% de tus gastos van a {cat_mayor} (${monto_mayor:,.0f}). Considera reducir este gasto en un 15-20%.',
                'beneficios': ['Reducir gastos innecesarios', 'Mejor distribución del presupuesto', 'Más ahorros disponibles'],
                'accion': 'Ver mis gastos',
                'link': 'finanzas.html',
                'completada': False,
                'progreso': 0,
                'ahorro_potencial': ahorro_potencial
            })

    # 4. Sin ingresos registrados
    if total_ingresos == 0:
        recomendaciones.append({
            'id': 5,
            'tipo': 'info',
            'prioridad': 'Alta',
            'icono': '💼',
            'titulo': 'No tienes ingresos registrados',
            'descripcion': 'Registra tus ingresos para tener un análisis completo de tus finanzas y recibir mejores recomendaciones.',
            'beneficios': ['Análisis completo', 'Recomendaciones precisas', 'Mejor planificación'],
            'accion': 'Registrar ingreso',
            'link': 'finanzas.html',
            'completada': False,
            'progreso': 0,
            'ahorro_potencial': 0
        })

    # 5. Regla 50/30/20
    if total_ingresos > 0:
        porcentaje_gasto = (total_gastos / total_ingresos) * 100
        if porcentaje_gasto > 80:
            recomendaciones.append({
                'id': 6,
                'tipo': 'advertencia',
                'prioridad': 'Alta',
                'icono': '⚠️',
                'titulo': 'Gastas más del 80% de tus ingresos',
                'descripcion': f'Estás usando el {porcentaje_gasto:.0f}% de tus ingresos en gastos. La regla 50/30/20 recomienda no gastar más del 80% para poder ahorrar.',
                'beneficios': ['Equilibrio financiero', 'Capacidad de ahorro', 'Reducción de estrés financiero'],
                'accion': 'Ver simulador',
                'link': 'simulador.html',
                'completada': False,
                'progreso': 0,
                'ahorro_potencial': total_gastos * 0.1
            })
        elif porcentaje_gasto < 50:
            recomendaciones.append({
                'id': 7,
                'tipo': 'exito',
                'prioridad': 'Baja',
                'icono': '🌟',
                'titulo': '¡Excelente control financiero!',
                'descripcion': f'Solo usas el {porcentaje_gasto:.0f}% de tus ingresos en gastos. Considera invertir el excedente para hacer crecer tu dinero.',
                'beneficios': ['Oportunidades de inversión', 'Crecimiento del patrimonio', 'Mayor seguridad financiera'],
                'accion': 'Ver simulador de inversiones',
                'link': 'simulador.html',
                'completada': False,
                'progreso': 0,
                'ahorro_potencial': 0
            })

    # 6. Fondo de emergencia
    if total_ingresos > 0 and balance > 0:
        fondo_recomendado = total_ingresos * 3
        recomendaciones.append({
            'id': 8,
            'tipo': 'info',
            'prioridad': 'Media',
            'icono': '🛡️',
            'titulo': 'Construye tu fondo de emergencia',
            'descripcion': f'Se recomienda tener un fondo de emergencia de al menos 3 meses de ingresos (${fondo_recomendado:,.0f}). Crea una meta de ahorro para esto.',
            'beneficios': ['Protección contra emergencias', 'Tranquilidad financiera', 'Independencia económica'],
            'accion': 'Crear meta',
            'link': 'perfil.html',
            'completada': False,
            'progreso': 0,
            'ahorro_potencial': total_ingresos * 0.1
        })

    # 7. Simulador
    recomendaciones.append({
        'id': 9,
        'tipo': 'info',
        'prioridad': 'Baja',
        'icono': '📈',
        'titulo': 'Simula el crecimiento de tu dinero',
        'descripcion': 'Usa el simulador de FinanBot para ver cómo crecería tu dinero con diferentes tipos de inversión sin usar dinero real.',
        'beneficios': ['Aprender sobre inversiones', 'Tomar decisiones informadas', 'Planificación financiera'],
        'accion': 'Ir al simulador',
        'link': 'simulador.html',
        'completada': False,
        'progreso': 0,
        'ahorro_potencial': 0
    })

    return jsonify(recomendaciones), 200