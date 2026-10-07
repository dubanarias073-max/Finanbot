# finanbot_ia_2.py
# ══════════════════════════════════════════════════════════════════
#  FinanBot IA 2 — cerebro conversacional de FinanBot
#
#  FinanBot sigue haciendo con sus reglas lo que debe ser exacto
#  (registrar, editar, borrar, calcular IVA/descuentos, metas…).
#  Este módulo se encarga de CONVERSAR: entiende preguntas libres,
#  razona con los datos reales del usuario y propone el siguiente
#  paso con botones que ejecutan los comandos de FinanBot.
#
#  Proveedor (se elige con variables de entorno, el primero que exista):
#    GEMINI_API_KEY      → Google Gemini   (tiene capa GRATIS: aistudio.google.com)
#    GROQ_API_KEY        → Groq / Llama    (tiene capa GRATIS: console.groq.com)
#    ANTHROPIC_API_KEY   → Claude
#    FINANBOT_IA2_BASE_URL (+ FINANBOT_IA2_API_KEY opcional)
#                        → cualquier API compatible con OpenAI, p. ej.
#                          Ollama local y gratis: http://localhost:11434/v1
#  Opcional: FINANBOT_IA2_MODEL para cambiar el modelo.
#
#  Si no hay ninguno configurado, o el proveedor falla, devuelve None
#  y FinanBot responde con sus reglas de siempre (15 s, o 60 s si se
#  agotó el cupo gratis).
# ══════════════════════════════════════════════════════════════════
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import date

TIMEOUT_S = 25
TIMEOUT_POR_MODELO_S = 12      # cuánto se espera a cada modelo Gemini
TIEMPO_MAX_TOTAL_S = 28        # máximo que el usuario espera entre todos los intentos
PAUSA_TRAS_FALLO_S = 15     # segundos usando las reglas después de un fallo
MAX_TURNOS_MEMORIA = 8          # pares usuario/bot que se recuerdan por conversación
MAX_CONVERSACIONES = 500
MAX_PALABRAS_RESPUESTA = 220

_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
          'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

# Memoria corta por conversación: {clave: deque[(rol, texto)]}
_memoria: dict[str, deque] = {}
_memoria_lock = threading.Lock()
# Si un proveedor falla, se pausa un rato para no hacer esperar al usuario en cada mensaje
_pausa_hasta = 0.0

# Google retira modelos cada cierto tiempo (gemini-2.5-flash ya da 404).
# Se prueban en orden y se recuerda el primero que funcione.
# Primero los "lite": son estables, rápidos y casi nunca están saturados.
GEMINI_MODELOS = ['gemini-3.1-flash-lite', 'gemini-2.5-flash-lite',
                  'gemini-flash-latest', 'gemini-3-flash-preview']
_gemini_modelo_ok: str | None = None
_sin_thinking_config: set[str] = set()


# ──────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DEL PROVEEDOR
# ──────────────────────────────────────────────────────────────────

def _proveedor() -> dict | None:
    modelo = os.getenv('FINANBOT_IA2_MODEL')
    if os.getenv('GEMINI_API_KEY'):
        return {'tipo': 'gemini', 'key': os.getenv('GEMINI_API_KEY'),
                'modelo': modelo or _gemini_modelo_ok or GEMINI_MODELOS[0]}
    if os.getenv('GROQ_API_KEY'):
        return {'tipo': 'openai', 'key': os.getenv('GROQ_API_KEY'),
                'url': 'https://api.groq.com/openai/v1/chat/completions',
                'modelo': modelo or 'llama-3.3-70b-versatile'}
    if os.getenv('ANTHROPIC_API_KEY'):
        return {'tipo': 'anthropic', 'key': os.getenv('ANTHROPIC_API_KEY'),
                'modelo': modelo or 'claude-haiku-5-5'}
    if os.getenv('FINANBOT_IA2_BASE_URL'):
        base = os.getenv('FINANBOT_IA2_BASE_URL').rstrip('/')
        return {'tipo': 'openai', 'key': os.getenv('FINANBOT_IA2_API_KEY', 'local'),
                'url': base + '/chat/completions', 'modelo': modelo or 'llama3.1'}
    return None


def disponible() -> bool:
    return _proveedor() is not None and time.time() >= _pausa_hasta


# ──────────────────────────────────────────────────────────────────
#  PROMPT
# ──────────────────────────────────────────────────────────────────

def _prompt_sistema(categorias_gasto, categorias_ingreso, ejemplos: dict, rutas: dict) -> str:
    hoy = date.today()
    cmds = '\n'.join(f'- {v}' for v in ejemplos.values())
    paginas = ', '.join(f'{k} → {v}' for k, v in rutas.items())
    return f"""Eres FinanBot IA 2, el asistente de finanzas personales de una app colombiana hecha por aprendices del SENA.
Hoy es {hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}. Moneda: pesos colombianos (COP), formato $1.250.000.

TU PERSONALIDAD
- Cercano, claro y práctico, como un amigo que sabe de finanzas. Tutea. Español de Colombia (entiendes "lucas", "barras", "corrientazo", "domicilio", "pasaje", "quincena", "gota a gota").
- Empático pero directo: si algo va mal en sus números, dilo con tacto y da un plan.
- Nada de relleno ni frases genéricas. Cada respuesta debe dejar al usuario con algo concreto que hacer.

CÓMO RESPONDER
- Usa SIEMPRE los datos reales del usuario que vienen en DATOS DEL USUARIO cuando sean relevantes: cita cifras, porcentajes, categorías y metas concretas. Haz las cuentas tú (cuánto ahorrar al mes, en cuántos meses llega a una meta, cuánto libera recortar X%).
- Nunca inventes datos del usuario. Si falta un dato, pregúntalo en una sola frase.
- Máximo {MAX_PALABRAS_RESPUESTA} palabras. Markdown simple: **negritas**, listas con "- " o "1.", tablas pequeñas solo si ayudan. Emojis con moderación.
- Puedes enlazar páginas de la app con markdown, por ejemplo [Mis Finanzas](finanzas.html). Páginas: {paginas}.
- Temas: finanzas personales, ahorro, presupuesto, deudas, crédito, inversión, impuestos, consumo inteligente, emprendimiento y negociación de salario. Si preguntan algo totalmente ajeno, responde en una frase amable y lleva la conversación a sus finanzas.
- Inversiones, impuestos, pensiones y créditos: explica con claridad y recuerda en una línea que es información educativa. Si das cifras oficiales que cambian (SMMLV, UVT, tasas, topes), di que son aproximadas y que las verifique en la fuente oficial (DIAN, Banco de la República, Superfinanciera).
- Deudas graves o préstamos "gota a gota": prioriza seguridad, sugiere renegociar con el banco y la Defensoría del Consumidor Financiero.

LO QUE LA APP PUEDE HACER (tú NO ejecutas nada: solo propones)
El usuario puede pedirle a FinanBot, escribiendo en este mismo chat:
{cmds}
- Ver resumen del mes, gastos por categoría, dónde gasta más (mapa), simular inversiones, generar reportes PDF/Excel.
- Crear y eliminar categorías desde el chat. Al crear, aclara si es de gasto o ingreso; al eliminar, el sistema conserva sus movimientos en la categoría "Otros" correspondiente.
Categorías de gasto válidas: {', '.join(categorias_gasto)}.
Categorías de ingreso válidas: {', '.join(categorias_ingreso)}.
Usa únicamente estas categorías al proponer un movimiento. La lista refleja las categorías activas de esta persona: incluye las personalizadas y excluye las que ocultó o eliminó. Si una categoría no está disponible, sugiere la más cercana de la lista.
Solo se pueden registrar o cambiar movimientos del MES ACTUAL. Meses anteriores se consultan en el Calendario.

IMPORTANTE
- Nunca digas que registraste, editaste o borraste algo: tú no puedes hacerlo.
- Si el usuario describe un gasto o ingreso (aunque sea informal, ej. "me gasté 20 lucas en un corrientazo"), dile en qué categoría encaja y ponle en "sugerencias" el comando exacto listo para tocar, ej. "Registra un gasto de $20.000 en Alimentación".

FORMATO DE SALIDA (obligatorio)
Responde SOLO con un objeto JSON válido, sin texto antes ni después:
{{"respuesta": "texto en markdown para el usuario",
  "sugerencias": ["hasta 3 mensajes cortos que el usuario podría enviar a continuación, escritos como si fuera él"],
  "enlaces": ["hasta 2 claves de páginas de la app relevantes, de esta lista: {', '.join(rutas)}"]}}"""


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _pesos(v) -> str:
    n = round(_num(v))
    return ('-' if n < 0 else '') + '$' + f'{abs(n):,.0f}'.replace(',', '.')


def _contexto_usuario(ctx: dict | None) -> str:
    """Resume los datos del usuario en texto compacto para el modelo."""
    if not ctx:
        return 'No hay datos financieros del usuario disponibles (puede ser invitado o no ha registrado nada).'

    hoy = date.today()
    lineas = [f'Mes analizado: {_MESES[hoy.month - 1]} {hoy.year} (día {hoy.day}).']
    if ctx.get('nombre'):
        lineas.append(f"Nombre: {ctx['nombre']}")
    ing, gas = _num(ctx.get('total_ingresos')), _num(ctx.get('total_gastos'))
    bal = _num(ctx.get('balance', ing - gas))
    lineas.append(f'Ingresos del mes: {_pesos(ing)} | Gastos del mes: {_pesos(gas)} | Balance: {_pesos(bal)}')
    if ing > 0:
        lineas.append(f'Gasta el {round(gas / ing * 100)}% de sus ingresos; ahorro libre {round(bal / ing * 100)}%.')
    for clave, etiqueta in (('ingreso_mensual', 'Salario mensual en su perfil'),
                            ('meta_ahorro', 'Meta de ahorro mensual del perfil')):
        if _num(ctx.get(clave)) > 0:
            lineas.append(f'{etiqueta}: {_pesos(ctx[clave])}')
    if ctx.get('num_transacciones') is not None:
        lineas.append(f"Movimientos registrados este mes: {ctx.get('num_transacciones')}")

    cats = ctx.get('gastos_por_categoria') or {}
    if cats:
        top = sorted(cats.items(), key=lambda x: -_num(x[1]))[:6]
        lineas.append('Gastos por categoría: ' + ', '.join(
            f'{c} {_pesos(v)} ({round(_num(v) / gas * 100) if gas else 0}%)' for c, v in top))
    cats_i = ctx.get('ingresos_por_categoria') or {}
    if cats_i:
        lineas.append('Ingresos por categoría: ' + ', '.join(f'{c} {_pesos(v)}' for c, v in list(cats_i.items())[:5]))

    metas = ctx.get('metas') or []
    if isinstance(metas, list) and metas:
        partes = []
        for m in metas[:6]:
            obj = _num(m.get('objetivo', m.get('monto_objetivo')))
            act = _num(m.get('actual', m.get('monto_actual')))
            pct = round(act / obj * 100) if obj else 0
            extra = ' (completada)' if m.get('completada') else ''
            if m.get('fecha_limite'):
                extra += f", fecha límite {m['fecha_limite']}"
            if m.get('modo') == 'automatico' and m.get('monto_automatico'):
                extra += f", aporte automático {_pesos(m['monto_automatico'])}/mes"
            partes.append(f"{m.get('nombre', 'Meta')}: {_pesos(act)} de {_pesos(obj)} ({pct}%){extra}")
        lineas.append('Metas: ' + ' | '.join(partes))
    elif ctx.get('num_metas') == 0:
        lineas.append('No tiene metas de ahorro.')

    movs = ctx.get('movimientos') or []
    if isinstance(movs, list) and movs:
        recientes = []
        for m in movs[:8]:
            lugar = m.get('ubicacion_nombre') or ''
            recientes.append(f"{m.get('fecha', '')} {m.get('tipo', '')} {m.get('categoria', '')} {_pesos(m.get('monto'))}"
                             + (f' en {lugar[:40]}' if lugar else ''))
        lineas.append('Movimientos recientes: ' + '; '.join(recientes))

    return '\n'.join(lineas)


# ──────────────────────────────────────────────────────────────────
#  LLAMADAS HTTP (sin librerías extra)
# ──────────────────────────────────────────────────────────────────

def _post(url: str, headers: dict, cuerpo: dict, timeout: float = TIMEOUT_S) -> dict:
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', **headers}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _config_gemini(modelo: str, pensar_poco: bool) -> dict:
    cfg = {'temperature': 0.6, 'maxOutputTokens': 4096, 'responseMimeType': 'application/json'}
    if pensar_poco:
        # Los modelos nuevos "piensan" antes de responder y eso los hace lentos.
        # Para un chat basta con pensar poco.
        if '2.5' in modelo:
            cfg['thinkingConfig'] = {'thinkingBudget': 0 if 'lite' in modelo else 512}
        else:
            cfg['thinkingConfig'] = {'thinkingLevel': 'low'}
    return cfg


def _llamar_gemini(p: dict, sistema: str, mensajes: list[tuple[str, str]]) -> str:
    global _gemini_modelo_ok
    base = {
        'system_instruction': {'parts': [{'text': sistema}]},
        'contents': [{'role': 'user' if r == 'user' else 'model', 'parts': [{'text': t}]} for r, t in mensajes],
    }
    # Si se fijó FINANBOT_IA2_MODEL solo se usa ese; si no, se prueban los de la lista
    candidatos = [p['modelo']] if os.getenv('FINANBOT_IA2_MODEL') else \
        [p['modelo']] + [m for m in GEMINI_MODELOS if m != p['modelo']]
    limite = time.time() + TIEMPO_MAX_TOTAL_S
    ultimo_error: Exception | None = None

    for modelo in candidatos:
        restante = limite - time.time()
        if restante < 3:
            break
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
               f"?key={p['key']}")
        pensar_poco = modelo not in _sin_thinking_config
        try:
            try:
                data = _post(url, {}, {**base, 'generationConfig': _config_gemini(modelo, pensar_poco)},
                             timeout=min(TIMEOUT_POR_MODELO_S, restante))
            except urllib.error.HTTPError as e:
                if e.code == 400 and pensar_poco:
                    # el modelo no acepta thinkingConfig → se repite sin él
                    _sin_thinking_config.add(modelo)
                    data = _post(url, {}, {**base, 'generationConfig': _config_gemini(modelo, False)},
                                 timeout=min(TIMEOUT_POR_MODELO_S, max(3, limite - time.time())))
                else:
                    raise
        except urllib.error.HTTPError as e:
            # 404 = modelo retirado · 429 = cupo gratis agotado (cada modelo tiene su propio cupo)
            # 500/503 = Google saturado → se prueba el siguiente modelo
            if e.code in (404, 429, 500, 503):
                print(f'[FinanBot IA 2] {modelo} no respondió (HTTP {e.code}), probando otro modelo…')
                ultimo_error = e
                if modelo == _gemini_modelo_ok:
                    _gemini_modelo_ok = None
                continue
            raise
        except (TimeoutError, urllib.error.URLError) as e:
            print(f'[FinanBot IA 2] {modelo} tardó demasiado, probando otro modelo…')
            ultimo_error = e
            if modelo == _gemini_modelo_ok:
                _gemini_modelo_ok = None
            continue

        partes = (data.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
        texto = ''.join(part.get('text', '') for part in partes if not part.get('thought'))
        if not texto.strip():
            print(f'[FinanBot IA 2] {modelo} devolvió una respuesta vacía, probando otro modelo…')
            continue
        if modelo != _gemini_modelo_ok:
            _gemini_modelo_ok = modelo
            print(f'[FinanBot IA 2] Usando modelo Gemini: {modelo}')
        return texto
    raise ultimo_error or RuntimeError('Ningún modelo Gemini respondió a tiempo')


def _llamar(p: dict, sistema: str, mensajes: list[tuple[str, str]]) -> str:
    if p['tipo'] == 'gemini':
        return _llamar_gemini(p, sistema, mensajes)

    if p['tipo'] == 'anthropic':
        data = _post('https://api.anthropic.com/v1/messages',
                     {'x-api-key': p['key'], 'anthropic-version': '2023-06-01'},
                     {'model': p['modelo'], 'max_tokens': 1200, 'temperature': 0.6, 'system': sistema,
                      'messages': [{'role': 'user' if r == 'user' else 'assistant', 'content': t} for r, t in mensajes]})
        return ''.join(b.get('text', '') for b in data.get('content', []) if b.get('type') == 'text')

    # OpenAI compatible (Groq, Ollama, LM Studio, OpenRouter…)
    cuerpo = {'model': p['modelo'], 'temperature': 0.6, 'max_tokens': 1200,
              'messages': [{'role': 'system', 'content': sistema}] +
                          [{'role': 'user' if r == 'user' else 'assistant', 'content': t} for r, t in mensajes]}
    if 'groq.com' in p['url']:
        cuerpo['response_format'] = {'type': 'json_object'}
    data = _post(p['url'], {'Authorization': f"Bearer {p['key']}"}, cuerpo)
    return data['choices'][0]['message']['content']


def _parsear(texto: str) -> dict | None:
    """Saca el JSON aunque el modelo lo envuelva en ```json … ``` o agregue texto."""
    if not texto:
        return None
    limpio = re.sub(r'^```(?:json)?\s*|\s*```$', '', texto.strip())
    try:
        data = json.loads(limpio)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', limpio, re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        # el modelo respondió texto plano: se usa tal cual
        return {'respuesta': limpio, 'sugerencias': [], 'enlaces': []}
    if not str(data.get('respuesta', '')).strip():
        return None
    return data


# ──────────────────────────────────────────────────────────────────
#  API PÚBLICA
# ──────────────────────────────────────────────────────────────────

def recordar(clave: str | None, rol: str, texto: str) -> None:
    """Guarda un turno en la memoria corta de la conversación."""
    if not clave or not texto:
        return
    with _memoria_lock:
        if clave not in _memoria and len(_memoria) >= MAX_CONVERSACIONES:
            _memoria.pop(next(iter(_memoria)))
        _memoria.setdefault(clave, deque(maxlen=MAX_TURNOS_MEMORIA * 2)).append((rol, texto[:1500]))


def responder(mensaje: str, ctx: dict | None, clave_conversacion: str | None, *,
              categorias_gasto, categorias_ingreso, ejemplos: dict, rutas: dict,
              referencia: str | None = None) -> dict | None:
    """Devuelve {'respuesta', 'sugerencias', 'enlaces'} o None si no hay modelo / falló."""
    global _pausa_hasta
    p = _proveedor()
    if not p or time.time() < _pausa_hasta:
        return None

    sistema = _prompt_sistema(categorias_gasto, categorias_ingreso, ejemplos, rutas)
    with _memoria_lock:
        previos = list(_memoria.get(clave_conversacion, [])) if clave_conversacion else []

    # el contexto de datos va en el mensaje actual para que siempre esté fresco
    actual = f'DATOS DEL USUARIO (actualizados ahora):\n{_contexto_usuario(ctx)}\n'
    if referencia:
        actual += f'\nNOTA DE REFERENCIA de la base de conocimiento de FinanBot (úsala si sirve, en tus palabras):\n{referencia[:2500]}\n'
    actual += f'\nMENSAJE DEL USUARIO:\n{mensaje}'

    # los modelos esperan que la conversación empiece con el usuario
    while previos and previos[0][0] != 'user':
        previos.pop(0)

    try:
        texto = _llamar(p, sistema, previos + [('user', actual)])
    except Exception as err:                      # red caída, timeout, cupo agotado en todos…
        espera = 60 if getattr(err, 'code', None) == 429 else PAUSA_TRAS_FALLO_S
        print(f'[FinanBot IA 2] El proveedor {p["tipo"]} falló: {err}. '
              f'Respondiendo con las reglas durante {espera} s.')
        _pausa_hasta = time.time() + espera
        return None

    data = _parsear(texto)
    if not data:
        print('[FinanBot IA 2] El modelo devolvió una respuesta vacía; responden las reglas.')
        return None

    respuesta = str(data['respuesta']).strip()
    sugerencias = [str(s).strip()[:90] for s in (data.get('sugerencias') or []) if str(s).strip()][:3]
    enlaces = [e for e in (data.get('enlaces') or []) if e in rutas][:2]

    recordar(clave_conversacion, 'user', mensaje)
    recordar(clave_conversacion, 'bot', respuesta)
    return {'respuesta': respuesta, 'sugerencias': sugerencias, 'enlaces': enlaces}