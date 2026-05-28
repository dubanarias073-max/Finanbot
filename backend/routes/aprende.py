# routes/aprende.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import Usuario
import math

aprende_bp = Blueprint('aprende', __name__)


# ── DATOS ──────────────────────────────────────────────────
# Todos los artículos con contenido completo
ARTICULOS = [
    {
        "id": "ahorro",
        "emoji": "💰",
        "nivel": "basico",
        "categoria": "Ahorro",
        "titulo": "¿Cómo empezar a ahorrar desde cero?",
        "descripcion": "Estrategias efectivas para ahorrar sin importar cuánto ganas.",
        "tiempo_min": 5,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Págate a ti primero"},
            {"tipo": "parrafo",   "texto": "Apenas recibas tu salario, transfiere un % fijo a una cuenta separada antes de gastar en cualquier cosa. No esperes 'ver qué sobra' porque casi nunca sobra."},
            {"tipo": "highlight", "texto": "💡 Empieza con el 10%. Si ganas $1.500.000, separa $150.000 antes de cualquier gasto."},
            {"tipo": "subtitulo", "texto": "Elimina gastos hormiga"},
            {"tipo": "ejemplo",   "texto": "☕ Café diario: $3.000 × 30 = $90.000/mes\n🚕 Taxis innecesarios: $15.000 × 8 = $120.000/mes\n📱 Apps que no usas: $25.000/mes\nTotal: $235.000/mes que podrías estar ahorrando"},
            {"tipo": "subtitulo", "texto": "Automatiza tu ahorro"},
            {"tipo": "parrafo",   "texto": "Configura una transferencia automática el día que recibes tu pago. Lo que no ves, no lo gastas. La mayoría de bancos colombianos permiten automatizar transferencias."},
            {"tipo": "highlight", "texto": "✅ Reto de 30 días: anota cada gasto durante un mes. Al final sabrás exactamente cuánto puedes ahorrar."},
        ]
    },
    {
        "id": "presupuesto",
        "emoji": "📋",
        "nivel": "basico",
        "categoria": "Presupuesto",
        "titulo": "La regla 50/30/20 explicada",
        "descripcion": "Distribuye tu salario de forma inteligente con esta regla simple.",
        "tiempo_min": 4,
        "contenido": [
            {"tipo": "subtitulo", "texto": "50% — Necesidades básicas"},
            {"tipo": "parrafo",   "texto": "Arriendo, comida, transporte, servicios, salud, educación."},
            {"tipo": "subtitulo", "texto": "30% — Deseos"},
            {"tipo": "parrafo",   "texto": "Entretenimiento, ropa, salidas, hobbies, suscripciones."},
            {"tipo": "subtitulo", "texto": "20% — Ahorro e inversión"},
            {"tipo": "parrafo",   "texto": "Fondo de emergencia, CDT, metas de ahorro, pensión voluntaria."},
            {"tipo": "ejemplo",   "texto": "Con $2.000.000:\n🟢 Necesidades (50%): $1.000.000\n🟡 Deseos (30%): $600.000\n🔵 Ahorro (20%): $400.000"},
            {"tipo": "highlight", "texto": "⚠️ Si tus necesidades superan el 50%, ajusta: 60/20/20. Lo importante es SIEMPRE guardar algo."},
        ]
    },
    {
        "id": "deudas",
        "emoji": "💳",
        "nivel": "basico",
        "categoria": "Deudas",
        "titulo": "Salir de deudas: bola de nieve y avalancha",
        "descripcion": "Dos métodos probados para eliminar tus deudas de una vez.",
        "tiempo_min": 6,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Paso 1: Inventario completo"},
            {"tipo": "parrafo",   "texto": "Anota todas tus deudas: nombre, monto total, cuota mensual y tasa de interés."},
            {"tipo": "subtitulo", "texto": "⛄ Método Bola de Nieve"},
            {"tipo": "lista",     "items": ["Paga el mínimo en todas", "Dinero extra → deuda más pequeña", "Al eliminarla, ese dinero va a la siguiente"]},
            {"tipo": "subtitulo", "texto": "🌊 Método Avalancha"},
            {"tipo": "ejemplo",   "texto": "Tarjeta 28% + Crédito 18% + Familiar 0%\nAvalancha: Tarjeta → Crédito → Familiar"},
            {"tipo": "highlight", "texto": "🚨 Mientras pagas deudas: NO adquieras nuevas. Evita 'gota a gota' — tasas del 300%+ anual."},
        ]
    },
    {
        "id": "inversion",
        "emoji": "📈",
        "nivel": "intermedio",
        "categoria": "Inversión",
        "titulo": "Inversiones para principiantes en Colombia",
        "descripcion": "CDT, fondos de inversión, acciones: cuál elegir según tu perfil.",
        "tiempo_min": 8,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Antes de invertir necesitas:"},
            {"tipo": "lista",     "items": ["✅ Fondo de emergencia de 3 meses", "✅ Deudas de alto interés pagadas", "✅ Conocimiento del producto"]},
            {"tipo": "ejemplo",   "texto": "CDT: Riesgo muy bajo · 8-14% anual · Desde $100.000\nFondos: Riesgo bajo-medio · Variable · Desde $50.000\nAcciones BVC: Riesgo alto · Variable · Largo plazo"},
            {"tipo": "subtitulo", "texto": "Reglas de oro"},
            {"tipo": "lista",     "items": ["Nunca inviertas dinero que necesites pronto", "Diversifica: no pongas todo en un solo lugar", "Invierte a largo plazo para maximizar", "Desconfía de rendimientos 'garantizados' muy altos"]},
            {"tipo": "highlight", "texto": "💡 Usa el Simulador de FinanBot para ver cómo crecería tu dinero sin riesgo real."},
        ]
    },
    {
        "id": "emergencia",
        "emoji": "🛡️",
        "nivel": "basico",
        "categoria": "Seguridad",
        "titulo": "El fondo de emergencia: tu red de seguridad",
        "descripcion": "Cuánto necesitas, dónde guardarlo y cómo construirlo.",
        "tiempo_min": 5,
        "contenido": [
            {"tipo": "subtitulo", "texto": "¿Para qué sirve?"},
            {"tipo": "lista",     "items": ["Pérdida de empleo inesperada", "Emergencia médica no cubierta", "Reparación urgente del carro o casa"]},
            {"tipo": "ejemplo",   "texto": "Gastos de $1.500.000/mes:\nFondo mínimo: $4.500.000 (3 meses)\nFondo ideal: $9.000.000 (6 meses)"},
            {"tipo": "subtitulo", "texto": "¿Dónde guardarlo?"},
            {"tipo": "lista",     "items": ["✅ Cuenta de ahorros de fácil acceso", "✅ Fondo de liquidez (Nequi, Daviplata)", "✅ CDT a 30 días renovable", "❌ NO en criptomonedas"]},
            {"tipo": "highlight", "texto": "⚠️ El fondo de emergencia va ANTES que cualquier inversión. Es tu primera prioridad."},
        ]
    },
    {
        "id": "interes",
        "emoji": "🔢",
        "nivel": "intermedio",
        "categoria": "Conceptos",
        "titulo": "Interés simple vs interés compuesto",
        "descripcion": "Entiende la diferencia y cómo multiplicar tu dinero en el tiempo.",
        "tiempo_min": 7,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Interés Simple"},
            {"tipo": "ejemplo",   "texto": "$1.000.000 al 10% anual × 3 años = $300.000 en intereses. Total: $1.300.000"},
            {"tipo": "subtitulo", "texto": "Interés Compuesto"},
            {"tipo": "ejemplo",   "texto": "$1.000.000 al 10% compuesto × 3 años:\nAño 1: $1.100.000 · Año 2: $1.210.000 · Año 3: $1.331.000\nTotal: $1.331.000 (vs $1.300.000 del simple)"},
            {"tipo": "subtitulo", "texto": "El poder del tiempo"},
            {"tipo": "ejemplo",   "texto": "$1.000.000 al 10% compuesto:\n10 años: $2.593.742\n20 años: $6.727.500\n30 años: $17.449.402"},
            {"tipo": "highlight", "texto": "💡 La clave es el tiempo. Quien empieza a los 25 tiene enorme ventaja sobre quien empieza a los 35."},
        ]
    },
    {
        "id": "pension",
        "emoji": "👴",
        "nivel": "intermedio",
        "categoria": "Pensión",
        "titulo": "Colpensiones vs fondos privados en Colombia",
        "descripcion": "Todo lo que debes saber sobre los dos regímenes pensionales.",
        "tiempo_min": 9,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Colpensiones (Prima Media)"},
            {"tipo": "lista",     "items": ["1.300 semanas cotizadas requeridas", "57 años mujeres / 62 hombres", "Pensión mínima garantizada: 1 SMMLV"]},
            {"tipo": "subtitulo", "texto": "AFP — Fondos Privados (RAIS)"},
            {"tipo": "lista",     "items": ["Cuenta individual a tu nombre", "Aportes voluntarios deducibles de renta", "Mejor para ingresos altos e independientes"]},
            {"tipo": "ejemplo",   "texto": "Aportes voluntarios deducibles de renta (Art. 126-1 E.T.)\n$300.000/mes en pensión voluntaria → ~$57.000/mes menos en impuestos"},
            {"tipo": "highlight", "texto": "⚠️ El 75% de colombianos NO se pensiona. Complementa siempre con ahorro e inversión personal."},
        ]
    },
    {
        "id": "inflacion",
        "emoji": "📉",
        "nivel": "intermedio",
        "categoria": "Economía",
        "titulo": "Cómo protegerte de la inflación",
        "descripcion": "La inflación reduce tu dinero. Aprende a protegerlo y hacerlo crecer.",
        "tiempo_min": 6,
        "contenido": [
            {"tipo": "ejemplo",   "texto": "$1.000.000 hoy con inflación del 10%:\nHoy: 100 artículos de $10.000\nEn 1 año: solo 90 artículos (cuestan $11.000)\nPerdiste el 10% de tu poder de compra."},
            {"tipo": "subtitulo", "texto": "¿Cómo protegerse?"},
            {"tipo": "lista",     "items": ["✅ CDT con tasas superiores a la inflación", "✅ Fondos de inversión en renta variable", "✅ Finca raíz (valorización histórica)", "❌ Efectivo guardado por meses"]},
            {"tipo": "highlight", "texto": "💡 Si inflación = 9% y tu CDT paga 12%, ganaste un 3% real de poder adquisitivo."},
        ]
    },
    {
        "id": "cripto",
        "emoji": "₿",
        "nivel": "avanzado",
        "categoria": "Criptos",
        "titulo": "Criptomonedas: riesgos y realidades",
        "descripcion": "Lo que debes saber antes de invertir en criptomonedas.",
        "tiempo_min": 8,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Riesgos reales"},
            {"tipo": "lista",     "items": ["Volatilidad extrema: Bitcoin cayó 75% en 7 meses (2021-2022)", "Sin regulación ni protección estatal", "Estafas, rug pulls y pirámides frecuentes", "Si pierdes la clave privada, pierdes todo"]},
            {"tipo": "ejemplo",   "texto": "Bitcoin nov 2021: $68.000 USD → jun 2022: $17.000 USD\nCaída del 75% en 7 meses"},
            {"tipo": "subtitulo", "texto": "Si decides invertir"},
            {"tipo": "lista",     "items": ["Máximo 5% de tu portafolio", "Solo dinero que puedes perder", "Plataformas serias: Binance, Coinbase", "Nunca sigas grupos de Telegram/WhatsApp"]},
            {"tipo": "highlight", "texto": "🚨 Señales de estafa: rendimientos garantizados altos, presión para invertir rápido, influencers pagados."},
        ]
    },
    {
        "id": "diversifica",
        "emoji": "🌱",
        "nivel": "intermedio",
        "categoria": "Estrategia",
        "titulo": "Por qué diversificar tus ingresos",
        "descripcion": "Depender de un solo ingreso es el mayor riesgo. Aprende cómo diversificar.",
        "tiempo_min": 5,
        "contenido": [
            {"tipo": "parrafo",   "texto": "Depender de un solo ingreso es el mayor riesgo financiero personal. Si se corta (despido, enfermedad), tu flujo de caja desaparece de inmediato."},
            {"tipo": "subtitulo", "texto": "Opciones de segunda fuente"},
            {"tipo": "lista",     "items": ["Freelance en tu área de expertise", "Venta de productos digitales (cursos, ebooks)", "Inversiones con dividendos o intereses", "Emprendimiento de bajo capital inicial"]},
            {"tipo": "ejemplo",   "texto": "Segunda fuente de $300.000/mes:\nEn 1 año extra: $3.600.000\nEn 5 años (invertidos): mucho más\nCambia completamente tu seguridad financiera."},
            {"tipo": "highlight", "texto": "💡 No necesitas reemplazar tu ingreso. Con un 20% adicional cambias tu estabilidad."},
        ]
    },
    {
        "id": "habitos",
        "emoji": "🧠",
        "nivel": "basico",
        "categoria": "Psicología",
        "titulo": "Hábitos financieros que cambian tu vida",
        "descripcion": "Los 7 hábitos que separan a quienes logran riqueza de quienes no.",
        "tiempo_min": 6,
        "contenido": [
            {"tipo": "subtitulo", "texto": "Los 7 hábitos financieros"},
            {"tipo": "lista",     "items": ["1. Registra cada peso que gastas", "2. Págate a ti primero (10-20%)", "3. Vive por debajo de tus posibilidades", "4. Aprende constantemente sobre dinero", "5. Evita deudas de consumo (tarjetas mal usadas)", "6. Invierte poco pero constante", "7. Revisa y ajusta tu presupuesto mensual"]},
            {"tipo": "ejemplo",   "texto": "El hábito #1 es el más poderoso: quienes registran sus gastos ahorran en promedio un 20% más que quienes no lo hacen."},
            {"tipo": "highlight", "texto": "🧠 Los hábitos financieros no se forman en un día. Empieza con uno solo esta semana."},
        ]
    },
    {
        "id": "finca",
        "emoji": "🏠",
        "nivel": "avanzado",
        "categoria": "Inversión",
        "titulo": "Invertir en finca raíz en Colombia",
        "descripcion": "Vivienda, locales, lotes: cómo evaluar una inversión inmobiliaria.",
        "tiempo_min": 10,
        "contenido": [
            {"tipo": "subtitulo", "texto": "¿Por qué finca raíz en Colombia?"},
            {"tipo": "lista",     "items": ["Valorización histórica del 5-12% anual en ciudades principales", "Ingreso por arriendo (3-6% anual del valor del inmueble)", "Cobertura contra la inflación", "Activo tangible con valor intrínseco"]},
            {"tipo": "ejemplo",   "texto": "Inmueble: $200.000.000\nArriendo: $1.000.000/mes\nRentabilidad anual: 6% + valorización ≈ 12% total"},
            {"tipo": "subtitulo", "texto": "Riesgos"},
            {"tipo": "lista",     "items": ["Baja liquidez (no puedes vender rápido)", "Requiere capital inicial alto", "Costos de mantenimiento y administración", "Riesgo de inquilinos problemáticos"]},
            {"tipo": "highlight", "texto": "💡 Sin capital para comprar: considera fondos de finca raíz (fiducias inmobiliarias en Colombia)."},
        ]
    },
]

# Base de conocimiento para búsqueda
BASE_CONOCIMIENTO = {
    "cdt": {
        "titulo": "CDT — Certificado de Depósito a Término",
        "cuerpo": "Es un producto de ahorro donde depositas dinero por un plazo fijo a cambio de una tasa de interés pactada desde el inicio. Ofrecido por bancos y cooperativas colombianas.",
        "puntos": [
            "Tasa garantizada desde el inicio (no varía durante el plazo)",
            "Monto mínimo desde $100.000 en algunos bancos",
            "Plazos: 30, 60, 90, 180, 360 días o más",
            "Asegurado por Fogafín hasta $50 millones",
            "Tasas referencia 2024: corto plazo 8-10% EA, mediano 10-13% EA, largo 12-14% EA",
        ],
        "ejemplo": "Inviertes $2.000.000 al 12% anual por 12 meses → $2.240.000 al vencer. Ganaste $240.000 sin hacer nada.",
        "consejo": "Ideal si tienes dinero que no necesitarás en el corto plazo. La tasa es predecible y el riesgo casi cero.",
        "tags": ["interés simple", "ahorro", "bancos", "inversión segura"]
    },
    "regla 50/30/20": {
        "titulo": "La Regla 50/30/20 para presupuestar tu dinero",
        "cuerpo": "Divide tus ingresos en tres categorías. Popularizada por Elizabeth Warren, aplica a cualquier nivel de ingresos.",
        "puntos": [
            "50% Necesidades: arriendo, comida, transporte, salud",
            "30% Deseos: entretenimiento, ropa, salidas, suscripciones",
            "20% Ahorro e inversión: CDT, metas, pensión voluntaria",
        ],
        "ejemplo": "Con $2.500.000: Necesidades $1.250.000 · Deseos $750.000 · Ahorro $500.000",
        "consejo": "Si tus necesidades superan el 50%, ajusta: 60/20/20. Lo más importante es siempre destinar algo al ahorro.",
        "tags": ["presupuesto", "ahorro", "planificación financiera"]
    },
    "interés compuesto": {
        "titulo": "Interés Compuesto — El poder de hacer crecer el dinero",
        "cuerpo": "Los intereses generan nuevos intereses. Einstein lo llamó 'la octava maravilla del mundo'.",
        "puntos": [
            "Fórmula: Capital Final = Capital × (1 + Tasa)^Tiempo",
            "$1.000.000 al 10% por 10 años = $2.593.742",
            "Vs interés simple a 10 años = $2.000.000",
            "La diferencia es $593.742 extra gracias al efecto compuesto",
        ],
        "ejemplo": "$1.000.000 al 10% compuesto:\n10 años: $2.593.742\n20 años: $6.727.500\n30 años: $17.449.402",
        "consejo": "La clave es el tiempo. Quien empieza a los 25 tiene enorme ventaja sobre quien empieza a los 35.",
        "tags": ["inversión", "CDT", "fondos", "tiempo", "rentabilidad"]
    },
    "fondo de emergencia": {
        "titulo": "Fondo de Emergencia — Tu red de seguridad financiera",
        "cuerpo": "Dinero reservado para imprevistos: pérdida de empleo, enfermedad, daño urgente.",
        "puntos": [
            "Empleado estable: 3 meses de gastos básicos",
            "Empleado en empresa inestable: 6 meses",
            "Independiente o freelance: 6-12 meses",
            "Guardarlo en cuenta de ahorros o fondo de liquidez (Nequi, Daviplata)",
            "NO en criptomonedas ni inversiones de largo plazo",
        ],
        "ejemplo": "Gastos básicos $1.500.000/mes:\nFondo mínimo: $4.500.000 · Fondo ideal: $9.000.000",
        "consejo": "El fondo de emergencia va ANTES que cualquier inversión. Es tu primera prioridad financiera.",
        "tags": ["ahorro", "seguridad financiera", "emergencias", "presupuesto"]
    },
    "salir de deudas": {
        "titulo": "Cómo salir de deudas — Métodos Bola de Nieve y Avalancha",
        "cuerpo": "Dos estrategias probadas para eliminar deudas según tu motivación o eficiencia matemática.",
        "puntos": [
            "Método Bola de Nieve: paga primero la deuda más pequeña (motivación)",
            "Método Avalancha: paga primero la de mayor tasa (eficiencia matemática)",
            "En ambos: paga el mínimo en todas las demás",
            "El dinero extra siempre va a la deuda prioritaria",
            "Evita adquirir nuevas deudas mientras pagas las actuales",
        ],
        "ejemplo": "Tarjeta 28% + Crédito 18% + Familiar 0%\nAvalancha: Tarjeta → Crédito → Familiar",
        "consejo": "Evita los 'gota a gota' — son ilegales y con tasas del 300%+ anual.",
        "tags": ["deudas", "crédito", "tarjeta de crédito", "finanzas personales"]
    },
    "inflación": {
        "titulo": "Inflación — Cómo proteger tu poder adquisitivo",
        "cuerpo": "Aumento generalizado de precios que reduce el poder adquisitivo del dinero. Referencia Colombia 2024: 9.28% anual.",
        "puntos": [
            "Si la inflación es 10%, lo que hoy cuesta $100.000 el próximo año cuesta $110.000",
            "CDT con tasa superior a la inflación: protege y crece",
            "Fondos de inversión en renta variable: mayor rentabilidad potencial",
            "Finca raíz: valorización histórica superior a inflación en Colombia",
            "Efectivo guardado por meses: pierde valor automáticamente",
        ],
        "ejemplo": "$1.000.000 con inflación 10%: pierdes $100.000 de poder de compra en 1 año sin hacer nada.",
        "consejo": "Si inflación = 9% y tu CDT paga 12%, ganaste un 3% real. Tu dinero creció en poder adquisitivo.",
        "tags": ["economía", "inversión", "poder adquisitivo", "CDT"]
    },
    "pensión en colombia": {
        "titulo": "Pensión en Colombia — Colpensiones vs Fondos Privados",
        "cuerpo": "Colombia tiene dos regímenes pensionales: Prima Media (Colpensiones) y Ahorro Individual (AFP).",
        "puntos": [
            "Colpensiones: 1.300 semanas cotizadas, 57 mujeres / 62 hombres",
            "AFP: cuenta individual, aportes voluntarios deducibles de renta",
            "Aportes voluntarios: Art. 126-1 E.T. Colombia — deducibles hasta 30% del ingreso",
            "$300.000/mes en pensión voluntaria ahorra ~$57.000/mes en impuestos",
            "El 75% de colombianos NO se pensiona — complementa con ahorro personal",
        ],
        "ejemplo": "AFP + $300.000/mes aportes voluntarios × 20 años al 8% anual = capital pensional significativo adicional.",
        "consejo": "Sea cual sea tu régimen, complementa con ahorro e inversión personal desde hoy.",
        "tags": ["pensión", "colpensiones", "AFP", "jubilación", "Colombia"]
    },
    "criptomonedas": {
        "titulo": "Criptomonedas — Riesgos y realidades antes de invertir",
        "cuerpo": "Monedas digitales descentralizadas con alta volatilidad y sin regulación estatal en Colombia.",
        "puntos": [
            "Bitcoin cayó 75% en 7 meses (nov 2021 a jun 2022)",
            "Sin regulación: no hay entidad que te proteja si pierdes",
            "Si pierdes tu clave privada, pierdes todo el capital",
            "Máximo 5% de tu portafolio si decides invertir",
            "Solo en plataformas reconocidas: Binance, Coinbase",
        ],
        "ejemplo": "Bitcoin nov 2021: $68.000 USD → jun 2022: $17.000 USD. Caída del 75% en 7 meses.",
        "consejo": "🚨 Señales de estafa: rendimientos garantizados altos, presión para invertir rápido, influencers pagados.",
        "tags": ["criptomonedas", "bitcoin", "riesgo", "inversión alternativa"]
    },
}

# Glosario completo
GLOSARIO = [
    {"nombre": "Activo",             "definicion": "Bien o derecho con valor económico que pertenece a una persona. Ejemplos: dinero, propiedades, inversiones.",                              "categoria": "Conceptos básicos"},
    {"nombre": "AFP",                "definicion": "Administradora de Fondos de Pensiones. Entidad privada que gestiona ahorros pensionales en el régimen RAIS (Ahorro Individual).",          "categoria": "Pensión"},
    {"nombre": "Ahorro",             "definicion": "Parte del ingreso que no se gasta y se reserva para uso futuro. Base de toda salud financiera personal.",                                  "categoria": "Conceptos básicos"},
    {"nombre": "Amortización",       "definicion": "Proceso de pago gradual de una deuda mediante cuotas periódicas que incluyen capital e intereses.",                                         "categoria": "Crédito"},
    {"nombre": "Apalancamiento",     "definicion": "Uso de deuda para aumentar la capacidad de inversión. Puede multiplicar ganancias pero también pérdidas.",                                   "categoria": "Inversión"},
    {"nombre": "Balance",            "definicion": "Diferencia entre tus ingresos y gastos en un período. Balance positivo significa que ingresas más de lo que gastas.",                       "categoria": "Conceptos básicos"},
    {"nombre": "BVC",                "definicion": "Bolsa de Valores de Colombia. Mercado organizado donde se compran y venden acciones de empresas colombianas.",                              "categoria": "Inversión"},
    {"nombre": "Capital",            "definicion": "Monto inicial de dinero que se invierte o presta. Base sobre la que se calculan los intereses.",                                            "categoria": "Conceptos básicos"},
    {"nombre": "CDT",                "definicion": "Certificado de Depósito a Término. Depositas dinero a un plazo fijo a cambio de una tasa de interés pactada desde el inicio.",             "categoria": "Ahorro e inversión"},
    {"nombre": "Colpensiones",       "definicion": "Administradora estatal del régimen de prima media pensional en Colombia. Gestiona los aportes de quienes no están en fondos privados.",    "categoria": "Pensión"},
    {"nombre": "Crédito",            "definicion": "Préstamo de dinero que debes devolver con intereses en un plazo determinado. Costo expresado como tasa de interés.",                       "categoria": "Crédito"},
    {"nombre": "Cuota fija",         "definicion": "Modalidad de pago de crédito donde la cuota mensual no varía. Se calcula con el sistema francés incluyendo capital e intereses.",           "categoria": "Crédito"},
    {"nombre": "Diversificación",    "definicion": "Estrategia de invertir en múltiples activos para reducir el riesgo total. 'No pongas todos los huevos en la misma canasta'.",             "categoria": "Inversión"},
    {"nombre": "Dividendo",          "definicion": "Parte de las ganancias de una empresa distribuida entre sus accionistas. Fuente de ingreso pasivo en acciones.",                           "categoria": "Inversión"},
    {"nombre": "DTF",                "definicion": "Depósito a Término Fijo. Tasa de referencia del mercado financiero colombiano, usada como base para créditos de libre inversión.",          "categoria": "Economía"},
    {"nombre": "EA (Efectivo Anual)","definicion": "Tasa que muestra el rendimiento o costo real de una inversión o crédito durante un año, considerando la capitalización periódica.",         "categoria": "Tasas"},
    {"nombre": "Fondo de emergencia","definicion": "Dinero reservado para imprevistos. Mínimo 3 meses de gastos básicos guardados en cuenta de fácil acceso inmediato.",                       "categoria": "Ahorro e inversión"},
    {"nombre": "Flujo de caja",      "definicion": "Movimiento de dinero que entra y sale de tu economía personal en un período determinado. Positivo si ingresas más de lo que gastas.",      "categoria": "Conceptos básicos"},
    {"nombre": "Inflación",          "definicion": "Aumento generalizado y sostenido de los precios. Reduce el poder adquisitivo del dinero con el tiempo. Referencia Colombia 2024: 9.28%.",  "categoria": "Economía"},
    {"nombre": "Interés compuesto",  "definicion": "Interés calculado sobre el capital inicial más los intereses ya acumulados. Los intereses generan nuevos intereses en cada período.",      "categoria": "Tasas"},
    {"nombre": "Interés simple",     "definicion": "Interés calculado siempre sobre el capital inicial únicamente. Los intereses generados no se reinvierten.",                                 "categoria": "Tasas"},
    {"nombre": "IPC",                "definicion": "Índice de Precios al Consumidor. Mide la variación de precios de una canasta de bienes y servicios. Principal medida de inflación.",       "categoria": "Economía"},
    {"nombre": "Inversión",          "definicion": "Destinar dinero con el objetivo de obtener una ganancia futura. Implica un nivel de riesgo proporcional al retorno esperado.",             "categoria": "Ahorro e inversión"},
    {"nombre": "Liquidez",           "definicion": "Facilidad con la que un activo puede convertirse en efectivo sin perder valor. El efectivo es el activo más líquido.",                     "categoria": "Conceptos básicos"},
    {"nombre": "Pasivo",             "definicion": "Deuda u obligación financiera que debes pagar en el futuro. Ejemplos: créditos, hipotecas, tarjetas de crédito.",                          "categoria": "Conceptos básicos"},
    {"nombre": "Patrimonio",         "definicion": "Diferencia entre tus activos y pasivos. Representa tu riqueza neta real en un momento determinado.",                                        "categoria": "Conceptos básicos"},
    {"nombre": "Pensión voluntaria", "definicion": "Aportes adicionales a un fondo de pensión más allá de lo obligatorio. Son deducibles de renta en Colombia según Art. 126-1 E.T.",          "categoria": "Pensión"},
    {"nombre": "Presupuesto",        "definicion": "Plan financiero que organiza tus ingresos y gastos para un período. Herramienta fundamental para controlar el dinero.",                     "categoria": "Conceptos básicos"},
    {"nombre": "Rentabilidad",       "definicion": "Ganancia obtenida sobre una inversión expresada como porcentaje del capital invertido.",                                                    "categoria": "Inversión"},
    {"nombre": "Retención en la fuente","definicion": "Anticipo del impuesto de renta que descuenta directamente el empleador del salario del trabajador.",                                    "categoria": "Impuestos"},
    {"nombre": "SMMLV",              "definicion": "Salario Mínimo Mensual Legal Vigente en Colombia. Para 2024: $1.300.000. Referencia para calcular pensiones y deducciones.",              "categoria": "Economía"},
    {"nombre": "Tasa EA",            "definicion": "Tasa Efectiva Anual. Expresa el costo o rendimiento real de un producto financiero por año, considerando capitalización.",                 "categoria": "Tasas"},
    {"nombre": "TRM",                "definicion": "Tasa Representativa del Mercado. Valor oficial del dólar en pesos colombianos, fijada diariamente por el Banco de la República.",          "categoria": "Economía"},
    {"nombre": "UVT",                "definicion": "Unidad de Valor Tributario. Valor de referencia para calcular impuestos en Colombia. Para 2024: $47.065.",                                 "categoria": "Impuestos"},
    {"nombre": "Yield",              "definicion": "Rendimiento de una inversión expresado como porcentaje anual. Similar a la rentabilidad pero usado principalmente en mercados de capitales.", "categoria": "Inversión"},
]


# ════════════════════════════════════════════════════════════
#  ENDPOINTS
# ════════════════════════════════════════════════════════════

# ── GET /api/aprende/articulos ────────────────────────────
@aprende_bp.route('/articulos', methods=['GET'])
def listar_articulos():
    """
    Lista todos los artículos con metadata (sin contenido completo).
    Filtros opcionales: ?nivel=basico&categoria=Ahorro
    Acceso público.
    """
    nivel     = request.args.get('nivel', '').strip().lower()
    categoria = request.args.get('categoria', '').strip()

    resultado = []
    for a in ARTICULOS:
        if nivel and a['nivel'] != nivel:
            continue
        if categoria and a['categoria'].lower() != categoria.lower():
            continue
        resultado.append({
            'id':          a['id'],
            'emoji':       a['emoji'],
            'nivel':       a['nivel'],
            'categoria':   a['categoria'],
            'titulo':      a['titulo'],
            'descripcion': a['descripcion'],
            'tiempo_min':  a['tiempo_min'],
        })

    return jsonify({
        'total':     len(resultado),
        'articulos': resultado,
    }), 200


# ── GET /api/aprende/articulos/<id> ───────────────────────
@aprende_bp.route('/articulos/<string:articulo_id>', methods=['GET'])
def obtener_articulo(articulo_id):
    """
    Devuelve un artículo completo con contenido.
    Acceso público.
    """
    articulo = next((a for a in ARTICULOS if a['id'] == articulo_id), None)
    if not articulo:
        return jsonify({'mensaje': f"Artículo '{articulo_id}' no encontrado."}), 404

    return jsonify(articulo), 200


# ── GET /api/aprende/buscar?q=... ─────────────────────────
@aprende_bp.route('/buscar', methods=['GET'])
def buscar():
    """
    Busca en la base de conocimiento financiero.
    También busca en artículos por título y descripción.
    Acceso público.
    Parámetro: ?q=texto
    """
    q = request.args.get('q', '').strip().lower()
    if not q or len(q) < 2:
        return jsonify({'mensaje': 'El parámetro q debe tener al menos 2 caracteres.'}), 400

    # Buscar en base de conocimiento
    encontrado = None
    for clave, contenido in BASE_CONOCIMIENTO.items():
        if (q in clave or clave in q
                or q in contenido['titulo'].lower()
                or any(q in tag.lower() for tag in contenido.get('tags', []))):
            encontrado = {'fuente': 'conocimiento', 'clave': clave, **contenido}
            break

    # Buscar también en artículos
    articulos_relacionados = [
        {
            'id':          a['id'],
            'emoji':       a['emoji'],
            'titulo':      a['titulo'],
            'descripcion': a['descripcion'],
            'nivel':       a['nivel'],
        }
        for a in ARTICULOS
        if q in a['titulo'].lower()
        or q in a['descripcion'].lower()
        or q in a['categoria'].lower()
    ]

    return jsonify({
        'query':                  q,
        'resultado_conocimiento': encontrado,
        'articulos_relacionados': articulos_relacionados,
        'total_articulos':        len(articulos_relacionados),
    }), 200


# ── GET /api/aprende/glosario ─────────────────────────────
@aprende_bp.route('/glosario', methods=['GET'])
def listar_glosario():
    """
    Devuelve el glosario completo de términos financieros.
    Filtros opcionales: ?letra=A&categoria=Inversión&q=texto
    Acceso público.
    """
    letra     = request.args.get('letra', '').strip().upper()
    categoria = request.args.get('categoria', '').strip()
    q         = request.args.get('q', '').strip().lower()

    resultado = GLOSARIO.copy()

    if letra:
        resultado = [t for t in resultado if t['nombre'].upper().startswith(letra)]
    if categoria:
        resultado = [t for t in resultado if t['categoria'].lower() == categoria.lower()]
    if q:
        resultado = [
            t for t in resultado
            if q in t['nombre'].lower()
            or q in t['definicion'].lower()
            or q in t['categoria'].lower()
        ]

    # Letras disponibles para filtro
    letras_disponibles = sorted(set(t['nombre'][0].upper() for t in GLOSARIO))

    # Categorías disponibles
    categorias_disponibles = sorted(set(t['categoria'] for t in GLOSARIO))

    return jsonify({
        'total':                  len(resultado),
        'terminos':               resultado,
        'letras_disponibles':     letras_disponibles,
        'categorias_disponibles': categorias_disponibles,
    }), 200


# ── POST /api/aprende/calcular ────────────────────────────
@aprende_bp.route('/calcular', methods=['POST'])
def calcular():
    """
    Motor de cálculos financieros del backend.
    Mueve la lógica de las calculadoras del frontend al servidor.
    Body: { "tipo": "interes_compuesto", "datos": {...} }

    Tipos soportados:
      - interes_simple
      - interes_compuesto
      - regla_50_30_20
      - meta_ahorro
      - retencion_fuente
      - cuota_credito
      - inflacion
      - pension_voluntaria
    """
    data = request.get_json(silent=True) or {}
    tipo = data.get('tipo', '').strip()
    d    = data.get('datos', {})

    if not tipo:
        return jsonify({'mensaje': 'El campo tipo es requerido.'}), 400

    try:
        resultado = _calcular(tipo, d)
        return jsonify({'tipo': tipo, 'resultado': resultado}), 200
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        return jsonify({'mensaje': f'Error en los datos: {str(e)}'}), 400


def _calcular(tipo, d):
    """Ejecuta el cálculo según el tipo solicitado."""

    if tipo == 'interes_simple':
        k      = float(d['capital'])
        tasa   = float(d['tasa_anual']) / 100
        meses  = float(d['meses'])
        tm     = tasa / 12
        interes = round(k * tm * meses, 2)
        total   = round(k + interes, 2)
        return {
            'capital_inicial':  k,
            'interes_generado': interes,
            'total_final':      total,
            'tasa_mensual_pct': round(tm * 100, 4),
        }

    elif tipo == 'interes_compuesto':
        k      = float(d['capital'])
        aporte = float(d.get('aporte_mensual', 0))
        tasa   = float(d['tasa_anual']) / 100
        anos   = float(d['anos'])
        tm     = tasa / 12
        meses  = int(anos * 12)
        bal    = k
        for _ in range(meses):
            bal = bal * (1 + tm) + aporte
        bal       = round(bal, 2)
        invertido = round(k + aporte * meses, 2)
        intereses = round(bal - invertido, 2)
        renta     = round((bal / k - 1) * 100, 2) if k > 0 else 0
        return {
            'total_invertido':  invertido,
            'intereses_ganados': intereses,
            'total_final':      bal,
            'rentabilidad_pct': renta,
        }

    elif tipo == 'regla_50_30_20':
        ing   = float(d['ingreso_mensual'])
        fijos = float(d.get('gastos_fijos', 0))
        pf    = round(fijos / ing * 100, 1) if ing > 0 else 0
        aviso = ''
        if fijos > 0:
            if pf > 70:
                aviso = f'⚠️ Zona crítica: tus gastos fijos representan el {pf}% de tus ingresos.'
            elif pf > 50:
                aviso = '⚠️ Tus gastos fijos superan el 50% recomendado. Considera reducirlos.'
            else:
                aviso = '✅ Tus gastos fijos están en rango controlado.'
        return {
            'necesidades_50': round(ing * 0.5, 2),
            'deseos_30':      round(ing * 0.3, 2),
            'ahorro_20':      round(ing * 0.2, 2),
            'gastos_fijos':   fijos,
            'pct_gastos_fijos': pf,
            'aviso':          aviso,
        }

    elif tipo == 'meta_ahorro':
        obj   = float(d['monto_objetivo'])
        act   = float(d.get('monto_actual', 0))
        men   = float(d['ahorro_mensual'])
        ren   = float(d.get('rendimiento_mensual_pct', 0)) / 100
        faltante = max(0, obj - act)
        if faltante == 0:
            return {'ya_alcanzada': True, 'monto_actual': act}
        if ren > 0:
            meses = 0
            bal   = act
            while bal < obj and meses < 1200:
                bal = bal * (1 + ren) + men
                meses += 1
        else:
            meses = math.ceil(faltante / men) if men > 0 else 99999
            bal   = round(act + men * meses, 2)
        anos  = meses // 12
        mr    = meses % 12
        if anos > 0:
            tiempo_txt = f"{anos} año{'s' if anos>1 else ''}" + (f" y {mr} mes{'es' if mr>1 else ''}" if mr else '')
        else:
            tiempo_txt = f"{meses} mes{'es' if meses>1 else ''}"
        return {
            'ya_alcanzada':  False,
            'faltante':      round(faltante, 2),
            'meses':         meses,
            'tiempo_texto':  tiempo_txt,
            'total_acumulado': round(bal, 2),
        }

    elif tipo == 'retencion_fuente':
        bruto = float(d['ingreso_bruto'])
        ded   = float(d.get('deducciones', 0))
        otros = float(d.get('otros_descuentos', 0))
        salud   = round(bruto * 0.04, 2)
        pension = round(bruto * 0.04, 2)
        base    = max(0, bruto - salud - pension - ded - otros)
        UVT     = 47065
        bUVT    = base / UVT
        ret     = 0.0
        if bUVT > 1090: ret = base * 0.39 - 27657 * UVT
        elif bUVT > 640: ret = base * 0.33 - 21003 * UVT
        elif bUVT > 300: ret = base * 0.28 - 7662 * UVT
        elif bUVT > 150: ret = base * 0.19 - 972 * UVT
        elif bUVT > 95:  ret = base * 0.19 - 1311 * UVT
        elif bUVT > 87:  ret = base * 0.19 - 1485 * UVT
        ret  = round(max(0, ret), 2)
        neto = round(bruto - salud - pension - ret - otros, 2)
        return {
            'ingreso_bruto':  bruto,
            'salud':          salud,
            'pension':        pension,
            'retencion':      ret,
            'otros':          otros,
            'salario_neto':   neto,
        }

    elif tipo == 'cuota_credito':
        P = float(d['monto'])
        r = float(d['tasa_anual']) / 100 / 12
        n = int(d['plazo_meses'])
        if r == 0:
            cuota = P / n
        else:
            cuota = P * r * (1 + r)**n / ((1 + r)**n - 1)
        cuota    = round(cuota, 2)
        total    = round(cuota * n, 2)
        intereses = round(total - P, 2)
        costo_pct = round(intereses / P * 100, 2) if P > 0 else 0
        return {
            'cuota_mensual':   cuota,
            'total_a_pagar':   total,
            'total_intereses': intereses,
            'costo_credito_pct': costo_pct,
        }

    elif tipo == 'inflacion':
        monto = float(d['monto'])
        tasa  = float(d['inflacion_anual_pct']) / 100
        anos  = float(d['anos'])
        futuro  = round(monto / (1 + tasa) ** anos, 2)
        perdida = round(monto - futuro, 2)
        return {
            'valor_hoy':         monto,
            'valor_real_futuro': futuro,
            'perdida_poder':     perdida,
            'tasa_minima_pct':   round(tasa * 100, 2),
        }

    elif tipo == 'pension_voluntaria':
        ing    = float(d['ingreso_mensual'])
        aporte = float(d['aporte_mensual'])
        anos   = float(d['anos'])
        rend   = float(d.get('rendimiento_anual_pct', 8)) / 100
        meses  = int(anos * 12)
        tm     = rend / 12
        bal    = 0.0
        for _ in range(meses):
            bal = bal * (1 + tm) + aporte
        bal        = round(bal, 2)
        tot_aporte = round(aporte * meses, 2)
        rendim     = round(bal - tot_aporte, 2)
        ahorro_imp = round(aporte * 0.19 * 12, 2)
        return {
            'capital_acumulado':    bal,
            'total_aportado':       tot_aporte,
            'rendimientos':         rendim,
            'ahorro_impuestos_ano': ahorro_imp,
        }

    else:
        raise ValueError(f"Tipo de cálculo '{tipo}' no reconocido.")


# ── GET /api/aprende/categorias ───────────────────────────
@aprende_bp.route('/categorias', methods=['GET'])
def listar_categorias():
    """
    Devuelve las categorías de artículos y niveles disponibles.
    Útil para construir filtros en el frontend.
    """
    categorias = sorted(set(a['categoria'] for a in ARTICULOS))
    niveles    = ['basico', 'intermedio', 'avanzado']
    return jsonify({
        'categorias': categorias,
        'niveles':    niveles,
        'total_articulos': len(ARTICULOS),
        'total_terminos_glosario': len(GLOSARIO),
        'total_temas_busqueda': len(BASE_CONOCIMIENTO),
    }), 200