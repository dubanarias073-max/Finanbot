from __future__ import annotations

from io import BytesIO
import math
import textwrap

from PIL import Image, ImageDraw, ImageFont


COLORES = ['#6D5BD0', '#0F9D9A', '#2E9D62', '#E69728']


def normalizar_graficos(datos) -> list[dict]:
    if not isinstance(datos, list):
        return []
    if len(datos) > 4:
        raise ValueError('Un documento puede incluir hasta 4 gráficos.')

    resultado = []
    for grafico in datos:
        if not isinstance(grafico, dict):
            raise ValueError('La estructura de un gráfico no es válida.')
        tipo = grafico.get('tipo')
        titulo = str(grafico.get('titulo') or '').strip()
        etiquetas = grafico.get('etiquetas')
        series = grafico.get('series')
        if tipo not in {'barras', 'lineas', 'circular'}:
            raise ValueError('El tipo de gráfico no es compatible.')
        if not titulo or len(titulo) > 120:
            raise ValueError('El título de un gráfico no es válido.')
        if not isinstance(etiquetas, list) or not 1 <= len(etiquetas) <= 16:
            raise ValueError('Un gráfico debe tener entre 1 y 16 etiquetas.')
        etiquetas_limpias = [str(etiqueta).strip()[:60] for etiqueta in etiquetas]
        if any(not etiqueta for etiqueta in etiquetas_limpias):
            raise ValueError('Las etiquetas del gráfico no pueden estar vacías.')
        if not isinstance(series, list) or not 1 <= len(series) <= 4:
            raise ValueError('Un gráfico debe tener entre 1 y 4 series.')
        if tipo == 'circular' and len(series) != 1:
            raise ValueError('Un gráfico circular debe tener una sola serie.')

        series_limpias = []
        for serie in series:
            if not isinstance(serie, dict):
                raise ValueError('La estructura de una serie no es válida.')
            nombre = str(serie.get('nombre') or '').strip()
            valores = serie.get('valores')
            if not nombre or len(nombre) > 60:
                raise ValueError('El nombre de una serie no es válido.')
            if not isinstance(valores, list) or len(valores) != len(etiquetas_limpias):
                raise ValueError('Los valores deben corresponder a las etiquetas.')
            if any(
                isinstance(valor, bool) or not isinstance(valor, (int, float))
                or not math.isfinite(valor) or abs(valor) > 1e15
                for valor in valores
            ):
                raise ValueError('Los valores del gráfico deben ser números válidos.')
            if tipo == 'circular' and any(valor < 0 for valor in valores):
                raise ValueError('Un gráfico circular no admite valores negativos.')
            series_limpias.append({
                'nombre': nombre,
                'valores': [float(valor) for valor in valores],
            })
        if tipo == 'circular' and sum(series_limpias[0]['valores']) <= 0:
            raise ValueError('El gráfico circular debe incluir valores positivos.')

        resultado.append({
            'tipo': tipo,
            'titulo': titulo,
            'etiquetas': etiquetas_limpias,
            'series': series_limpias,
        })
    return resultado


def renderizar_grafico(grafico: dict) -> BytesIO:
    grafico = normalizar_graficos([grafico])[0]
    ancho, alto = 1100, 560
    imagen = Image.new('RGB', (ancho, alto), '#FFFFFF')
    dibujo = ImageDraw.Draw(imagen)
    fuente = ImageFont.load_default()

    dibujo.rounded_rectangle((8, 8, ancho - 8, alto - 8), radius=20, outline='#E6E2F0', width=2)
    dibujo.rounded_rectangle((8, 8, ancho - 8, 19), radius=5, fill=COLORES[0])
    dibujo.text((48, 42), grafico['titulo'], fill='#24164B', font=fuente)

    if grafico['tipo'] == 'circular':
        _dibujar_circular(dibujo, fuente, grafico)
    else:
        _dibujar_ejes(dibujo, fuente, grafico, ancho, alto)

    salida = BytesIO()
    imagen.save(salida, format='PNG', optimize=True)
    salida.seek(0)
    return salida


def _dibujar_ejes(dibujo, fuente, grafico: dict, ancho: int, alto: int) -> None:
    izquierda, derecha, arriba, abajo = 82, ancho - 54, 140, alto - 105
    valores = [valor for serie in grafico['series'] for valor in serie['valores']]
    minimo = min(0.0, min(valores))
    maximo = max(0.0, max(valores))
    if maximo == minimo:
        maximo = minimo + 1
    rango = maximo - minimo
    base_y = abajo - (0 - minimo) / rango * (abajo - arriba)
    for indice in range(5):
        y = arriba + indice * (abajo - arriba) / 4
        valor = maximo - indice * rango / 4
        dibujo.line((izquierda, y, derecha, y), fill='#E9E6F1', width=2)
        dibujo.text((18, y - 7), f'{valor:,.0f}', fill='#77718C', font=fuente)

    cantidad = len(grafico['etiquetas'])
    paso = (derecha - izquierda) / cantidad
    colores = COLORES[:len(grafico['series'])]
    if grafico['tipo'] == 'barras':
        ancho_barra = min(42, paso * 0.72 / len(grafico['series']))
        for serie_indice, serie in enumerate(grafico['series']):
            for indice, valor in enumerate(serie['valores']):
                centro = izquierda + paso * (indice + 0.5)
                x1 = centro + (serie_indice - (len(grafico['series']) - 1) / 2) * ancho_barra
                y = abajo - (valor - minimo) / rango * (abajo - arriba)
                dibujo.rounded_rectangle(
                    (x1 - ancho_barra * 0.4, min(y, base_y), x1 + ancho_barra * 0.4, max(y, base_y)),
                    radius=5,
                    fill=colores[serie_indice],
                )
    else:
        for serie_indice, serie in enumerate(grafico['series']):
            puntos = [
                (
                    izquierda + paso * (indice + 0.5),
                    abajo - (valor - minimo) / rango * (abajo - arriba),
                )
                for indice, valor in enumerate(serie['valores'])
            ]
            if len(puntos) > 1:
                dibujo.line(puntos, fill=colores[serie_indice], width=5, joint='curve')
            for x, y in puntos:
                dibujo.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colores[serie_indice])

    for indice, etiqueta in enumerate(grafico['etiquetas']):
        texto = textwrap.shorten(etiqueta, width=15, placeholder='…')
        dibujo.text((izquierda + paso * (indice + 0.5) - 25, abajo + 22), texto, fill='#514B63', font=fuente)

    for indice, serie in enumerate(grafico['series']):
        x = izquierda + (indice % 3) * 290
        y = 95 + (indice // 3) * 24
        dibujo.rounded_rectangle((x, y, x + 18, y + 18), radius=4, fill=colores[indice])
        nombre = textwrap.shorten(serie['nombre'], width=24, placeholder='…')
        dibujo.text((x + 26, y + 1), nombre, fill='#514B63', font=fuente)


def _dibujar_circular(dibujo, fuente, grafico: dict) -> None:
    valores = grafico['series'][0]['valores']
    total = sum(valores)
    caja = (70, 125, 480, 535)
    inicio = -90
    for indice, valor in enumerate(valores):
        fin = inicio + 360 * valor / total
        dibujo.pieslice(caja, inicio, fin, fill=COLORES[indice % len(COLORES)], outline='#FFFFFF', width=3)
        inicio = fin

    espacio = min(46, 360 / len(valores))
    for indice, (etiqueta, valor) in enumerate(zip(grafico['etiquetas'], valores)):
        y = 145 + indice * espacio
        dibujo.rounded_rectangle((560, y, 580, y + 20), radius=4, fill=COLORES[indice % len(COLORES)])
        nombre = textwrap.shorten(etiqueta, width=32, placeholder='…')
        dibujo.text((596, y + 1), f'{nombre}  ·  {valor:,.0f} ({valor / total:.1%})',
                    fill='#514B63', font=fuente)
