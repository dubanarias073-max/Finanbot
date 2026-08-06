import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.perfil import PerfilUpdate


def test_perfil_update_accepts_fecha_salario():
    payload = PerfilUpdate(nombre='Ana', ingreso_mensual=2500000, fecha_salario='2026-08-20')

    assert payload.nombre == 'Ana'
    assert payload.ingreso_mensual == 2500000
    assert payload.fecha_salario == '2026-08-20'
