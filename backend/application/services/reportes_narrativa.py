def resumen_financiero(
    ingresos: float,
    gastos: float,
    balance: float,
    numero_movimientos: int,
    categoria_mayor: str | None = None,
    monto_categoria_mayor: float = 0,
) -> str:
    texto = (
        f"El informe consolida {numero_movimientos} movimientos registrados: "
        f"${ingresos:,.0f} en ingresos y ${gastos:,.0f} en gastos. "
    )
    if balance > 0:
        texto += f"El balance es favorable, con un saldo de ${balance:,.0f}. "
    elif balance < 0:
        texto += f"Los gastos superan los ingresos por ${abs(balance):,.0f}. "
    else:
        texto += "Los ingresos y los gastos registrados se encuentran equilibrados. "

    if categoria_mayor and gastos > 0:
        participacion = monto_categoria_mayor / gastos * 100
        texto += (
            f"La categoría con mayor gasto es {categoria_mayor}, con "
            f"${monto_categoria_mayor:,.0f} ({participacion:.1f}% del total de gastos)."
        )
    elif gastos == 0:
        texto += "No se registraron gastos en los movimientos incluidos."
    return texto


def resumen_mensual(nombre_mes: str, anio: int, datos: dict) -> str:
    ingresos = datos['total_ingresos']
    gastos = datos['total_gastos']
    balance = datos['balance']
    movimientos = len(datos['ingresos']) + len(datos['gastos'])

    texto = (
        f"Durante {nombre_mes} de {anio} se registraron {movimientos} movimientos, "
        f"con ingresos por ${ingresos:,.0f} y gastos por ${gastos:,.0f}. "
    )
    if balance > 0:
        texto += f"El mes cerró con un saldo favorable de ${balance:,.0f}. "
    elif balance < 0:
        texto += f"Los gastos superaron los ingresos del mes por ${abs(balance):,.0f}. "
    else:
        texto += "Los ingresos y los gastos del mes quedaron equilibrados. "

    categoria = datos['cat_mayor']
    if categoria and gastos > 0:
        monto = datos['cat_gastos'][categoria]
        participacion = monto / gastos * 100
        texto += (
            f"El mayor gasto se concentró en {categoria}: "
            f"${monto:,.0f}, equivalente al {participacion:.1f}% de los gastos."
        )
    elif gastos == 0:
        texto += "No se registraron gastos durante el mes."
    return texto


def resumen_simulacion(
    nombre_tipo: str,
    plazo_texto: str,
    capital: float,
    aporte_mensual: float,
    total_invertido: float,
    valor_final: float,
    ganancia: float,
    retencion: float,
    saldo_neto: float,
    tasa: float,
) -> str:
    texto = (
        f"Esta proyección de {nombre_tipo} considera un capital inicial de "
        f"${capital:,.0f}"
    )
    if aporte_mensual > 0:
        texto += f" y aportes mensuales de ${aporte_mensual:,.0f}"
    texto += (
        f" durante {plazo_texto}. El total aportado sería de ${total_invertido:,.0f}; "
        f"con una tasa anual del {tasa:g}%, el valor proyectado es "
        f"${valor_final:,.0f} y la ganancia bruta estimada es ${ganancia:,.0f}. "
        f"Después de la retención estimada de ${retencion:,.0f}, el saldo neto "
        f"proyectado sería ${saldo_neto:,.0f}. Los resultados son estimaciones, "
        "no garantizan rendimientos y no incluyen comisiones ni cambios en las tasas."
    )
    return texto
