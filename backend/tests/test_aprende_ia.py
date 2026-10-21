import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.aprende as aprende


def test_tutor_de_aprende_consulta_la_ia_sin_acciones_de_cuenta(monkeypatch):
    recibido = {}

    class FinanBotFalso:
        def responder_con_acciones(self, mensaje, ctx, accion):
            recibido.update(mensaje=mensaje, ctx=ctx, accion=accion)
            return 'Explicación educativa', [{'tipo': 'no_ejecutada'}]

    monkeypatch.setattr(aprende, 'FinanBotIA', FinanBotFalso)
    resultado = aprende.tutor_ia(aprende.PreguntaAprendizaje(pregunta='  interés compuesto  '))

    assert resultado == {'respuesta': 'Explicación educativa'}
    assert 'interés compuesto' in recibido['mensaje']
    assert recibido['ctx'] is None
    assert recibido['accion'] is None


def test_tutor_de_aprende_rechaza_pregunta_vacia():
    with pytest.raises(HTTPException) as error:
        aprende.tutor_ia(aprende.PreguntaAprendizaje(pregunta='   '))

    assert error.value.status_code == 400
