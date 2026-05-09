# finanbot_ia.py - Motor de Inteligencia Financiera de FinanBot
import re
import random
import math
from datetime import datetime

class FinanBotIA:

    def __init__(self):
        self.contexto = []
        self.nombre_usuario = None
        self.ultimo_tema = None
        self.turno = 0

        self.transiciones = [
            "\n\n¿Hay algo más en lo que pueda ayudarte?",
            "\n\n¿Quieres que haga algún cálculo o registre algo?",
            "\n\n¿Te gustaría simular una inversión o crear una meta?",
            "\n\n¿Necesitas que profundice en algún punto?",
        ]

        # =============================================
        # BASE DE CONOCIMIENTO FINANCIERO EXPANDIDA
        # =============================================
        self.conocimientos = {
            'ahorro': {
                'respuesta': (
                    "💰 **Estrategias de ahorro inteligente:**\n\n"
                    "**1. La regla del pago primero**\n"
                    "En cuanto recibas tu salario, transfiere inmediatamente el 10-20% a una cuenta separada. No lo pienses, hazlo automático.\n\n"
                    "**2. Elimina gastos hormiga**\n"
                    "• Café diario: $3.000 × 30 = **$90.000/mes**\n"
                    "• Taxis innecesarios: $15.000 × 8 = **$120.000/mes**\n"
                    "• Suscripciones olvidadas: hasta **$80.000/mes**\n\n"
                    "**3. La regla de las 48 horas**\n"
                    "Antes de comprar algo no esencial, espera 48 horas. Si lo olvidaste, ¡ahorraste!\n\n"
                    "**4. Automatiza tu ahorro**\n"
                    "La mayoría de bancos colombianos permiten transferencias automáticas programadas.\n\n"
                    "💡 ¿Quieres que calcule cuánto puedes ahorrar con tu ingreso actual?"
                ),
                'acciones': [
                    {'texto': '🎯 Crear meta de ahorro', 'link': 'perfil.html'},
                    {'texto': '📊 Ver mis gastos', 'link': 'finanzas.html'},
                    {'texto': '📈 Simular ahorro', 'link': 'simulador.html'}
                ]
            },
            'presupuesto': {
                'respuesta': (
                    "📋 **La regla 50/30/20:**\n\n"
                    "🟢 **50% — Necesidades:** Arriendo, comida, transporte, servicios, salud.\n\n"
                    "🟡 **30% — Deseos:** Entretenimiento, ropa, salidas, tecnología.\n\n"
                    "🔵 **20% — Ahorro:** Fondo de emergencia, CDT, inversiones.\n\n"
                    "💡 Si me dices tu salario, te calculo exactamente cuánto destinar a cada categoría."
                ),
                'acciones': [
                    {'texto': '📈 Simular inversión', 'link': 'simulador.html'},
                    {'texto': '📚 Ver calculadoras', 'link': 'aprende.html'}
                ]
            },
            'deudas': {
                'respuesta': (
                    "💳 **Plan para salir de deudas:**\n\n"
                    "⛄ **Método Bola de Nieve** — Paga la deuda más pequeña primero. Genera motivación.\n\n"
                    "🌊 **Método Avalancha** — Paga la de mayor tasa primero. Ahorras más dinero.\n\n"
                    "**Reglas de oro:**\n"
                    "• No adquieras nuevas deudas mientras pagas\n"
                    "• Evita el 'gota a gota' — es ilegal y peligroso\n"
                    "• Negocia si estás en mora, no ignores\n"
                    "• Superfinanciera: **01 8000 120 100**"
                ),
                'acciones': [
                    {'texto': '💡 Ver recomendaciones', 'link': 'recomendaciones.html'},
                    {'texto': '📊 Mis finanzas', 'link': 'finanzas.html'}
                ]
            },
            'inversion': {
                'respuesta': (
                    "📈 **Inversiones en Colombia:**\n\n"
                    "Antes de invertir, asegúrate de tener:\n"
                    "✅ Fondo de emergencia de 3-6 meses\n"
                    "✅ Deudas de alto interés pagadas\n\n"
                    "🟢 **CDT — Bajo riesgo:** 8-14% anual\n"
                    "🟡 **Fondos de inversión — Riesgo medio:** Desde $50.000\n"
                    "🔴 **Acciones BVC — Alto riesgo:** Ideal largo plazo (+5 años)\n\n"
                    "💡 ¿Quieres que simule cuánto crecería tu dinero? Dime el monto, tasa y plazo."
                ),
                'acciones': [
                    {'texto': '📈 Usar simulador', 'link': 'simulador.html'},
                    {'texto': '📚 Aprender más', 'link': 'aprende.html'}
                ]
            },
            'emergencia': {
                'respuesta': (
                    "🚨 **Fondo de emergencia:**\n\n"
                    "**¿Cuánto necesitas?**\n"
                    "• Empleado: 3-6 meses de gastos\n"
                    "• Independiente: 6-12 meses\n\n"
                    "**¿Dónde guardarlo?**\n"
                    "✅ Cuenta de ahorros · ✅ CDT 30 días · ✅ Daviplata/Nequi\n"
                    "❌ No en criptos · ❌ No en efectivo en casa\n\n"
                    "**Regla clave:** El fondo va ANTES que cualquier inversión."
                ),
                'acciones': [
                    {'texto': '🎯 Crear meta de emergencia', 'link': 'perfil.html'},
                    {'texto': '📈 Simular ahorro', 'link': 'simulador.html'}
                ]
            },
            'interes': {
                'respuesta': (
                    "🔢 **Interés simple vs. Interés compuesto:**\n\n"
                    "**📊 Interés Simple**\n"
                    "Fórmula: `Capital × Tasa × Tiempo`\n"
                    "El capital no cambia, solo se acumulan intereses sobre el monto original.\n"
                    "Ejemplo: $1.000.000 al 10% anual × 3 años = **$1.300.000**\n\n"
                    "**📈 Interés Compuesto**\n"
                    "Fórmula: `Capital × (1 + Tasa)^Tiempo`\n"
                    "Los intereses generan nuevos intereses. El dinero crece exponencialmente.\n"
                    "Ejemplo: $1.000.000 al 10% anual × 3 años = **$1.331.000**\n\n"
                    "**El poder del tiempo:**\n"
                    "$1.000.000 al 10% anual:\n"
                    "• 10 años: **$2.593.742**\n"
                    "• 20 años: **$6.727.500**\n"
                    "• 30 años: **$17.449.402**\n\n"
                    "💡 ¿Quieres que calcule el interés de tu inversión específica?"
                ),
                'acciones': [
                    {'texto': '📈 Calcular en simulador', 'link': 'simulador.html'},
                    {'texto': '📚 Calculadoras', 'link': 'aprende.html'}
                ]
            },
            'pension': {
                'respuesta': (
                    "👴 **Colpensiones vs. Fondos privados:**\n\n"
                    "**🏛️ Colpensiones** — 1.300 semanas · 57/62 años · Pensión mínima garantizada\n\n"
                    "**🏢 Fondos Privados** — Cuenta individual · Aportes voluntarios con beneficios tributarios\n\n"
                    "⚠️ El 75% de colombianos no se pensiona. Complementa siempre con ahorro personal."
                ),
                'acciones': [{'texto': '📈 Simular pensional', 'link': 'simulador.html'}]
            },
            'inflacion': {
                'respuesta': (
                    "📉 **Inflación — Cómo proteger tu dinero:**\n\n"
                    "La inflación reduce tu poder adquisitivo silenciosamente.\n"
                    "$1.000.000 hoy con inflación del 10% = $900.000 de poder real el próximo año.\n\n"
                    "✅ CDT tasas superiores a inflación · ✅ Fondos de renta variable\n"
                    "✅ Finca raíz · ✅ Acciones sólidas · ✅ Dólares\n\n"
                    "❌ Efectivo por meses · ❌ Cuenta con tasa muy baja"
                ),
                'acciones': [{'texto': '📈 Simular inversión', 'link': 'simulador.html'}]
            },
            'cripto': {
                'respuesta': (
                    "₿ **Criptomonedas — Riesgos y realidades:**\n\n"
                    "• Volatilidad extrema: Bitcoin cayó 75% en 2022\n"
                    "• Sin regulación ni protección al inversor en Colombia\n"
                    "• Estafas frecuentes: rug pulls, esquemas Ponzi\n\n"
                    "✅ Si decides invertir: máximo **5%** de tu portafolio, solo en plataformas reconocidas.\n"
                    "🚨 Señal de estafa: rendimientos garantizados muy altos."
                ),
                'acciones': [{'texto': '📚 Aprender más', 'link': 'aprende.html'}]
            },
            'impuesto': {
                'respuesta': (
                    "🧾 **Impuestos en Colombia:**\n\n"
                    "Debes declarar renta si:\n"
                    "• Ingresos brutos > $57.124.000/año\n"
                    "• Patrimonio bruto > $190.854.000\n"
                    "• Consumos con tarjeta > $57.124.000\n\n"
                    "💡 Aportes a pensión voluntaria reducen tu base gravable.\n"
                    "📌 Más info: www.dian.gov.co"
                ),
                'acciones': []
            }
        }

        # =============================================
        # GLOSARIO FINANCIERO COMPLETO
        # =============================================
        self.glosario = {
            'saldo': "El **saldo** es la cantidad de dinero que tienes disponible en una cuenta, cartera o inversión en un momento dado. Puede ser:\n• **Saldo positivo (+):** tienes más de lo que debes.\n• **Saldo negativo (-):** debes más de lo que tienes.\n• **Saldo disponible:** lo que puedes usar ahora mismo.",
            'balance': "El **balance** es la diferencia entre tus ingresos totales y tus gastos totales. Si es positivo, vas bien. Si es negativo, gastas más de lo que ganas.",
            'capital': "El **capital** es el monto de dinero inicial que inviertes o que tienes disponible antes de que genere intereses o rendimientos.",
            'tasa': "La **tasa de interés** es el porcentaje que se cobra o paga por usar dinero. Puede ser:\n• **Tasa mensual:** porcentaje por mes.\n• **Tasa anual (EA):** porcentaje efectivo anual.\n• **Tasa nominal:** tasa antes de capitalizaciones.",
            'interes': "El **interés** es el rendimiento o ganancia que genera un capital invertido, o el costo adicional de un préstamo. Es el 'precio' del dinero.",
            'rendimiento': "El **rendimiento** es la ganancia o beneficio que genera una inversión, expresado generalmente en porcentaje.",
            'liquidez': "La **liquidez** es la facilidad con que puedes convertir un activo en dinero en efectivo sin perder valor.",
            'activo': "Un **activo** es todo lo que tienes y tiene valor: dinero, propiedades, inversiones, vehículos, negocios.",
            'pasivo': "Un **pasivo** es todo lo que debes: deudas, préstamos, hipotecas, tarjetas de crédito.",
            'patrimonio': "El **patrimonio neto** = Activos - Pasivos. Es lo que realmente posees después de descontar tus deudas.",
            'dividendo': "Un **dividendo** es la parte de las ganancias de una empresa que se reparte entre sus accionistas.",
            'portafolio': "Un **portafolio de inversión** es el conjunto de todos tus instrumentos financieros: acciones, CDTs, fondos, etc.",
            'diversificacion': "La **diversificación** es distribuir el dinero en diferentes inversiones para reducir el riesgo. 'No pongas todos los huevos en la misma canasta.'",
            'cdt': "Un **CDT (Certificado de Depósito a Término)** es un producto bancario donde depositas dinero por un plazo fijo a cambio de una tasa de interés garantizada.",
            'inflacion': "La **inflación** es el aumento generalizado de precios que reduce el poder adquisitivo del dinero con el tiempo.",
            'deflacion': "La **deflación** es la disminución generalizada de precios. Parece buena, pero puede indicar una economía débil.",
            'riesgo': "El **riesgo financiero** es la probabilidad de perder dinero en una inversión. A mayor rendimiento esperado, generalmente mayor riesgo.",
            'amortizacion': "La **amortización** es el proceso de pagar una deuda en cuotas periódicas que incluyen capital más intereses.",
            'cuota': "Una **cuota** es el pago periódico (mensual, quincenal) que haces para pagar un préstamo o crédito.",
            'mora': "La **mora** ocurre cuando no pagas una deuda en la fecha pactada. Genera intereses adicionales y daña tu historial crediticio.",
            'historial crediticio': "El **historial crediticio** es el registro de cómo has pagado tus deudas. Un buen historial te da acceso a mejores tasas y créditos.",
            'bvc': "La **BVC (Bolsa de Valores de Colombia)** es el mercado donde se compran y venden acciones de empresas colombianas.",
            'accion': "Una **acción** es una pequeña parte de la propiedad de una empresa. Si la empresa gana, tú ganas.",
            'bono': "Un **bono** es un préstamo que le haces al gobierno o a una empresa. Te pagan intereses periódicos y devuelven el capital al final.",
            'fondo de inversion': "Un **fondo de inversión** agrupa el dinero de muchos inversores para comprar activos diversificados. Es manejado por expertos.",
            'tasa ea': "La **tasa EA (Efectiva Anual)** es la tasa de interés real que te cobran o pagan en un año, considerando la capitalización.",
            'interes compuesto': "El **interés compuesto** es cuando los intereses generados se suman al capital y a su vez generan nuevos intereses. Es exponencial.",
            'interes simple': "El **interés simple** se calcula siempre sobre el capital original. No hay capitalización de intereses.",
            'plazo': "El **plazo** es el período de tiempo acordado para pagar una deuda o mantener una inversión.",
            'vencimiento': "El **vencimiento** es la fecha en que termina un contrato financiero: cuando debes devolver el dinero o cuando te lo devuelven.",
            'rentabilidad': "La **rentabilidad** es la relación entre la ganancia obtenida y el capital invertido, expresada en porcentaje.",
            'flujo de caja': "El **flujo de caja** es el movimiento de dinero que entra y sale de tu bolsillo o negocio en un período de tiempo.",
            'presupuesto': "Un **presupuesto** es un plan que organiza cuánto dinero entra y cuánto puedes gastar en cada categoría.",
            'ahorro': "El **ahorro** es la parte del ingreso que no se gasta y se guarda para uso futuro o para generar rendimientos.",
            'inversion': "Una **inversión** es destinar dinero a un activo con la expectativa de obtener un rendimiento en el futuro.",
            'deuda': "Una **deuda** es una obligación de pagar dinero a alguien en el futuro, generalmente con intereses.",
            'credito': "El **crédito** es la capacidad de obtener dinero prestado con el compromiso de devolverlo más intereses.",
            'tasa de cambio': "La **tasa de cambio** es el precio de una moneda en términos de otra. Ej: cuántos pesos colombianos vale 1 dólar.",
            'iva': "El **IVA (Impuesto al Valor Agregado)** es un impuesto que se cobra sobre la venta de bienes y servicios. En Colombia es del 19%.",
            'retencion': "La **retención en la fuente** es un anticipo de impuestos que se descuenta directamente del pago.",
            'utilidad': "La **utilidad** es la ganancia obtenida después de descontar todos los costos y gastos.",
            'gasto': "Un **gasto** es la salida de dinero para pagar bienes o servicios que se consumen.",
            'ingreso': "Un **ingreso** es la entrada de dinero proveniente del trabajo, inversiones, negocios u otras fuentes.",
            'patrimonio neto': "El **patrimonio neto** es la diferencia entre lo que tienes (activos) y lo que debes (pasivos). Es tu riqueza real.",
            'leverage': "El **apalancamiento (leverage)** es usar deuda para aumentar el potencial de inversión. Amplifica ganancias y pérdidas.",
            'tir': "La **TIR (Tasa Interna de Retorno)** es la tasa de rendimiento que hace que el valor presente neto de una inversión sea cero.",
            'van': "El **VAN (Valor Actual Neto)** mide la rentabilidad de una inversión en términos de dinero de hoy.",
        }

    # ============================================
    # DETECTAR INTENCIÓN
    # ============================================
    def detectar_intencion(self, mensaje):
        msg = mensaje.lower().strip()
        msg = re.sub(r'[¿?¡!.,]', '', msg)

        mapa = {
            'saludo': ['hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'hey', 'buenas', 'saludos', 'ey', 'que tal', 'como estas'],
            'ahorro': ['ahorr', 'guardar dinero', 'reducir gastos', 'economizar', 'gastos hormiga', 'no me alcanza'],
            'inversion': ['invert', 'inversión', 'invertir', 'rendimiento', 'cdt', 'acciones', 'fondos', 'bolsa'],
            'deuda': ['deuda', 'credito', 'crédito', 'prestamo', 'préstamo', 'debo', 'endeud', 'mora', 'bola de nieve'],
            'presupuesto': ['presupuesto', '50/30/20', 'distribuir', 'organizar dinero', 'planificar', 'cuanto gastar'],
            'emergencia': ['emergencia', 'fondo de emergencia', 'imprevisto', 'colchon', 'reserva'],
            'interes': ['interés', 'interes', 'compuesto', 'tasa de interes'],
            'inflacion': ['inflacion', 'inflación', 'poder adquisitivo', 'devaluacion', 'todo está caro'],
            'impuesto': ['impuesto', 'declaracion', 'dian', 'tributar', 'renta'],
            'pension': ['pension', 'pensión', 'jubilacion', 'retiro', 'colpensiones', 'porvenir'],
            'cripto': ['cripto', 'bitcoin', 'ethereum', 'crypto', 'blockchain', 'nft'],
            'glosario': ['que es', 'qué es', 'que significa', 'qué significa', 'define', 'definicion', 'explicame', 'explícame', 'como funciona', 'cómo funciona'],
            'problema_financiero': ['tengo', 'mi meta', 'quiero llegar', 'banco me ofrece', 'tasa del', 'cuántos meses', 'cuantos meses', 'cuánto me falta', 'cuanto me falta', 'si saco', 'si retiro', 'si invierto', 'cuanto gano', 'cuánto gano', 'resolver', 'problema', 'ejercicio', 'calcula', 'calcúlame', 'calculame', 'ayúdame', 'ayudame'],
            'mis_datos': ['mis finanzas', 'mi balance', 'cuanto tengo', 'mis gastos', 'mi situacion', 'como estoy', 'mi dinero', 'resumen'],
            'mis_metas': ['mis metas', 'mis objetivos', 'como van mis metas'],
            'simular': ['simular', 'simulacion', 'simulador', 'quiero simular'],
            'calcular_5030': ['distribuye mi salario', 'aplica 50/30/20', 'cuanto debo gastar', 'dividir mi sueldo'],
            'calcular_meta': ['cuanto tiempo para', 'cuando alcanzo', 'cuantos meses para mi meta', 'tiempo para ahorrar'],
            'despedida': ['adios', 'hasta luego', 'chao', 'bye', 'nos vemos'],
            'gracias': ['gracias', 'muchas gracias', 'te lo agradezco', 'perfecto gracias'],
            'ayuda': ['ayuda', 'help', 'que puedes hacer', 'para que sirves', 'capacidades', 'funciones', 'comandos'],
            'broma': ['chiste', 'broma', 'algo curioso', 'dato curioso', 'sabias que'],
        }

        for intencion, palabras in mapa.items():
            for palabra in palabras:
                if palabra in msg:
                    return intencion
        return 'desconocido'

    # ============================================
    # MÉTODO PRINCIPAL
    # ============================================
    def responder_con_acciones(self, mensaje, contexto_financiero=None, accion_ejecutada=None):
        self.contexto.append(mensaje)
        self.turno += 1
        intencion = self.detectar_intencion(mensaje)
        msg_lower = mensaje.lower()

        # Detectar nombre
        for frase in ['me llamo ', 'mi nombre es ', 'soy ']:
            if frase in msg_lower:
                idx = msg_lower.find(frase) + len(frase)
                posible = mensaje[idx:].split()[0]
                posible = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ]', '', posible)
                if posible and len(posible) > 1:
                    self.nombre_usuario = posible.capitalize()

        nombre = None
        if contexto_financiero and contexto_financiero.get('nombre'):
            nombre = contexto_financiero['nombre']
        elif self.nombre_usuario:
            nombre = self.nombre_usuario

        # PRIORIDAD 1 — Acción CRUD
        if accion_ejecutada:
            return self._respuesta_accion_ejecutada(accion_ejecutada, contexto_financiero)

        # PRIORIDAD 2 — Resolver problema financiero complejo
        if intencion == 'problema_financiero' or self._es_problema_financiero(mensaje):
            resultado = self._resolver_problema_financiero(mensaje)
            if resultado:
                return resultado

        # PRIORIDAD 3 — Glosario
        if intencion == 'glosario':
            resultado = self._buscar_en_glosario(mensaje)
            if resultado:
                return resultado

        # PRIORIDAD 4 — Intenciones especiales
        if intencion == 'saludo':
            return self._saludo_inteligente(nombre, contexto_financiero)
        if intencion == 'despedida':
            return self._despedida(nombre), []
        if intencion == 'gracias':
            return self._respuesta_gracias(nombre), []
        if intencion == 'ayuda':
            return self._respuesta_ayuda(), [
                {'texto': '📊 Mis Finanzas', 'link': 'finanzas.html'},
                {'texto': '🎯 Mis Metas', 'link': 'perfil.html'},
                {'texto': '📈 Simulador', 'link': 'simulador.html'},
                {'texto': '📚 Aprende', 'link': 'aprende.html'}
            ]
        if intencion == 'broma':
            return self._curiosidad_financiera(), [{'texto': '📚 Aprender más', 'link': 'aprende.html'}]

        # PRIORIDAD 5 — Datos del usuario
        if intencion in ('mis_datos', 'mis_metas') and contexto_financiero:
            return self._analisis_financiero_inteligente(contexto_financiero)

        if intencion == 'simular':
            return (
                "📈 **¡Claro! Puedo simularlo ahora mismo.**\n\n"
                "Solo dime:\n"
                "💰 **Capital inicial** — ej: $2.000.000\n"
                "📊 **Tasa anual** — ej: 10%\n"
                "⏱️ **Plazo** — ej: 12 meses o 2 años\n\n"
                "Ejemplo: *\"Simula $2.000.000 al 10% por 24 meses\"*",
                [{'texto': '📈 Ir al Simulador', 'link': 'simulador.html'}]
            )

        if intencion == 'calcular_5030':
            return self._calcular_5030_desde_mensaje(mensaje, contexto_financiero)

        if intencion == 'calcular_meta':
            return self._calcular_meta_desde_mensaje(mensaje, contexto_financiero)

        # PRIORIDAD 6 — Base de conocimientos
        for tema, data in self.conocimientos.items():
            claves = self._claves_tema(tema)
            if any(c in msg_lower for c in claves):
                self.ultimo_tema = tema
                transicion = random.choice(self.transiciones)
                return data['respuesta'] + transicion, data['acciones']

        # PRIORIDAD 7 — Respuesta desconocida
        return self._respuesta_desconocido(mensaje, nombre)

    # ============================================
    # RESOLVER PROBLEMAS FINANCIEROS COMPLEJOS
    # ============================================
    def _es_problema_financiero(self, mensaje):
        """Detecta si el mensaje es un problema financiero complejo"""
        indicadores = [
            r'\$[\d,\.]+', r'\d+%', r'tasa del \d+', r'tengo \$', r'tengo \d+',
            r'meta.*\d+', r'cuánto.*mes', r'cuantos.*mes', r'interés simple',
            r'interés compuesto', r'si saco', r'si retiro', r'meses antes',
            r'llegar a', r'juntar', r'alcanzar.*meta'
        ]
        msg = mensaje.lower()
        coincidencias = sum(1 for p in indicadores if re.search(p, msg))
        return coincidencias >= 2

    def _extraer_numero(self, texto):
        """Extrae el primer número del texto"""
        texto = str(texto).replace(',', '').replace('.', '')
        match = re.search(r'\$?\s*(\d+)', texto)
        if match:
            return float(match.group(1))
        return None

    def _extraer_todos_numeros(self, texto):
        """Extrae todos los números del texto"""
        texto_limpio = texto.replace(',', '').replace('.', '')
        matches = re.findall(r'\$?\s*(\d+(?:\.\d+)?)', texto_limpio)
        return [float(m) for m in matches if float(m) > 0]

    def _extraer_tasa(self, texto):
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', texto)
        if match:
            return float(match.group(1))
        # Buscar "tasa del X" o "tasa de X"
        match2 = re.search(r'tasa\s+de[l]?\s+(\d+(?:\.\d+)?)', texto.lower())
        if match2:
            return float(match2.group(1))
        return None

    def _extraer_tiempo_meses(self, texto):
        msg = texto.lower()
        match = re.search(r'(\d+)\s*(año|años)', msg)
        if match:
            return int(match.group(1)) * 12
        match2 = re.search(r'(\d+)\s*(mes|meses)', msg)
        if match2:
            return int(match2.group(1))
        return None

    def _resolver_problema_financiero(self, mensaje):
        """Motor de resolución de problemas financieros en lenguaje natural"""
        msg = mensaje.lower()
        numeros = self._extraer_todos_numeros(mensaje)
        tasa = self._extraer_tasa(mensaje)
        meses_param = self._extraer_tiempo_meses(mensaje)

        # -----------------------------------------------
        # PROBLEMA: Interés simple con meta específica
        # Ej: "Tengo $2.150, meta $3.000, tasa 1.5% mensual"
        # -----------------------------------------------
        tiene_capital = any(p in msg for p in ['tengo', 'capital', 'guardados', 'ahorrado', 'disponible'])
        tiene_meta = any(p in msg for p in ['meta', 'llegar a', 'juntar', 'alcanzar', 'quiero tener'])
        tiene_interes_simple = any(p in msg for p in ['interés simple', 'interes simple', 'simple'])
        tiene_retiro_anticipado = any(p in msg for p in ['antes', 'retiro anticipado', 'saco', 'retiro', 'meses antes'])

        if tiene_capital and tiene_meta and tasa and len(numeros) >= 2:
            # Identificar capital y meta
            capital = None
            meta = None

            # Buscar capital con contexto
            cap_match = re.search(r'(?:tengo|capital|guardados?|ahorrado?|disponible)[^\d]*\$?\s*([\d,\.]+)', msg)
            if cap_match:
                capital = float(cap_match.group(1).replace(',', '').replace('.', ''))

            # Buscar meta con contexto
            meta_match = re.search(r'(?:meta|llegar a|juntar|alcanzar|quiero tener|quiero llegar)[^\d]*\$?\s*([\d,\.]+)', msg)
            if meta_match:
                meta = float(meta_match.group(1).replace(',', '').replace('.', ''))

            # Si no encontró por contexto, usar los dos números más grandes
            if not capital or not meta:
                nums_grandes = sorted(numeros, reverse=True)
                if len(nums_grandes) >= 2:
                    meta = nums_grandes[0]
                    capital = nums_grandes[1]

            if capital and meta and tasa and capital < meta:
                # Detectar si la tasa es mensual o anual
                es_mensual = 'mensual' in msg or 'al mes' in msg or 'por mes' in msg
                tasa_mensual = tasa if es_mensual else tasa / 12
                tipo_tasa = f"{tasa}% mensual" if es_mensual else f"{tasa}% anual ({tasa_mensual:.4f}% mensual)"

                interes_necesario = meta - capital

                # Cálculo con interés simple
                if tiene_interes_simple or not any(p in msg for p in ['compuesto', 'capitali']):
                    # Meses para meta: Capital * tasa_mensual * n = interes_necesario
                    meses_para_meta = interes_necesario / (capital * tasa_mensual / 100)
                    meses_para_meta_redondeado = math.ceil(meses_para_meta)

                    # Verificar con meses exactos
                    interes_en_meses = capital * (tasa_mensual / 100) * meses_para_meta_redondeado
                    total_en_meses = capital + interes_en_meses

                    resp = (
                        f"🧮 **Resolución del problema — Interés Simple:**\n\n"
                        f"📋 **Datos identificados:**\n"
                        f"• Capital inicial: **${capital:,.2f}**\n"
                        f"• Meta objetivo: **${meta:,.2f}**\n"
                        f"• Tasa: **{tipo_tasa}**\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"**1️⃣ ¿Cuánto falta ganar en intereses?**\n\n"
                        f"Intereses necesarios = Meta − Capital\n"
                        f"Intereses necesarios = ${meta:,.2f} − ${capital:,.2f}\n"
                        f"**= ${interes_necesario:,.2f}**\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"**2️⃣ ¿Exactamente en cuántos meses?**\n\n"
                        f"Fórmula: Meses = Interés_necesario ÷ (Capital × Tasa_mensual)\n"
                        f"Meses = ${interes_necesario:,.2f} ÷ (${capital:,.2f} × {tasa_mensual/100:.4f})\n"
                        f"Meses exactos = {meses_para_meta:.4f}\n"
                        f"**Redondeando hacia arriba = {meses_para_meta_redondeado} meses**\n\n"
                        f"✅ En {meses_para_meta_redondeado} meses tendrías:\n"
                        f"${capital:,.2f} + ${interes_en_meses:,.2f} = **${total_en_meses:,.2f}**\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    )

                    # Retiro anticipado
                    if tiene_retiro_anticipado:
                        meses_antes_match = re.search(r'(\d+)\s*mes(?:es)?\s*antes', msg)
                        meses_antes = int(meses_antes_match.group(1)) if meses_antes_match else 3

                        meses_retiro = max(1, meses_para_meta_redondeado - meses_antes)
                        interes_retiro = capital * (tasa_mensual / 100) * meses_retiro
                        total_retiro = capital + interes_retiro
                        diferencia = meta - total_retiro

                        resp += (
                            f"**3️⃣ ¿Si retiras {meses_antes} meses antes?**\n\n"
                            f"Meses transcurridos = {meses_para_meta_redondeado} − {meses_antes} = **{meses_retiro} meses**\n\n"
                            f"Interés generado en {meses_retiro} meses:\n"
                            f"${capital:,.2f} × {tasa_mensual/100:.4f} × {meses_retiro} = **${interes_retiro:,.2f}**\n\n"
                            f"💰 **Total al retirar: ${total_retiro:,.2f}**\n\n"
                            f"📉 Diferencia vs meta (${meta:,.2f}): **−${diferencia:,.2f}**\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        )
                    else:
                        # Incluir retiro anticipado por defecto (3 meses antes)
                        meses_retiro = max(1, meses_para_meta_redondeado - 3)
                        interes_retiro = capital * (tasa_mensual / 100) * meses_retiro
                        total_retiro = capital + interes_retiro

                        resp += (
                            f"**3️⃣ ¿Si retiras 3 meses antes de la meta?**\n\n"
                            f"Meses transcurridos: {meses_para_meta_redondeado} − 3 = **{meses_retiro} meses**\n\n"
                            f"Interés en {meses_retiro} meses:\n"
                            f"${capital:,.2f} × {tasa_mensual/100:.4f} × {meses_retiro} = **${interes_retiro:,.2f}**\n\n"
                            f"💰 **Total al retirar anticipadamente: ${total_retiro:,.2f}**\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        )

                    resp += (
                        f"📊 **Resumen ejecutivo:**\n"
                        f"• Intereses necesarios: **${interes_necesario:,.2f}**\n"
                        f"• Tiempo para la meta: **{meses_para_meta_redondeado} meses**\n"
                        f"• Retiro anticipado (3 meses antes): **${total_retiro:,.2f}**\n\n"
                        f"💡 ¿Quieres que simule este escenario con interés compuesto para comparar?"
                    )

                    return resp, [
                        {'texto': '📈 Ver en Simulador', 'link': 'simulador.html'},
                        {'texto': '🎯 Crear esta meta', 'link': 'perfil.html'}
                    ]

                # Cálculo con interés compuesto
                else:
                    tasa_dec = tasa_mensual / 100
                    meses_ic = math.log(meta / capital) / math.log(1 + tasa_dec)
                    meses_ic_redondeado = math.ceil(meses_ic)
                    total_ic = capital * ((1 + tasa_dec) ** meses_ic_redondeado)
                    interes_ic = total_ic - capital

                    resp = (
                        f"🧮 **Resolución — Interés Compuesto:**\n\n"
                        f"📋 **Datos:**\n"
                        f"• Capital: **${capital:,.2f}**\n"
                        f"• Meta: **${meta:,.2f}**\n"
                        f"• Tasa: **{tipo_tasa}**\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"**1️⃣ Intereses necesarios:**\n"
                        f"${meta:,.2f} − ${capital:,.2f} = **${interes_necesario:,.2f}**\n\n"
                        f"**2️⃣ Meses para la meta:**\n"
                        f"Fórmula: n = log(Meta/Capital) ÷ log(1 + Tasa)\n"
                        f"n = {meses_ic:.4f} → **{meses_ic_redondeado} meses**\n\n"
                        f"✅ En {meses_ic_redondeado} meses tendrías: **${total_ic:,.2f}**\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    )

                    if tiene_retiro_anticipado:
                        meses_retiro = max(1, meses_ic_redondeado - 3)
                        total_retiro = capital * ((1 + tasa_dec) ** meses_retiro)
                        resp += (
                            f"**3️⃣ Retiro 3 meses antes:**\n"
                            f"**${total_retiro:,.2f}**\n\n"
                        )

                    return resp, [{'texto': '📈 Ver en Simulador', 'link': 'simulador.html'}]

        # -----------------------------------------------
        # PROBLEMA: Interés simple o compuesto general
        # -----------------------------------------------
        if tasa and len(numeros) >= 2:
            capital = numeros[0] if numeros[0] > numeros[-1] else numeros[-1]
            meses = meses_param or 12

            tasa_mensual = tasa if ('mensual' in msg or 'al mes' in msg) else tasa / 12
            tasa_dec = tasa_mensual / 100

            if 'simple' in msg:
                interes = capital * tasa_dec * meses
                total = capital + interes
                resp = (
                    f"🔢 **Cálculo de Interés Simple:**\n\n"
                    f"• Capital: **${capital:,.2f}**\n"
                    f"• Tasa mensual: **{tasa_mensual:.2f}%**\n"
                    f"• Plazo: **{meses} meses**\n\n"
                    f"Interés = ${capital:,.2f} × {tasa_dec:.4f} × {meses}\n"
                    f"**Interés = ${interes:,.2f}**\n\n"
                    f"**Total final = ${total:,.2f}**"
                )
                return resp, [{'texto': '📈 Ver en Simulador', 'link': 'simulador.html'}]

            elif 'compuesto' in msg or not 'simple' in msg:
                total = capital * ((1 + tasa_dec) ** meses)
                interes = total - capital
                resp = (
                    f"📈 **Cálculo de Interés Compuesto:**\n\n"
                    f"• Capital: **${capital:,.2f}**\n"
                    f"• Tasa mensual: **{tasa_mensual:.2f}%**\n"
                    f"• Plazo: **{meses} meses**\n\n"
                    f"Total = ${capital:,.2f} × (1 + {tasa_dec:.4f})^{meses}\n"
                    f"**Interés = ${interes:,.2f}**\n\n"
                    f"**Total final = ${total:,.2f}**"
                )
                return resp, [{'texto': '📈 Ver en Simulador', 'link': 'simulador.html'}]

        return None

    # ============================================
    # GLOSARIO FINANCIERO
    # ============================================
    def _buscar_en_glosario(self, mensaje):
        msg = mensaje.lower()
        msg = re.sub(r'[¿?¡!.,]', '', msg)

        # Quitar palabras de pregunta
        for q in ['que es', 'qué es', 'que significa', 'qué significa', 'define', 'definicion', 'explicame', 'explícame', 'como funciona', 'cómo funciona', 'qué son', 'que son']:
            msg = msg.replace(q, '').strip()

        msg = msg.strip()

        # Buscar coincidencia exacta primero
        for termino, definicion in self.glosario.items():
            if termino in msg:
                resp = (
                    f"📖 **{termino.upper()}:**\n\n"
                    f"{definicion}\n\n"
                    f"¿Quieres que profundice más en este tema o calcule algo relacionado?"
                )
                acciones = []
                if any(t in termino for t in ['inversion', 'interes', 'cdt', 'rendimiento']):
                    acciones.append({'texto': '📈 Ir al Simulador', 'link': 'simulador.html'})
                if any(t in termino for t in ['ahorro', 'meta', 'presupuesto']):
                    acciones.append({'texto': '🎯 Mis metas', 'link': 'perfil.html'})
                acciones.append({'texto': '📚 Aprender más', 'link': 'aprende.html'})
                return resp, acciones

        # Búsqueda parcial
        for termino, definicion in self.glosario.items():
            palabras_termino = termino.split()
            if any(p in msg for p in palabras_termino if len(p) > 3):
                resp = (
                    f"📖 **{termino.upper()}:**\n\n"
                    f"{definicion}\n\n"
                    f"¿Quieres saber algo más?"
                )
                return resp, [{'texto': '📚 Aprender más', 'link': 'aprende.html'}]

        return None

    # ============================================
    # CALCULADORAS EN CHAT
    # ============================================
    def _calcular_5030_desde_mensaje(self, mensaje, ctx):
        ingreso = self._extraer_numero(mensaje)
        if not ingreso and ctx:
            ingreso = ctx.get('ingreso_mensual', 0)
        if not ingreso or ingreso <= 0:
            return (
                "📋 **Calculadora 50/30/20**\n\n"
                "Dime tu ingreso mensual:\n"
                "Ejemplo: *\"Distribuye mi salario de $2.500.000\"*",
                [{'texto': '📚 Ver calculadoras', 'link': 'aprende.html'}]
            )
        nec = ingreso * 0.5
        des = ingreso * 0.3
        aho = ingreso * 0.2
        resp = (
            f"📋 **Distribución 50/30/20 para ${ingreso:,.0f}:**\n\n"
            f"🟢 **Necesidades (50%): ${nec:,.0f}**\nArriendo, comida, transporte, servicios, salud.\n\n"
            f"🟡 **Deseos (30%): ${des:,.0f}**\nRopa, entretenimiento, salidas, tecnología.\n\n"
            f"🔵 **Ahorro (20%): ${aho:,.0f}**\nFondo emergencia, metas, inversiones.\n\n"
            f"💡 Ahorrando ${aho:,.0f}/mes, en un año: **${aho*12:,.0f}**"
        )
        return resp, [
            {'texto': '🎯 Crear meta', 'link': 'perfil.html'},
            {'texto': '📈 Simular inversión', 'link': 'simulador.html'}
        ]

    def _calcular_meta_desde_mensaje(self, mensaje, ctx):
        numeros = self._extraer_todos_numeros(mensaje)
        if len(numeros) < 2:
            return (
                "🎯 **Calculadora de Meta**\n\n"
                "Dime cuánto quieres ahorrar y cuánto puedes apartar al mes.\n"
                "Ejemplo: *\"¿Cuánto tiempo para ahorrar $5.000.000 guardando $400.000 al mes?\"*",
                [{'texto': '🎯 Ver mis metas', 'link': 'perfil.html'}]
            )
        vals = sorted(numeros, reverse=True)
        meta = vals[0]
        mensual = vals[1]
        if mensual <= 0:
            return ("Dime cuánto puedes ahorrar al mes.", [])
        meses = math.ceil(meta / mensual)
        anos = meses // 12
        mr = meses % 12
        plazo = f"{anos} año{'s' if anos > 1 else ''}" if anos > 0 else ""
        if mr > 0:
            plazo += f" y {mr} mes{'es' if mr > 1 else ''}"
        tasa_m = 0.08 / 12
        acum = 0
        meses_ci = 0
        while acum < meta and meses_ci < 1200:
            acum = acum * (1 + tasa_m) + mensual
            meses_ci += 1
        resp = (
            f"🎯 **Calculadora de Meta:**\n\n"
            f"🏁 Meta: **${meta:,.0f}** · 💵 Ahorro mensual: **${mensual:,.0f}**\n\n"
            f"⏱️ Sin intereses: **{plazo or str(meses) + ' meses'}**\n"
            f"📈 Con interés compuesto (8% anual): **{meses_ci} meses** *(ahorras {meses - meses_ci} meses)*\n\n"
            f"💡 Aumentando un 20% tu ahorro (${mensual*1.2:,.0f}), la alcanzarías en **{math.ceil(meta/(mensual*1.2))} meses**."
        )
        return resp, [
            {'texto': '🎯 Crear esta meta', 'link': 'perfil.html'},
            {'texto': '📈 Simular', 'link': 'simulador.html'}
        ]

    # ============================================
    # SALUDO INTELIGENTE
    # ============================================
    def _saludo_inteligente(self, nombre, ctx):
        hora = datetime.now().hour
        momento = "¡Buenos días" if hora < 12 else "¡Buenas tardes" if hora < 18 else "¡Buenas noches"
        base = f"{momento}, **{nombre}**! 👋\n\n" if nombre else f"{momento}! 👋 Soy **FinanBot**.\n\n"

        if ctx:
            balance = ctx.get('balance', 0)
            ingresos = ctx.get('total_ingresos', 0)
            gastos = ctx.get('total_gastos', 0)
            num_trans = ctx.get('num_transacciones', 0)
            num_metas = ctx.get('num_metas', 0)

            if num_trans == 0:
                base += (
                    "Veo que aún no tienes transacciones. ¡Empecemos!\n\n"
                    "Puedo ayudarte a:\n"
                    "• 📝 Registrar gastos e ingresos\n"
                    "• 🎯 Crear metas de ahorro\n"
                    "• 📈 Simular inversiones\n"
                    "• 🧮 Resolver problemas financieros\n"
                    "• 📖 Explicarte cualquier término financiero\n\n"
                    "¿Por dónde empezamos?"
                )
            else:
                porc = round((gastos / ingresos * 100)) if ingresos > 0 else 0
                estado = "✅" if balance >= 0 else "⚠️"
                base += (
                    f"Tu situación actual:\n\n"
                    f"📊 Balance: **${balance:,.0f}** {estado}\n"
                    f"💰 Ingresos: **${ingresos:,.0f}**\n"
                    f"💸 Gastos: **${gastos:,.0f}** ({porc}%)\n"
                    f"🎯 Metas: **{num_metas}**\n\n"
                )
                if balance < 0:
                    base += "⚠️ Tus gastos superan tus ingresos. ¿Analizamos cómo mejorar?"
                elif porc > 80:
                    base += f"📌 Gastas el {porc}% de tus ingresos. Revisemos la regla 50/30/20."
                else:
                    base += "¡Vas bien! ¿En qué te ayudo hoy?"
        else:
            base += (
                "Soy tu asistente financiero personal.\n\n"
                "Puedo **registrar** tus finanzas, **calcular** intereses, **resolver** problemas financieros, "
                "**explicar** términos, **simular** inversiones y mucho más.\n\n"
                "¿Qué necesitas?"
            )

        return base, [
            {'texto': '📊 Mis finanzas', 'link': 'finanzas.html'},
            {'texto': '💡 Recomendaciones', 'link': 'recomendaciones.html'},
            {'texto': '❓ ¿Qué puedes hacer?', 'link': '#'}
        ]

    def _despedida(self, nombre):
        frases = [
            f"😊 ¡Hasta pronto{', ' + nombre if nombre else ''}! Cada peso bien gestionado hoy es libertad mañana.",
            f"👋 ¡Nos vemos{', ' + nombre if nombre else ''}! Sigue construyendo tu futuro financiero.",
            f"🌟 ¡Hasta luego{', ' + nombre if nombre else ''}! Que tus finanzas siempre estén en verde. 💚",
        ]
        return random.choice(frases)

    def _respuesta_gracias(self, nombre):
        frases = [
            f"😊 ¡Con gusto{', ' + nombre if nombre else ''}! ¿Algo más en lo que pueda ayudarte?",
            f"🤖 ¡Es un placer{', ' + nombre if nombre else ''}! Tu bienestar financiero es mi misión.",
            f"✨ ¡No hay de qué! También puedo resolver problemas financieros, explicar términos o calcular inversiones.",
        ]
        return random.choice(frases)

    def _respuesta_ayuda(self):
        return (
            "🤖 **FinanBot — Todo lo que puedo hacer por ti:**\n\n"
            "**📝 Gestión de datos:**\n"
            "• *\"Registra un gasto de $50.000 en ropa\"*\n"
            "• *\"Agrega un ingreso de $2.000.000 por salario\"*\n"
            "• *\"Crea una meta de $1.000.000 para vacaciones\"*\n"
            "• *\"Borra el último gasto\"* · *\"Actualiza mi salario\"*\n\n"

            "**🧮 Problemas financieros complejos:**\n"
            "• *\"Tengo $2.150, quiero llegar a $3.000 con tasa 1.5% mensual. ¿Cuántos meses?\"*\n"
            "• *\"¿Cuánto gano si invierto $5M al 10% anual por 3 años con interés compuesto?\"*\n"
            "• *\"Tengo $1M, tasa 8% anual, ¿cuándo triplico mi dinero?\"*\n\n"

            "**📖 Glosario financiero:**\n"
            "• *\"¿Qué es el saldo?\"* · *\"¿Qué es la tasa EA?\"*\n"
            "• *\"¿Qué es amortización?\"* · *\"¿Qué es un CDT?\"*\n"
            "• *\"¿Qué es el VAN?\"* · *\"¿Qué es liquidez?\"*\n\n"

            "**📊 Calculadoras:**\n"
            "• Regla 50/30/20 para tu salario\n"
            "• Interés simple y compuesto\n"
            "• Tiempo para alcanzar una meta\n"
            "• Operaciones matemáticas\n\n"

            "**📈 Simulaciones:**\n"
            "• *\"Simula $2.000.000 al 10% por 24 meses\"*\n\n"

            "**💡 Conocimiento financiero:**\n"
            "Ahorro, deudas, inversión, inflación, pensión, criptos, impuestos.\n\n"

            "Escríbeme en lenguaje natural, como si le hablaras a una persona."
        )

    def _curiosidad_financiera(self):
        curiosidades = [
            "🧠 **¿Sabías que...?**\nWarren Buffett hizo el 99% de su fortuna después de los 50 años gracias al interés compuesto. Empezó a los 11 años.",
            "🧠 **¿Sabías que...?**\nSi ahorras $10.000 diarios durante 10 años al 10% anual compuesto, tendrías más de **$58 millones**.",
            "🧠 **¿Sabías que...?**\nEl 75% de los colombianos no se pensionará nunca. La mejor pensión es la que tú construyes hoy.",
            "🧠 **¿Sabías que...?**\nLa regla 72 dice: divide 72 entre la tasa de interés y obtienes los años para doblar tu dinero. Al 8% anual: 72/8 = **9 años**.",
            "🧠 **¿Sabías que...?**\nUna deuda con el 'gota a gota' puede tener tasas del 20% **diario**, lo que equivale a más del 7.000% anual.",
        ]
        return random.choice(curiosidades)

    # ============================================
    # ANÁLISIS FINANCIERO
    # ============================================
    def _analisis_financiero_inteligente(self, ctx):
        balance = ctx.get('balance', 0)
        ingresos = ctx.get('total_ingresos', 0)
        gastos = ctx.get('total_gastos', 0)
        num_trans = ctx.get('num_transacciones', 0)
        num_metas = ctx.get('num_metas', 0)
        cat_mayor = ctx.get('categoria_mayor_gasto')
        monto_mayor = ctx.get('monto_mayor_gasto', 0)
        metas = ctx.get('metas', [])
        ingreso_mensual = ctx.get('ingreso_mensual', 0)

        resp = "📊 **Análisis financiero completo:**\n\n"
        resp += f"• Ingresos: **${ingresos:,.0f}**\n"
        resp += f"• Gastos: **${gastos:,.0f}**\n"
        resp += f"• Balance: **${balance:,.0f}**\n"
        resp += f"• Transacciones: **{num_trans}**\n\n"

        if ingresos > 0:
            porc = round(gastos / ingresos * 100)
            if balance < 0:
                resp += f"⚠️ Gastas el **{porc}%** de tus ingresos. Balance negativo. Revisa la regla 50/30/20.\n\n"
            elif porc > 80:
                resp += f"📌 Gastas el **{porc}%**. Intenta reducirlo al 70-75%.\n\n"
            elif porc > 50:
                resp += f"🙂 Gastas el **{porc}%**. Podrías ahorrar **${balance * 0.3:,.0f}** más.\n\n"
            else:
                resp += f"✅ Solo gastas el **{porc}%**. Podrías invertir **${balance * 0.2:,.0f}**.\n\n"

        if cat_mayor and monto_mayor > 0:
            resp += f"💸 Mayor gasto: **{cat_mayor}** — ${monto_mayor:,.0f}\n\n"

        if metas:
            resp += f"🎯 **{len(metas)} meta(s):**\n"
            for m in metas[:3]:
                barra = self._barra_progreso(m['porcentaje'])
                resp += f"• **{m['nombre']}:** {barra} {m['porcentaje']}%\n"
            resp += "\n"

        if ingreso_mensual > 0:
            resp += (
                f"📋 **Distribución ideal (50/30/20):**\n"
                f"🟢 Necesidades: **${ingreso_mensual*0.5:,.0f}**\n"
                f"🟡 Deseos: **${ingreso_mensual*0.3:,.0f}**\n"
                f"🔵 Ahorro: **${ingreso_mensual*0.2:,.0f}**\n"
            )

        return resp, [
            {'texto': '📊 Ver detalle', 'link': 'finanzas.html'},
            {'texto': '💡 Recomendaciones', 'link': 'recomendaciones.html'},
            {'texto': '🎯 Mis metas', 'link': 'perfil.html'}
        ]

    def _barra_progreso(self, porcentaje):
        llenos = round(porcentaje / 10)
        return '█' * llenos + '░' * (10 - llenos)

    # ============================================
    # RESPUESTAS DE ACCIONES CRUD
    # ============================================
    def _respuesta_accion_ejecutada(self, accion, ctx):
        tipo = accion.get('tipo')

        if tipo == 'calculo':
            return (
                f"🧮 **Resultado:** **= {accion['resultado']:,}**\n\n"
                f"¿Quieres que registre este valor o hacer otra operación?",
                []
            )

        elif tipo == 'meta_creada':
            nombre_meta = accion['nombre']
            monto = accion['monto']
            resp = (
                f"✅ **¡Meta creada!**\n\n"
                f"🎯 **{nombre_meta}** — ${monto:,.0f}\n"
                f"📊 Progreso: ░░░░░░░░░░ 0%\n\n"
            )
            if ctx and ctx.get('balance', 0) > 0:
                ahorro = ctx['balance'] * 0.2
                if ahorro > 0:
                    meses = math.ceil(monto / ahorro)
                    resp += f"💡 Ahorrando el 20% (~**${ahorro:,.0f}/mes**) la alcanzarías en **{meses} meses**.\n\n"
            resp += "Puedes verla y abonar desde **Mi Perfil**."
            return resp, [
                {'texto': '🎯 Ver mis metas', 'link': 'perfil.html'},
                {'texto': '📊 Dashboard', 'link': 'dashboard.html'}
            ]

        elif tipo == 'meta_eliminada':
            return (
                f"🗑️ Meta **{accion['nombre']}** eliminada. Si fue un error, puedes crearla de nuevo.",
                [{'texto': '🎯 Ver mis metas', 'link': 'perfil.html'}]
            )

        elif tipo == 'meta_actualizada':
            nuevo = accion['nuevo_monto']
            nombre_meta = accion['nombre']
            meta_obj = next((m for m in ctx.get('metas', []) if m['nombre'] == nombre_meta), None) if ctx else None
            resp = f"✅ **Meta actualizada** — {nombre_meta}: **${nuevo:,.0f}**\n"
            if meta_obj:
                resp += f"\n📊 {self._barra_progreso(meta_obj['porcentaje'])} **{meta_obj['porcentaje']}%**"
            return resp, [{'texto': '🎯 Ver mis metas', 'link': 'perfil.html'}]

        elif tipo == 'consulta_metas':
            metas = accion.get('metas', [])
            if not metas:
                return (
                    "🎯 No tienes metas aún.\n\n"
                    "Ejemplo: *\"Crea una meta de $500.000 para mi viaje\"*",
                    [{'texto': '➕ Crear meta', 'link': 'perfil.html'}]
                )
            resp = f"🎯 **{len(metas)} meta(s):**\n\n"
            for m in metas:
                barra = self._barra_progreso(m['porcentaje'])
                estado = '✅ Completada' if m['completada'] else f"{m['porcentaje']}%"
                faltante = m['objetivo'] - m['actual']
                resp += f"**{m['nombre']}** {barra} {estado}\n"
                resp += f"${m['actual']:,.0f} / ${m['objetivo']:,.0f}"
                if not m['completada']:
                    resp += f" · Faltan **${faltante:,.0f}**"
                resp += "\n\n"
            return resp, [{'texto': '🎯 Ver mis metas', 'link': 'perfil.html'}]

        elif tipo == 'gasto_registrado':
            monto = accion['monto']
            categoria = accion['categoria']
            nuevo_balance = ctx.get('balance', 0) - monto if ctx else 0
            resp = (
                f"✅ **Gasto registrado**\n\n"
                f"💸 **${monto:,.0f}** · {categoria}\n"
                f"📊 Nuevo balance: **${nuevo_balance:,.0f}**\n\n"
            )
            if ctx and ctx.get('total_ingresos', 0) > 0:
                porc = round((ctx['total_gastos'] + monto) / ctx['total_ingresos'] * 100)
                alerta = "⚠️ ¡Cuidado!" if porc > 80 else "📊"
                resp += f"{alerta} Llevas el **{porc}%** de tus ingresos gastados."
            return resp, [
                {'texto': '📊 Mis finanzas', 'link': 'finanzas.html'},
                {'texto': '🏠 Dashboard', 'link': 'dashboard.html'}
            ]

        elif tipo == 'gasto_eliminado':
            return (
                f"🗑️ Gasto de **${accion['monto']:,.0f}** en **{accion['categoria']}** eliminado.\nBalance actualizado.",
                [{'texto': '📊 Mis finanzas', 'link': 'finanzas.html'}]
            )

        elif tipo == 'ingreso_registrado':
            monto = accion['monto']
            categoria = accion['categoria']
            nuevo_balance = ctx.get('balance', 0) + monto if ctx else 0
            return (
                f"✅ **Ingreso registrado**\n\n"
                f"💰 **${monto:,.0f}** · {categoria}\n"
                f"📊 Nuevo balance: **${nuevo_balance:,.0f}**\n\n"
                f"💡 Si apartas el 20% (**${monto*0.2:,.0f}**), aplicarías la regla de oro del ahorro.",
                [
                    {'texto': '📊 Mis finanzas', 'link': 'finanzas.html'},
                    {'texto': '🏠 Dashboard', 'link': 'dashboard.html'}
                ]
            )

        elif tipo == 'ingreso_eliminado':
            return (
                f"🗑️ Ingreso de **${accion['monto']:,.0f}** en **{accion['categoria']}** eliminado.\nBalance actualizado.",
                [{'texto': '📊 Mis finanzas', 'link': 'finanzas.html'}]
            )

        elif tipo == 'consulta_gastos':
            num = accion.get('num_gastos', 0)
            total = accion.get('total_gastos', 0)
            por_cat = accion.get('gastos_por_categoria', {})
            recientes = accion.get('recientes', [])
            resp = f"📊 **{num} gastos · Total: ${total:,.0f}**\n\n"
            if por_cat:
                total_ref = total if total > 0 else 1
                for cat, monto in sorted(por_cat.items(), key=lambda x: x[1], reverse=True)[:6]:
                    porc = round(monto / total_ref * 100)
                    barra = '█' * round(porc/10) + '░' * (10 - round(porc/10))
                    resp += f"• **{cat}:** {barra} ${monto:,.0f} ({porc}%)\n"
                resp += "\n"
            if recientes:
                resp += "**Últimos:**\n"
                for t in recientes[:3]:
                    resp += f"• {t['categoria']}: **${t['monto']:,.0f}** · {t['fecha']}\n"
            return resp, [
                {'texto': '📊 Ver todos', 'link': 'finanzas.html'},
                {'texto': '💡 Recomendaciones', 'link': 'recomendaciones.html'}
            ]

        elif tipo == 'consulta_ingresos':
            num = accion.get('num_ingresos', 0)
            total = accion.get('total_ingresos', 0)
            recientes = accion.get('recientes', [])
            resp = f"💰 **{num} ingresos · Total: ${total:,.0f}**\n\n"
            if recientes:
                for t in recientes[:3]:
                    resp += f"• {t['categoria']}: **${t['monto']:,.0f}** · {t['fecha']}\n"
            return resp, [{'texto': '📊 Ver todos', 'link': 'finanzas.html'}]

        elif tipo == 'salario_actualizado':
            nuevo = accion['nuevo_salario']
            return (
                f"✅ **Salario actualizado: ${nuevo:,.0f}**\n\n"
                f"📋 Distribución ideal (50/30/20):\n"
                f"🟢 Necesidades: **${nuevo*0.5:,.0f}**\n"
                f"🟡 Deseos: **${nuevo*0.3:,.0f}**\n"
                f"🔵 Ahorro: **${nuevo*0.2:,.0f}**",
                [
                    {'texto': '👤 Ver perfil', 'link': 'perfil.html'},
                    {'texto': '💡 Recomendaciones', 'link': 'recomendaciones.html'}
                ]
            )

        elif tipo == 'meta_mensual_actualizada':
            nuevo = accion['nuevo_monto']
            return (
                f"✅ **Meta mensual: ${nuevo:,.0f}**\n\n"
                f"• En 6 meses: **${nuevo*6:,.0f}**\n"
                f"• En 1 año: **${nuevo*12:,.0f}**",
                [{'texto': '👤 Ver perfil', 'link': 'perfil.html'}]
            )

        elif tipo == 'simulacion_realizada':
            capital = accion['capital']
            tasa = accion['tasa']
            plazo = accion['plazo']
            resultado = accion['resultado']
            ganancia = accion['ganancia']
            porc = round((ganancia / capital) * 100)
            anos = plazo // 12
            mr = plazo % 12
            plazo_txt = f"{anos} año{'s' if anos > 1 else ''}" if anos > 0 else ""
            if mr > 0:
                plazo_txt += f" y {mr} mes{'es' if mr > 1 else ''}"

            return (
                f"📈 **¡Simulación completada!**\n\n"
                f"💰 Capital: **${capital:,.0f}** · 📊 Tasa: **{tasa}%** · ⏱️ Plazo: **{plazo_txt}**\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏆 **Resultado: ${resultado:,.0f}**\n"
                f"📈 **Ganancia: ${ganancia:,.0f} (+{porc}%)**\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"✅ Guardada en tu historial. ¿Ves la gráfica completa en el simulador?",
                [
                    {'texto': '📈 Ver simulación completa', 'link': 'simulador.html'},
                    {'texto': '📊 Dashboard', 'link': 'dashboard.html'}
                ]
            )

        elif tipo == 'consulta_resumen':
            balance = accion.get('balance', 0)
            ingresos = accion.get('total_ingresos', 0)
            gastos = accion.get('total_gastos', 0)
            num_metas = accion.get('num_metas', 0)
            num_trans = accion.get('num_transacciones', 0)
            porc = round(gastos / ingresos * 100) if ingresos > 0 else 0
            resp = (
                f"📊 **Tu resumen:**\n\n"
                f"💰 Ingresos: **${ingresos:,.0f}**\n"
                f"💸 Gastos: **${gastos:,.0f}** ({porc}%)\n"
                f"📈 Balance: **${balance:,.0f}**\n"
                f"🎯 Metas: **{num_metas}** · 📋 Trans: **{num_trans}**\n\n"
            )
            if balance < 0:
                resp += "⚠️ Balance negativo. Revisa tus gastos urgentemente."
            elif porc > 80:
                resp += f"📌 Gastas el {porc}%. Lo ideal es no superar el 80%."
            else:
                resp += f"✅ ¡Bien! Podrías invertir **${balance*0.3:,.0f}** productivamente."
            return resp, [
                {'texto': '🏠 Dashboard', 'link': 'dashboard.html'},
                {'texto': '💡 Recomendaciones', 'link': 'recomendaciones.html'}
            ]

        elif tipo == 'pide_monto':
            ctx_tipo = accion.get('contexto', 'transacción')
            return (
                f"💭 Quiero ayudarte a registrar un **{ctx_tipo}**. ¿Por cuánto es?\n\n"
                f"Ejemplo: *\"Registra un {ctx_tipo} de $50.000 en alimentación\"*",
                []
            )

        elif tipo == 'sin_datos':
            return (
                f"📭 No tienes **{accion.get('contexto', 'datos')}** aún.\n"
                f"¿Quieres que te ayude a agregar el primero?",
                [{'texto': '📊 Mis Finanzas', 'link': 'finanzas.html'}]
            )

        elif tipo == 'error':
            return (
                f"❌ {accion.get('mensaje', 'Error inesperado.')}\n\nIntenta reformular tu mensaje.",
                []
            )

        return "✅ Listo, acción completada.", []

    # ============================================
    # RESPUESTA DESCONOCIDA
    # ============================================
    def _respuesta_desconocido(self, mensaje, nombre):
        respuestas = [
            (
                f"🤔 Entiendo que dices *\"{mensaje[:50]}\"*, pero no logro identificar exactamente qué necesitas.\n\n"
                f"Puedo ayudarte con:\n"
                f"• 📖 *\"¿Qué es el saldo/tasa/amortización...?\"*\n"
                f"• 🧮 Problemas con capital, tasas y metas\n"
                f"• 📝 Registrar gastos, ingresos o metas\n"
                f"• 📈 Simular inversiones\n"
                f"• 💡 Consejos financieros\n\n"
                f"¿Puedes ser más específico?"
            ),
            (
                f"💬 No logro identificar la acción en *\"{mensaje[:40]}\"*.\n\n"
                f"Intenta con:\n"
                f"• *\"¿Qué es la tasa EA?\"*\n"
                f"• *\"Tengo $2M, meta $3M, tasa 1.5% mensual\"*\n"
                f"• *\"Registra un gasto de $50.000 en ropa\"*\n"
                f"• *\"Simula $1M al 10% por 12 meses\"*"
            ),
        ]
        return random.choice(respuestas), [
            {'texto': '❓ ¿Qué puedes hacer?', 'link': '#'},
            {'texto': '📊 Mis Finanzas', 'link': 'finanzas.html'}
        ]

    # ============================================
    # CLAVES POR TEMA
    # ============================================
    def _claves_tema(self, tema):
        mapa = {
            'ahorro': ['ahorrar', 'ahorro', 'gastos hormiga', 'guardar dinero', 'economizar'],
            'presupuesto': ['50/30/20', 'presupuesto', 'regla 50', 'distribuir salario', 'planificar gastos'],
            'deudas': ['deuda', 'salir de deudas', 'bola de nieve', 'avalancha', 'crédito', 'préstamo', 'mora'],
            'inversion': ['invertir', 'inversión', 'cdt', 'acciones', 'fondos de inversión', 'bvc'],
            'emergencia': ['fondo de emergencia', 'emergencia', 'imprevisto', 'colchón', 'reserva'],
            'interes': ['interés simple', 'interés compuesto', 'interes compuesto', 'interes simple'],
            'pension': ['colpensiones', 'fondos privados', 'pensión', 'jubilación', 'cotizar'],
            'inflacion': ['inflación', 'inflacion', 'poder adquisitivo', 'devaluación'],
            'cripto': ['criptomoneda', 'bitcoin', 'ethereum', 'crypto', 'blockchain'],
            'impuesto': ['impuesto', 'declaración de renta', 'dian', 'tributar'],
        }
        return mapa.get(tema, [])


def obtener_respuesta(mensaje):
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones(mensaje)
    return respuesta