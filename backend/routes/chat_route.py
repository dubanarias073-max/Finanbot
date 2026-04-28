# routes/chat_route.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from finanbot_ia import FinanBotIA
from models import Transaccion, MetaAhorro, Usuario

chat_bp = Blueprint('chat_bp', __name__)

# Una instancia por usuario
sesiones = {}

@chat_bp.route('/mensaje', methods=['POST'])
def mensaje():
    # Intentar obtener usuario autenticado
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
    if len(mensaje_usuario) > 500:
        return jsonify({'error': 'Mensaje demasiado largo'}), 400

    # Obtener o crear sesión del bot
    session_key = usuario_id or 'invitado'
    if session_key not in sesiones:
        sesiones[session_key] = FinanBotIA()

    bot = sesiones[session_key]

    # Cargar datos financieros del usuario si está autenticado
    contexto_financiero = None
    if usuario_id:
        try:
            transacciones = Transaccion.query.filter_by(usuario_id=int(usuario_id)).all()
            metas = MetaAhorro.query.filter_by(usuario_id=int(usuario_id)).all()
            usuario = Usuario.query.get(int(usuario_id))

            total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
            total_gastos = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')

            from collections import defaultdict
            gastos_cat = defaultdict(float)
            for t in transacciones:
                if t.tipo == 'gasto':
                    gastos_cat[t.categoria.nombre if t.categoria else 'Otros'] += float(t.monto)

            cat_mayor = max(gastos_cat, key=gastos_cat.get) if gastos_cat else None

            contexto_financiero = {
                'nombre': usuario.nombre if usuario else 'Usuario',
                'total_ingresos': total_ingresos,
                'total_gastos': total_gastos,
                'balance': total_ingresos - total_gastos,
                'num_transacciones': len(transacciones),
                'num_metas': len(metas),
                'categoria_mayor_gasto': cat_mayor,
                'monto_mayor_gasto': gastos_cat[cat_mayor] if cat_mayor else 0
            }
        except Exception as e:
            print(f"Error cargando contexto: {e}")

    respuesta, acciones = bot.responder_con_acciones(mensaje_usuario, contexto_financiero)

    return jsonify({
        'respuesta': respuesta,
        'acciones': acciones,
        'estado': 'ok'
    }), 200