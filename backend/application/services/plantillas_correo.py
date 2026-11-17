# application/services/plantillas_correo.py
# ══════════════════════════════════════════════════════════════════
#  Plantilla HTML de los correos de FinanBot (registro, nuevo inicio
#  de sesión, recuperación de contraseña).
#
#  Diseño: tarjeta blanca con barra de color arriba, título con la marca,
#  saludo, texto, botón principal y una nota gris al pie con el enlace
#  de respaldo. Todo con tablas y estilos en línea, porque Gmail y
#  Outlook ignoran las hojas de estilo y muchas propiedades modernas.
# ══════════════════════════════════════════════════════════════════
from __future__ import annotations

import html
from dataclasses import dataclass

MORADO = '#6D5BD0'
MORADO_CLARO = '#8B5CF6'
VERDE = '#10B981'
ROJO = '#EF4444'
TEXTO = '#1F1D3A'
TEXTO_SUAVE = '#4B4F63'
GRIS = '#8A90A6'
FONDO = '#F3F1FF'
FUENTE = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


@dataclass
class Boton:
    texto: str
    url: str
    color: str = MORADO
    contorno: bool = False      # True = botón secundario (borde de color, fondo blanco)


def _e(texto: str) -> str:
    return html.escape(str(texto or ''), quote=True)


def _boton(b: Boton) -> str:
    fondo = '#FFFFFF' if b.contorno else b.color
    color_texto = b.color if b.contorno else '#FFFFFF'
    return (
        f'<a href="{_e(b.url)}" target="_blank" '
        f'style="display:inline-block;margin:6px;padding:14px 28px;border-radius:12px;'
        f'background:{fondo};border:2px solid {b.color};color:{color_texto};'
        f'font-family:{FUENTE};font-size:15px;font-weight:700;text-decoration:none;">'
        f'{_e(b.texto)}</a>'
    )


def correo_html(
    *,
    titulo: str,
    nombre: str | None,
    parrafos: list[str],
    botones: list[Boton] | None = None,
    codigo: str | None = None,
    detalles: list[tuple[str, str]] | None = None,
    nota: str | None = None,
    enlace_respaldo: str | None = None,
    preencabezado: str = '',
) -> str:
    """Arma el HTML del correo.

    parrafos: texto plano; se permite **negrita** con doble asterisco.
    detalles: filas (etiqueta, valor) en un recuadro, ej. fecha o dispositivo.
    codigo: código de verificación grande y fácil de copiar.
    """
    def con_negritas(texto: str) -> str:
        partes = _e(texto).split('**')
        return ''.join(f'<strong style="color:{TEXTO};">{p}</strong>' if i % 2 else p
                       for i, p in enumerate(partes))

    saludo = (f'Hola, <strong style="color:{TEXTO};">{_e(nombre)}</strong>:' if nombre else 'Hola:')
    cuerpo = ''.join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.65;color:{TEXTO_SUAVE};">'
        f'{con_negritas(p)}</p>' for p in parrafos
    )

    bloque_codigo = ''
    if codigo:
        bloque_codigo = (
            f'<div style="margin:22px 0;text-align:center;">'
            f'<div style="display:inline-block;padding:14px 26px;border-radius:12px;'
            f'background:{FONDO};border:1px dashed {MORADO_CLARO};font-family:Consolas,Menlo,monospace;'
            f'font-size:30px;font-weight:700;letter-spacing:8px;color:{MORADO};">{_e(codigo)}</div></div>'
        )

    bloque_detalles = ''
    if detalles:
        filas = ''.join(
            f'<tr><td style="padding:6px 0;font-size:13px;color:{GRIS};width:120px;vertical-align:top;">{_e(k)}</td>'
            f'<td style="padding:6px 0;font-size:14px;color:{TEXTO};font-weight:600;">{_e(v)}</td></tr>'
            for k, v in detalles
        )
        bloque_detalles = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:6px 0 18px;padding:12px 16px;background:{FONDO};border-radius:12px;">'
            f'{filas}</table>'
        )

    bloque_botones = ''
    if botones:
        bloque_botones = (
            f'<div style="margin:24px 0 8px;text-align:center;">{"".join(_boton(b) for b in botones)}</div>'
        )

    pie = ''
    if nota or enlace_respaldo:
        pie = f'<div style="margin-top:22px;font-size:12.5px;line-height:1.6;color:{GRIS};">'
        if nota:
            pie += f'<p style="margin:0 0 6px;">{con_negritas(nota)}</p>'
        if enlace_respaldo:
            pie += (
                '<p style="margin:0;">¿Tu aplicación de correo no abre el botón? Copia y pega esta dirección en tu navegador:</p>'
                f'<p style="margin:4px 0 0;word-break:break-all;"><a href="{_e(enlace_respaldo)}" '
                f'style="color:{MORADO};">{_e(enlace_respaldo)}</a></p>'
            )
        pie += '</div>'

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{_e(titulo)}</title>
</head>
<body style="margin:0;padding:0;background:{FONDO};">
<span style="display:none;max-height:0;overflow:hidden;opacity:0;">{_e(preencabezado)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FONDO};">
<tr><td align="center" style="padding:32px 14px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="max-width:560px;background:#FFFFFF;border-radius:18px;overflow:hidden;
                box-shadow:0 8px 30px rgba(76,61,180,0.12);">
    <tr><td style="height:6px;line-height:6px;font-size:0;background:{MORADO};
                   background-image:linear-gradient(90deg,{MORADO},{MORADO_CLARO},#C084FC);">&nbsp;</td></tr>
    <tr><td style="padding:30px 34px 32px;font-family:{FUENTE};">
      <h1 style="margin:0 0 18px;font-size:24px;line-height:1.3;color:{TEXTO};font-weight:800;">
        <span style="color:{MORADO};">FinanBot</span> — {_e(titulo)}
      </h1>
      <p style="margin:0 0 14px;font-size:15px;line-height:1.65;color:{TEXTO_SUAVE};">{saludo}</p>
      {cuerpo}
      {bloque_detalles}
      {bloque_codigo}
      {bloque_botones}
      {pie}
    </td></tr>
  </table>
  <p style="margin:18px 0 0;font-family:{FUENTE};font-size:11.5px;color:{GRIS};">
    Este es un correo automático de FinanBot · Tus finanzas, más claras.
  </p>
</td></tr>
</table>
</body>
</html>"""


def describir_dispositivo(user_agent: str | None) -> str:
    """'Chrome en Windows', 'Safari en iPhone'… a partir del User-Agent."""
    ua = (user_agent or '').lower()
    if not ua:
        return 'Dispositivo desconocido'
    if 'edg/' in ua:
        navegador = 'Edge'
    elif 'opr/' in ua or 'opera' in ua:
        navegador = 'Opera'
    elif 'firefox' in ua:
        navegador = 'Firefox'
    elif 'chrome' in ua or 'crios' in ua:
        navegador = 'Chrome'
    elif 'safari' in ua:
        navegador = 'Safari'
    else:
        navegador = 'Navegador'
    if 'iphone' in ua:
        sistema = 'iPhone'
    elif 'ipad' in ua:
        sistema = 'iPad'
    elif 'android' in ua:
        sistema = 'Android'
    elif 'windows' in ua:
        sistema = 'Windows'
    elif 'mac os' in ua or 'macintosh' in ua:
        sistema = 'Mac'
    elif 'linux' in ua:
        sistema = 'Linux'
    else:
        sistema = 'otro sistema'
    return f'{navegador} en {sistema}'
