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
            'tipo': 'info',
            'icono': '📝',
            'titulo': 'Empieza a registrar tus finanzas',
            'descripcion': 'Aún no tienes transacciones registradas. Comienza registrando tus ingresos y gastos para recibir recomendaciones personalizadas.',
            'accion': 'Ir a Mis Finanzas',
            'link': 'finanzas.html'
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
            'tipo': 'alerta',
            'icono': '🚨',
            'titulo': 'Tu balance es negativo',
            'descripcion': f'Estás gastando más de lo que ingresas. Tu balance actual es -${abs(balance):,.0f}. Revisa tus gastos y busca reducir los no esenciales.',
            'accion': 'Ver mis finanzas',
            'link': 'finanzas.html'
        })

    # 2. Balance positivo — sugerir ahorro
    if balance > 0:
        ahorro_sugerido = balance * 0.20
        recomendaciones.append({
            'tipo': 'exito',
            'icono': '💰',
            'titulo': '¡Tienes balance positivo!',
            'descripcion': f'Tu balance es ${balance:,.0f}. Podrías ahorrar el 20% de tu excedente, es decir ${ahorro_sugerido:,.0f} mensuales.',
            'accion': 'Crear meta de ahorro',
            'link': 'perfil.html'
        })

    # 3. Categoría con más gastos
    if gastos_categoria:
        cat_mayor = max(gastos_categoria, key=gastos_categoria.get)
        monto_mayor = gastos_categoria[cat_mayor]
        porcentaje = (monto_mayor / total_gastos * 100) if total_gastos > 0 else 0
        if porcentaje > 30:
            recomendaciones.append({
                'tipo': 'advertencia',
                'icono': '📊',
                'titulo': f'Alto gasto en {cat_mayor}',
                'descripcion': f'El {porcentaje:.0f}% de tus gastos van a {cat_mayor} (${monto_mayor:,.0f}). Considera reducir este gasto en un 15-20%.',
                'accion': 'Ver mis gastos',
                'link': 'finanzas.html'
            })

    # 4. Sin ingresos registrados
    if total_ingresos == 0:
        recomendaciones.append({
            'tipo': 'info',
            'icono': '💼',
            'titulo': 'No tienes ingresos registrados',
            'descripcion': 'Registra tus ingresos para tener un análisis completo de tus finanzas y recibir mejores recomendaciones.',
            'accion': 'Registrar ingreso',
            'link': 'finanzas.html'
        })

    # 5. Regla 50/30/20
    if total_ingresos > 0:
        porcentaje_gasto = (total_gastos / total_ingresos) * 100
        if porcentaje_gasto > 80:
            recomendaciones.append({
                'tipo': 'advertencia',
                'icono': '⚠️',
                'titulo': 'Gastas más del 80% de tus ingresos',
                'descripcion': f'Estás usando el {porcentaje_gasto:.0f}% de tus ingresos en gastos. La regla 50/30/20 recomienda no gastar más del 80% para poder ahorrar.',
                'accion': 'Ver simulador',
                'link': 'simulador.html'
            })
        elif porcentaje_gasto < 50:
            recomendaciones.append({
                'tipo': 'exito',
                'icono': '🌟',
                'titulo': '¡Excelente control financiero!',
                'descripcion': f'Solo usas el {porcentaje_gasto:.0f}% de tus ingresos en gastos. Considera invertir el excedente para hacer crecer tu dinero.',
                'accion': 'Ver simulador de inversiones',
                'link': 'simulador.html'
            })

    # 6. Fondo de emergencia
    if total_ingresos > 0 and balance > 0:
        fondo_recomendado = total_ingresos * 3
        recomendaciones.append({
            'tipo': 'info',
            'icono': '🚨',
            'titulo': 'Construye tu fondo de emergencia',
            'descripcion': f'Se recomienda tener un fondo de emergencia de al menos 3 meses de ingresos (${fondo_recomendado:,.0f}). Crea una meta de ahorro para esto.',
            'accion': 'Crear meta',
            'link': 'perfil.html'
        })

    # 7. Simulador
    recomendaciones.append({
        'tipo': 'info',
        'icono': '📈',
        'titulo': 'Simula el crecimiento de tu dinero',
        'descripcion': 'Usa el simulador de FinanBot para ver cómo crecería tu dinero con diferentes tipos de inversión sin usar dinero real.',
        'accion': 'Ir al simulador',
        'link': 'simulador.html'
    })

    return jsonify(recomendaciones), 200