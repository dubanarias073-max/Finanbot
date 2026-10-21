import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from application.services.reportes_narrativa import (
    resumen_financiero,
    resumen_mensual,
    resumen_simulacion,
)


def test_resumen_financiero_redacta_balance_y_categoria_principal():
    texto = resumen_financiero(2_000_000, 1_200_000, 800_000, 14, 'Arriendo', 600_000)

    assert '14 movimientos registrados' in texto
    assert 'saldo de $800,000' in texto
    assert 'Arriendo' in texto
    assert '50.0%' in texto


def test_resumen_mensual_informa_saldo_negativo_y_gasto_principal():
    datos = {
        'total_ingresos': 800_000,
        'total_gastos': 1_000_000,
        'balance': -200_000,
        'ingresos': [object()],
        'gastos': [object(), object()],
        'cat_mayor': 'Transporte',
        'cat_gastos': {'Transporte': 250_000},
    }

    texto = resumen_mensual('Marzo', 2026, datos)

    assert 'Marzo de 2026' in texto
    assert 'superaron los ingresos del mes por $200,000' in texto
    assert 'Transporte' in texto


def test_resumen_simulacion_advierte_que_es_una_proyeccion():
    texto = resumen_simulacion(
        'CDT', '1 año', 1_000_000, 50_000, 1_600_000,
        1_700_000, 100_000, 4_000, 1_696_000, 10,
    )

    assert 'aportes mensuales de $50,000' in texto
    assert 'saldo neto proyectado sería $1,696,000' in texto
    assert 'no garantizan rendimientos' in texto
