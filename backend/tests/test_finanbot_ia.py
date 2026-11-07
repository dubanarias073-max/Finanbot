import sys
from datetime import timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from finanbot_ia import FinanBotIA
import finanbot_ia_2
from routes.aprende import ENCICLOPEDIA
from routes.chat_route import extraer_categoria
from routes.recomendaciones import filtrar_transacciones_recientes
from timezone import bogota_today


def test_conserva_signo_porcentaje_en_calculadora():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones("¿Cuánto es 20% de 100?", None, None)
    assert "20%" in respuesta
    assert "20 porcentaje" not in respuesta


def test_calcula_descuento_con_frase_natural():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones("un producto vale 2000 al 10% de descuento, cuanto vale el producto?", None, None)
    assert "precio final" in respuesta.lower() or "descuento" in respuesta.lower()
    assert "1800" in respuesta


def test_responde_siempre_con_tupla_en_preguntas_de_conocimiento():
    bot = FinanBotIA()
    respuesta, acciones = bot.responder_con_acciones("¿Qué es un CDT?", None, None)
    assert isinstance(respuesta, str)
    assert isinstance(acciones, list)


def test_ia2_tiene_prioridad_en_conversacion_cuando_esta_disponible(monkeypatch):
    bot = FinanBotIA()
    bot._intencion = 'chat'
    bot._imagenes_actuales = []
    bot._clave_conv = 'conversation-test'
    monkeypatch.setattr(finanbot_ia_2, 'disponible', lambda: True)
    monkeypatch.setattr(
        finanbot_ia_2,
        'responder',
        lambda *args, **kwargs: {
            'respuesta': 'Respuesta desde Gemini.',
            'sugerencias': [],
            'enlaces': [],
            'documento': None,
        },
    )

    respuesta, acciones = bot._sin_accion('¿Cómo puedo organizar mis finanzas?', None)

    assert respuesta == 'Respuesta desde Gemini.'
    assert acciones == []
    assert bot._respuesta_de_ia2 is True


def test_ia2_chat_solicita_y_devuelve_texto_plano(monkeypatch):
    llamada = {}

    def responder_texto(p, sistema, mensajes, imagenes, max_output_tokens, json_mode):
        llamada['sistema'] = sistema
        llamada['json_mode'] = json_mode
        return '¡Hola! ¿En qué puedo ayudarte con tus finanzas?'

    monkeypatch.setattr(
        finanbot_ia_2,
        '_proveedor',
        lambda: {'tipo': 'gemini', 'key': 'test-key', 'modelo': 'gemini-test'},
    )
    monkeypatch.setattr(finanbot_ia_2, '_llamar', responder_texto)

    resultado = finanbot_ia_2.responder(
        'hola',
        None,
        None,
        categorias_gasto=[],
        categorias_ingreso=[],
        ejemplos={},
        rutas={},
    )

    assert resultado['respuesta'] == '¡Hola! ¿En qué puedo ayudarte con tus finanzas?'
    assert llamada['json_mode'] is False
    assert 'No devuelvas JSON' in llamada['sistema']


def test_parsear_chat_extrae_respuesta_y_no_muestra_json_crudo():
    resultado = finanbot_ia_2._parsear(
        '{"respuesta":"Hola, ¿cómo estás?","sugerencias":[]}',
        respuesta_plana=True,
    )

    assert resultado['respuesta'] == 'Hola, ¿cómo estás?'
    assert finanbot_ia_2._parsear(
        '{"mensaje":"respuesta sin el campo esperado"}',
        respuesta_plana=True,
    ) is None


def test_config_gemini_solo_fuerza_json_para_respuestas_estructuradas():
    assert 'responseMimeType' not in finanbot_ia_2._config_gemini(
        'gemini-3.1-flash-lite', False, json_mode=False,
    )
    assert finanbot_ia_2._config_gemini(
        'gemini-3.1-flash-lite', False,
    )['responseMimeType'] == 'application/json'


def test_saludo_enrutado_a_gemini_antes_de_la_bienvenida_ia1(monkeypatch):
    bot = FinanBotIA()
    monkeypatch.setattr(finanbot_ia_2, 'disponible', lambda: True)
    monkeypatch.setattr(
        finanbot_ia_2,
        'responder',
        lambda *args, **kwargs: {
            'respuesta': '¡Hola! Respuesta de Gemini.',
            'sugerencias': [],
            'enlaces': [],
            'documento': None,
        },
    )

    respuesta, _ = bot.responder_con_acciones(
        'hola chat',
        {'nombre': 'Ana'},
        {'tipo': 'bienvenida', 'nombre': 'Ana', 'resumen': {}},
    )

    assert respuesta == '¡Hola! Respuesta de Gemini.'
    assert bot._respuesta_de_ia2 is True


def test_bienvenida_ia1_se_usa_si_gemini_no_esta_disponible(monkeypatch):
    bot = FinanBotIA()
    monkeypatch.setattr(finanbot_ia_2, 'disponible', lambda: False)

    respuesta, _ = bot.responder_con_acciones(
        'hola chat',
        {'nombre': 'Ana'},
        {'tipo': 'bienvenida', 'nombre': 'Ana', 'resumen': {}},
    )

    assert 'Ana' in respuesta
    assert 'Soy **FinanBot**' in respuesta
    assert bot._respuesta_de_ia2 is False


def test_bienvenida_ia1_se_usa_si_gemini_falla(monkeypatch):
    bot = FinanBotIA()
    monkeypatch.setattr(finanbot_ia_2, 'disponible', lambda: True)
    monkeypatch.setattr(finanbot_ia_2, 'responder', lambda *args, **kwargs: None)

    respuesta, _ = bot.responder_con_acciones(
        'hola chat',
        {'nombre': 'Ana'},
        {'tipo': 'bienvenida', 'nombre': 'Ana', 'resumen': {}},
    )

    assert 'Ana' in respuesta
    assert 'Soy **FinanBot**' in respuesta
    assert bot._respuesta_de_ia2 is False


def test_contexto_ia2_incluye_regla_personalizada():
    contexto = finanbot_ia_2._contexto_usuario({
        'nombre': 'Usuario',
        'total_ingresos': 2_000_000,
        'total_gastos': 1_000_000,
        'balance': 1_000_000,
        'ingreso_mensual': 2_000_000,
        'regla_presupuesto': {'nec': 60, 'des': 20, 'aho': 20, 'nombre': 'Ahorradora'},
    })

    assert '60% necesidades, 20% deseos, 20% ahorro' in contexto
    assert '$1.200.000' in contexto


def test_fallback_ia1_usa_regla_personalizada_en_presupuesto():
    bot = FinanBotIA()
    bot._intencion = 'chat'
    bot._imagenes_actuales = []
    respuesta = bot._respuesta_inteligente_contextual(
        '¿Cómo organizo mi presupuesto?',
        {
            'ingreso_mensual': 2_000_000,
            'regla_presupuesto': {
                'nec': 60, 'des': 20, 'aho': 20, 'nombre': 'Ahorradora',
            },
        },
    )

    assert respuesta is not None
    assert '60% para necesidades' in respuesta
    assert '$1.200.000' in respuesta
    assert '50/30/20' not in respuesta


def test_redirige_consulta_ajena_a_finanzas_al_chat_financiero():
    bot = FinanBotIA()
    respuesta, acciones = bot.responder_con_acciones(
        "chat como consigo novia jajaja", None, None
    )

    assert "chat especializado en finanzas personales" in respuesta
    assert "temas ajenos a las finanzas" in respuesta
    assert acciones == []


def test_redirige_concepto_desconocido_a_temas_financieros():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones("¿Qué es la jardinería?", None, None)

    assert "chat especializado en finanzas personales" in respuesta
    assert "Ahorro" in respuesta


def test_respuesta_inteligente_para_mejorar_finanzas():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones("quiero mejorar mis finanzas", None, None)
    assert "primer paso" in respuesta.lower() or "plan" in respuesta.lower()


def test_simulacion_incluye_boton_con_datos_sugeridos():
    bot = FinanBotIA()
    _, acciones = bot.responder_con_acciones("simula 1000000 al 10% por 12 meses", None, None)
    assert any("simulador.html" in (a.get("link") or "") and "capital" in (a.get("link") or "") for a in acciones)


def test_interes_compuesto_responde_de_forma_especifica():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones("quiero calcular el interés compuesto de 1000000 al 10% por 12 meses", None, None)
    assert "compuesto" in respuesta.lower() or "interés compuesto" in respuesta.lower()


def test_aprende_incluye_contexto_de_metas_de_ahorro():
    assert "meta_ahorro" in ENCICLOPEDIA
    assert ENCICLOPEDIA["meta_ahorro"]["categoria"] == "Metas financieras"


def test_filtra_transacciones_de_ultimos_7_dias():
    hoy = bogota_today()
    transacciones = [
        {'fecha': (hoy - timedelta(days=10)).isoformat(), 'monto': 100000},
        {'fecha': (hoy - timedelta(days=2)).isoformat(), 'monto': 50000},
    ]

    filtradas = filtrar_transacciones_recientes(transacciones, dias=7)

    assert len(filtradas) == 1
    assert filtradas[0]['monto'] == 50000


def test_reconoce_categorias_nuevas_para_gastos():
    assert extraer_categoria('gaste 50000 en viaje', 'gasto') == 'Viajes'
    assert extraer_categoria('gaste 20000 en mascota', 'gasto') == 'Mascotas'


def test_registro_de_gasto_incluye_emoji_de_categoria():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones('gaste 50000 en viaje', None, None)
    assert '✈️' in respuesta or '🧾' in respuesta
