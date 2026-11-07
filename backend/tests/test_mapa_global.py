import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.append(str(Path(__file__).resolve().parents[1]))

import routes.transacciones as transacciones


def test_lugares_cercanos_divide_busqueda_que_cruza_antimeridiano(monkeypatch):
    consultas = []
    monkeypatch.setattr(transacciones, '_LUGARES_CACHE', {})

    def consultar(s, w, n, e):
        consultas.append((s, w, n, e))
        return []

    monkeypatch.setattr(transacciones, '_consultar_overpass', consultar)

    resultado = transacciones.lugares_cercanos(
        s=-0.01, w=179.99, n=0.01, e=-179.99, usuario_id='1',
    )

    assert resultado == []
    assert len(consultas) == 2
    assert consultas[0][1] < 180 and consultas[0][3] == 180
    assert consultas[1][1] == -180 and consultas[1][3] < -179


def test_lugares_cercanos_acepta_coordenadas_globales(monkeypatch):
    consultas = []
    monkeypatch.setattr(transacciones, '_LUGARES_CACHE', {})
    monkeypatch.setattr(
        transacciones, '_consultar_overpass',
        lambda s, w, n, e: consultas.append((s, w, n, e)) or [],
    )

    resultado = transacciones.lugares_cercanos(
        s=51.50, w=-0.13, n=51.51, e=-0.12, usuario_id='1',
    )

    assert resultado == []
    assert len(consultas) == 1
    assert consultas[0][1] < 0 and consultas[0][3] < 0


def test_formatear_lugar_conserva_coordenadas_cero():
    lugar = transacciones._formatear_lugar({
        'type': 'node',
        'id': 42,
        'lat': 0,
        'lon': 0,
        'tags': {'name': 'Banco del Ecuador', 'amenity': 'bank'},
    })

    assert lugar['latitud'] == 0
    assert lugar['longitud'] == 0


def test_formatear_lugar_descarta_coordenadas_invalidas():
    lugar = transacciones._formatear_lugar({
        'type': 'node',
        'id': 42,
        'lat': 91,
        'lon': 0,
        'tags': {'name': 'Banco', 'amenity': 'bank'},
    })

    assert lugar is None


@pytest.mark.parametrize(
    ('s', 'w', 'n', 'e'),
    [
        (-91, 0, 0, 1),
        (0, -181, 1, 0),
        (0, 0, 1, 181),
        (0, 1, 1, 1),
        (0, 0, 1, 1),
    ],
)
def test_lugares_cercanos_rechaza_limites_invalidos(s, w, n, e):
    with pytest.raises(HTTPException) as error:
        transacciones.lugares_cercanos(s=s, w=w, n=n, e=e, usuario_id='1')

    assert error.value.status_code == 400
