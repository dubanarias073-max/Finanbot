# finanbot_ia.py

from datetime import datetime
from collections import deque
import random
import re

# ══════════════════════════════════════════════════════════════════
#  RUTAS REALES DEL PROYECTO  (usadas en los botones de acción)
# ══════════════════════════════════════════════════════════════════
RUTAS = {
    'dashboard':      'dashboard.html',
    'finanzas':       'finanzas.html',
    'metas':          'finanzas.html#metas',
    'simulador':      'simulador.html',
    'recomendaciones':'recomendaciones.html',
    'aprende':        'aprende.html',
    'perfil':         'perfil.html',
    'chat':           'chat.html',
    'exportar_pdf':   'exportar.html',
    'exportar_excel': 'exportar.html',
}

# ══════════════════════════════════════════════════════════════════
#  PERSONALIDAD  ─  frases de variedad para respuestas
# ══════════════════════════════════════════════════════════════════
_OK   = ["¡Listo!", "¡Hecho!", "¡Perfecto!", "¡Excelente!", "Ahí está.", "¡Sin problema!"]
_TIPS = ["💡 Tip:", "💡 Dato útil:", "📌 Consejo:", "💡 Recuerda:"]

def _ok():  return random.choice(_OK)
def _tip(): return random.choice(_TIPS)

# ══════════════════════════════════════════════════════════════════
#  BASE DE CONOCIMIENTO FINANCIERO
#  Organizada por intención.  Motor usa coincidencia de palabras.
# ══════════════════════════════════════════════════════════════════
BASE = {

# ─── AHORRO ──────────────────────────────────────────────────────
"ahorro|ahorrar|cómo ahorrar|como ahorrar|tips ahorro|consejos ahorro|guardar dinero|economizar": {
    "titulo": "💰 Ahorro personal — Cómo hacerlo bien",
    "cuerpo": """**Ahorrar** es reservar parte de tus ingresos antes de gastar, no después. La gente que ahorra bien aplica una sola regla: *págate a ti primero*.

**Los 5 principios que funcionan:**
1. **Págate primero** — Apenas llegue tu ingreso, transfiere un % fijo a una cuenta separada. Si esperas "lo que sobre", nunca sobra nada.
2. **Regla 50/30/20** — 50% necesidades, 30% gustos, 20% ahorro mínimo.
3. **Automatiza** — Programa la transferencia el mismo día que recibes el pago. Lo que no ves, no lo gastas.
4. **Elimina gastos hormiga** — Café diario $3.000 × 30 = $90.000/mes. Domicilios frecuentes $15.000 × 8 = $120.000/mes. Se acumula rápido.
5. **Regla de las 48h** — Antes de comprar algo no planeado, espera 2 días. El 80% de las veces ya no lo quieres.

**¿Cuánto ahorrar si ganas $2.000.000?**
→ Meta ideal: $400.000/mes (20%)
→ Mínimo recomendado: $200.000/mes (10%)

💡 *Nequi y Daviplata generan rendimiento diario. Son perfectos para el fondo de ahorro separado.*""",
    "sug": "¿Quieres crear una meta de ahorro? Dime el monto y el objetivo.",
    "btns": [("🎯 Crear meta de ahorro", RUTAS['finanzas']),
             ("📊 Ver mi balance", RUTAS['dashboard']),
             ("📚 Aprende más", RUTAS['aprende'])]
},

# ─── CDT ─────────────────────────────────────────────────────────
"cdt|certificado de depósito|certificado de deposito|qué es cdt|que es cdt|cómo funciona cdt|como funciona cdt|invertir cdt|plazo fijo": {
    "titulo": "🏦 CDT — Certificado de Depósito a Término",
    "cuerpo": """Un **CDT** es el producto de inversión más popular de Colombia. Depositas dinero en un banco por un plazo fijo y recibes una tasa de interés garantizada desde el primer día.

**Cómo funciona paso a paso:**
1. Vas al banco (o plataforma digital) y depositas un monto mínimo
2. Acuerdas la tasa y el plazo antes de firmar — esa tasa no cambia
3. Al vencimiento recibes tu capital + intereses
4. Está asegurado por **Fogafín hasta $50 millones** si el banco quiebra

**Plazos disponibles:** 30 · 60 · 90 · 180 · 360 días o más

**Tasas de referencia 2024 en Colombia:**
| Plazo | Tasa EA |
|---|---|
| 30-90 días | 8-10% |
| 180 días | 10-13% |
| 360+ días | 12-15% |

**Ejemplo práctico:**
$2.000.000 al 12% anual por 12 meses = **$2.240.000** al vencer.
Ganaste $240.000 sin hacer absolutamente nada.

⚠️ Si necesitas el dinero antes del plazo, generalmente puedes romperlo pero con penalidad.""",
    "sug": "¿Quieres simular cuánto ganarías en un CDT? Dime el monto, la tasa y el plazo.",
    "btns": [("📈 Ir al simulador", RUTAS['simulador']),
             ("📚 Aprende sobre inversión", RUTAS['aprende'])]
},

# ─── INVERSIÓN ───────────────────────────────────────────────────
"invertir|inversión|inversion|cómo invertir|como invertir|dónde invertir|donde invertir|mejores inversiones|quiero invertir|opciones de inversión": {
    "titulo": "📈 Cómo invertir en Colombia — Guía para principiantes",
    "cuerpo": """Invertir es hacer que tu dinero trabaje para ti en lugar de quedarse quieto perdiendo valor por la inflación.

**Antes de invertir necesitas (en este orden):**
1. ✅ Fondo de emergencia de 3-6 meses de gastos
2. ✅ Deudas de alto interés pagadas (tarjetas, gota a gota)
3. ✅ Entender el producto antes de poner un peso

**Opciones en Colombia ordenadas por riesgo:**

🟢 **Muy bajo riesgo:**
• CDT: 8-15% EA, capital garantizado, Fogafín lo protege
• Cuentas de ahorro Nequi/Daviplata: rendimiento diario ~7%

🟡 **Riesgo medio:**
• Fondos de inversión conservadores o moderados: 6-12% anual
• TES (bonos del gobierno colombiano)
• Finca raíz: valorización + arriendo, requiere capital

🔴 **Alto riesgo:**
• Acciones BVC (Bancolombia, Ecopetrol, Grupo Sura)
• Criptomonedas (solo dinero que puedas perder completamente)

**Regla de oro:** no inviertas en algo que no entiendes.
**Señal de estafa:** cualquier inversión que prometa rentabilidades garantizadas del 5-10% mensual.""",
    "sug": "¿Cuánto tienes disponible para invertir? Te ayudo a simular opciones.",
    "btns": [("📈 Usar simulador", RUTAS['simulador']),
             ("💡 Recomendaciones", RUTAS['recomendaciones']),
             ("📚 Aprende más", RUTAS['aprende'])]
},

# ─── PRESUPUESTO / REGLA 50/30/20 ────────────────────────────────
"presupuesto|regla 50|50/30/20|50 30 20|distribuir salario|organizar dinero|organizar gastos|cómo organizar|como organizar": {
    "titulo": "📋 Presupuesto personal — La regla 50/30/20",
    "cuerpo": """La **regla 50/30/20** es el método más simple y efectivo para organizar tu dinero mensualmente.

**La distribución:**

| Categoría | % | Qué incluye |
|---|---|---|
| 🏠 Necesidades | 50% | Arriendo, comida, transporte, servicios, salud, educación |
| 🎬 Deseos | 30% | Entretenimiento, ropa, salidas, hobbies, suscripciones |
| 💰 Ahorro | 20% | Fondo emergencia, CDT, metas, pensión voluntaria |

**Ejemplo con $3.000.000:**
• Necesidades: $1.500.000
• Deseos: $900.000
• Ahorro: $600.000

**¿Qué pasa si tus necesidades superan el 50%?**
→ Es normal en ciudades como Bogotá o Medellín. Empieza con 60/20/20.
→ Lo único innegociable: siempre debe haber un % para ahorro, así sea el 5%.

**Cómo aplicarla:**
1. Calcula tu ingreso neto mensual real
2. Multiplica por 0.5, 0.3 y 0.2
3. Abre una cuenta separada para el ahorro
4. Revisa el avance cada semana""",
    "sug": "Dime cuánto ganas y te calculo exactamente los montos de cada categoría.",
    "btns": [("💸 Registrar mis gastos", RUTAS['finanzas']),
             ("📊 Ver mi balance", RUTAS['dashboard'])]
},

# ─── DEUDAS ──────────────────────────────────────────────────────
"deuda|deudas|salir de deudas|pagar deudas|bola de nieve|avalancha|endeudado|crédito|credito|préstamo|prestamo": {
    "titulo": "💳 Salir de deudas — Métodos probados",
    "cuerpo": """Estar endeudado no es el fin. Con el método correcto puedes salir, y más rápido de lo que crees.

**Paso 1 — Haz el inventario completo:**
Anota TODAS tus deudas: nombre, monto total, cuota mensual y tasa de interés anual.

**Método ⛄ Bola de Nieve (David Ramsey — para motivación):**
1. Ordena deudas de menor a mayor monto
2. Paga el mínimo en todas
3. Todo el dinero extra → a la deuda más pequeña
4. Al pagarla, ese dinero pasa a la siguiente
✅ *Ventaja:* ves resultados rápidos, te mantiene motivado

**Método 🌊 Avalancha (matemáticamente óptimo):**
1. Ordena deudas de mayor a menor tasa de interés
2. Paga el mínimo en todas
3. Todo el extra → a la de mayor tasa
✅ *Ventaja:* pagas menos intereses en total

**Ejemplo:**
Tarjeta 28% + Crédito 18% + Familiar 0%
→ Avalancha: Tarjeta primero → Crédito → Familiar

**⚠️ Deudas que debes evitar a toda costa:**
• Gota a gota: tasas ilegales del 300-1000% anual, peligroso
• Pagar solo el mínimo de tarjeta de crédito: la deuda nunca desaparece
• Apps de préstamo rápido: tasas disfrazadas altísimas""",
    "sug": "¿Cuánto debes en total? Dime y te calculo cuánto tiempo tardarías en salir.",
    "btns": [("📊 Ver mis finanzas", RUTAS['dashboard']),
             ("💡 Ver recomendaciones", RUTAS['recomendaciones'])]
},

# ─── FONDO DE EMERGENCIA ─────────────────────────────────────────
"fondo de emergencia|emergencia|colchón financiero|colchon financiero|reserva de emergencia|para imprevistos|ahorro de emergencia": {
    "titulo": "🛡️ Fondo de emergencia — Tu red de seguridad",
    "cuerpo": """El **fondo de emergencia** es dinero guardado exclusivamente para situaciones urgentes e imprevistas. Es la primera prioridad financiera, antes que cualquier inversión.

**¿Para qué sirve?**
• Pérdida repentina de empleo
• Emergencia médica no cubierta por EPS
• Reparación urgente del vehículo o vivienda
• Cualquier crisis que interrumpa tus ingresos

**¿Cuánto necesitas?**
| Situación | Meses recomendados |
|---|---|
| Empleado en empresa estable | 3 meses |
| Empleado en empresa inestable | 4-6 meses |
| Independiente / Freelance | 6-12 meses |

**Ejemplo:** Si tus gastos básicos son $1.500.000/mes:
• Mínimo: $4.500.000 (3 meses)
• Ideal: $9.000.000 (6 meses)

**¿Dónde guardarlo?**
✅ Nequi o Daviplata (acceso inmediato + rendimiento diario)
✅ CDT a 30 días renovable
✅ Cuenta de ahorros aparte de la del día a día
❌ NO en criptomonedas (pueden caer justo cuando los necesitas)
❌ NO en inversiones de largo plazo (baja liquidez)

🔑 **Regla clave:** el fondo de emergencia NO es para vacaciones, ropa ni caprichos. Solo para emergencias reales.""",
    "sug": "¿Cuánto son tus gastos básicos al mes? Te digo exactamente cuánto necesitas ahorrar.",
    "btns": [("🎯 Crear meta de ahorro", RUTAS['finanzas']),
             ("📊 Ver mi balance", RUTAS['dashboard'])]
},

# ─── TARJETA DE CRÉDITO ──────────────────────────────────────────
"tarjeta de crédito|tarjeta credito|tarjeta|cuota mínima|cuota minima|extracto|fecha de pago|intereses tarjeta": {
    "titulo": "💳 Tarjeta de crédito — Cómo usarla a tu favor",
    "cuerpo": """La tarjeta de crédito puede ser tu mejor aliada o tu peor enemiga. Todo depende de una sola cosa: si pagas el total o no.

**✅ Cómo usarla bien:**
• Paga el **TOTAL** del extracto antes de la fecha límite → no pagas intereses
• Úsala solo para gastos que ya tenías planeados
• Aprovecha los beneficios: millas, cashback, cuotas sin intereses
• Ponle un límite mental: nunca más del 30% del cupo disponible

**❌ Qué evitar a toda costa:**
• Pagar solo el mínimo — la deuda se vuelve permanente
• Usarla para gastos que no puedes pagar de contado
• Sacar avances en efectivo (tasas del 40%+ anual)
• Tener varias tarjetas con saldo pendiente

**El costo real del pago mínimo:**
$1.000.000 de deuda al 28% EA pagando el mínimo (5% mensual):
→ Tardas **~7 años** en pagarla
→ Terminas pagando **más de $2.500.000** en total
→ Pagas **$1.500.000 extra solo en intereses**

**Tasa máxima 2024 en Colombia:** ~28-30% EA (de las más altas de Latinoamérica)

💡 Si ya tienes saldo en tarjeta, págala ANTES de cualquier inversión. No hay inversión conservadora que rinda más del 28%.""",
    "sug": "¿Quieres calcular cuánto te costaría una deuda en tarjeta? Dime el monto y la tasa.",
    "btns": [("💸 Ver mis gastos", RUTAS['finanzas']),
             ("💡 Ver recomendaciones", RUTAS['recomendaciones'])]
},

# ─── INFLACIÓN ───────────────────────────────────────────────────
"inflación|inflacion|ipc|índice de precios|indice de precios|poder adquisitivo|precios suben|todo está caro|todo esta caro": {
    "titulo": "📉 Inflación — Qué es y cómo proteger tu dinero",
    "cuerpo": """La **inflación** es el aumento generalizado y sostenido de los precios. Si la inflación es del 9%, lo que hoy cuesta $100.000 el próximo año costará $109.000.

**El efecto sobre tu dinero:**
$1.000.000 guardado en efectivo con inflación del 9%:
→ En 1 año: solo puedes comprar lo que antes valía $917.000
→ En 3 años: equivale a $772.000 de hoy
→ ¡Perdiste poder de compra sin gastar un peso!

**Colombia 2024:** IPC ≈ 7-9% anual (Banco de la República y DANE)

**Cómo protegerte:**
✅ CDT con tasa superior a la inflación → si CDT paga 12% e inflación es 9%, ganaste 3% real
✅ Fondos de renta variable → históricamente superan la inflación
✅ Finca raíz → valorización histórica en Colombia supera la inflación
✅ Dólares u otros activos → diversificación de riesgo cambiario
❌ Efectivo guardado → pierde valor garantizadamente

**Concepto clave — Tasa de interés real:**
Tasa real = Tasa nominal − Inflación
Si tu CDT paga 7% y la inflación es 9% → tasa real = -2% (¡estás perdiendo!)
Si tu CDT paga 12% y la inflación es 9% → tasa real = +3% (ganando de verdad)""",
    "sug": "¿Quieres calcular cuánto pierde tu dinero guardado con la inflación actual?",
    "btns": [("📈 Simular inversión", RUTAS['simulador']),
             ("📚 Aprende más", RUTAS['aprende'])]
},

# ─── INTERÉS SIMPLE VS COMPUESTO ─────────────────────────────────
"interés simple|interes simple|interés compuesto|interes compuesto|cómo funciona el interés|como funciona el interes|qué es interés|que es interes|diferencia interés": {
    "titulo": "🔢 Interés simple vs interés compuesto",
    "cuerpo": """Son dos formas de calcular el rendimiento de una inversión (o el costo de una deuda).

**Interés simple:**
Los intereses se calculan siempre sobre el capital original. Los intereses ganados no generan nuevos intereses.

Fórmula: Interés = Capital × Tasa × Tiempo

Ejemplo: $1.000.000 al 10% anual por 3 años
→ Interés cada año: $100.000 (siempre igual)
→ Total al final: $1.300.000

---

**Interés compuesto:**
Los intereses del período anterior se suman al capital. Los intereses generan nuevos intereses. Einstein lo llamó "la octava maravilla del mundo".

Fórmula: Capital Final = Capital × (1 + Tasa)^Tiempo

Ejemplo: $1.000.000 al 10% compuesto por 3 años
→ Año 1: $1.100.000
→ Año 2: $1.210.000
→ Año 3: **$1.331.000** (vs $1.300.000 del simple)

**El poder del tiempo con interés compuesto:**
$1.000.000 al 10% anual:
• 10 años → $2.593.742
• 20 años → $6.727.500
• 30 años → $17.449.402

💡 La diferencia entre quien empieza a ahorrar a los 25 y quien empieza a los 35 puede ser de $10.000.000+ al retirarse, con los mismos aportes.""",
    "sug": "¿Quieres simular el crecimiento de tus ahorros con interés compuesto?",
    "btns": [("📈 Ir al simulador", RUTAS['simulador']),
             ("📚 Aprende más", RUTAS['aprende'])]
},

# ─── PENSIÓN ─────────────────────────────────────────────────────
"pensión|pension|colpensiones|afp|fondo de pensiones|jubilación|jubilacion|retiro|vejez|semanas cotizadas": {
    "titulo": "👴 Pensión en Colombia — Colpensiones vs AFP",
    "cuerpo": """Colombia tiene dos sistemas de pensión y elegir bien puede significar millones de diferencia.

**🏛️ Colpensiones — Régimen de Prima Media:**
• Administrado por el Estado (no es una cuenta tuya)
• Requisitos: 1.300 semanas cotizadas (~25 años)
• Edad: 57 mujeres / 62 hombres
• Pensión mínima garantizada: 1 SMMLV
• Pensión calculada sobre promedio de últimos 10 años de salario

**🏢 AFP — Régimen de Ahorro Individual (RAIS):**
• Cuenta individual a tu nombre (Porvenir, Colfondos, Protección)
• Tus aportes se invierten y generan rendimientos
• Puedes elegir el perfil de riesgo del portafolio
• Los aportes voluntarios son deducibles de renta (Art. 126-1 E.T.)
• El saldo es heritable

**¿Quién conviene Colpensiones?**
→ Mujeres (menor edad de pensión), empleados con salario estable y bajo, personas con muchos años cotizados

**¿Quién conviene AFP?**
→ Hombres, independientes, personas con ingresos altos o variables

**⚠️ Dato duro:** El 75% de los colombianos NO se pensiona por cotizaciones discontinuas.

**Aportes voluntarios — beneficio tributario:**
$300.000/mes en pensión voluntaria:
→ ~$57.000/mes menos en impuestos
→ En 20 años al 8%: capital adicional de ~$178.000.000""",
    "sug": "¿Quieres calcular cuánto acumularías con aportes voluntarios a pensión?",
    "btns": [("📈 Simular pensión voluntaria", RUTAS['simulador']),
             ("📚 Aprende más", RUTAS['aprende'])]
},

# ─── CRIPTOMONEDAS ───────────────────────────────────────────────
"criptomonedas|cripto|bitcoin|ethereum|btc|eth|blockchain|crypto|criptoactivos": {
    "titulo": "₿ Criptomonedas — Lo que debes saber antes de invertir",
    "cuerpo": """Las criptomonedas son activos digitales descentralizados. Pueden generar grandes ganancias o grandes pérdidas. La diferencia está en el conocimiento.

**Riesgos reales:**
• Volatilidad extrema: Bitcoin cayó 75% en 7 meses (nov 2021 → jun 2022)
• Sin regulación en Colombia: si pierdes, nadie te protege
• Si pierdes tu clave privada, pierdes TODO permanentemente
• Estafas frecuentes: rug pulls, esquemas Ponzi, influencers pagados
• Exchanges pueden quebrar (FTX quebró en 2022 con millones de clientes)

**Si decides invertir:**
• Máximo 5-10% de tu portafolio total
• Solo dinero que puedas perder completamente
• Solo en plataformas reconocidas: Binance, Coinbase, Kraken
• Guarda en wallet propia (no en el exchange)
• Nunca sigas "grupos de inversión" de WhatsApp o Telegram

**🚨 Señales de estafa que debes conocer:**
→ "Rendimientos garantizados del 5-10% mensual"
→ "Invierte hoy, oferta vence mañana"
→ Influencers que piden referidos con comisión
→ Plataformas sin información de quiénes son ni dónde están

**Impuestos en Colombia:**
La DIAN considera las criptos activos sujetos a declaración de renta.
Las ganancias se declaran como ganancia ocasional (10%).""",
    "sug": "¿Tienes dudas sobre una plataforma de cripto específica? Cuéntame y te digo si parece confiable.",
    "btns": [("📚 Aprende sobre inversión", RUTAS['aprende']),
             ("💡 Ver recomendaciones", RUTAS['recomendaciones'])]
},

# ─── FINCA RAÍZ ──────────────────────────────────────────────────
"finca raíz|finca raiz|bienes raíces|bienes raices|apartamento|casa|inmueble|arriendo|arrendar|hipoteca|leasing habitacional": {
    "titulo": "🏠 Inversión en Finca Raíz en Colombia",
    "cuerpo": """La finca raíz es históricamente una de las mejores inversiones en Colombia, pero tiene características que debes conocer.

**¿Por qué funciona en Colombia?**
• Valorización histórica: 5-12% anual en ciudades principales
• Ingreso por arriendo: 3-6% anual del valor del inmueble
• Cobertura contra inflación (el canon se ajusta con el IPC)
• Activo tangible con valor intrínseco

**Ejemplo real:**
Inmueble en Medellín: $200.000.000
Canon de arriendo: $900.000/mes = $10.800.000/año
Rendimiento por arriendo: 5.4%
Valorización anual 8%: $16.000.000
Retorno total bruto: ~12-13% anual

**Costos que debes considerar:**
• Predial: 0.3-1.5% del avalúo catastral/año
• Administración: 5-15% del canon mensual
• Mantenimiento: 1-3% del valor del inmueble/año
• Notaría al comprar/vender: 0.5-1% del valor

**Si no tienes capital para comprar:**
✅ Fiducias inmobiliarias: desde $5-10 millones
✅ Fondos de inversión inmobiliaria
✅ Crowdfunding inmobiliario

**⚠️ Riesgo principal:**
Baja liquidez — no puedes vender rápidamente si necesitas dinero.""",
    "sug": "¿Tienes algún monto disponible? Te ayudo a comparar CDT vs finca raíz.",
    "btns": [("📈 Simular inversión", RUTAS['simulador']),
             ("📚 Aprende más", RUTAS['aprende'])]
},

# ─── IMPUESTOS / DIAN ────────────────────────────────────────────
"impuestos|renta|declaración de renta|declaracion de renta|dian|iva|retención|retencion|tributar|tributos|uvt": {
    "titulo": "🧾 Impuestos en Colombia — Lo esencial",
    "cuerpo": """Los impuestos no tienen por qué ser un dolor de cabeza si sabes lo básico.

**Impuesto de renta — ¿quién declara?**
Para 2024 (vigencia 2023) debes declarar si:
• Ingresos brutos > $59.377.000 en el año
• Patrimonio bruto > $190.854.000
• Consumos con tarjeta > $59.377.000
• Eres responsable de IVA

**Retención en la fuente:**
Tu empleador descuenta mensualmente un anticipo del impuesto de renta directamente de tu salario. Si declaras y retuvieron más de lo que debes → la DIAN te devuelve.

**Deducciones que puedes usar legalmente:**
✅ Intereses de crédito hipotecario: hasta $21.629.000/año
✅ Aportes voluntarios a pensión: hasta 30% del ingreso
✅ Medicina prepagada
✅ 4×1000 certificado por el banco
✅ Dependientes económicos

**IVA en Colombia:**
• Tasa general: 19%
• Canasta básica, medicamentos, libros: 0% o exentos
• Algunos servicios: 5%

**UVT 2024:** $47.065 (Unidad de Valor Tributario — referencia para calcular obligaciones)

💡 Los aportes voluntarios a pensión son la deducción más accesible: por cada $100.000 aportados ahorras entre $19.000 y $39.000 en impuestos.""",
    "sug": "¿Tienes una pregunta específica sobre tu situación tributaria? Cuéntame.",
    "btns": [("📈 Simular pensión voluntaria", RUTAS['simulador']),
             ("👤 Ver mi perfil", RUTAS['perfil'])]
},

# ─── SOBRE FINANBOT ──────────────────────────────────────────────
"finanbot|qué es finanbot|que es finanbot|cómo funciona finanbot|como funciona finanbot|para qué sirve|para que sirve|proyecto sena": {
    "titulo": "🤖 ¿Qué es FinanBot?",
    "cuerpo": """**FinanBot** es tu asistente financiero personal inteligente, desarrollado como proyecto SENA (Ficha 3407184).

**¿Qué puedes hacer?**
• 💸 Registrar gastos e ingresos con lenguaje natural
• 🎯 Crear y dar seguimiento a metas de ahorro
• 📈 Simular inversiones con interés compuesto
• 🏷️ Calcular descuentos, IVA, repartos, aumentos
• 📊 Ver tu balance y resumen financiero
• 🧮 Resolver cualquier cálculo matemático
• 💡 Recibir consejos y respuestas sobre finanzas
• 📄 Generar reportes PDF/Excel de tus finanzas
• 👤 Actualizar tu perfil (nombre, salario, metas)

**Cómo hablarme — ejemplos reales:**
• *"Gasté $25.000 en el bus"* → registra el gasto
• *"$80.000 con 15% de descuento"* → calcula el precio
• *"Simula $500.000 al 10% por 1 año"* → proyecta la inversión
• *"¿Qué es un CDT?"* → te explico
• *"Cambia mi nombre a Juan"* → actualiza tu perfil
• *"Hazme un reporte"* → genera el PDF

No necesitas comandos exactos. Habla como le escribirías a un amigo.""",
    "sug": "¿Por dónde quieres empezar?",
    "btns": [("🏠 Ir al dashboard", RUTAS['dashboard']),
             ("💸 Registrar finanzas", RUTAS['finanzas']),
             ("📚 Centro de aprendizaje", RUTAS['aprende'])]
},

# ─── QUÉS PUEDES HACER ───────────────────────────────────────────
"qué puedes hacer|que puedes hacer|qué haces|que haces|capacidades|funciones|ayuda|comandos|cómo te uso|como te uso": {
    "titulo": "🤖 Todo lo que puedo hacer por ti",
    "cuerpo": """Aquí está todo lo que puedes pedirme:

**💸 Transacciones:**
• *"Gasté $30.000 en comida"* — registra gasto
• *"Recibí $2.000.000 de salario"* — registra ingreso
• *"Borra el último gasto de transporte"* — elimina
• *"Muéstrame mis gastos de esta semana"* — consulta

**🎯 Metas de ahorro:**
• *"Crea una meta de $1.000.000 para viajes"*
• *"Actualiza mi meta de viajes a $400.000"*
• *"Ver todas mis metas"*

**📈 Simulaciones:**
• *"Simula $500.000 al 12% por 6 meses"*
• *"Si invierto 2 millones al 8% por 2 años, ¿cuánto tengo?"*

**🧮 Calculadora financiera:**
• *"$80.000 con 20% de descuento"*
• *"$50.000 más IVA"*
• *"Divide $150.000 entre 3 personas"*
• *"¿Cuánto es 350 por 12?"*
• *"¿Qué porcentaje es $30.000 de $200.000?"*

**👤 Perfil:**
• *"Cambia mi nombre a María"*
• *"Actualiza mi salario a $3.500.000"*
• *"Mi correo es nuevo@email.com"*

**📄 Reportes:**
• *"Hazme un reporte"* → genera PDF o Excel descargable

**💡 Preguntas financieras:**
• *"¿Qué es un CDT?"*
• *"¿Cómo salgo de deudas?"*
• *"¿Cuánto debo tener en fondo de emergencia?"*
• *"¿Qué es el interés compuesto?"*""",
    "sug": "¿Con cuál empezamos?",
    "btns": [("💸 Mis finanzas", RUTAS['finanzas']),
             ("📈 Simulador", RUTAS['simulador']),
             ("📚 Aprende", RUTAS['aprende'])]
},

# ─── SALARIO MÍNIMO / SMMLV ──────────────────────────────────────
"smmlv|salario mínimo|salario minimo|mínimo legal|minimo legal|sueldo mínimo|sueldo minimo": {
    "titulo": "💵 Salario Mínimo en Colombia (SMMLV)",
    "cuerpo": """El **SMMLV** (Salario Mínimo Mensual Legal Vigente) es la referencia base del sistema laboral colombiano.

**2024:**
• SMMLV: $1.300.000
• Auxilio de transporte: $162.000
• Total con auxilio: $1.462.000

**¿Cómo se usa el SMMLV?**
• Base para calcular pensiones y aportes
• Referencia para multas y sanciones
• Mínimo para créditos y garantías
• Referencia de la pensión mínima

**Si ganas el mínimo, ¿cuánto recibes en neto?**
Salario bruto: $1.300.000
Descuento salud (4%): $52.000
Descuento pensión (4%): $52.000
Salario neto aprox.: $1.196.000 + auxilio transporte $162.000 = **$1.358.000**

**Regla del 20% con el mínimo:**
Meta de ahorro sugerida: $260.000/mes
Fondo de emergencia mínimo (3 meses): $3.888.000""",
    "sug": "¿Quieres ver cómo distribuir el salario mínimo según la regla 50/30/20?",
    "btns": [("📊 Ver mi balance", RUTAS['dashboard']),
             ("💸 Registrar mis gastos", RUTAS['finanzas'])]
},

# ─── DIVERSIFICACIÓN ─────────────────────────────────────────────
"diversificar|diversificacion|diversificación|portafolio|no pongas todos los huevos|riesgo inversión": {
    "titulo": "🌱 Diversificación — Cómo reducir el riesgo",
    "cuerpo": """**Diversificar** significa distribuir tu dinero en diferentes tipos de activos para que si uno baja, los demás puedan compensar.

**¿Por qué diversificar?**
Si pones $10.000.000 todo en acciones de una sola empresa y esa empresa quiebra, pierdes todo. Si los distribuyes entre CDT, acciones y fondos, una caída parcial no te destruye.

**Ejemplo de portafolio conservador ($5.000.000):**
• CDT 6 meses 12%: $3.000.000 (60%) — bajo riesgo
• Fondo de inversión moderado: $1.500.000 (30%) — riesgo medio
• Acciones BVC largo plazo: $500.000 (10%) — alto riesgo

**Reglas de diversificación:**
1. No más del 50% en un solo activo o institución
2. Mezcla activos con comportamientos distintos
3. Diversifica también en tiempo (no todo al mismo plazo)
4. Criptomonedas: máximo 5-10% del portafolio total

**Diversificación de ingresos:**
Una segunda fuente de ingresos reduce tu riesgo financiero personal. Freelance, inversiones con rendimiento, negocio pequeño.
$300.000/mes extra = $3.600.000/año adicionales.""",
    "sug": "¿Quieres simular cómo se vería un portafolio diversificado con tu capital disponible?",
    "btns": [("📈 Usar simulador", RUTAS['simulador']),
             ("💡 Ver recomendaciones", RUTAS['recomendaciones'])]
},

# ─── ANÁLISIS TÉCNICO ─────────────────────────────────────────────
"análisis técnico|analisis tecnico|gráficos|candelas|velas|soportes resistencias|soporte resistencia|trading|trader": {
    "titulo": "📊 Análisis Técnico — Lectura de gráficos y tendencias",
    "cuerpo": """El **análisis técnico** es el estudio de los gráficos de precios históricos para predecir movimientos futuros. Se basa en la idea de que los patrones del pasado tienden a repetirse.

**Conceptos clave:**

**Soportes y Resistencias:**
• **Soporte:** Nivel de precio donde cae la demanda. El precio "rebota" hacia arriba.
• **Resistencia:** Nivel donde cae la oferta. El precio "cae" hacia abajo.
• Cuando un soporte se rompe a la baja, se convierte en resistencia.
• Cuando una resistencia se rompe al alza, se convierte en soporte.

**Tipos de velas japonesas:**
• **Vela verde (alcista):** Cierre > Apertura. Señal compradora.
• **Vela roja (bajista):** Cierre < Apertura. Señal vendedora.
• Mecha larga = indecisión del mercado
• Sin mecha = fuerza en la dirección

**Indicadores técnicos principales:**
| Indicador | Señal alcista | Señal bajista |
|---|---|---|
| RSI (fuerza relativa) | <30 (sobreventa) | >70 (sobrecompra) |
| MACD | Cruza hacia arriba | Cruza hacia abajo |
| Medias móviles | Precio > MA | Precio < MA |
| Bandas Bollinger | Toca banda baja | Toca banda alta |

**Advertencia importante:**
⚠️ El análisis técnico es probabilístico, NO definitivo. El mercado puede sorprenderte. Nunca operes con dinero que no puedas perder.

💡 La mayoría de traders retail PIERDEN dinero. Es un juego de habilidad extrema.""",
    "sug": "¿Quieres aprender sobre análisis fundamental como complemento?",
    "btns": [("📚 Aprende más", RUTAS['aprende']),
             ("📈 Ir al simulador", RUTAS['simulador'])]
},

# ─── ANÁLISIS FUNDAMENTAL ────────────────────────────────────────
"análisis fundamental|fundamental|earnings|utilidades|pe ratio|p/e|precio ganancia|rentabilidad empresa|valuation": {
    "titulo": "📈 Análisis Fundamental — Valuar empresas",
    "cuerpo": """El **análisis fundamental** evalúa el valor intrínseco de una empresa basándose en sus estados financieros y perspectivas.

**Indicadores clave:**

**P/E Ratio (Price to Earnings):**
P/E = Precio de la acción / Ganancia por acción

Interpretación:
• P/E bajo (<15): Posiblemente subvaluado o con problemas
• P/E medio (15-25): Valoración normal
• P/E alto (>25): Posiblemente sobrevalorado o con gran potencial
• Comparar SIEMPRE con el promedio del sector

Ejemplo:
Acción BVC: $45.000, Ganancia por acción: $2.000
P/E = 45.000 / 2.000 = 22.5x

**ROE (Retorno sobre Patrimonio):**
ROE = Ganancia Neta / Patrimonio × 100

Mide cuánto beneficio la empresa genera con el capital invertido.
ROE >15% es excelente. ROE <5% es preocupante.

**Deuda/EBITDA:**
Mide cuántas veces la ganancia operativa podría pagar la deuda.
< 3x: Saludable
> 5x: Riesgoso

**Crecimiento de Ingresos:**
Comparar ingresos año a año.
Crecimiento >15% anual es positivo.

**¿Cuándo comprar?**
1. Empresa con fundamentals fuertes (ROE >15%, deuda baja)
2. Precio de la acción ha caído temporalmente
3. P/E está por debajo del promedio histórico
4. Tienes horizonte de largo plazo (>5 años)

💡 Recuerda: Invertir en empresas es comprar un % de sus ganancias futuras.""",
    "sug": "¿Quieres aprender las diferencias entre trading (corto plazo) e inversión (largo plazo)?",
    "btns": [("📚 Aprende más", RUTAS['aprende']),
             ("📈 Simulador", RUTAS['simulador'])]
},

# ─── BONOS Y RENTA FIJA ──────────────────────────────────────────
"bonos|renta fija|tasa fija|cupón|yield|títulos deuda|tes|bonos del gobierno|corporate bonds": {
    "titulo": "💼 Bonos y Renta Fija — Inversión predecible",
    "cuerpo": """Un **bono** es un préstamo que le das a una empresa o gobierno. A cambio, recibes pagos periódicos (cupones) y devuelven el capital al vencimiento.

**Partes de un bono:**

• **Valor nominal:** Cantidad original que prestas
• **Tasa cupón:** % de interés que recibes periódicamente (anual)
• **Plazo:** Cuándo se devuelve el capital (3, 5, 10, 30 años)
• **Precio:** Puede variar en el mercado (sube si tasas bajan, baja si suben)

**Ejemplo real:**
TES (Bonos del Gobierno Colombiano)
Nominal: $1.000.000
Plazo: 10 años
Tasa: 8% anual
→ Recibirás $80.000 cada año durante 10 años
→ Al año 10, recibirás $1.000.000 + último cupón

**Tipos de bonos:**

| Tipo | Riesgo | Rendimiento |
|---|---|---|
| TES (Gobierno) | Muy bajo | 7-9% |
| Corporativos (AAA) | Bajo | 9-11% |
| Corporativos (BBB) | Medio | 11-15% |
| Corporativos (B) | Alto | 15-25%+ |

**Yield (Rentabilidad real):**
Si compras un bono a descuento (menos que su valor), el yield es mayor que la tasa cupón.

Precio compra: $950.000 (descuento)
Tasa cupón: 8%
Yield: ~8.4%

**Riesgo de tasa de interés:**
Si compras un bono al 8% y las tasas suben a 12%, tu bono se devalúa en el mercado.
Si planeas vender antes del vencimiento, podrías perder.

💡 La ventaja de bonos: flujo predecible de ingresos. Ideal para jubilados.""",
    "sug": "¿Quieres comparar bonos vs acciones para tu portafolio?",
    "btns": [("📊 Simulador", RUTAS['simulador']),
             ("💡 Recomendaciones", RUTAS['recomendaciones'])]
},

# ─── OPCIONES Y FUTUROS ──────────────────────────────────────────
"opciones|futuros|derivatives|derivados|call|put|strike|contrato futuro|forwards": {
    "titulo": "🎯 Derivados — Opciones y Futuros (Avanzado)",
    "cuerpo": """Los **derivados** son contratos cuyo valor depende de otro activo subyacente (acciones, commodities, divisas).

**Opciones:**

Una opción es el DERECHO (no obligación) de comprar o vender un activo a un precio fijo (strike) en una fecha futura.

**Tipos:**
• **Call (Opción de compra):** Derecho a COMPRAR
• **Put (Opción de venta):** Derecho a VENDER

**Ejemplo — Call sobre Ecopetrol:**
Compras una call de Ecopetrol a $2.600 con expiración en 1 mes
• Si Ecopetrol sube a $3.000: Ejerces → Compras a $2.600, vendes a $3.000 = Ganancia $400
• Si Ecopetrol baja a $2.400: NO ejerces, pierdes solo la prima (lo que pagaste)

**Ventaja:** Apalancamiento (controlas mucho dinero con poco capital)
**Desventaja:** Pérdida total del capital invertido en opciones

---

**Futuros:**

Un futuro es un CONTRATO OBLIGATORIO de comprar/vender un activo a un precio fijo en una fecha futura.

**Diferencia con opciones:**
• Opción: Derecho (puedes no ejercer)
• Futuro: Obligación (DEBES liquidar)

**Ejemplo — Futuro de café:**
Agricultor vende futuro de café a $2.000/kg
Esto le garantiza un precio fijo independientemente de variaciones del mercado

**Riesgo:**
Si el precio cae a $1.500, igual recibe $2.000 → GANANCIA
Si el precio sube a $3.000, solo recibe $2.000 → PÉRDIDA

---

**⚠️ ADVERTENCIA IMPORTANTE:**
Opciones y futuros son instrumentos ALTAMENTE ESPECULATIVOS. Solo para expertos.
El 95% de principiantes pierde dinero con derivados.
Requieren depósitos de garantía (margin) que pueden ser liquidados automáticamente.""",
    "sug": "Estos instrumentos requieren experiencia. ¿Quieres aprender a construir portafolios conservadores primero?",
    "btns": [("📚 Aprende más", RUTAS['aprende']),
             ("💡 Recomendaciones", RUTAS['recomendaciones'])]
},

# ─── FOREX ───────────────────────────────────────────────────────
"forex|divisas|dólar|euro|libra|trading de divisas|cambio moneda|tipo de cambio|tasa de cambio": {
    "titulo": "💱 FOREX — Trading de Divisas",
    "cuerpo": """**FOREX** es el mercado de divisas. Es el mercado financiero más grande del mundo (~$7 billones diarios).

**¿Cómo funciona?**

Una divisa se cotiza siempre en pares: USD/COP (Dólar vs Peso Colombiano)

USD/COP = 4.100
→ 1 dólar = 4.100 pesos

Si crees que el dólar SUBIRÁ:
Compras USD/COP. Si sube a 4.150, ganas en dólares.

Si crees que el dólar BAJARÁ:
Vendes USD/COP en corto.

**Características:**
• Mercado abierto 24/5 (cierra fin de semana)
• Máximo apalancamiento (~500:1 en brokers internacionales)
• Spreads muy bajos (~2 pips)
• Volatilidad alta

**Pares principales (Majors):**
EUR/USD, GBP/USD, USD/JPY, etc.

**Pares emergentes (Exoticos):**
USD/COP (Dólar-Peso), USD/MXN (Dólar-Peso Mexicano), etc.

**⚠️ RIESGOS:**
1. Apalancamiento extremo = pérdidas amplificadas
2. Volatilidad geopolítica (guerras, anuncios Fed)
3. Manipulación de brokers no regulados
4. El 95% de traders retail PIERDEN

**Estafas comunes:**
• Brokers sin regulación (offshore)
• Promesas de "rentabilidad garantizada"
• Señales de trading "100% confiables"
• Plataformas copiadas de brokers legales

💡 El FOREX legítimo requiere educación seria y años de experiencia. NO es un atajo al dinero.""",
    "sug": "Si buscas inversión con divisas de bajo riesgo, ¿quieres conocer sobre fondos dolarizados?",
    "btns": [("📚 Aprende más", RUTAS['aprende']),
             ("💡 Recomendaciones", RUTAS['recomendaciones'])]
},

# ─── FONDOS INDEXADOS ────────────────────────────────────────────
"fondos indexados|fondo índice|index funds|etf|fondos pasivos|colcap|índice accionario": {
    "titulo": "📊 Fondos Indexados — Inversión pasiva inteligente",
    "cuerpo": """Un **fondo indexado** replica el desempeño de un índice (como el Colcap o el S&P 500).

**¿Por qué?**
La mayoría de administradores activos NO pueden vencer al mercado. Los fondos indexados sí, porque SIMPLEMENTE REPLICAN el índice.

**Ejemplo — Fondo COLCAP:**
El Colcap agrupa las 20 acciones más grandes de Colombia.
Un fondo indexado compra todas esas 20 acciones en las mismas proporciones.

**Ventajas vs Fondos Activos:**

| Aspecto | Fondo Activo | Fondo Indexado |
|---|---|---|
| Comisión | 1-3% anual | 0.1-0.5% anual |
| Rendimiento promedio | Pierde vs índice | Iguala al índice |
| Transparencia | Baja | Alta |
| Volatilidad | Alta | Igual al índice |

**Estadística probada:**
En 15 años, el 87% de fondos activos no vencen al S&P 500 (pasivo).

**ETFs (Exchange Traded Funds):**
Fondos indexados que cotizan en bolsa como acciones.
Pueden comprarse y venderse durante el día (más liquidez que fondos tradicionales).

**Fondos indexados principales en Colombia:**
• SURA Fondo Índice Accionario
• Skandia Fondo Índice Colcap
• Credicorp Fondo Índice S&P 500

**¿Cuándo comprar fondos indexados?**
• Eres principiante y no tienes tiempo de investigar
• Quieres rentabilidad con bajo mantenimiento
• Tienes horizonte de largo plazo (>10 años)

💡 Warren Buffett recomienda fondos indexados para la mayoría de inversores. Es la inversión más inteligente después de tener fondo de emergencia.""",
    "sug": "¿Quieres comparar diferentes fondos indexados disponibles en Colombia?",
    "btns": [("📚 Aprende más", RUTAS['aprende']),
             ("💡 Recomendaciones", RUTAS['recomendaciones'])]
},

# ─── SEGUROS ─────────────────────────────────────────────────────
"seguro|seguros|póliza|cobertura|seguro de vida|seguro automotor|seguro hogar|aseguranza": {
    "titulo": "🛡️ Seguros — Protección financiera",
    "cuerpo": """Un **seguro** es un contrato donde pagas una prima (cuota) para transferir el riesgo de un evento a una aseguradora.

**Tipos principales:**

**Seguros de Vida:**
• Vida temporal: Protege por X años. Es barato (~$20-50/mes)
• Vida permanente: Protege toda la vida. Más caro pero incluye componente de ahorro

Regla: Asegura 10-12x tu ingreso anual
Si ganas $2.000.000/año → Póliza de ~$24.000.000

**Seguro Automotor (Obligatorio):**
Responsabilidad civil: Te cubre si causas daño a terceros
Cobertura integral: Cubre daños a tu auto también

**Seguro de Hogar:**
Cubre robo, incendio, daños naturales

**Seguros de Salud:**
• EPS (Régimen contributivo): Básico, obligatorio si tienes empleo
• Medicina prepagada: Privada, mejor cobertura, más caro
• ARL (Riesgos laborales): Si eres empleado, ya está cubierto

---

**¿Es el seguro una inversión?**
NO. El seguro es PROTECCIÓN, no inversión.
El dinero que ahorres EN SEGUROS baratos lo INVIERTES en CDT, acciones o fondos.

**Ejemplo:**
Seguro de vida temporal: $30/mes
Seguro de vida permanente: $300/mes

La diferencia ($270/mes) la INVIERTES en CDT al 12% anual
En 30 años: ~$250.000.000 vs posiblemente $0 de ganancia en seguro permanente

💡 Necesitas seguros de RESPONSABILIDAD CIVIL. Los de ahorro son una trampa financiera.""",
    "sug": "¿Necesitas calcular cuánta cobertura de seguro es adecuada para tu situación?",
    "btns": [("📚 Aprende más", RUTAS['aprende']),
             ("👤 Mi perfil", RUTAS['perfil'])]
},

# ─── PLANIFICACIÓN TRIBUTARIA ────────────────────────────────────
"planificación tributaria|optimización fiscal|deducción|crédito fiscal|exención|incentivos tributarios|reforma tributaria": {
    "titulo": "🧾 Planificación Tributaria Avanzada",
    "cuerpo": """**Planificación tributaria** es organizar tus finanzas LEGALMENTE para pagar la menor cantidad de impuestos posible.

**No es evasión (ilegal), es optimización (legal).**

**Deducciones disponibles en Colombia 2024:**

1. **Aportes voluntarios a pensión:** Hasta 30% del ingreso
   Deducción tributaria: ~19-39% del aporte
   $300.000 aportados = $57.000 - $117.000 en ahorro fiscal

2. **Intereses hipotecarios:** Hasta $21.629.000/año
   Solo para crédito hipotecario para vivienda propia

3. **Donaciones a ONGS reconocidas:** 100% deducible (algunos casos)

4. **Medicina prepagada:** 100% deducible si no usas EPS

5. **Gastos de educación:** Parcialmente deducibles

6. **Pérdidas del ejercicio anterior:** Se trasladan al siguiente

---

**Estructuración legal:**

Si eres independiente/profesional:
• Constituirse como persona jurídica (SAS) puede beneficiarte
• Separar ingresos y gastos adecuadamente
• Documentar TODOS los gastos

**Plazos de prescripción:**
La DIAN tiene 5 años para auditarte (6 años si hay indicio de fraude)

**⚠️ Multas por evasión:**
• Multa: 100-200% del impuesto evadido
• Intereses: 1-2% mensual
• Cárcel: Hasta 8 años para casos graves

💡 Más dinero se pierde por dejar de usar deducciones legales que por pagar impuestos correctamente. Consulta un contador.""",
    "sug": "¿Quieres calcular cuánto podrías ahorrar con aportes voluntarios a pensión?",
    "btns": [("📈 Simular pensión voluntaria", RUTAS['simulador']),
             ("🧾 Aprende más", RUTAS['aprende'])]
},

# ─── CRÉDITO HIPOTECARIO ─────────────────────────────────────────
"hipoteca|crédito hipotecario|credito hipotecario|mortgage|tasa hipotecaria|cuota hipotecaria": {
    "titulo": "🏠 Crédito Hipotecario — Compra de vivienda",
    "cuerpo": """Un **crédito hipotecario** es un préstamo para comprar una vivienda. La propiedad queda como garantía.

**Requisitos en Colombia:**

• Capacidad de pago: Ingresos suficientes (relación cuota/ingreso ~40-50%)
• Activos: Antecedentes de crédito limpios
• Antigüedad laboral: Mínimo 6-12 meses en el empleo
• Capital inicial: 10-30% del valor de la propiedad

**Simulación real:**

Vivienda: $150.000.000
Capital inicial (20%): $30.000.000
Préstamo solicitado: $120.000.000
Plazo: 20 años (240 meses)
Tasa: 8% anual

Cuota mensual ≈ $1.010.000

**Costos adicionales:**
• Tasación: 0.5-1% del valor
• Escritura pública: 1-2% del valor
• Registro catastral: ~$100.000
• Seguros: Incendio, terremoto (obligatorios)
• Mantenimiento: 1-3% anual del valor

**Tipos de tasa:**
• **Tasa fija:** No cambia. Predecible pero tasa inicial más alta
• **Tasa variable:** Ajusta con DTF o IBR. Riesgo si suben tasas
• **Mixta:** Fija primeros años, luego variable

**¿Cuándo comprar vivienda con crédito?**
✅ Si planeas vivir >7 años (los primeros años vas principalmente a intereses)
✅ Si tu ingreso es estable
✅ Si tienes fondo de emergencia aparte
❌ Si está en crisis laboral
❌ Si no tienes capital inicial (>10%)

**Cálculo del poder adquisitivo:**
Ingreso mensual: $3.000.000
Máximo recomendado en cuota (30%): $900.000
Con tasa 8% a 20 años: Puedes pedir ~$110.000.000

💡 No compres la casa MÁS cara que puedas pedir. Compra la que necesites.""",
    "sug": "¿Quieres simular cuota y cantidad de vivienda que podrías financiar?",
    "btns": [("📈 Simulador", RUTAS['simulador']),
             ("💡 Recomendaciones", RUTAS['recomendaciones'])]
},

# ─── LEASING Y ARRENDAMIENTO ─────────────────────────────────────
"leasing|arrendamiento operativo|leasing habitacional|arrendar|alquiler|contrato arrendamiento": {
    "titulo": "🔄 Leasing — Alternativa a compra",
    "cuerpo": """**Leasing** es arriendo a largo plazo con opción de compra al final.

**Leasing Operativo (Vehículos, equipos):**

Características:
• Cuota mensual fija incluye: valor del bien + mantenimiento + seguros
• Riesgo de depreciación: La asume el arrendador
• Al final: Devuelves el bien, NO lo tienes

Ejemplo — Auto:
Valor auto: $30.000.000
Cuota leasing: $750.000/mes (36 meses)
Incluye: Mantenimiento, neumáticos, póliza todo riesgo

Ventajas:
✅ Cuota baja vs financiar + mantener
✅ Auto nuevo siempre (garantía)
✅ Sin riesgo de depreciación

Desventajas:
❌ Millas limitadas (~1.500/mes, pagar extra si excedes)
❌ Desgaste normal contado en inspección final
❌ No es tuyo

---

**Leasing Habitacional (Vivienda):**

Es arriendo a largo plazo con opción de compra.

Ventaja: Puedes "probar" vivir en una zona antes de comprar

---

**Leasing vs Comprar Auto:**

| Aspecto | Leasing | Financiar |
|---|---|---|
| Cuota | $750 | $500 + gastos |
| Mantenimiento | Incluido | Por tu cuenta |
| Depreciación | Asume arrendador | Tú pierdes ~40-50% |
| Al terminar | Devuelves | Te pertenece |
| Mejor para | Quien quiere nuevo | Quien maneja mucho |

💡 Si cambias auto cada 3-4 años: Leasing.
Si cambias cada 8-10 años: Comprar.""",
    "sug": "¿Quieres calcular cuál es más conveniente para ti: leasing o crédito automotor?",
    "btns": [("📈 Simulador", RUTAS['simulador']),
             ("💡 Recomendaciones", RUTAS['recomendaciones'])]
},

# ─── NETWORTH Y RATIO FINANCIEROS ──────────────────────────────────
"networth|net worth|patrimonio neto|assets|liabilities|activos pasivos|balance personal|solvencia|ratios financieros": {
    "titulo": "📊 Net Worth — Tu patrimonio neto",
    "cuerpo": """**Net Worth (Patrimonio Neto)** = ACTIVOS - PASIVOS

Es el valor real que posees después de pagar todas tus deudas.

**Cálculo:**

ACTIVOS (Lo que tienes):
• Dinero en efectivo: $500.000
• Banco: $3.000.000
• CDT: $5.000.000
• Auto: $20.000.000
• Vivienda: $150.000.000
• Acciones: $2.000.000
Total Activos: $180.500.000

PASIVOS (Lo que debes):
• Crédito auto: $15.000.000
• Tarjeta de crédito: $2.000.000
• Crédito personal: $1.000.000
Total Pasivos: $18.000.000

NET WORTH = $180.500.000 - $18.000.000 = **$162.500.000**

---

**Ratios Financieros Personales:**

**1. Ratio de Liquidez = Activos Líquidos / Pasivos Mensuales**
Cuántos meses puedes mantener tu estilo de vida sin ingresos.
> 6 meses es excelente

**2. Ratio Deuda/Ingresos = Deudas Totales / Ingresos Anuales**
< 2x es saludable
> 4x es riesgoso

**3. Ratio de Ahorro = Ahorro Anual / Ingresos Anuales**
>20% es excelente

**4. Ratio Endeudamiento = Pasivos / Activos**
< 30% es excelente
> 70% es riesgoso

---

**¿Por qué importa tu Net Worth?**
1. Mide tu verdadera riqueza
2. Te muestra si estás avanzando
3. Base para decisiones (¿puedes pedir un crédito?)
4. Motivación: Aumentarlo anualmente es el objetivo

**Meta:** Incrementar net worth 20-30% anual

💡 El objetivo no es tener mucho ingreso. Es tener mucho patrimonio neto (activos - deudas).""",
    "sug": "¿Quieres calcular tu net worth y ver cómo ha evolucionado?",
    "btns": [("📊 Mis finanzas", RUTAS['finanzas']),
             ("📈 Dashboard", RUTAS['dashboard'])]
},

}  # fin BASE


# ══════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL  ─  FinanBotIA
# ══════════════════════════════════════════════════════════════════

class FinanBotIA:
    MAX_HISTORIAL = 20

    def __init__(self):
        self.historial: deque = deque(maxlen=self.MAX_HISTORIAL)
        self.memoria = {
            'ultimo_tema': 'general',
            'ultimo_objetivo': None,
            'ultimo_balance': None,
            'resumen': [],
            'historial_reciente': [],
        }

    # ── API pública ───────────────────────────────────────────────

    def responder_con_acciones(
        self,
        mensaje: str,
        ctx: dict | None,
        accion: dict | None,
    ) -> tuple[str, list[dict]]:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.historial.append({'rol': 'usuario', 'msg': mensaje, 'timestamp': ts})
        self._actualizar_memoria(mensaje, ctx)
        respuesta, acciones_ui = self._generar(mensaje, ctx, accion)
        respuesta = self._personalizar_respuesta(respuesta, mensaje, ctx)
        self.historial.append({'rol': 'bot', 'msg': respuesta[:200], 'timestamp': ts})
        return respuesta, acciones_ui

    # ── Router principal ──────────────────────────────────────────

    def _generar(self, mensaje, ctx, accion):
        if accion is None:
            return self._sin_accion(mensaje, ctx)

        tipo = accion.get('tipo', '')

        # Bienvenida
        if tipo == 'bienvenida':
            return self._bienvenida(accion, ctx), _btns_bienvenida()

        # Calculadora financiera
        mapa_calc = {
            'descuento':    self._descuento,
            'iva_sumado':   self._iva,
            'iva_descontado': self._iva,
            'propina':      self._propina,
            'aumento':      self._aumento,
            'reparto':      self._reparto,
            'porcentaje_de': self._porcentaje,
            'interes_simple': self._interes_simple,
            'interes_compuesto': self._interes_compuesto,
            'saldo_restante': self._saldo_restante,
            'calculo':      self._calculo,
        }
        if tipo in mapa_calc:
            return mapa_calc[tipo](accion), _btns_calc()

        # Transacciones
        if tipo == 'gasto_registrado':
            return self._gasto_reg(accion, ctx), _btns_trans()
        if tipo == 'ingreso_registrado':
            return self._ingreso_reg(accion, ctx), _btns_trans()
        if tipo == 'gasto_eliminado':
            return self._eliminado('gasto', accion), _btns_trans()
        if tipo == 'ingreso_eliminado':
            return self._eliminado('ingreso', accion), _btns_trans()

        # Metas
        if tipo == 'meta_creada':
            return self._meta_creada(accion, ctx), _btns_metas()
        if tipo == 'meta_actualizada':
            return self._meta_actualizada(accion), _btns_metas()
        if tipo == 'meta_eliminada':
            return f"🗑️ Meta **{accion['nombre']}** eliminada correctamente.", _btns_metas()
        if tipo == 'consulta_metas':
            return self._consulta_metas(accion), _btns_metas()

        # Consultas
        if tipo == 'consulta_gastos':
            return self._gastos(accion), _btns_finanzas()
        if tipo == 'consulta_ingresos':
            return self._ingresos(accion), _btns_finanzas()
        if tipo == 'consulta_resumen':
            return self._resumen(accion, ctx), _btns_resumen()

        # Simulación
        if tipo == 'simulacion_realizada':
            return self._simulacion(accion), _btns_simulacion(accion)

        # Perfil
        if tipo == 'salario_actualizado':
            s = accion['nuevo_salario']
            return (f"✅ Salario actualizado a **${s:,.0f}**.\n\n"
                    f"💡 La regla 20% sugiere ahorrar **${int(s*0.2):,.0f}/mes**."), _btns_perfil()
        if tipo == 'meta_mensual_actualizada':
            m = accion['nuevo_monto']
            return f"✅ Meta mensual de ahorro actualizada a **${m:,.0f}**.", _btns_perfil()
        if tipo == 'perfil_actualizado':
            campo = accion.get('campo', '')
            valor = accion.get('valor', '')
            msgs = {
                'nombre': f"✅ Tu nombre ahora es **{valor}**. ¡Hola, {valor}! 👋",
                'correo': f"✅ Correo actualizado a **{valor}**.",
            }
            return msgs.get(campo, f"✅ Perfil actualizado: {campo} → {valor}"), _btns_perfil()

        # Reporte
        if tipo == 'reporte':
            fmt = accion.get('formato', 'pdf')
            return self._reporte(fmt), _btns_reporte(fmt)

        # Estados especiales
        if tipo in ('confirmar_eliminar_meta', 'confirmar_eliminar_gasto',
                    'confirmar_eliminar_ingreso'):
            return (f"🤔 {accion.get('mensaje', '¿Confirmas?')}\n\n"
                    "Dime el nombre o monto exacto para eliminarlo de forma segura."), []
        if tipo == 'sin_datos':
            return (f"📭 No tienes {accion.get('contexto','registros')} aún.\n\n"
                    "¿Quieres agregar uno? Solo dime qué fue y el monto."), _btns_finanzas()
        if tipo == 'pide_monto':
            textos = {
                'gasto':      "💬 ¿De cuánto fue el gasto?",
                'ingreso':    "💬 ¿Cuánto recibiste?",
                'meta':       "💬 ¿Cuánto quieres ahorrar en esta meta?",
                'simulacion': "💬 ¿Cuánto dinero quieres simular? Dime también la tasa y el plazo.",
            }
            return textos.get(accion.get('contexto',''), "💬 ¿De cuánto es?"), []
        if tipo == 'error':
            return (f"⚠️ {accion.get('mensaje','Ocurrió un error.')}\n\n"
                    "Por favor intenta de nuevo."), []

        return self._sin_accion(mensaje, ctx)

    # ══════════════════════════════════════════════════════════════
    #  BIENVENIDA INTELIGENTE
    # ══════════════════════════════════════════════════════════════

    def _bienvenida(self, a, ctx):
        nombre  = a.get('nombre', 'Usuario')
        resumen = a.get('resumen', {})
        hora    = datetime.now().hour
        saludo  = "¡Buenos días" if hora < 12 else ("¡Buenas tardes" if hora < 18 else "¡Buenas noches")
        emoji   = "🌅" if hora < 12 else ("☀️" if hora < 18 else "🌙")

        lineas = [
            f"{saludo}, **{nombre}**! {emoji} Soy **FinanBot** 🤖, tu asistente financiero inteligente.\n",
            "**Soy una IA** (Inteligencia Artificial) entrenada para ayudarte con tus finanzas.\n",
            "✅ Puedo registrar, calcular y analizar  |  ⚠️ Mis consejos son orientativos, no una asesoría legal\n"
        ]

        n_trans = resumen.get('num_transacciones', 0)
        if n_trans > 0:
            bal  = resumen['balance']
            ico  = "📈" if bal >= 0 else "📉"
            lineas.append(
                f"\n{ico} **Tu estado financiero:**\n"
                f"• Balance: **${bal:,.0f}**\n"
                f"• Ingresos: ${resumen['total_ingresos']:,.0f}  |  Gastos: ${resumen['total_gastos']:,.0f}\n"
                f"• Metas activas: {resumen['num_metas']}  |  Movimientos: {n_trans}\n"
            )
            if bal < 0:
                lineas.append("⚠️ *Tu balance está negativo. ¿Quieres que revisemos tus gastos?*\n")
            elif resumen['total_ingresos'] > 0:
                pct = round(bal / resumen['total_ingresos'] * 100)
                if pct >= 20:
                    lineas.append(f"✅ *¡Excelente! Estás ahorrando el {pct}% de tus ingresos.*\n")
                else:
                    lineas.append(f"💡 *Estás ahorrando el {pct}% de tus ingresos. La meta es llegar al 20%.*\n")
        else:
            lineas.append("\nAún no tienes movimientos registrados. ¡Empecemos ahora!\n")

        lineas.append("**¿Qué puedo hacer por ti?** 💡\n")
        lineas.append("• 💸 Registrar gastos e ingresos  •  🎯 Crear metas de ahorro")
        lineas.append("• 📈 Simular inversiones  •  🏷️ Calcular descuentos e IVA")
        lineas.append("• 🧮 Resolver cálculos  •  💬 Responder dudas financieras")
        lineas.append("• 📄 Generar reportes  •  👤 Actualizar tu perfil\n")
        lineas.append("*Habla conmigo de forma natural. No necesitas comandos exactos.* 😊\n")
        lineas.append("_🔒 Tus datos están protegidos. Confidencialidad garantizada._")

        return "\n".join(lineas)

    # ══════════════════════════════════════════════════════════════
    #  CALCULADORA FINANCIERA  ─  respuestas con tabla
    # ══════════════════════════════════════════════════════════════

    def _descuento(self, a):
        orig, pct = a['precio_original'], a['porcentaje']
        desc, fin = a['valor_descuento'], a['precio_final']
        return (
            f"🏷️ **Descuento del {pct}%**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Precio original | ${orig:,.0f} |\n"
            f"| Descuento ({pct}%) | −${desc:,.0f} |\n"
            f"| **Precio final** | **${fin:,.0f}** |\n\n"
            f"💰 *Ahorras ${desc:,.0f} con esta oferta.*"
        )

    def _iva(self, a):
        if a['tipo'] == 'iva_sumado':
            base, tasa, iva, tot = a['base'], a['tasa_iva'], a['valor_iva'], a['total']
            return (
                f"🧾 **Precio con IVA del {tasa}%**\n\n"
                f"| | Valor |\n|---|---|\n"
                f"| Base sin IVA | ${base:,.0f} |\n"
                f"| IVA ({tasa}%) | +${iva:,.0f} |\n"
                f"| **Total con IVA** | **${tot:,.0f}** |\n\n"
                f"📌 *IVA general en Colombia: 19%. Se usó {tasa}%.*"
            )
        tot, tasa, base, iva = a['valor_con_iva'], a['tasa_iva'], a['base_sin_iva'], a['valor_iva']
        return (
            f"🧾 **Precio sin IVA ({tasa}%)**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Precio con IVA | ${tot:,.0f} |\n"
            f"| IVA incluido ({tasa}%) | −${iva:,.0f} |\n"
            f"| **Base sin IVA** | **${base:,.0f}** |"
        )

    def _propina(self, a):
        c, p, prop, tot = a['cuenta'], a['porcentaje'], a['propina'], a['total']
        return (
            f"🍽️ **Propina del {p}%**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Cuenta | ${c:,.0f} |\n"
            f"| Propina ({p}%) | +${prop:,.0f} |\n"
            f"| **Total a pagar** | **${tot:,.0f}** |"
        )

    def _aumento(self, a):
        orig, p, aum, nuevo = a['valor_original'], a['porcentaje'], a['valor_aumento'], a['valor_nuevo']
        return (
            f"📊 **Aumento del {p}%**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Valor original | ${orig:,.0f} |\n"
            f"| Aumento ({p}%) | +${aum:,.0f} |\n"
            f"| **Nuevo valor** | **${nuevo:,.0f}** |"
        )

    def _reparto(self, a):
        tot, pers, pp = a['total'], a['personas'], a['por_persona']
        rnd = int(pp // 1000 * 1000 + 1000)
        return (
            f"➗ **Reparto entre {pers} personas**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Total | ${tot:,.0f} |\n"
            f"| Personas | {pers} |\n"
            f"| **Le toca a cada uno** | **${pp:,.0f}** |\n\n"
            f"💡 *Para redondear: cada uno paga ${rnd:,.0f}*"
        )

    def _porcentaje(self, a):
        parte, tot, pct = a['parte'], a['total'], a['porcentaje']
        return (
            f"📐 **Porcentaje calculado**\n\n"
            f"${parte:,.0f} representa el **{pct}%** de ${tot:,.0f}.\n\n"
            f"*Fórmula: ({parte:,.0f} ÷ {tot:,.0f}) × 100 = {pct}%*"
        )

    def _interes_simple(self, a):
        cap, tasa, plazo = a['capital'], a['tasa_anual'], a['plazo_meses']
        intg, tot = a['interes_ganado'], a['total']
        return (
            f"💵 **Interés simple**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Capital | ${cap:,.0f} |\n"
            f"| Tasa anual | {tasa}% |\n"
            f"| Plazo | {plazo} meses |\n"
            f"| Interés ganado | +${intg:,.0f} |\n"
            f"| **Total al vencer** | **${tot:,.0f}** |\n\n"
            f"💡 *Con interés compuesto ganarías más. ¿Quieres simular?*"
        )

    def _interes_compuesto(self, a):
        cap, tasa, plazo = a['capital'], a['tasa_anual'], a['plazo_meses']
        final, gan = a['valor_final'], a['ganancia']
        return (
            f"📈 **Interés compuesto**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Capital inicial | ${cap:,.0f} |\n"
            f"| Tasa anual | {tasa}% |\n"
            f"| Plazo | {plazo} meses |\n"
            f"| **Monto final** | **${final:,.0f}** |\n"
            f"| Ganancia | +${gan:,.0f} |"
        )

    def _saldo_restante(self, a):
        tot, gasto, rest = a['total'], a['gasto'], a['restante']
        ico = "✅" if rest >= 0 else "⚠️"
        return (
            f"{ico} **Saldo restante**\n\n"
            f"| | Valor |\n|---|---|\n"
            f"| Disponible | ${tot:,.0f} |\n"
            f"| Gasto | −${gasto:,.0f} |\n"
            f"| **Te queda** | **${rest:,.0f}** |"
        )

    def _calculo(self, a):
        res = a['resultado']
        op  = a.get('operacion', '')
        return f"🧮 El resultado es **{res:,.2f}**\n\n*Operación: {op}*"

    # ══════════════════════════════════════════════════════════════
    #  TRANSACCIONES
    # ══════════════════════════════════════════════════════════════

    def _gasto_reg(self, a, ctx):
        monto, cat = a['monto'], a['categoria']
        lineas = [f"{_ok()} Gasto registrado.\n\n💸 **${monto:,.0f}** en **{cat}**\n"]
        if ctx:
            bal  = ctx.get('balance', 0) - monto
            lineas.append(f"📊 Balance actualizado: **${bal:,.0f}**")
            meta_m = ctx.get('meta_ahorro_mensual', 0)
            tot_g  = ctx.get('total_gastos', 0) + monto
            if meta_m > 0 and tot_g > ctx.get('meta_ahorro_mensual', 0) * 3:
                lineas.append(f"\n⚠️ {_tip()} Tus gastos registrados suman ${tot_g:,.0f}. ¡Ojo con el presupuesto!")
        return "\n".join(lineas)

    def _ingreso_reg(self, a, ctx):
        monto, cat = a['monto'], a['categoria']
        lineas = [f"{_ok()} Ingreso registrado.\n\n💰 **+${monto:,.0f}** en **{cat}**\n"]
        if ctx:
            bal = ctx.get('balance', 0) + monto
            lineas.append(f"📊 Balance actualizado: **${bal:,.0f}**")
            lineas.append(f"\n💡 *Regla del 20%: guarda **${int(monto*0.2):,.0f}** de este ingreso.*")
        return "\n".join(lineas)

    def _eliminado(self, tipo_t, a):
        monto, cat = a['monto'], a['categoria']
        ico = "💸" if tipo_t == 'gasto' else "💰"
        return (f"🗑️ {tipo_t.capitalize()} eliminado.\n\n"
                f"{ico} **${monto:,.0f}** en **{cat}** fue removido de tu historial.")

    # ══════════════════════════════════════════════════════════════
    #  METAS
    # ══════════════════════════════════════════════════════════════

    def _meta_creada(self, a, ctx):
        nombre, monto = a['nombre'], a['monto']
        lineas = [f"🎯 ¡Meta creada!\n\n**{nombre}** — objetivo: ${monto:,.0f}\n"]
        if ctx:
            meta_m = ctx.get('meta_ahorro_mensual', 0)
            if meta_m > 0:
                meses = round(monto / meta_m)
                lineas.append(f"📅 Ahorrando **${meta_m:,.0f}/mes**, la alcanzas en **{meses} meses**.")
        lineas.append("\n💡 Cuéntame cuando quieras actualizar tu progreso.")
        return "\n".join(lineas)

    def _meta_actualizada(self, a):
        nombre, nuevo = a['nombre'], a['nuevo_monto']
        return f"✅ Meta actualizada.\n\n**{nombre}** → progreso: **${nuevo:,.0f}**"

    def _consulta_metas(self, a):
        metas = a.get('metas', [])
        if not metas:
            return "📭 Aún no tienes metas. ¿Quieres crear una? Dime el monto y el objetivo."
        lineas = ["🎯 **Tus metas de ahorro:**\n"]
        for m in metas:
            barra  = self._barra(m['porcentaje'])
            estado = "✅ Completada" if m['completada'] else f"{m['porcentaje']}%"
            lineas.append(f"**{m['nombre']}**\n  {barra} {estado}\n  ${m['actual']:,.0f} de ${m['objetivo']:,.0f}\n")
        return "\n".join(lineas)

    # ══════════════════════════════════════════════════════════════
    #  CONSULTAS
    # ══════════════════════════════════════════════════════════════

    def _gastos(self, a):
        tot  = a.get('total_gastos', 0)
        n    = a.get('num_gastos', 0)
        cats = a.get('gastos_por_categoria', {})
        rec  = a.get('recientes', [])
        lineas = [f"💸 **Tus gastos**\n\nTotal: **${tot:,.0f}** en {n} movimiento(s).\n"]
        if cats:
            lineas.append("**Por categoría:**")
            for cat, monto in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:5]:
                pct = round(monto / tot * 100) if tot > 0 else 0
                lineas.append(f"  • {cat}: ${monto:,.0f} ({pct}%)")
        if rec:
            lineas.append("\n**Últimos movimientos:**")
            for t in rec[:4]:
                lineas.append(f"  • {t['categoria']}: ${t['monto']:,.0f} — {t['fecha']}")
        return "\n".join(lineas)

    def _ingresos(self, a):
        tot = a.get('total_ingresos', 0)
        n   = a.get('num_ingresos', 0)
        rec = a.get('recientes', [])
        lineas = [f"💰 **Tus ingresos**\n\nTotal: **${tot:,.0f}** en {n} movimiento(s).\n"]
        if rec:
            lineas.append("**Últimos ingresos:**")
            for t in rec[:5]:
                lineas.append(f"  • {t['categoria']}: ${t['monto']:,.0f} — {t['fecha']}")
        return "\n".join(lineas)

    def _resumen(self, a, ctx):
        bal  = a.get('balance', 0)
        ing  = a.get('total_ingresos', 0)
        gas  = a.get('total_gastos', 0)
        n_m  = a.get('num_metas', 0)
        n_t  = a.get('num_transacciones', 0)
        cats = a.get('gastos_por_categoria', {})
        ico  = "📈" if bal >= 0 else "📉"

        lineas = [
            f"{ico} **Resumen financiero**\n",
            f"| Concepto | Valor |",
            f"|---|---|",
            f"| 💰 Ingresos | ${ing:,.0f} |",
            f"| 💸 Gastos | ${gas:,.0f} |",
            f"| 📊 Balance | **${bal:,.0f}** |",
            f"| 🎯 Metas activas | {n_m} |",
            f"| 📋 Movimientos | {n_t} |\n",
        ]

        if cats:
            mayor = max(cats, key=cats.get)
            lineas.append(f"📌 *Mayor gasto: **{mayor}** (${cats[mayor]:,.0f})*\n")

        if bal < 0:
            lineas.append("⚠️ *Balance negativo. ¿Hay ingresos sin registrar o gastos que puedas reducir?*")
        elif ing > 0:
            pct = round(bal / ing * 100)
            if pct >= 20:
                lineas.append(f"✅ *¡Excelente! Estás ahorrando el {pct}% de tus ingresos. Sigue así.*")
            elif pct > 0:
                lineas.append(f"💡 *Estás ahorrando el {pct}% de tus ingresos. La meta ideal es el 20%.*")
            else:
                lineas.append("💡 *Tu balance está en cero. Intenta separar aunque sea el 5% de ahorro.*")
        return "\n".join(lineas)

    # ══════════════════════════════════════════════════════════════
    #  SIMULACIÓN
    # ══════════════════════════════════════════════════════════════

    def _simulacion(self, a):
        cap, tasa = a['capital'], a['tasa']
        plazo, res, gan = a['plazo'], a['resultado'], a['ganancia']
        anos, mr = plazo // 12, plazo % 12
        p_txt = (f"{anos} año{'s' if anos > 1 else ''}" if anos > 0 else "")
        if mr: p_txt += f" {mr} mes{'es' if mr > 1 else ''}"
        return (
            f"📈 **Simulación de inversión**\n\n"
            f"| Concepto | Valor |\n|---|---|\n"
            f"| Capital inicial | ${cap:,.0f} |\n"
            f"| Tasa anual | {tasa}% EA |\n"
            f"| Plazo | {p_txt.strip()} |\n"
            f"| **Total al vencer** | **${res:,.0f}** |\n"
            f"| Ganancia | +${gan:,.0f} |\n\n"
            f"💡 *Simulación con interés compuesto mensual. Los rendimientos reales pueden variar.*"
        )

    # ══════════════════════════════════════════════════════════════
    #  REPORTE
    # ══════════════════════════════════════════════════════════════

    def _reporte(self, fmt):
        if fmt == 'excel':
            return ("📊 **Reporte Excel listo para descargar.**\n\n"
                    "Incluye: ingresos, gastos por categoría, metas, simulaciones y balance.\n"
                    "Haz clic en el botón ↓")
        return ("📄 **Reporte PDF listo para descargar.**\n\n"
                "Incluye: resumen financiero, gráficos de gastos, metas y análisis.\n"
                "Haz clic en el botón ↓")

    # ══════════════════════════════════════════════════════════════
    #  MOTOR DE CONOCIMIENTO  ─  responde CUALQUIER pregunta
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _normalizar_respuesta(texto: str) -> str:
        if not texto:
            return texto
        texto = re.sub(r'(?<!\w)(\d+(?:[.,]\d+)?)\s*%', r'\1 porcentaje', texto)
        return texto.replace('%', 'porcentaje')

    def _detectar_tema(self, mensaje: str) -> str:
        msg = mensaje.lower()
        if any(p in msg for p in ['deuda', 'tarjeta', 'prestamo', 'crédito', 'credito']):
            return 'deuda'
        if any(p in msg for p in ['meta', 'ahorro', 'guardar', 'economizar', 'objetivo']):
            return 'ahorro'
        if any(p in msg for p in ['invers', 'cdt', 'fondo', 'cripto', 'acciones', 'renta']):
            return 'inversion'
        if any(p in msg for p in ['gasto', 'ingreso', 'balance', 'finanzas', 'presupuesto']):
            return 'finanzas'
        return 'general'

    def _actualizar_memoria(self, mensaje: str, ctx: dict | None) -> None:
        tema = self._detectar_tema(mensaje)
        self.memoria['ultimo_tema'] = tema
        if ctx and ctx.get('balance') is not None:
            self.memoria['ultimo_balance'] = ctx.get('balance')
        if ctx and ctx.get('metas'):
            self.memoria['ultimo_objetivo'] = ctx['metas'][0].get('nombre') if isinstance(ctx['metas'], list) and ctx['metas'] else None
        historial = self.memoria.get('resumen', [])
        historial.append(mensaje.strip())
        self.memoria['resumen'] = historial[-6:]

        reciente = self.memoria.get('historial_reciente', [])
        reciente.append(mensaje.strip())
        self.memoria['historial_reciente'] = reciente[-8:]

    def _frase_empatica(self, ctx: dict | None, tema: str) -> str:
        if ctx and ctx.get('balance', 0) < 0:
            return 'Entiendo que este momento puede sentirse pesado, pero vamos paso a paso y lo solucionamos juntos.'
        if ctx and ctx.get('num_metas', 0) > 0:
            return 'Veo que ya estás trabajando en metas, así que te voy a orientar de forma práctica y sencilla.'
        if tema == 'deuda':
            return 'Lo importante ahora es avanzar con calma y sin presión; podemos encontrar una salida clara.'
        if tema == 'ahorro':
            return 'Me alegra que quieras mejorar tu ahorro; pequeños pasos bien hechos marcan la diferencia.'
        return 'Estoy aquí para ayudarte con claridad y sin complicarte la vida.'

    def _sugerencia_personalizada(self, mensaje: str, ctx: dict | None, tema: str) -> str | None:
        if not ctx:
            return None

        balance = ctx.get('balance', 0)
        ingresos = ctx.get('total_ingresos', 0)
        metas = ctx.get('metas', []) or []
        categoria_mayor = ctx.get('categoria_mayor_gasto')

        if balance < 0:
            return 'Tu balance actual está negativo, así que hoy priorizaría registrar todos los gastos y revisar la categoría que más pesa.'

        if ingresos > 0:
            ahorro_pct = round(balance / ingresos * 100) if ingresos else 0
            if ahorro_pct < 20 and tema in {'ahorro', 'finanzas'}:
                return f'Con tus ingresos actuales, un siguiente paso útil sería ahorrar al menos el 20 porcentaje mensual y dejarlo automático.'

        if metas:
            meta_activa = next((m for m in metas if not m.get('completada')), None)
            if meta_activa:
                faltante = max(0, float(meta_activa.get('objetivo', 0)) - float(meta_activa.get('actual', 0)))
                if faltante > 0:
                    return f'Tienes una meta activa: {meta_activa.get("nombre", "tu objetivo")}. Faltan ${faltante:,.0f} para completarla.'

        if categoria_mayor:
            return f'Veo que tu mayor gasto está en {categoria_mayor}; podemos buscar una forma sencilla de reducirlo sin afectar lo esencial.'

        return None

    def _corregir_pedido(self, mensaje: str) -> str | None:
        msg = mensaje.lower()
        if any(p in msg for p in ['ahorrar', 'guardar', 'ahorro']) and re.search(r'(\d+(?:[.,]\d+)?)\s*%', msg):
            pct = None
            for valor in re.findall(r'(\d+(?:[.,]\d+)?)\s*%', mensaje):
                pct = float(valor.replace(',', '.'))
            if pct is not None and pct > 100:
                return (
                    "⚠️ Ese porcentaje parece demasiado alto. Ahorrar más del 100 porcentaje de tus ingresos no es realista para la mayoría de personas. "
                    "Lo más recomendable suele ser entre 10 y 20 porcentaje de tus ingresos, o incluso menos si tu situación está ajustada. "
                    "Si quieres, te ayudo a calcular una meta más sostenible."
                )
        if any(p in msg for p in ['descuento', 'rebaja', 'oferta']) and re.search(r'(\d+(?:[.,]\d+)?)\s*%', msg):
            pct = None
            for valor in re.findall(r'(\d+(?:[.,]\d+)?)\s*%', mensaje):
                pct = float(valor.replace(',', '.'))
            if pct is not None and pct > 100:
                return "⚠️ Un descuento superior al 100 porcentaje no tiene sentido práctico; revisa el dato o el porcentaje que quieres aplicar."
        return None

    def _personalizar_respuesta(self, respuesta: str, mensaje: str, ctx: dict | None) -> str:
        if not respuesta:
            return respuesta

        tema = self._detectar_tema(mensaje)
        if tema != self.memoria.get('ultimo_tema', 'general'):
            self.memoria['ultimo_tema'] = tema

        intro = self._frase_empatica(ctx, tema)
        sugerencia = self._sugerencia_personalizada(mensaje, ctx, tema)
        correccion = self._corregir_pedido(mensaje)

        if correccion:
            respuesta = f"{correccion}\n\n{respuesta}"

        if sugerencia:
            respuesta = f"{respuesta}\n\n💬 {sugerencia}"

        if self.memoria.get('historial_reciente') and len(self.memoria['historial_reciente']) > 1:
            respuesta = f"{respuesta}\n\n🧠 Contexto reciente: {', '.join(self.memoria['historial_reciente'][-3:])}."

        respuesta = f"{intro}\n\n{respuesta}"
        return self._normalizar_respuesta(respuesta)

    def _respuesta_inteligente_contextual(self, mensaje: str, ctx: dict | None) -> str | None:
        msg = mensaje.lower().strip()
        if not msg:
            return None

        if re.search(r'(\d+(?:[.,]\d+)?)\s*%\s*(?:de|del|de los|de las)?\s*(\d+(?:[.,]\d+)?)', msg):
            match = re.search(r'(\d+(?:[.,]\d+)?)\s*%\s*(?:de|del|de los|de las)?\s*(\d+(?:[.,]\d+)?)', msg)
            if match:
                pct = float(match.group(1).replace(',', '.'))
                base = float(match.group(2).replace(',', '.'))
                resultado = round((pct / 100) * base)
                return f"🧮 El {int(pct) if float(pct).is_integer() else pct} porcentaje de {base:,.0f} es **{resultado:,.0f}**."

        if any(p in msg for p in ['mejorar mis finanzas', 'mejorar finanzas', 'quiero mejorar', 'como mejorar', 'cómo mejorar', 'plan financiero', 'mejorar mi dinero']):
            balance = ctx.get('balance', 0) if ctx else 0
            lineas = [
                "🤖 Claro. El mejor camino no es hacer todo a la vez, sino empezar con un plan simple y realista.",
                "1️⃣ Primer paso: registrar ingresos y gastos con claridad.",
                "2️⃣ Segundo: separar un porcentaje fijo para ahorro automático.",
                "3️⃣ Tercero: revisar gastos repetitivos y reducir lo que no aporta valor.",
            ]
            if balance < 0:
                lineas.append(f"Tu balance actual es ${balance:,.0f}, así que hoy priorizaría cortar gastos hormiga y revisar si hay ingresos sin registrar.")
            else:
                lineas.append("Tu balance está en positivo, así que el siguiente paso ideal es automatizar un ahorro mensual y evitar gastos innecesarios.")
            lineas.append("Si me dices tu ingreso mensual, te preparo un plan mucho más preciso.")
            return "\n".join(lineas)

        if any(p in msg for p in ['quiero ahorrar', 'ahorrar más', 'ahorrar mas', 'guardar dinero', 'economizar', 'como ahorrar', 'cómo ahorrar']):
            return (
                "💡 La forma más efectiva de ahorrar es automatizarlo desde el inicio del mes.\n\n"
                "1️⃣ Define una meta concreta y un plazo.\n"
                "2️⃣ Programa una transferencia automática al recibir tu sueldo.\n"
                "3️⃣ Usa una cuenta separada para no gastar ese dinero por impulso.\n\n"
                "Si me dices cuánto ganas, te propongo un plan realista."
            )

        if any(p in msg for p in ['deuda', 'deudas', 'pagar deudas', 'salir de deudas']):
            return (
                "⚠️ Para salir de deudas, lo más útil es priorizar primero las que tienen mayor tasa.\n\n"
                "1️⃣ Haz una lista completa de todas tus deudas.\n"
                "2️⃣ Paga el mínimo en todas, pero dirige el dinero extra a la más costosa.\n"
                "3️⃣ Evita usar más crédito mientras estás cerrando la deuda."
            )

        return None

    def _extraer_monto(self, texto: str) -> int | None:
        n = re.sub(r'(\d)[\.,](\d{3})\b', r'\1\2', texto)
        for patron, mult in [
            (r'\$\s*(\d+(?:\.\d+)?)', None),
            (r'(\d+(?:\.\d+)?)\s*millones?', 1_000_000),
            (r'(\d+(?:\.\d+)?)\s*mil\b', 1_000),
            (r'\b(\d+(?:\.\d+)?)\s*k\b', 1_000),
            (r'\b(\d{4,})\b', 1),
        ]:
            m = re.search(patron, n, re.IGNORECASE)
            if m:
                v = float(m.group(1))
                if mult:
                    return int(v * mult)
                t = texto.lower()
                if 'millon' in t and v < 1_000:
                    return int(v * 1_000_000)
                if 'mil' in t and v < 10_000:
                    return int(v * 1_000)
                return int(v)
        return None

    def _extraer_porcentaje(self, texto: str) -> float | None:
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:%|por\s*ciento)', texto, re.IGNORECASE)
        return float(m.group(1).replace(',', '.')) if m else None

    def _extraer_plazo(self, texto: str) -> int | None:
        m = re.search(r'(\d+)\s*(mes(?:es)?|año(?:s)?)', texto.lower())
        if m:
            v = int(m.group(1))
            return v * 12 if 'año' in m.group(2) else v
        return None

    def _resolver_operacion_directa(self, mensaje: str) -> tuple[str, list[dict]] | None:
        msg = mensaje.lower()
        valor = self._extraer_monto(mensaje)
        pct = self._extraer_porcentaje(mensaje)

        if valor is not None and pct is not None and ('descuento' in msg or 'rebaja' in msg or 'oferta' in msg):
            desc = round(valor * pct / 100, 2)
            final = round(valor - desc, 2)
            return (
                f"🏷️ **Descuento aplicado**\n\n"
                f"Precio original: **${valor:,.0f}**\n"
                f"Descuento: **{pct}%**\n"
                f"Valor del descuento: **${desc:,.0f}**\n"
                f"**Precio final: ${int(final)}**\n"
                f"(equivalente a **${final:,.0f}**)",
                _btns_calc(),
            )

        if valor is not None and pct is not None and ('interés compuesto' in msg or 'interes compuesto' in msg):
            plazo = self._extraer_plazo(mensaje) or 12
            tasa_mensual = pct / 100 / 12
            final = round(valor * ((1 + tasa_mensual) ** plazo), 2)
            ganancia = round(final - valor, 2)
            return (
                f"📈 **Interés compuesto**\n\n"
                f"Capital inicial: **${valor:,.0f}**\n"
                f"Tasa anual: **{pct}%**\n"
                f"Plazo: **{plazo} meses**\n"
                f"**Monto final: ${final:,.0f}**\n"
                f"Ganancia: **${ganancia:,.0f}**",
                _btns_simulacion({'capital': valor, 'tasa': int(pct), 'plazo': plazo}),
            )

        if valor is not None and pct is not None and ('interés simple' in msg or 'interes simple' in msg):
            plazo = self._extraer_plazo(mensaje) or 12
            interes = round(valor * (pct / 100) * (plazo / 12), 2)
            total = round(valor + interes, 2)
            return (
                f"💵 **Interés simple**\n\n"
                f"Capital: **${valor:,.0f}**\n"
                f"Tasa anual: **{pct}%**\n"
                f"Plazo: **{plazo} meses**\n"
                f"Interés generado: **${interes:,.0f}**\n"
                f"**Total: ${total:,.0f}**",
                _btns_calc(),
            )

        if 'simula' in msg or 'simular' in msg or 'simulación' in msg:
            capital = self._extraer_monto(mensaje)
            tasa = pct
            plazo = self._extraer_plazo(mensaje) or 12
            if capital is not None and tasa is not None:
                return (
                    f"📈 **Simulación sugerida**\n\n"
                    f"Capital: **${capital:,.0f}**\n"
                    f"Tasa: **{tasa}% anual**\n"
                    f"Plazo: **{plazo} meses**\n"
                    f"Te dejo el botón para abrir el simulador con esos datos.",
                    _btns_simulacion({'capital': capital, 'tasa': int(tasa), 'plazo': plazo}),
                )

        return None

    def _sin_accion(self, mensaje: str, ctx) -> tuple[str, list[dict]]:
        msg = mensaje.lower()

        respuesta_contextual = self._respuesta_inteligente_contextual(mensaje, ctx)
        if respuesta_contextual:
            return respuesta_contextual, []

        directa = self._resolver_operacion_directa(mensaje)
        if directa is not None:
            return directa[0], directa[1]

        # 1. Buscar en base de conocimiento CON RAZONAMIENTO
        for claves, contenido in BASE.items():
            for clave in claves.split('|'):
                if clave.strip() and clave.strip() in msg:
                    # Agregar contexto personalizado según el tema
                    resp = f"## {contenido['titulo']}\n\n"
                    
                    # Preámbulo inteligente según el tema
                    if any(x in claves for x in ['invertir', 'inversión', 'cdt', 'finca raíz', 'criptomonedas']):
                        resp += ("🤖 *Como IA, te doy información educativa. Consulta con un asesor financiero antes de invertir.*\n\n")
                    
                    if any(x in claves for x in ['deuda', 'tarjeta', 'gota a gota']):
                        resp += ("⚠️ *Si estás en crisis de deudas, busca ayuda profesional o contacta a Asobancaria.*\n\n")
                    
                    resp += f"{contenido['cuerpo']}"
                    
                    if contenido.get('sug'):
                        resp += f"\n\n---\n💬 *{contenido['sug']}*"
                    
                    # Agregar contexto personal del usuario
                    if ctx and ctx.get('num_transacciones', 0) > 0:
                        if any(x in claves for x in ['ahorrar', 'ahorro', 'presupuesto']):
                            bal = ctx.get('balance', 0)
                            if bal > 0:
                                resp += f"\n\n💡 **Tu situación:** Balance actual de **${bal:,.0f}**. ¿Quieres crear una meta específica?"
                            else:
                                resp += f"\n\n💡 **Tu situación:** Balance en **${bal:,.0f}**. Prioriza registrar todos tus ingresos."
                        
                        if any(x in claves for x in ['deuda', 'tarjeta', 'salir de deudas']):
                            gastos = ctx.get('total_gastos', 0)
                            if gastos > 0:
                                resp += f"\n\n💡 **Tu situación:** Gastos registrados por **${gastos:,.0f}**. Podemos analizar dónde optimizar."
                    
                    return resp, []

        # 2. Instrucciones de uso
        if any(p in msg for p in ['cómo registro','como registro','cómo agrego','como agrego',
                                   'cómo uso','como uso','qué comandos','que comandos']):
            return self._como_usar(), []

        # 3. Enseñar a resolver CON RAZONAMIENTO PASO A PASO
        if any(p in msg for p in ['ayudame','ayúdame','necesito ayuda','enséñame','enseñame',
                                   'explícame','explicame','no entiendo','no sé','no se']):
            return self._ensenar_razonamiento(msg, ctx), []

        # 4. Agradecimientos
        if any(p in msg for p in ['gracias','muchas gracias','chevere','excelente','genial',
                                   'perfecto','muy bien','está bien','esta bien']):
            return random.choice([
                "¡Con gusto! 😊 Estoy aquí para lo que necesites.",
                "¡Para eso estoy! 🤝 ¿Hay algo más en lo que te pueda ayudar?",
                "¡Me alegra haberte ayudado! 💙 Cualquier duda, aquí estoy.",
                "🤖 ¡Estoy para servir! ¿Otra pregunta?",
            ]), []

        # 5. Identidad - MEJORADO CON MÁS CLARIDAD
        if any(p in msg for p in ['quién eres','quien eres','qué eres','que eres','cómo te llamas','como te llamas']):
            return (
                "Soy **FinanBot** 🤖, una **IA (Inteligencia Artificial)** creada como proyecto SENA para ayudarte con finanzas personales.\n\n"
                "**¿Qué me diferencia?**\n"
                "✅ Disponible 24/7 para responder dudas  ✅ Rápido en cálculos  ✅ Personalizado a tu contexto\n"
                "⚠️ No reemplazo asesor financiero profesional  ⚠️ Mis consejos son educativos\n\n"
                "**Puedo:**\n"
                "• Registrar tus gastos e ingresos en lenguaje natural\n"
                "• Simular inversiones con interés compuesto\n"
                "• Responder preguntas sobre CDT, deudas, ahorro, impuestos\n"
                "• Calcular descuentos, IVA, repartos\n"
                "• Crear metas financieras y generar reportes\n\n"
                "¡Cuéntame qué necesitas! 💬"
            ), []

        # 6. Respuesta con contexto del usuario
        if ctx and ctx.get('num_transacciones', 0) > 0:
            bal   = ctx.get('balance', 0)
            mayor = ctx.get('categoria_mayor_gasto')
            ingresos = ctx.get('total_ingresos', 0)
            
            lineas = [f"🤔 No estoy seguro de qué necesitas exactamente, pero puedo ayudarte analizando tu situación:\n"]
            
            # Razonamiento contextual
            if bal < 0:
                lineas.append(f"\n📊 **Balance negativo:** ${bal:,.0f}")
                lineas.append("→ Sugerencia: Revisa si hay ingresos sin registrar o gastos a eliminar.")
            elif ingresos > 0:
                ahorro_pct = round(bal / ingresos * 100)
                lineas.append(f"\n📊 **Estás ahorrando:** {ahorro_pct}% de tus ingresos")
                if ahorro_pct < 20:
                    lineas.append("→ Meta: Aumentar a 20% mensual usando la regla 50/30/20")
            
            if mayor:
                lineas.append(f"\n💸 **Mayor categoría de gasto:** {mayor}")
                lineas.append("→ Podemos buscar formas de reducir estos gastos")
            
            lineas.append("\n💡 ¿Qué quieres lograr? (ahorrar más, pagar deudas, invertir, etc.)")
            return "\n".join(lineas), []

        # 7. Respuesta genérica inteligente - MEJORADA
        return self._resp_generica_mejorada(mensaje), []

    def _resp_generica(self, mensaje: str) -> str:
        """Intenta dar una respuesta útil aunque no haya coincidencia exacta."""
        msg = mensaje.lower()

        # Detectar preguntas con "qué es" o "cómo funciona"
        if re.search(r'qu[eé]\s+es\s+(\w+)', msg) or re.search(r'c[oó]mo\s+funciona\s+(\w+)', msg):
            return (
                "🤔 No tengo información específica sobre ese tema en mi base de conocimiento.\n\n"
                "Pero puedo responder preguntas sobre:\n"
                "• CDT, inflación, interés compuesto, fondo de emergencia\n"
                "• Cómo ahorrar, invertir, salir de deudas\n"
                "• Tarjetas de crédito, pensión, impuestos, criptomonedas\n"
                "• Presupuesto, regla 50/30/20, diversificación\n\n"
                "¿Cuál de estos temas te interesa? 💬"
            )

        return (
            "🤔 No estoy seguro de entender completamente tu mensaje. Puedo ayudarte con:\n\n"
            "• 💸 *'Gasté $30.000 en comida'* — registrar gasto\n"
            "• 🏷️ *'$80.000 con 15% de descuento'* — calcular precio\n"
            "• 📈 *'Simula $500.000 al 10% por 1 año'* — proyectar inversión\n"
            "• 💡 *'¿Qué es un CDT?'* — respuesta educativa\n"
            "• 📊 *'¿Cómo están mis finanzas?'* — ver tu balance\n\n"
            "Reformula tu pregunta y con gusto te ayudo. 😊"
        )

    def _como_usar(self):
        return (
            "## 💬 Cómo hablarme\n\n"
            "Habla de forma natural, como con un amigo. Ejemplos:\n\n"
            "**Registrar:**\n"
            "• *'Gasté $25.000 en el bus'*\n"
            "• *'Recibí $2.000.000 de salario'*\n"
            "• *'Borra el último gasto de comida'*\n\n"
            "**Calcular:**\n"
            "• *'$80.000 con 20% de descuento'*\n"
            "• *'¿Cuánto es $50.000 más IVA?'*\n"
            "• *'Divide $180.000 entre 3 personas'*\n\n"
            "**Metas y simulaciones:**\n"
            "• *'Crea una meta de $1.000.000 para viajes'*\n"
            "• *'Simula $500.000 al 12% por 6 meses'*\n\n"
            "**Preguntas:**\n"
            "• *'¿Qué es el interés compuesto?'*\n"
            "• *'¿Cómo salgo de deudas?'*\n"
            "• *'¿Cómo funciona un CDT?'*\n\n"
            "**Perfil y reportes:**\n"
            "• *'Cambia mi nombre a Duban'*\n"
            "• *'Hazme un reporte PDF'*"
        )

    def _ensenar_razonamiento(self, msg, ctx):
        """Enseña paso a paso con razonamiento detallado."""
        lineas = ["😊 Claro, te enseño paso a paso el razonamiento:\n"]
        if any(p in msg for p in ['deuda','debo','prestamo','crédito','credito']):
            lineas += [
                "**🔍 ANÁLISIS:** Las deudas con altas tasas drenan tu dinero en intereses.",
                "**🎯 META:** Pagar lo antes posible el monto principal.\n",
                "**📋 ESTRATEGIA — Método Avalancha (óptimo matemáticamente):**",
                "1️⃣ Anota TODAS tus deudas: monto, tasa de interés, cuota mínima",
                "2️⃣ Ordénalas de mayor a menor tasa de interés",
                "3️⃣ Paga el mínimo en todas EXCEPTO la de mayor tasa",
                "4️⃣ Todo dinero extra → va a la deuda de mayor tasa",
                "5️⃣ Cuando esa se pague, el dinero pasa a la siguiente\n",
                "**💡 Razón:** Ahorras más en intereses vs el método 'bola de nieve'\n",
                "**⚠️ Paso crítico:** Identifica qué causó la deuda y evita repetir el patrón.",
            ]
        elif any(p in msg for p in ['ahorrar','ahorro','guardar','economizar']):
            lineas += [
                "**🔍 ANÁLISIS:** Si no ahorras de forma automática, el dinero se gasta naturalmente.",
                "**🎯 META:** Separar dinero ANTES de gastar, no después.\n",
                "**📋 ESTRATEGIA — Sistema Automático (probado):**",
                "1️⃣ Define tu meta: ¿cuánto quieres ahorrar? (sugerencia: 20% del ingreso)",
                "2️⃣ El DÍA que recibes ingreso, programa transferencia automática",
                "3️⃣ Abre cuenta SEPARADA solo para ese ahorro (no la toques)",
                "4️⃣ Lo que no ves, no lo gastas (psicología del dinero)",
                "5️⃣ Revisa progreso cada domingo\n",
                "**💡 Razón:** El dinero 'accidental' se gasta en gastos hormiga.",
                "**Ejemplo:** $50.000 diarios en café × 30 días = $1.500.000/mes gastado sin pensar\n",
            ]
        elif any(p in msg for p in ['invertir','inversión','inversion','cdt']):
            lineas += [
                "**🔍 ANÁLISIS:** El dinero guardado pierde valor por inflación (9% en 2024).",
                "**🎯 META:** Hacer que tu dinero trabaje ganando más que la inflación.\n",
                "**📋 CHECKLIST ANTES DE INVERTIR:**",
                "✅ ¿Tengo fondo de emergencia de 3-6 meses?",
                "✅ ¿Estoy libre de deudas de alto interés (tarjeta > 20%)?",
                "✅ ¿Entiendo el producto donde voy a invertir?",
                "✅ ¿Puedo dejar ese dinero invertido sin necesitarlo en 1+ año?\n",
                "**📋 OPCIONES en Colombia (de menor a mayor riesgo):**",
                "1️⃣ CDT 12% → Bajo riesgo, dinero garantizado (Fogafín)",
                "2️⃣ Fondo conservador 8-10% → Riesgo bajo-medio, flexible",
                "3️⃣ Acciones BVC 10-15% → Riesgo medio-alto, largo plazo",
                "4️⃣ Criptomonedas → Alto riesgo, solo si entiendes bien\n",
                "**⚠️ Regla de oro:** No inviertas en algo que no entiendas. Consuma asesor.",
            ]
        elif any(p in msg for p in ['presupuesto','gastos','organizar']):
            lineas += [
                "**🔍 ANÁLISIS:** Gastar sin presupuesto es como conducir sin mapa.",
                "**🎯 META:** Saber exactamente a dónde va cada peso.\n",
                "**📋 ESTRATEGIA — Regla 50/30/20:**",
                "50% NECESIDADES (arriendo, comida, transporte, servicios, salud)",
                "30% DESEOS (entretenimiento, ropa, salidas, hobbies)",
                "20% AHORRO (fondo emergencia, inversiones, metas)\n",
                "**PASOS:**",
                "1️⃣ Calcula ingreso neto REAL (salario − impuestos)",
                "2️⃣ Multiplica por 0.5, 0.3, 0.2",
                "3️⃣ Abre 3 cuentas separadas o bolsas de dinero",
                "4️⃣ Registra CADA gasto en FinanBot por categoría",
                "5️⃣ Analiza cada viernes: ¿dónde me excedí?\n",
                "**💡 Razón:** Visibilidad = control. Lo que se mide, se mejora.",
            ]
        else:
            lineas.append("Dime en cuál área necesitas ayuda:")
            lineas.append("• 💰 Ahorrar más dinero")
            lineas.append("• 💳 Pagar deudas")
            lineas.append("• 📈 Empezar a invertir")
            lineas.append("• 📋 Organizar presupuesto")
            if ctx and ctx.get('categoria_mayor_gasto'):
                lineas.append(f"\nVi que tu mayor gasto está en **{ctx['categoria_mayor_gasto']}**. Podemos optimizar ahí.")
        return "\n".join(lineas)

    def _resp_generica_mejorada(self, mensaje: str) -> str:
        """Intenta dar una respuesta útil aunque no haya coincidencia exacta."""
        msg = mensaje.lower()

        # Detectar preguntas con "qué es" o "cómo funciona"
        if re.search(r'qu[eé]\s+es\s+(\w+)', msg) or re.search(r'c[oó]mo\s+funciona\s+(\w+)', msg):
            return (
                "🤖 No tengo esa información específica en mi base, pero puedo enseñarte sobre:\n\n"
                "**Inversiones:** CDT • Fondos • Acciones • Criptomonedas\n"
                "**Deudas:** Tarjeta de crédito • Préstamos • Salir de deudas\n"
                "**Ahorro:** Fondo de emergencia • Metas • Presupuesto\n"
                "**Conceptos:** Inflación • Interés compuesto • Diversificación • Impuestos\n\n"
                "¿Cuál de estos temas te interesa? 💬"
            )

        return (
            "🤔 No estoy 100% seguro qué necesitas, pero puedo ayudarte con esto:\n\n"
            "**📝 Registrar:**  *'Gasté $30.000 en comida'* o *'Recibí $2M de salario'*\n"
            "**🧮 Calcular:**  *'$80.000 con 20% descuento'* o *'$50.000 más IVA'*\n"
            "**📈 Simular:**  *'Simula $500.000 al 10% por 1 año'*\n"
            "**💡 Preguntar:**  *'¿Qué es un CDT?'* o *'¿Cómo ahorrar más?'*\n"
            "**🎯 Metas:**  *'Crea meta de $1M para viajes'*\n\n"
            "Reformula así tu pregunta o cuéntame qué necesitas lograr financieramente 😊"
        )

    # ─── Utilidades ───────────────────────────────────────────────
    @staticmethod
    def _barra(pct, largo=10):
        f = int(pct / 100 * largo)
        return f"[{'█'*f}{'░'*(largo-f)}]"


# ══════════════════════════════════════════════════════════════════
#  BOTONES DE ACCIÓN  ─  URLs reales del proyecto
# ══════════════════════════════════════════════════════════════════

def _btn(texto, link): return {'tipo': 'link', 'texto': texto, 'link': link}
def _sug(texto):       return {'tipo': 'sugerencia', 'texto': texto}

def _btns_bienvenida():
    return [
        _sug('¿Cómo están mis finanzas?'),
        _sug('Registra un gasto'),
        _sug('¿Qué es un CDT?'),
        _sug('¿Cómo puedo ahorrar más?'),
        _btn('📊 Dashboard', RUTAS['dashboard']),
        _btn('💸 Mis finanzas', RUTAS['finanzas']),
    ]

def _btns_calc():
    return [
        _sug('Otro cálculo'),
        _btn('📊 Ver mis finanzas', RUTAS['finanzas']),
    ]

def _btns_trans():
    return [
        _sug('¿Cómo están mis finanzas?'),
        _btn('💸 Ver mis finanzas', RUTAS['finanzas']),
        _btn('📊 Dashboard', RUTAS['dashboard']),
    ]

def _btns_metas():
    return [
        _sug('Ver todas mis metas'),
        _sug('Crear otra meta'),
        _btn('🎯 Ver metas', RUTAS['metas']),
    ]

def _btns_finanzas():
    return [
        _btn('💸 Ir a mis finanzas', RUTAS['finanzas']),
        _btn('📊 Ver dashboard', RUTAS['dashboard']),
    ]

def _btns_resumen():
    return [
        _sug('Ver mis gastos por categoría'),
        _sug('Ver mis metas'),
        _sug('¿Cómo puedo mejorar?'),
        _btn('📊 Dashboard', RUTAS['dashboard']),
        _btn('💡 Recomendaciones', RUTAS['recomendaciones']),
    ]

def _btns_simulacion(accion=None):
    accion = accion or {}
    capital = accion.get('capital')
    tasa = accion.get('tasa')
    plazo = accion.get('plazo')
    link = RUTAS['simulador']
    if capital is not None or tasa is not None or plazo is not None:
        params = []
        if capital is not None:
            params.append(f'capital={int(capital)}')
        if tasa is not None:
            params.append(f'tasa={int(tasa)}')
        if plazo is not None:
            params.append(f'plazo={int(plazo)}')
        link = f"{RUTAS['simulador']}?{'&'.join(params)}"
    return [
        _sug('Simular otra inversión'),
        _sug('¿Qué es un CDT?'),
        _btn('🧪 Simular esta propuesta', link),
        _btn('📈 Simulador', RUTAS['simulador']),
    ]

def _btns_perfil():
    return [
        _btn('👤 Ver mi perfil', RUTAS['perfil']),
        _btn('📊 Dashboard', RUTAS['dashboard']),
    ]

def _btns_reporte(fmt='pdf'):
    url = RUTAS['exportar_excel'] if fmt == 'excel' else RUTAS['exportar_pdf']
    icono = '📊 Descargar Excel' if fmt == 'excel' else '📄 Descargar PDF'
    return [
        _btn(icono, url),
        _btn('👤 Ver mi perfil', RUTAS['perfil']),
    ]