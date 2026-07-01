import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from finanbot_ia import FinanBotIA
from routes.aprende import ENCICLOPEDIA


def test_reemplaza_signo_porcentaje_por_texto():
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones("¿Cuánto es 20% de 100?", None, None)
    assert "20 porcentaje" in respuesta
    assert "%" not in respuesta


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
