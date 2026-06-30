# routes/aprende.py

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Any, Optional
import math
import re

router = APIRouter()


# ════════════════════════════════════════════════════════════════════════════
#  ENCICLOPEDIA FINANCIERA  (sin cambios — Python puro)
# ════════════════════════════════════════════════════════════════════════════

ENCICLOPEDIA = {
   
    # ── AHORRO ───────────────────────────────────────────────────────────────
    "ahorro": {
        "id": "ahorro",
        "emoji": "💰",
        "categoria": "Ahorro",
        "nivel": "basico",
        "titulo": "Ahorro personal",
        "resumen": "El ahorro es la parte del ingreso que no se gasta y se reserva para uso futuro. Es la base de toda salud financiera.",
        "secciones": [
            {
                "subtitulo": "¿Qué es el ahorro?",
                "contenido": "Ahorrar es guardar una parte de lo que ganas antes de gastar. No es lo que queda al final del mes — es lo primero que separas. La regla universal es págate a ti primero: cuando recibas tu ingreso, transfiere un porcentaje fijo a una cuenta separada antes de cualquier otro gasto."
            },
            {
                "subtitulo": "¿Cuánto debo ahorrar?",
                "contenido": "La regla más usada es el 20% del ingreso mensual. Si ganas $2.000.000 → deberías ahorrar $400.000 mensualmente. Si eso es imposible ahora, empieza con el 5% o el 10% y auméntalo progresivamente. Lo importante es el hábito, no el monto inicial."
            },
            {
                "subtitulo": "Los 'gastos hormiga': el enemigo silencioso",
                "contenido": "Los gastos pequeños y frecuentes destruyen el ahorro sin que lo notes. Un café diario de $3.000 son $90.000 al mes. Dos domicilios a la semana a $15.000 son $120.000. Una suscripción olvidada son $25.000. Total: $235.000 mensuales que podrías estar ahorrando sin cambiar tu calidad de vida."
            },
            {
                "subtitulo": "Cómo automatizar el ahorro",
                "contenido": "Configura una transferencia automática el mismo día que recibes tu ingreso hacia una cuenta de ahorros separada. La mayoría de bancos colombianos (Bancolombia, Davivienda, BBVA, Nequi, Daviplata) permiten programar esto gratuitamente. Lo que no ves, no lo gastas."
            },
            {
                "subtitulo": "Tipos de ahorro según el plazo",
                "contenido": "Corto plazo (0-12 meses): cuenta de ahorros o Nequi para emergencias y metas inmediatas. Mediano plazo (1-3 años): CDT o fondos de liquidez con mejor rendimiento. Largo plazo (+3 años): fondos de inversión, pensión voluntaria o finca raíz."
            }
        ],
        "ejemplo": {
            "titulo": "Ejemplo real con $1.800.000 de ingreso mensual",
            "detalle": "Regla del 20% → $360.000/mes en ahorro.\n\nMes 1: $360.000\nMes 6: $2.160.000\nMes 12: $4.320.000\nMes 36 (3 años): $12.960.000 + intereses del CDT ≈ $14.500.000\n\n¿Con qué? Con el dinero que antes 'se perdía' sin saber cómo."
        },
        "consejo": "💡 Reto de 30 días: anota CADA gasto durante un mes completo. Al final sabrás exactamente cuánto puedes ahorrar sin esfuerzo real.",
        "tags": ["ahorro", "dinero", "ingreso", "presupuesto", "gastos", "pagarte a ti primero", "nequi", "daviplata"],
        "relacionados": ["presupuesto", "fondo_emergencia", "cdt", "meta_ahorro"]
    },

    # ── PRESUPUESTO / REGLA 50/30/20 ─────────────────────────────────────────
    "presupuesto": {
        "id": "presupuesto",
        "emoji": "📋",
        "categoria": "Presupuesto",
        "nivel": "basico",
        "titulo": "Presupuesto personal — Regla 50/30/20",
        "resumen": "Un presupuesto es el plan que define cómo vas a usar tu dinero cada mes. La regla 50/30/20 es el método más simple y efectivo para empezar.",
        "secciones": [
            {
                "subtitulo": "¿Por qué necesitas un presupuesto?",
                "contenido": "Sin presupuesto, el dinero 'desaparece' sin explicación. Con presupuesto, tomas decisiones conscientes sobre cada peso que entra y sale. El 86% de las personas que siguen un presupuesto logran ahorrar más que quienes no lo hacen."
            },
            {
                "subtitulo": "La Regla 50/30/20 explicada",
                "contenido": "50% Necesidades: todo lo que debes pagar para vivir (arriendo, comida, transporte, salud, servicios públicos, educación). 30% Deseos: lo que quieres pero no necesitas (restaurantes, entretenimiento, ropa nueva, suscripciones, hobbies). 20% Ahorro e inversión: CDT, fondo de emergencia, metas de ahorro, pensión voluntaria."
            },
            {
                "subtitulo": "¿Qué pasa si mis necesidades superan el 50%?",
                "contenido": "Es muy común en Colombia, especialmente en ciudades con alto costo de arriendo. En ese caso ajusta: usa 60/20/20 o incluso 70/15/15. Lo ÚNICO innegociable es que siempre haya un porcentaje para ahorro, así sea el 5%. El orden importa: primero paga necesidades, luego ahorra, con lo que queda disfruta."
            },
            {
                "subtitulo": "Cómo hacer tu presupuesto en 4 pasos",
                "contenido": "1. Calcula tu ingreso neto mensual real (lo que efectivamente recibes después de descuentos). 2. Lista todos tus gastos fijos del último mes. 3. Aplica la regla 50/30/20. 4. Revísalo y ajústalo cada mes — el primer presupuesto nunca es perfecto."
            }
        ],
        "ejemplo": {
            "titulo": "Ingreso mensual: $2.500.000",
            "detalle": "50% Necesidades → $1.250.000\n   Arriendo: $800.000\n   Comida: $300.000\n   Transporte: $150.000\n\n30% Deseos → $750.000\n   Salidas/entretenimiento: $400.000\n   Ropa/otros: $350.000\n\n20% Ahorro → $500.000\n   Fondo de emergencia: $200.000\n   Meta vacaciones: $150.000\n   CDT/inversión: $150.000"
        },
        "consejo": "💡 Usa FinanBot para registrar tus gastos por categoría. Al final del mes verás automáticamente en qué categoría te excediste.",
        "tags": ["presupuesto", "regla 50 30 20", "50/30/20", "necesidades", "deseos", "ahorro", "distribución ingreso", "planificación"],
        "relacionados": ["ahorro", "gastos", "fondo_emergencia", "inversion"]
    },

    # ── CDT ───────────────────────────────────────────────────────────────────
    "cdt": {
        "id": "cdt",
        "emoji": "🏦",
        "categoria": "Inversión",
        "nivel": "basico",
        "titulo": "CDT — Certificado de Depósito a Término",
        "resumen": "El CDT es el producto de ahorro e inversión más conocido en Colombia. Depositas dinero por un plazo fijo y recibes una tasa de interés garantizada desde el inicio.",
        "secciones": [
            {
                "subtitulo": "¿Qué es un CDT?",
                "contenido": "Es un producto financiero ofrecido por bancos, cooperativas y corporaciones financieras en Colombia. Depositas un monto mínimo por un plazo determinado (30, 60, 90, 180 o 360 días) y al vencer recibes tu capital más los intereses pactados. La tasa no cambia durante el plazo — es fija desde el primer día."
            },
            {
                "subtitulo": "Tasas de referencia 2024 en Colombia",
                "contenido": "Corto plazo (30-90 días): 8% - 10% EA. Mediano plazo (180-360 días): 10% - 13% EA. Largo plazo (más de 1 año): 12% - 14% EA. Estas tasas varían según el banco, el monto y el plazo. Los bancos digitales y cooperativas suelen ofrecer mejores tasas que la banca tradicional."
            },
            {
                "subtitulo": "¿Qué pasa si necesito el dinero antes del plazo?",
                "contenido": "En la mayoría de casos puedes romper el CDT antes del vencimiento, pero con una penalidad que reduce o elimina los intereses ganados. Por eso es fundamental que el dinero que inviertas en CDT sea dinero que no vas a necesitar en el corto plazo. Para dinero de emergencia usa mejor una cuenta de ahorros o Nequi."
            },
            {
                "subtitulo": "Seguridad y respaldo del CDT",
                "contenido": "Los CDT en entidades vigiladas por la Superfinanciera están asegurados por Fogafín hasta $50 millones por persona por entidad. Esto significa que si el banco quiebra, el gobierno te devuelve hasta ese monto. Es uno de los instrumentos más seguros del mercado colombiano."
            },
            {
                "subtitulo": "¿Dónde abrir un CDT en Colombia?",
                "contenido": "Banca tradicional: Bancolombia, Davivienda, BBVA, Banco de Bogotá, Banco Popular. Banca digital con mejores tasas: Bancamía, JFK, cooperativas financieras. Plataformas de inversión: Tyba, Tributi, que concentran varias opciones. Siempre compara tasas antes de decidir."
            }
        ],
        "ejemplo": {
            "titulo": "CDT de $3.000.000 al 12% EA por 12 meses",
            "detalle": "Capital inicial: $3.000.000\nTasa: 12% EA (efectiva anual)\nPlazo: 12 meses\n\nInterés ganado: $360.000\nTotal al vencer: $3.360.000\n\n¿Cuánto pagaste por este dinero extra? Nada.\n¿Qué riesgo tomaste? Casi ninguno.\n¿Puedes superar la inflación? Sí, si la inflación es menor al 12%."
        },
        "consejo": "💡 Asegúrate de que la tasa del CDT supere la inflación actual para que tu dinero realmente crezca en poder adquisitivo y no solo en pesos nominales.",
        "tags": ["cdt", "certificado deposito termino", "inversión", "tasa fija", "fogafin", "banco", "plazo fijo", "rendimiento", "colombia"],
        "relacionados": ["ahorro", "interes_compuesto", "inflacion", "inversion"]
    },

    # ── FONDO DE EMERGENCIA ───────────────────────────────────────────────────
    "fondo_emergencia": {
        "id": "fondo_emergencia",
        "emoji": "🛡️",
        "categoria": "Seguridad financiera",
        "nivel": "basico",
        "titulo": "Fondo de emergencia — Tu red de seguridad financiera",
        "resumen": "El fondo de emergencia es dinero reservado exclusivamente para imprevistos graves. Es lo primero que debes construir antes de cualquier inversión.",
        "secciones": [
            {
                "subtitulo": "¿Para qué sirve el fondo de emergencia?",
                "contenido": "Para cubrir gastos urgentes e inesperados sin endeudarte: pérdida repentina de empleo, emergencia médica no cubierta por EPS, falla grave del carro o moto que necesitas para trabajar, reparación urgente del lugar donde vives, o cualquier crisis que interrumpa tu flujo de ingresos."
            },
            {
                "subtitulo": "¿Cuánto dinero necesito?",
                "contenido": "Empleado en empresa estable con buen historial: 3 meses de gastos básicos. Empleado en empresa inestable o sector variable: 4-6 meses. Trabajador independiente, freelance o emprendedor: 6-12 meses. Los gastos básicos incluyen: arriendo, comida, servicios, transporte, mínimo de deudas."
            },
            {
                "subtitulo": "¿Dónde guardar el fondo de emergencia?",
                "contenido": "Debe estar en un lugar de fácil acceso (puedes retirar en menos de 24 horas) y con algo de rendimiento. Opciones recomendadas: cuenta de ahorros tradicional, Nequi o Daviplata (rendimiento diario), fondos de liquidez (como Fiduciaria Bancolombia o Skandia), CDT a 30 días renovable. NO en criptomonedas, acciones o inversiones de largo plazo — podrían estar en baja justo cuando más los necesitas."
            },
            {
                "subtitulo": "El fondo de emergencia va ANTES que invertir",
                "contenido": "Este es el error más común: querer invertir antes de tener fondo de emergencia. Si inviertes $5.000.000 en acciones y de pronto necesitas $2.000.000 urgente, podrías vender en el peor momento (pérdida) o endeudarte. El fondo de emergencia te da la tranquilidad para invertir sin miedo al corto plazo."
            },
            {
                "subtitulo": "Cómo construirlo paso a paso",
                "contenido": "Paso 1: Calcula cuánto son 3 meses de tus gastos básicos. Paso 2: Abre una cuenta separada solo para emergencias (Nequi o cuenta de ahorros aparte). Paso 3: Transfiere mensualmente hasta completarlo (puede tomar 6-12 meses). Paso 4: No lo toques para gastos que no sean emergencias reales. ¿Ropa en oferta es emergencia? No. ¿Despido inesperado? Sí."
            }
        ],
        "ejemplo": {
            "titulo": "Gastos básicos mensuales: $1.600.000",
            "detalle": "Arriendo: $800.000\nComida: $400.000\nTransporte: $150.000\nServicios: $150.000\nDeuda mínima: $100.000\nTotal básico: $1.600.000\n\nFondo mínimo (3 meses): $4.800.000\nFondo ideal (6 meses): $9.600.000\n\nSi ahorras $400.000/mes para el fondo → lo completas en 12 meses (3 meses) o 24 meses (6 meses)."
        },
        "consejo": "💡 Una vez completes tu fondo de emergencia, NUNCA lo uses para vacaciones, caprichos o inversiones. Existe solo para emergencias reales. Si lo usas, reconstrúyelo antes de invertir.",
        "tags": ["fondo emergencia", "emergencia", "seguridad financiera", "ahorro emergencia", "imprevistos", "colchon", "nequi", "liquidez"],
        "relacionados": ["ahorro", "presupuesto", "deudas", "inversion"]
    },

    # ── DEUDAS ────────────────────────────────────────────────────────────────
    "deudas": {
        "id": "deudas",
        "emoji": "💳",
        "categoria": "Deudas y crédito",
        "nivel": "basico",
        "titulo": "Cómo salir de deudas — Bola de nieve y avalancha",
        "resumen": "Salir de deudas requiere un plan estructurado. Existen dos métodos probados: la Bola de Nieve (motivación) y la Avalancha (eficiencia matemática).",
        "secciones": [
            {
                "subtitulo": "Paso 1: Inventario completo de deudas",
                "contenido": "Antes de cualquier estrategia, lista todas tus deudas en papel o digital: nombre del acreedor, monto total, cuota mensual, y tasa de interés anual. Incluye tarjetas de crédito, créditos de libre inversión, préstamos familiares, crédito de vehículo, hipoteca. La mayoría de personas se sorprende del total real cuando lo ve todo junto."
            },
            {
                "subtitulo": "Método Bola de Nieve (Dave Ramsey)",
                "contenido": "Ordena tus deudas de menor a mayor monto total. Paga el mínimo en todas las demás. Enfoca todo el dinero extra en la deuda más pequeña. Cuando la elimines, pasa todo ese dinero (el mínimo que ya no pagas + el extra) a la siguiente. La ventaja: eliminar deudas pequeñas rápido genera victorias psicológicas que mantienen la motivación."
            },
            {
                "subtitulo": "Método Avalancha (matemáticamente óptimo)",
                "contenido": "Ordena tus deudas de mayor a menor tasa de interés. Paga el mínimo en todas las demás. Enfoca todo el dinero extra en la de mayor tasa. La ventaja: pagas menos intereses en total. La desventaja: si la deuda más cara es grande, puede tardar meses sin ver resultados visibles. Requiere más disciplina psicológica."
            },
            {
                "subtitulo": "¿Cuál método elegir?",
                "contenido": "Si eres una persona que necesita motivación constante para no rendirse → Bola de Nieve. Si eres analítico y te motiva la eficiencia matemática → Avalancha. Cualquiera es infinitamente mejor que no tener ningún plan. Lo más importante: no adquieras nuevas deudas mientras pagas las actuales."
            },
            {
                "subtitulo": "Las deudas peligrosas en Colombia",
                "contenido": "Gota a gota: ilegales, con tasas del 300% a 1.200% anual, usualmente vinculados a crimen organizado. Nunca. Tarjetas de crédito con tasa máxima: hasta 28% EA — si solo pagas el mínimo, la deuda nunca se extingue. Créditos informales: muy altos y sin regulación. Préstamos día a día en apps: tasas efectivas enormes disfrazadas de 'comisiones'."
            }
        ],
        "ejemplo": {
            "titulo": "Ejemplo: 3 deudas usando Avalancha",
            "detalle": "Deuda A: Tarjeta de crédito → $1.500.000 / Tasa 28% EA\nDeuda B: Crédito libre inversión → $5.000.000 / Tasa 18% EA\nDeuda C: Préstamo familiar → $2.000.000 / Tasa 0%\n\nOrden Avalancha: A → B → C\nDinero extra disponible: $300.000/mes\n\nTodo el extra va a A hasta liquidarla.\nLuego todo (mínimo de A + extra) va a B.\nPor último C (sin interés, puede esperar).\n\nResultado: ahorras entre $400.000 y $800.000 en intereses vs. pagar aleatoriamente."
        },
        "consejo": "🚨 Si tienes deudas con 'gota a gota' o prestamistas informales, busca asesoría urgente. Son ilegales y peligrosos. Puedes denunciar ante la Policía Nacional o la Superintendencia Financiera.",
        "tags": ["deudas", "salir de deudas", "bola de nieve", "avalancha", "tarjeta crédito", "crédito", "intereses", "gota a gota", "endeudamiento"],
        "relacionados": ["tarjeta_credito", "interes_compuesto", "presupuesto", "fondo_emergencia"]
    },

    # ── INTERÉS COMPUESTO ─────────────────────────────────────────────────────
    "interes_compuesto": {
        "id": "interes_compuesto",
        "emoji": "📈",
        "categoria": "Conceptos financieros",
        "nivel": "intermedio",
        "titulo": "Interés compuesto — La octava maravilla del mundo",
        "resumen": "El interés compuesto es el proceso por el cual los intereses generan nuevos intereses, creando un efecto de crecimiento exponencial. Einstein lo llamó 'la octava maravilla del mundo'.",
        "secciones": [
            {
                "subtitulo": "Interés simple vs interés compuesto",
                "contenido": "Interés simple: los intereses se calculan siempre sobre el capital original. Si inviertes $1.000.000 al 10% simple por 3 años, cada año ganas $100.000 en intereses → total $1.300.000. Interés compuesto: los intereses del período anterior se suman al capital para el siguiente cálculo. Los intereses generan intereses."
            },
            {
                "subtitulo": "La fórmula del interés compuesto",
                "contenido": "Capital Final = Capital × (1 + Tasa)^Tiempo\n\nDonde: Capital = monto inicial, Tasa = tasa de interés por período, Tiempo = número de períodos. Para tasas anuales aplicadas mensualmente: Tasa mensual = (1 + Tasa anual)^(1/12) - 1."
            },
            {
                "subtitulo": "El tiempo es tu mayor aliado",
                "contenido": "La variable más poderosa del interés compuesto no es la tasa ni el monto inicial — es el tiempo. Quien empieza a los 25 años tiene enorme ventaja sobre quien empieza a los 35 años, aunque este último invierta el doble mensualmente. Por eso el mejor momento para invertir es hoy. El segundo mejor momento es mañana."
            },
            {
                "subtitulo": "La regla del 72: cuándo se duplica tu dinero",
                "contenido": "Divide 72 entre la tasa de interés anual y obtendrás los años que tarda en duplicarse tu inversión. Con CDT al 12%: 72/12 = 6 años para duplicar tu capital. Con el 8%: 72/8 = 9 años. Con el 4% (cuenta de ahorros): 72/4 = 18 años. Esta regla te ayuda a comparar opciones de inversión rápidamente."
            },
            {
                "subtitulo": "El interés compuesto en tu contra: las deudas",
                "contenido": "Exactamente el mismo efecto funciona en tu contra con deudas de alta tasa. Una tarjeta de crédito al 28% EA con deuda de $2.000.000 a la que solo pagas el mínimo: en 3 años habrás pagado $1.800.000 en intereses y todavía deberás más del capital original. El interés compuesto de las deudas destruye el patrimonio."
            }
        ],
        "ejemplo": {
            "titulo": "$1.000.000 al 10% anual compuesto",
            "detalle": "Año 1:  $1.100.000\nAño 2:  $1.210.000\nAño 3:  $1.331.000\nAño 5:  $1.610.510\nAño 10: $2.593.742\nAño 20: $6.727.500\nAño 30: $17.449.402\n\nVs interés simple a 30 años:\nCapital + intereses = $1.000.000 + (100.000 × 30) = $4.000.000\n\nDiferencia: $13.449.402 extra gracias al efecto compuesto."
        },
        "consejo": "💡 Aunque sea pequeño, empieza a invertir HOY. $100.000 mensuales durante 30 años al 10% compuesto = más de $21.000.000. El tiempo hace el trabajo por ti.",
        "tags": ["interés compuesto", "interés simple", "inversión", "rendimiento", "tiempo", "crecimiento exponencial", "regla del 72", "warren buffett"],
        "relacionados": ["cdt", "inversion", "ahorro", "pension_voluntaria"]
    },

    # ── INFLACIÓN ─────────────────────────────────────────────────────────────
    "inflacion": {
        "id": "inflacion",
        "emoji": "📉",
        "categoria": "Economía",
        "nivel": "intermedio",
        "titulo": "Inflación — Cómo proteger tu poder adquisitivo",
        "resumen": "La inflación es el aumento generalizado y sostenido de los precios. Reduce silenciosamente el valor de tu dinero cada año sin que lo notes.",
        "secciones": [
            {
                "subtitulo": "¿Qué es la inflación?",
                "contenido": "Si la inflación es del 9%, lo que hoy cuesta $100.000 el próximo año costará $109.000. Tu $100.000 puede comprar menos cosas que antes — eso es pérdida de poder adquisitivo. Colombia ha tenido inflaciones históricas entre 3% y 13% en los últimos 10 años. El DANE publica el IPC mensualmente."
            },
            {
                "subtitulo": "Inflación 2024 en Colombia",
                "contenido": "La inflación en Colombia cerró 2023 en 9.28% anual, después de un pico de 13.1% en 2022. Para 2024, el Banco de la República proyecta una reducción progresiva hacia el 5-6%. Esto significa que si tu dinero no crece al menos al ritmo de la inflación, estás perdiendo poder adquisitivo aunque el número en tu cuenta aumente."
            },
            {
                "subtitulo": "El efectivo es el peor enemigo en épocas de inflación",
                "contenido": "Dinero guardado en efectivo o en una cuenta de ahorros con 2-3% de rendimiento cuando la inflación es del 9%, implica una pérdida real del 6-7% anual. $10.000.000 guardados en una caja un año = poder comprar lo que antes costaba $9.072.000. Perdiste $928.000 en poder adquisitivo sin gastar nada."
            },
            {
                "subtitulo": "Cómo protegerte de la inflación",
                "contenido": "CDT con tasa superior a la inflación: si el CDT paga 12% y la inflación es 9%, tu ganancia real es del 3%. Fondos de inversión en renta variable: históricamente superan la inflación en el largo plazo. Finca raíz: valorización histórica en Colombia supera la inflación en ciudades principales. Dólares o activos en moneda extranjera: diversifica el riesgo cambiario."
            },
            {
                "subtitulo": "La tasa de interés real: lo que realmente ganas",
                "contenido": "Tasa real = Tasa nominal − Inflación (aproximación). Si tu CDT paga 12% y la inflación es 9% → tasa real ≈ 3%. Eso significa que tu dinero creció un 3% en poder adquisitivo real. Si el CDT paga 7% y la inflación es 9% → tasa real ≈ -2%. Perdiste poder adquisitivo aunque ganaste pesos."
            }
        ],
        "ejemplo": {
            "titulo": "$5.000.000 con inflación del 9% anual",
            "detalle": "Año 0: Puedes comprar 100 artículos de $50.000\nAño 1: Esos artículos cuestan $54.500 → solo compras 91\nAño 2: Cuestan $59.405 → solo compras 84\nAño 3: Cuestan $64.751 → solo compras 77\n\nEn 3 años perdiste el 23% de tu poder adquisitivo guardando el dinero.\n\nSolución: CDT al 12% → en 3 años tienes $7.049.280 y la inflación acumulada fue del 29.5% → poder adquisitivo neto +2%."
        },
        "consejo": "💡 Regla práctica: si tu inversión rinde menos que la inflación del año, estás perdiendo dinero aunque el número en tu cuenta sea mayor. Siempre compara tasas contra la inflación real.",
        "tags": ["inflación", "IPC", "poder adquisitivo", "precios", "Banco de la República", "Colombia", "tasa real", "devaluación"],
        "relacionados": ["cdt", "inversion", "ahorro", "interes_compuesto"]
    },

    # ── PENSIÓN COLOMBIA ──────────────────────────────────────────────────────
    "pension": {
        "id": "pension",
        "emoji": "👴",
        "categoria": "Pensión y jubilación",
        "nivel": "intermedio",
        "titulo": "Pensión en Colombia — Colpensiones vs Fondos Privados (AFP)",
        "resumen": "Colombia tiene dos regímenes pensionales: Prima Media (Colpensiones) y Ahorro Individual (AFP). Elegir mal puede costar millones de pesos en el largo plazo.",
        "secciones": [
            {
                "subtitulo": "Colpensiones — Régimen de Prima Media (RPM)",
                "contenido": "El Estado administra los aportes de todos los afiliados en un fondo común. Para pensionarse necesitas: 1.300 semanas cotizadas (25 años), y tener 57 años si eres mujer o 62 si eres hombre. La pensión mínima garantizada es 1 SMMLV (para 2024: $1.300.000). Si cotizaste bien, puedes recibir hasta el 80% del salario base de liquidación."
            },
            {
                "subtitulo": "AFP — Régimen de Ahorro Individual (RAIS)",
                "contenido": "Cada afiliado tiene una cuenta individual a su nombre. Los aportes se invierten y generan rendimientos. Para pensionarse: capital suficiente en la cuenta, o 1.150 semanas + 57/62 años con garantía de pensión mínima. Las AFP en Colombia: Colfondos, Porvenir, Protección, Old Mutual (Skandia). Puedes elegir el nivel de riesgo del portafolio."
            },
            {
                "subtitulo": "¿Cuál es mejor para ti?",
                "contenido": "Colpensiones conviene a: mujeres (menor edad de pensión), personas con ingresos bajos o variables, quienes han cotizado muchos años al mismo salario. AFP conviene a: hombres con ingresos altos y estables, independientes con ingresos fluctuantes, quienes quieren herencia (el saldo de la cuenta es heritable). La decisión es compleja — considera asesoría especializada."
            },
            {
                "subtitulo": "Aportes voluntarios: tu mejor aliado tributario",
                "contenido": "Independientemente del régimen, puedes hacer aportes voluntarios a pensión (Artículo 126-1 del Estatuto Tributario). Estos aportes son deducibles de renta hasta el 30% del ingreso, con un máximo de 3.800 UVT anuales. En términos prácticos: $300.000/mes en aportes voluntarios pueden ahorrarte cerca de $57.000/mes en impuestos si eres contribuyente de renta."
            },
            {
                "subtitulo": "La cruda realidad pensional en Colombia",
                "contenido": "El 75% de los colombianos NO se pensiona. Las razones principales: cotización discontinua por informalidad laboral, cambios de trabajo frecuentes sin continuidad, bajos salarios históricos. Si eres independiente o tienes ingresos variables, planifica tu pensión desde hoy con ahorro adicional. No depender solo del sistema pensional obligatorio es fundamental."
            }
        ],
        "ejemplo": {
            "titulo": "Aportes voluntarios: $300.000/mes durante 20 años al 8% anual",
            "detalle": "Total aportado: $72.000.000\nRendimientos al 8% anual compuesto: $106.000.000 aprox.\nCapital pensional adicional: ~$178.000.000\n\nAhorro en impuestos anual (tasa 19%): $570.000/año\nAhorro total en 20 años solo en impuestos: $11.400.000\n\nConclusión: Es una de las mejores inversiones disponibles para quien tributa renta."
        },
        "consejo": "💡 No importa en qué régimen estés: complementa SIEMPRE con ahorro e inversión personal. El sistema pensional colombiano no garantiza bienestar financiero en la vejez por sí solo.",
        "tags": ["pensión", "colpensiones", "AFP", "RAIS", "RPM", "jubilación", "retiro", "aportes voluntarios", "Colombia", "vejez"],
        "relacionados": ["interes_compuesto", "inversion", "ahorro", "impuestos"]
    },

    # ── INVERSIÓN ─────────────────────────────────────────────────────────────
    "inversion": {
        "id": "inversion",
        "emoji": "💹",
        "categoria": "Inversión",
        "nivel": "intermedio",
        "titulo": "Inversiones para principiantes en Colombia",
        "resumen": "Invertir es hacer que tu dinero trabaje para ti. Conoce los vehículos de inversión disponibles en Colombia según tu perfil de riesgo y plazo.",
        "secciones": [
            {
                "subtitulo": "Antes de invertir: los 3 requisitos",
                "contenido": "1. Fondo de emergencia completo (3-6 meses de gastos). Si no lo tienes, construyelo primero. 2. Deudas de alto interés pagadas. No tiene sentido invertir al 12% teniendo deudas al 28%. Primero paga la tarjeta. 3. Conocimiento del instrumento. Nunca inviertas en algo que no entiendes completamente. La ignorancia financiera es el mayor riesgo."
            },
            {
                "subtitulo": "Perfil de riesgo: ¿quién eres como inversor?",
                "contenido": "Conservador: prioriza no perder capital sobre ganar rendimiento alto. Instrumentos: CDT, cuentas de ahorro, fondos conservadores. Moderado: acepta algo de fluctuación por mejor rendimiento a mediano plazo. Instrumentos: fondos balanceados, títulos de deuda pública (TES). Agresivo: acepta volatilidad importante por mayor potencial de retorno. Instrumentos: acciones BVC, ETFs, fondos de renta variable."
            },
            {
                "subtitulo": "Opciones de inversión en Colombia por riesgo",
                "contenido": "Riesgo muy bajo: CDT (8-14% EA), cuentas de ahorro (2-5%), Fogafín garantizados. Riesgo bajo-medio: Fondos de inversión colectiva conservadores y moderados, TES (títulos del gobierno). Riesgo medio-alto: acciones en la BVC (Bancolombia, Ecopetrol, Grupo Sura), fondos de renta variable. Riesgo alto: criptomonedas, startups, materias primas. Riesgo muy alto: derivados, divisas (Forex), apalancamiento."
            },
            {
                "subtitulo": "La diversificación: no pongas todos los huevos en una canasta",
                "contenido": "Un portafolio diversificado distribuye el riesgo entre diferentes tipos de activos, sectores y geografías. Si una inversión baja, las demás pueden compensar. Ejemplo conservador: 60% CDT + 30% fondo moderado + 10% acciones. Ejemplo moderado: 30% CDT + 40% fondo balanceado + 20% acciones Colombia + 10% ETF internacional."
            },
            {
                "subtitulo": "El error más costoso: tratar de 'ganarle al mercado'",
                "contenido": "El 90% de los inversores individuales que intentan elegir acciones ganan menos que un simple índice de mercado. En vez de tratar de predecir cuál acción subirá, considera invertir en ETFs o fondos indexados que replican el mercado completo. Warren Buffett recomienda esto para la mayoría de inversores no profesionales."
            }
        ],
        "ejemplo": {
            "titulo": "Portafolio conservador con $5.000.000",
            "detalle": "CDT 6 meses al 12% EA: $3.000.000\nFondo de inversión moderado: $1.500.000\nAcción Bancolombia (largo plazo): $500.000\n\nRendimiento estimado anual:\nCDT: $360.000\nFondo: $150.000-$300.000\nAcción: variable (-10% a +25%)\n\nTotal estimado: $5.600.000 a $6.000.000 en 12 meses\n(Escenario moderado — no garantizado)"
        },
        "consejo": "💡 Desconfía de cualquier inversión que prometa rendimientos garantizados muy altos (más del 3-4% mensual). En Colombia, las pirámides y esquemas Ponzi son frecuentes. Si suena demasiado bueno, es una estafa.",
        "tags": ["inversión", "invertir", "portafolio", "riesgo", "CDT", "acciones", "BVC", "fondos", "ETF", "diversificación", "Colombia"],
        "relacionados": ["cdt", "interes_compuesto", "inflacion", "fondo_emergencia"]
    },

    # ── CRIPTOMONEDAS ─────────────────────────────────────────────────────────
    "criptomonedas": {
        "id": "criptomonedas",
        "emoji": "₿",
        "categoria": "Inversión alternativa",
        "nivel": "avanzado",
        "titulo": "Criptomonedas — Riesgos y realidades antes de invertir",
        "resumen": "Las criptomonedas son activos digitales descentralizados con alta volatilidad y sin respaldo estatal. Invertir en ellas requiere conocimiento y tolerancia al riesgo extremo.",
        "secciones": [
            {
                "subtitulo": "¿Qué son las criptomonedas?",
                "contenido": "Son activos digitales que funcionan en redes descentralizadas (blockchain) sin control de ningún gobierno o banco central. Las principales: Bitcoin (BTC) como reserva de valor, Ethereum (ETH) como plataforma de contratos inteligentes, y miles de altcoins con diferentes propósitos (o sin ninguno real)."
            },
            {
                "subtitulo": "El riesgo real que debes entender",
                "contenido": "Volatilidad extrema: Bitcoin cayó un 75% entre noviembre 2021 y junio 2022 (de $68.000 a $17.000 USD). Sin regulación: en Colombia las criptomonedas no tienen protección estatal. Si una exchange quiebra o te hackean, pierdes todo. Sin garantía: si pierdes tu clave privada (seed phrase), pierdes el acceso permanentemente. No hay banco que te ayude."
            },
            {
                "subtitulo": "El ecosistema de estafas en Colombia",
                "contenido": "Las estafas de criptomonedas son masivas en Colombia. Señales de alerta: rendimientos garantizados muy altos ('te garantizamos 10% mensual'), presión para invertir rápido ('esta oferta vence mañana'), referidos con comisión (estructura piramidal), influencers pagados sin disclaimers, plataformas sin regulación ni sede física conocida."
            },
            {
                "subtitulo": "Si decides invertir: reglas de oro",
                "contenido": "Máximo 5-10% de tu portafolio total. Solo dinero que puedes perder completamente sin afectar tu vida. Plataformas reconocidas: Binance, Coinbase, Kraken, Bitso (disponible en Colombia). Guarda tus criptos en wallet propia si el monto es importante (no en exchanges). Nunca inviertas siguiendo consejos de grupos de WhatsApp o Telegram."
            },
            {
                "subtitulo": "Las criptomonedas y los impuestos en Colombia",
                "contenido": "La DIAN considera las criptomonedas como activos sujetos a declaración de renta. Las ganancias son gravables como ganancia ocasional al 10%. Si tienes montos significativos, debes declararlos en tu patrimonio. El incumplimiento puede generar sanciones. Consulta con un contador antes de invertir montos importantes."
            }
        ],
        "ejemplo": {
            "titulo": "Bitcoin: volatilidad histórica",
            "detalle": "Nov 2021: $68.000 USD (máximo histórico)\nJun 2022: $17.000 USD (caída del 75%)\nDic 2022: $16.500 USD (otro mínimo)\nDic 2023: $44.000 USD (recuperación)\nMar 2024: $73.000 USD (nuevo máximo histórico)\n\nConclusion: quien compró en el máximo y vendió en el mínimo, perdió el 75% de su inversión. Quien aguantó y vendió en 2024, ganó el 7%. El timing es imposible de predecir."
        },
        "consejo": "🚨 Regla de oro: si no entiendes cómo funciona técnicamente el activo en el que vas a invertir, no inviertas. En criptomonedas, la ignorancia se paga con pérdidas reales.",
        "tags": ["criptomonedas", "bitcoin", "ethereum", "blockchain", "crypto", "BTC", "estafa", "volatilidad", "Binance", "DIAN", "Colombia"],
        "relacionados": ["inversion", "inflacion", "interes_compuesto"]
    },

    # ── TARJETA DE CRÉDITO ────────────────────────────────────────────────────
    "tarjeta_credito": {
        "id": "tarjeta_credito",
        "emoji": "💳",
        "categoria": "Crédito",
        "nivel": "basico",
        "titulo": "Tarjeta de crédito — Cómo usarla a tu favor",
        "resumen": "La tarjeta de crédito es una herramienta financiera poderosa que puede trabajar para ti (cashback, millas, diferido sin intereses) o en tu contra (28% EA de intereses, deuda perpetua).",
        "secciones": [
            {
                "subtitulo": "¿Cómo funciona la tarjeta de crédito?",
                "contenido": "El banco te presta dinero para compras con un límite de crédito. Tienes un período de gracia (generalmente 15-45 días) para pagar sin intereses. Si pagas el total del extracto antes de la fecha límite: no pagas intereses. Si pagas solo el mínimo o cualquier monto parcial: pagas intereses sobre el saldo pendiente."
            },
            {
                "subtitulo": "La tasa de interés: el número que debes conocer",
                "contenido": "En Colombia, la tasa máxima para tarjetas de crédito es del 28-30% EA (efectiva anual), una de las más altas de Latinoamérica. Esto significa que $1.000.000 de deuda al 28% anual genera $280.000 en intereses en un año. Si solo pagas el mínimo (5-10% del saldo), la deuda puede tardar 10+ años en pagarse."
            },
            {
                "subtitulo": "El truco del pago mínimo",
                "contenido": "El pago mínimo está diseñado por el banco para maximizar sus intereses, no para beneficiarte. Ejemplo: $3.000.000 de deuda al 28% EA, pagando el mínimo mensual del 5% ($150.000): tardarás 7-8 años en pagar la deuda y habrás pagado más de $2.000.000 adicionales solo en intereses."
            },
            {
                "subtitulo": "Cómo usar la tarjeta a tu favor",
                "contenido": "SIEMPRE paga el total del extracto antes de la fecha de pago. Usa la tarjeta para gastos que ya tenías planeados — no la uses para gastar de más. Aprovecha beneficios: cashback (devolución de dinero), millas para viajes, seguros incluidos, compras en cuotas sin intereses en establecimientos aliados. La tarjeta de crédito bien usada es un préstamo gratuito por 30-45 días."
            },
            {
                "subtitulo": "Señales de que tienes problemas con la tarjeta",
                "contenido": "Señales de alerta: usas la tarjeta para pagar servicios básicos que antes pagabas en efectivo, llegas al límite antes de mitad de mes, pagas el mínimo regularmente, tienes más de una tarjeta con saldo pendiente, usas una tarjeta para pagar otra. Solución: congela las tarjetas (literalmente), haz un plan de pago agresivo y no uses tarjeta hasta saldar."
            }
        ],
        "ejemplo": {
            "titulo": "Misma deuda, dos estrategias — $2.000.000 al 28% EA",
            "detalle": "Estrategia A — Solo mínimo (5%):\nPago mensual inicial: $100.000\nTiempo para saldar: ~9 años\nIntereses totales: ~$2.400.000\nTotal pagado: ~$4.400.000\n\nEstrategia B — Pago fijo de $300.000/mes:\nTiempo para saldar: 8 meses\nIntereses totales: ~$200.000\nTotal pagado: ~$2.200.000\n\nDiferencia: $2.200.000 ahorrados y 8 años de vida sin esa deuda."
        },
        "consejo": "💡 Si tienes saldo en tarjeta de crédito al 28%, prioritiza pagarlo antes de cualquier inversión. No hay inversión conservadora en Colombia que rinda más del 28%. Pagar la deuda ES la mejor inversión.",
        "tags": ["tarjeta crédito", "tasa máxima", "pago mínimo", "crédito", "deuda", "cuotas", "intereses", "extracto"],
        "relacionados": ["deudas", "presupuesto", "interes_compuesto"]
    },

    # ── FINCA RAÍZ ────────────────────────────────────────────────────────────
    "finca_raiz": {
        "id": "finca_raiz",
        "emoji": "🏠",
        "categoria": "Inversión inmobiliaria",
        "nivel": "avanzado",
        "titulo": "Invertir en finca raíz en Colombia",
        "resumen": "La inversión en finca raíz ha sido históricamente una de las mejores opciones en Colombia, ofreciendo valorización y arriendo como fuentes de retorno.",
        "secciones": [
            {
                "subtitulo": "¿Por qué finca raíz en Colombia?",
                "contenido": "Valorización histórica: en ciudades principales (Bogotá, Medellín, Cali, Cartagena) los inmuebles han valorizado entre 5-12% anual en los últimos 20 años, superando la inflación. Ingreso por arriendo: 3-6% anual del valor del inmueble (canon mensual). Cobertura inflacionaria: los cánones de arriendo se actualizan anualmente según el IPC. Activo tangible con valor intrínseco."
            },
            {
                "subtitulo": "Los números reales de un arriendo",
                "contenido": "Inmueble de $200.000.000 con canon de $900.000/mes → $10.800.000/año → rendimiento por arriendo del 5.4%. Si el inmueble valorizó un 7% → ganancia de valorización $14.000.000. Retorno total anual: $24.800.000 / 12.4% sobre el capital. Descontando administración, predial, mant.: retorno neto ≈ 9-10%."
            },
            {
                "subtitulo": "Los riesgos que nadie menciona",
                "contenido": "Baja liquidez: no puedes vender rápidamente si necesitas el dinero (puede tardar meses o años). Capital inicial alto: en Colombia se requieren mínimo $150-300 millones para propiedades rentables. Costos ocultos: predial, administración, mantenimiento, seguros, periodos sin arrendatario, derechos notariales al comprar/vender. Inquilinos problemáticos: el proceso judicial de desalojo en Colombia puede tardar 1-2 años."
            },
            {
                "subtitulo": "Sin capital para comprar: opciones alternativas",
                "contenido": "Fiducias inmobiliarias: inviertes en proyectos inmobiliarios desde $5-10 millones. Fondos de inversión inmobiliaria (FIIs): inviertes en portafolios de propiedades desde montos bajos. Crowdfunding inmobiliario: plataformas que permiten co-invertir en propiedades. Leasing habitacional: opción para adquirir vivienda con requisitos diferentes al crédito hipotecario."
            }
        ],
        "ejemplo": {
            "titulo": "Comparación: CDT vs Finca Raíz con $200.000.000",
            "detalle": "CDT al 12% por 5 años:\nTotal: $352.470.000\nGanancia: $152.470.000\nRiesgo: Casi cero\nLiquidez: Alta\n\nFinca raíz 5 años:\nValorización 8%: $293.878.000\nArriendo acumulado (5%): $50.000.000\nTotal bruto: $343.878.000\nMenos costos: $343.878.000 - $20.000.000 = $323.878.000\n\nCDT gana en este escenario + tiene menos riesgo + más liquidez.\nFinca raíz gana en escenarios de alta valorización y en el largo plazo (10-20 años)."
        },
        "consejo": "💡 En Colombia, la finca raíz es mejor inversión en horizontes de 10+ años. Para plazos menores a 5 años, generalmente el CDT o fondos de inversión ofrecen mejor relación riesgo-retorno.",
        "tags": ["finca raíz", "inmobiliario", "arriendo", "vivienda", "valorización", "predial", "hipoteca", "leasing", "fiducia"],
        "relacionados": ["inversion", "inflacion", "cdt", "interes_compuesto"]
    },

    # ── IMPUESTOS ─────────────────────────────────────────────────────────────
    "impuestos": {
        "id": "impuestos",
        "emoji": "🧾",
        "categoria": "Impuestos",
        "nivel": "intermedio",
        "titulo": "Impuestos en Colombia — Lo que todo ciudadano debe saber",
        "resumen": "Conocer el sistema tributario colombiano te permite optimizar legalmente tu carga impositiva y evitar sanciones de la DIAN.",
        "secciones": [
            {
                "subtitulo": "¿Quién debe declarar renta en Colombia?",
                "contenido": "Para 2024 (vigencia 2023), debes declarar si: tus ingresos brutos superaron $59.377.000, tienes patrimonio bruto superior a $190.854.000, eres responsable de IVA, tienes consumos en tarjeta que superen $59.377.000, o eres empleado con más de un empleador. Los umbrales se actualizan anualmente. La declaración se hace entre abril y octubre del año siguiente."
            },
            {
                "subtitulo": "Retención en la fuente: el impuesto 'invisible'",
                "contenido": "Tu empleador descuenta mensualmente un porcentaje de tu salario como anticipo del impuesto de renta. La tabla de retención 2024 aplica diferentes tasas según el ingreso mensual en UVT (para 2024: $47.065 por UVT). Si te retienen más de lo que debes, la DIAN te devuelve el saldo a favor. Si retienen menos, debes pagar al declarar."
            },
            {
                "subtitulo": "Deducciones que puedes usar legalmente",
                "contenido": "Intereses de crédito hipotecario o leasing habitacional (hasta $21.629.000 anuales). Aportes voluntarios a pensión (hasta el 30% del ingreso). Aportes a AFC (Ahorro para el Fomento de la Construcción). Medicina prepagada. 4x1000 certificado. Dependientes económicos. Estas deducciones reducen la base gravable sobre la que calculas el impuesto."
            },
            {
                "subtitulo": "IVA en Colombia",
                "contenido": "La tasa general del IVA es 19%. Existen bienes y servicios exentos (0%) como la canasta básica alimentaria, medicamentos, libros y servicios de salud. Bienes excluidos: no causan IVA. Algunos sectores tienen tarifas diferenciales: 5% para ciertos bienes agropecuarios, turismo, etc. Desde 2022 existe el IVA diferido para compras con tarjeta débito en días especiales."
            }
        ],
        "ejemplo": {
            "titulo": "Cálculo simplificado de renta 2024",
            "detalle": "Salario mensual bruto: $4.000.000\nAnual bruto: $48.000.000\n\nDeducciones:\nSalud empleado (4%): $1.920.000\nPensión empleado (4%): $1.920.000\nAporte voluntario pensión: $3.600.000\n\nBase gravable: $48.000.000 - $7.440.000 = $40.560.000\nEn UVT 2024 ($47.065): 861 UVT\n\nImpuesto según tabla: aprox $400.000 anuales\n(La retención mensual debería ser ~$33.000)"
        },
        "consejo": "💡 Los aportes voluntarios a pensión son la deducción más accesible y poderosa para empleados. Si tributa renta, cada $100.000 aportados voluntariamente te ahorra entre $19.000 y $39.000 en impuestos.",
        "tags": ["impuestos", "DIAN", "renta", "IVA", "retención fuente", "declaración", "deducciones", "UVT", "Colombia"],
        "relacionados": ["pension", "inversion", "ahorro"]
    },

    # ── HABITOS FINANCIEROS ───────────────────────────────────────────────────
    "habitos": {
        "id": "habitos",
        "emoji": "🧠",
        "categoria": "Educación financiera",
        "nivel": "basico",
        "titulo": "Los 7 hábitos que cambian tu vida financiera",
        "resumen": "La riqueza no es solo cuestión de ingresos — es cuestión de hábitos. Estas 7 prácticas separan a quienes logran libertad financiera de quienes siempre están ajustados.",
        "secciones": [
            {
                "subtitulo": "Hábito 1: Registra cada peso que gastas",
                "contenido": "La mayoría de personas no sabe realmente en qué gasta su dinero. Registrar cada gasto durante 30 días es el ejercicio más revelador que existe. Quienes registran sus gastos ahorran en promedio un 20% más que quienes no lo hacen. La conciencia es el primer paso al cambio."
            },
            {
                "subtitulo": "Hábito 2: Págate a ti primero",
                "contenido": "Cuando recibes tu ingreso, lo primero que haces es transferir tu ahorro programado a una cuenta separada — ANTES de pagar cualquier otra cosa. No el ahorro de 'lo que sobra' (que nunca sobra) sino el ahorro planificado del porcentaje que decidiste."
            },
            {
                "subtitulo": "Hábito 3: Vive por debajo de tus posibilidades",
                "contenido": "La trampa del consumo: cuando aumenta el ingreso, aumentan los gastos de forma proporcional — el 'nivel de vida' sube y no se ahorra más. El secreto de quienes construyen riqueza: mantienen gastos estables aunque el ingreso suba, y destinan el incremental al ahorro e inversión."
            },
            {
                "subtitulo": "Hábito 4: Aprende continuamente sobre dinero",
                "contenido": "La educación financiera no se enseña en el colegio ni en la universidad tradicional. Debes buscarla activamente. Lee libros como 'Padre Rico Padre Pobre', 'El hombre más rico de Babilonia', 'La psicología del dinero'. Escucha podcasts. Úsate FinanBot para entender conceptos. La ignorancia financiera cuesta millones."
            },
            {
                "subtitulo": "Hábitos 5-7: Evitar deudas de consumo, invertir constante, revisar mensualmente",
                "contenido": "Hábito 5 — Evita deudas de consumo: nunca financiar ropa, electrodomésticos, vacaciones o tecnología a largo plazo con intereses. Si no tienes el dinero, espera y ahorra. Hábito 6 — Invierte poco pero constante: $100.000 mensuales consistentes durante años superan $1.000.000 invertidos una sola vez. La constancia gana. Hábito 7 — Revisa mensualmente: dedica 30 minutos al mes a revisar tus finanzas, ajustar el presupuesto y evaluar el progreso de tus metas."
            }
        ],
        "ejemplo": {
            "titulo": "El costo de no tener hábitos financieros",
            "detalle": "Persona A: Sin hábitos — gana $3.000.000/mes durante 30 años\nIngreso total: $1.080.000.000\nAhorro/patrimonio final: ≈ $10.000.000\n\nPersona B: Con hábitos — gana $3.000.000/mes durante 30 años\nAhorra 20% ($600.000/mes) e invierte al 10%\nPatrimonio final: ≈ $1.350.000.000\n\nDiferencia: $1.340.000.000\nMismo ingreso. Diferente resultado. Solo por hábitos."
        },
        "consejo": "💡 No intentes implementar los 7 hábitos a la vez. Elige uno solo, practícalo durante 3 meses hasta que sea automático, y luego añade el siguiente. La consistencia en poco supera el esfuerzo en mucho.",
        "tags": ["hábitos financieros", "educación financiera", "disciplina", "presupuesto", "ahorro", "riqueza", "libertad financiera", "psicología del dinero"],
        "relacionados": ["presupuesto", "ahorro", "inversion", "fondo_emergencia"]
    },

}



# ════════════════════════════════════════════════════════════════════════════
#  GLOSARIO COMPLETO (35 términos)
# ════════════════════════════════════════════════════════════════════════════

GLOSARIO = [
    {"nombre": "Activo",              "definicion": "Bien o derecho con valor económico que pertenece a una persona. Ejemplos: dinero, propiedades, inversiones, cuentas por cobrar.",                                "categoria": "Conceptos básicos"},
    {"nombre": "AFP",                 "definicion": "Administradora de Fondos de Pensiones. Entidad privada que gestiona ahorros pensionales en el régimen de Ahorro Individual (RAIS). Las AFP en Colombia: Colfondos, Porvenir, Protección, Old Mutual.", "categoria": "Pensión"},
    {"nombre": "Ahorro",              "definicion": "Parte del ingreso que no se gasta y se reserva para uso futuro. Base de toda salud financiera personal.",                                                        "categoria": "Conceptos básicos"},
    {"nombre": "Amortización",        "definicion": "Proceso de pago gradual de una deuda mediante cuotas periódicas que incluyen capital e intereses. En Colombia el sistema más común es el francés (cuota fija).", "categoria": "Crédito"},
    {"nombre": "Apalancamiento",      "definicion": "Uso de deuda para aumentar la capacidad de inversión. Puede multiplicar ganancias pero también pérdidas. Ejemplo: comprar finca raíz con crédito hipotecario.",   "categoria": "Inversión"},
    {"nombre": "AFC",                 "definicion": "Ahorro para el Fomento de la Construcción. Cuenta de ahorro que permite deducción tributaria destinada a la adquisición de vivienda en Colombia.",               "categoria": "Ahorro e inversión"},
    {"nombre": "Balance",             "definicion": "Diferencia entre ingresos y gastos en un período. Balance positivo: ingresas más de lo que gastas. Balance negativo: gastas más de lo que ingresas.",            "categoria": "Conceptos básicos"},
    {"nombre": "BVC",                 "definicion": "Bolsa de Valores de Colombia. Mercado organizado donde se compran y venden acciones de empresas colombianas como Bancolombia, Ecopetrol, Grupo Sura.",             "categoria": "Inversión"},
    {"nombre": "Capital",             "definicion": "Monto inicial de dinero que se invierte o presta. Base sobre la que se calculan los intereses.",                                                                    "categoria": "Conceptos básicos"},
    {"nombre": "CDT",                 "definicion": "Certificado de Depósito a Término. Depositas dinero por un plazo fijo a cambio de una tasa de interés pactada desde el inicio. Asegurado por Fogafín hasta $50M.",  "categoria": "Ahorro e inversión"},
    {"nombre": "Colpensiones",        "definicion": "Administradora estatal del régimen de Prima Media pensional en Colombia. El Estado gestiona los aportes colectivamente y garantiza pensión mínima.",               "categoria": "Pensión"},
    {"nombre": "Crédito",             "definicion": "Préstamo de dinero que debes devolver con intereses en un plazo determinado. El costo se expresa como tasa de interés anual (EA).",                                "categoria": "Crédito"},
    {"nombre": "Cuota fija",          "definicion": "Sistema de amortización (francés) donde la cuota mensual no varía durante todo el plazo. Incluye capital e intereses que se redistribuyen cada mes.",               "categoria": "Crédito"},
    {"nombre": "DANE",                "definicion": "Departamento Administrativo Nacional de Estadística. Entidad que mide la inflación (IPC) y otras variables económicas en Colombia.",                               "categoria": "Economía"},
    {"nombre": "DIAN",                "definicion": "Dirección de Impuestos y Aduanas Nacionales. Entidad que administra el recaudo de impuestos en Colombia (renta, IVA, retención en la fuente).",                   "categoria": "Impuestos"},
    {"nombre": "Diversificación",     "definicion": "Estrategia de invertir en múltiples activos para reducir el riesgo total. 'No pongas todos los huevos en una canasta'. Reduce la exposición a pérdidas.",          "categoria": "Inversión"},
    {"nombre": "Dividendo",           "definicion": "Parte de las ganancias de una empresa distribuida entre sus accionistas. Fuente de ingreso pasivo en inversión en acciones.",                                      "categoria": "Inversión"},
    {"nombre": "DTF",                 "definicion": "Depósito a Término Fijo. Tasa de referencia del mercado financiero colombiano, usada como base para créditos de libre inversión y comerciales.",                   "categoria": "Economía"},
    {"nombre": "EA (Efectivo Anual)", "definicion": "Tasa Efectiva Anual. Muestra el rendimiento o costo real de un producto financiero durante un año, considerando la capitalización periódica. Es la tasa comparable.",  "categoria": "Tasas"},
    {"nombre": "Fogafín",             "definicion": "Fondo de Garantías de Instituciones Financieras. Asegura los depósitos en bancos colombianos vigilados hasta $50 millones por persona por entidad.",              "categoria": "Seguridad financiera"},
    {"nombre": "Fondo de emergencia", "definicion": "Dinero reservado exclusivamente para imprevistos graves. Recomendado: 3-6 meses de gastos básicos en cuenta de fácil acceso. Primera prioridad financiera.",        "categoria": "Ahorro e inversión"},
    {"nombre": "Inflación",           "definicion": "Aumento generalizado y sostenido de los precios que reduce el poder adquisitivo del dinero. Medida en Colombia por el IPC que publica el DANE.",                   "categoria": "Economía"},
    {"nombre": "Interés compuesto",   "definicion": "Interés calculado sobre el capital inicial más los intereses acumulados. Los intereses generan nuevos intereses, creando crecimiento exponencial.",                "categoria": "Tasas"},
    {"nombre": "Interés simple",      "definicion": "Interés calculado siempre sobre el capital inicial únicamente. Los intereses no se reinvierten. Menos poderoso que el compuesto en el largo plazo.",               "categoria": "Tasas"},
    {"nombre": "IPC",                 "definicion": "Índice de Precios al Consumidor. Mide la variación de precios de una canasta de bienes y servicios. Principal indicador de inflación en Colombia.",                 "categoria": "Economía"},
    {"nombre": "Liquidez",            "definicion": "Facilidad con la que un activo puede convertirse en efectivo sin perder valor. El efectivo es el activo más líquido. La finca raíz tiene baja liquidez.",           "categoria": "Conceptos básicos"},
    {"nombre": "Pasivo",              "definicion": "Deuda u obligación financiera que debes pagar en el futuro. Ejemplos: créditos hipotecarios, tarjetas de crédito, leasing, préstamos.",                           "categoria": "Conceptos básicos"},
    {"nombre": "Patrimonio",          "definicion": "Diferencia entre tus activos y pasivos. Representa tu riqueza neta real. Patrimonio = Activos − Pasivos.",                                                          "categoria": "Conceptos básicos"},
    {"nombre": "Retención fuente",    "definicion": "Anticipo del impuesto de renta que descuenta el empleador directamente del salario cada mes. Se cruza con el impuesto definitivo al declarar renta.",               "categoria": "Impuestos"},
    {"nombre": "SMMLV",               "definicion": "Salario Mínimo Mensual Legal Vigente en Colombia. Para 2024: $1.300.000. Referencia para cálculo de pensiones, multas y aportes parafiscales.",                  "categoria": "Economía"},
    {"nombre": "TES",                 "definicion": "Títulos de Tesorería. Bonos del gobierno colombiano. Considerados de muy bajo riesgo. Disponibles en el mercado secundario o a través de fondos.",                  "categoria": "Inversión"},
    {"nombre": "TRM",                 "definicion": "Tasa Representativa del Mercado. Valor oficial del dólar en pesos colombianos, fijada diariamente por el Banco de la República.",                                  "categoria": "Economía"},
    {"nombre": "UVT",                 "definicion": "Unidad de Valor Tributario. Valor de referencia para calcular impuestos, sanciones y obligaciones tributarias en Colombia. Para 2024: $47.065.",                    "categoria": "Impuestos"},
    {"nombre": "Yield",               "definicion": "Rendimiento de una inversión expresado como porcentaje anual. Similar a la rentabilidad pero usado principalmente en mercados de capitales y bonos.",              "categoria": "Inversión"},
    {"nombre": "4x1000",              "definicion": "Gravamen a los Movimientos Financieros (GMF). Impuesto del 4 por cada 1.000 pesos en transacciones bancarias. Algunas cuentas tienen exención parcial.",          "categoria": "Impuestos"},
]


# ════════════════════════════════════════════════════════════════════════════
#  MOTOR DE BÚSQUEDA TIPO GOOGLE  (sin cambios — Python puro)
# ════════════════════════════════════════════════════════════════════════════

def normalizar(texto):
    """Normaliza texto para búsqueda: minúsculas, sin tildes."""
    import unicodedata
    texto = texto.lower().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto


def calcular_relevancia(query_norm, articulo):
    score = 0
    q = query_norm

    titulo_norm = normalizar(articulo['titulo'])
    if q in titulo_norm:
        score += 50
    elif any(palabra in titulo_norm for palabra in q.split() if len(palabra) > 3):
        score += 25

    resumen_norm = normalizar(articulo['resumen'])
    if q in resumen_norm:
        score += 20
    elif any(palabra in resumen_norm for palabra in q.split() if len(palabra) > 3):
        score += 10

    for tag in articulo.get('tags', []):
        tag_norm = normalizar(tag)
        if q in tag_norm or tag_norm in q:
            score += 15
            break
        elif any(palabra in tag_norm for palabra in q.split() if len(palabra) > 3):
            score += 8

    cat_norm = normalizar(articulo['categoria'])
    if q in cat_norm or any(p in cat_norm for p in q.split() if len(p) > 3):
        score += 10

    for seccion in articulo.get('secciones', []):
        contenido_norm = normalizar(seccion.get('contenido', ''))
        if q in contenido_norm:
            score += 12
            break
        elif any(palabra in contenido_norm for palabra in q.split() if len(palabra) > 4):
            score += 6
            break

    if q in articulo['id'] or articulo['id'] in q:
        score += 30

    return score


def buscar_en_enciclopedia(query):
    query_norm = normalizar(query)

    resultados = []
    for clave, articulo in ENCICLOPEDIA.items():
        score = calcular_relevancia(query_norm, articulo)
        if score > 0:
            resultados.append({
                'score': score,
                'id': articulo['id'],
                'emoji': articulo['emoji'],
                'categoria': articulo['categoria'],
                'nivel': articulo['nivel'],
                'titulo': articulo['titulo'],
                'resumen': articulo['resumen'],
            })

    resultados.sort(key=lambda x: x['score'], reverse=True)
    return resultados


def buscar_en_glosario(query):
    query_norm = normalizar(query)
    resultados = []
    for termino in GLOSARIO:
        nombre_norm = normalizar(termino['nombre'])
        def_norm    = normalizar(termino['definicion'])
        cat_norm    = normalizar(termino['categoria'])
        if (query_norm in nombre_norm or nombre_norm in query_norm or
                query_norm in def_norm or query_norm in cat_norm or
                any(p in nombre_norm for p in query_norm.split() if len(p) > 2)):
            resultados.append(termino)
    return resultados


# ════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

# ── GET /buscar?q=... ─────────────────────────────────────────
@router.get('/buscar')
def buscar(q: str = Query(...)):
    q = q.strip()
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail='El parámetro q debe tener al menos 2 caracteres.')

    articulos = buscar_en_enciclopedia(q)
    glosario  = buscar_en_glosario(q)

    sugerencias = []
    if articulos:
        primer_id = articulos[0]['id']
        relacionados = ENCICLOPEDIA.get(primer_id, {}).get('relacionados', [])
        for rel_id in relacionados[:4]:
            rel = ENCICLOPEDIA.get(rel_id)
            if rel:
                sugerencias.append({
                    'id': rel['id'],
                    'emoji': rel['emoji'],
                    'titulo': rel['titulo'],
                    'categoria': rel['categoria'],
                })

    return {
        'query': q,
        'total_articulos': len(articulos),
        'total_glosario': len(glosario),
        'articulos': articulos,
        'glosario': glosario[:5],
        'sugerencias': sugerencias,
    }


# ── GET /articulos ────────────────────────────────────────────
@router.get('/articulos')
def listar_articulos(nivel: Optional[str] = None, categoria: Optional[str] = None):
    nivel     = (nivel or '').strip().lower()
    categoria = (categoria or '').strip()

    resultado = []
    for art in ENCICLOPEDIA.values():
        if nivel and art['nivel'] != nivel:
            continue
        if categoria and normalizar(art['categoria']) != normalizar(categoria):
            continue
        resultado.append({
            'id': art['id'],
            'emoji': art['emoji'],
            'categoria': art['categoria'],
            'nivel': art['nivel'],
            'titulo': art['titulo'],
            'resumen': art['resumen'],
            'num_secciones': len(art.get('secciones', [])),
        })

    return {'total': len(resultado), 'articulos': resultado}


# ── GET /articulos/{articulo_id} ───────────────────────────────────────
@router.get('/articulos/{articulo_id}')
def obtener_articulo(articulo_id: str):
    art = ENCICLOPEDIA.get(articulo_id)
    if not art:
        raise HTTPException(status_code=404, detail=f"Artículo '{articulo_id}' no encontrado.")

    relacionados_full = []
    for rel_id in art.get('relacionados', []):
        rel = ENCICLOPEDIA.get(rel_id)
        if rel:
            relacionados_full.append({
                'id': rel['id'],
                'emoji': rel['emoji'],
                'titulo': rel['titulo'],
                'categoria': rel['categoria'],
                'nivel': rel['nivel'],
            })

    return {**art, 'relacionados_detalle': relacionados_full}


# ── GET /glosario ─────────────────────────────────────────────
@router.get('/glosario')
def listar_glosario(letra: Optional[str] = None, categoria: Optional[str] = None, q: Optional[str] = None):
    letra     = (letra or '').strip().upper()
    categoria = (categoria or '').strip()
    q         = (q or '').strip()

    resultado = list(GLOSARIO)

    if letra:
        resultado = [t for t in resultado if t['nombre'][0].upper() == letra]
    if categoria:
        resultado = [t for t in resultado if normalizar(t['categoria']) == normalizar(categoria)]
    if q:
        resultado = buscar_en_glosario(q)

    letras_disponibles     = sorted({t['nombre'][0].upper() for t in GLOSARIO})
    categorias_disponibles = sorted({t['categoria'] for t in GLOSARIO})

    return {
        'total': len(resultado),
        'terminos': resultado,
        'letras_disponibles': letras_disponibles,
        'categorias_disponibles': categorias_disponibles,
    }


# ── GET /categorias ───────────────────────────────────────────
@router.get('/categorias')
def listar_categorias():
    categorias = sorted({a['categoria'] for a in ENCICLOPEDIA.values()})
    niveles    = ['basico', 'intermedio', 'avanzado']

    por_nivel = {
        n: sum(1 for a in ENCICLOPEDIA.values() if a['nivel'] == n)
        for n in niveles
    }

    return {
        'total_articulos': len(ENCICLOPEDIA),
        'total_terminos_glosario': len(GLOSARIO),
        'categorias': categorias,
        'niveles': niveles,
        'articulos_por_nivel': por_nivel,
    }


# ── POST /calcular ────────────────────────────────────────────

class CalculoRequest(BaseModel):
    tipo: str
    datos: dict[str, Any] = {}


@router.post('/calcular')
def calcular(body: CalculoRequest):
    tipo = body.tipo.strip()
    d    = body.datos

    if not tipo:
        raise HTTPException(status_code=400, detail='El campo tipo es requerido.')

    try:
        resultado = _ejecutar_calculo(tipo, d)
        return {'tipo': tipo, 'resultado': resultado}
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        raise HTTPException(status_code=400, detail=f'Error en los datos: {str(e)}')


def _ejecutar_calculo(tipo, d):
    """Ejecuta el cálculo financiero según el tipo. (sin cambios — Python puro)"""

    if tipo == 'interes_simple':
        k, tasa, meses = float(d['capital']), float(d['tasa_anual']) / 100, float(d['meses'])
        tm = tasa / 12
        interes = round(k * tm * meses, 2)
        return {
            'capital_inicial': k,
            'interes_generado': interes,
            'total_final': round(k + interes, 2),
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
            'total_invertido': invertido,
            'intereses_ganados': intereses,
            'total_final': bal,
            'rentabilidad_pct': renta,
        }

    elif tipo == 'regla_50_30_20':
        ing   = float(d['ingreso_mensual'])
        fijos = float(d.get('gastos_fijos', 0))
        pf    = round(fijos / ing * 100, 1) if ing > 0 else 0
        aviso = ''
        if fijos > 0:
            if pf > 70:   aviso = f'⚠️ Zona crítica: {pf}% de tus ingresos son gastos fijos.'
            elif pf > 50: aviso = '⚠️ Tus gastos fijos superan el 50% recomendado.'
            else:         aviso = '✅ Tus gastos fijos están en rango controlado.'
        return {
            'necesidades_50': round(ing * 0.5, 2),
            'deseos_30': round(ing * 0.3, 2),
            'ahorro_20': round(ing * 0.2, 2),
            'gastos_fijos': fijos,
            'pct_gastos_fijos': pf,
            'aviso': aviso,
        }

    elif tipo == 'meta_ahorro':
        obj = float(d['monto_objetivo'])
        act = float(d.get('monto_actual', 0))
        men = float(d['ahorro_mensual'])
        ren = float(d.get('rendimiento_mensual_pct', 0)) / 100
        faltante = max(0, obj - act)
        if faltante == 0:
            return {'ya_alcanzada': True, 'monto_actual': act}
        if ren > 0:
            meses, bal = 0, act
            while bal < obj and meses < 1200:
                bal = bal * (1 + ren) + men
                meses += 1
        else:
            meses = math.ceil(faltante / men) if men > 0 else 99999
            bal   = round(act + men * meses, 2)
        anos, mr = meses // 12, meses % 12
        if anos > 0:
            txt = f"{anos} año{'s' if anos > 1 else ''}" + (f" y {mr} mes{'es' if mr > 1 else ''}" if mr else '')
        else:
            txt = f"{meses} mes{'es' if meses > 1 else ''}"
        return {
            'ya_alcanzada': False,
            'faltante': round(faltante, 2),
            'meses': meses,
            'tiempo_texto': txt,
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
            'ingreso_bruto': bruto, 'salud': salud, 'pension': pension,
            'retencion': ret, 'otros': otros, 'salario_neto': neto,
        }

    elif tipo == 'cuota_credito':
        P = float(d['monto'])
        r = float(d['tasa_anual']) / 100 / 12
        n = int(d['plazo_meses'])
        cuota = P / n if r == 0 else P * r * (1 + r)**n / ((1 + r)**n - 1)
        cuota     = round(cuota, 2)
        total     = round(cuota * n, 2)
        intereses = round(total - P, 2)
        costo_pct = round(intereses / P * 100, 2) if P > 0 else 0
        return {
            'cuota_mensual': cuota, 'total_a_pagar': total,
            'total_intereses': intereses, 'costo_credito_pct': costo_pct,
        }

    elif tipo == 'inflacion':
        monto = float(d['monto'])
        tasa  = float(d['inflacion_anual_pct']) / 100
        anos  = float(d['anos'])
        futuro  = round(monto / (1 + tasa) ** anos, 2)
        perdida = round(monto - futuro, 2)
        return {
            'valor_hoy': monto, 'valor_real_futuro': futuro,
            'perdida_poder': perdida, 'tasa_minima_pct': round(tasa * 100, 2),
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
            'capital_acumulado': bal,
            'total_aportado': tot_aporte,
            'rendimientos': rendim,
            'ahorro_impuestos_ano': ahorro_imp,
        }

    else:
        raise ValueError(f"Tipo de cálculo '{tipo}' no reconocido.")