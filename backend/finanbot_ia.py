# finanbot_ia.py - Motor de IA Financiera de FinanBot

import re

class FinanBotIA:
    def __init__(self):
        self.contexto = []
        self.nombre_usuario = None
        self.conocimientos = {
            'ahorro': "💰 **Cómo empezar a ahorrar desde cero:**\n\nAhorra antes de gastar. Transfiere el 10-20% de tu salario inmediatamente a una cuenta separada.\nIdentifica y elimina gastos hormiga como café diario, taxis innecesarios y apps sin uso.\nAutomatiza tu ahorro y define metas claras para mantener la motivación.",
            'presupuesto': "📋 **Regla 50/30/20:**\n\n50% para necesidades básicas, 30% para deseos y 20% para ahorro e inversión.\nSi tus necesidades superan el 50%, ajusta a 60/20/20 o 70/15/15, pero siempre aparta algo para ahorrar.",
            'deudas': "💳 **Como salir de deudas paso a paso:**\n\nHaz un inventario de todas tus deudas con monto, cuota y tasa.\nMétodo Bola de Nieve: paga primero la deuda más pequeña para ganar motivación.\nMétodo Avalancha: paga primero la deuda con mayor tasa para ahorrar intereses.\nNo adquieras nuevas deudas mientras pagas y evita créditos peligrosos como el 'gota a gota'.",
            'inversion': "📈 **Inversiones para principiantes en Colombia:**\n\nEmpieza con un fondo de emergencia y paga deudas de alto interés.\nCDT: bajo riesgo, 8-14% anual.\nFondos de inversión colectiva: diversificación fácil.\nAcciones en la BVC: riesgo mayor, ideal a largo plazo.\nNunca inviertas dinero que necesitas pronto.",
            'emergencia': "🚨 **Por qué necesitas un fondo de emergencia:**\n\nEs un ahorro para imprevistos como pérdida de empleo o gastos médicos.\nIdeal: 6 meses de gastos básicos; mínimo: 3 meses.\nGuárdalo en una cuenta de fácil acceso o fondo de liquidez, no en inversiones de largo plazo ni efectivo en casa.",
            'interes': "🔢 **Interés simple vs interés compuesto:**\n\nInterés simple se calcula sobre el capital inicial.\nInterés compuesto se calcula sobre el capital más los intereses acumulados.\nEjemplo: $1.000.000 al 10% anual queda $1.300.000 con interés simple en 3 años, y $1.331.000 con interés compuesto.",
            'pension': "👴 **Colpensiones vs fondos privados:**\n\nColpensiones es el régimen de prima media administrado por el Estado.\nLos fondos privados son cuentas individuales y permiten aportes voluntarios.\nCotiza siempre que puedas y complementa con ahorro personal.",
            'inflacion': "📉 **Cómo protegerte de la inflación:**\n\nLa inflación reduce tu poder adquisitivo.\nBusca productos que rindan más que la inflación: CDT, fondos de inversión, acciones y activos reales.\nNo dejes el dinero quieto en efectivo o bajo el colchón.",
            'cripto': "₿ **Criptomonedas: riesgos y realidades:**\n\nLas criptos son muy volátiles y no reguladas.\nSolo invierte lo que puedas perder completamente, idealmente menos del 5% de tu portafolio.\nUsa plataformas reconocidas y evita promesas de rendimientos garantizados."        
        }

    def detectar_intencion(self, mensaje):
        msg = mensaje.lower().strip()
        msg = re.sub(r'[¿?¡!.,]', '', msg)

        intenciones = {
            'saludo': ['hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'hey', 'buenas', 'saludos'],
            'ahorro': ['ahorr', 'guardar dinero', 'reducir gastos', 'economizar'],
            'inversion': ['invert', 'inversión', 'invertir', 'rendimiento', 'cdt', 'acciones', 'fondos', 'bolsa'],
            'deuda': ['deuda', 'credito', 'crédito', 'prestamo', 'préstamo', 'debo', 'endeud'],
            'presupuesto': ['presupuesto', '50/30/20', 'distribuir', 'organizar dinero', 'planificar'],
            'gastos': ['gasto', 'gastos', 'control', 'controlar', 'donde se va', 'en que gasto'],
            'ingreso': ['ingreso', 'salario', 'sueldo', 'ganar mas', 'dinero extra'],
            'emergencia': ['emergencia', 'fondo', 'imprevisto', 'colchon', 'reserva'],
            'meta': ['meta', 'objetivo', 'sueño', 'quiero comprar', 'quiero viajar', 'alcanzar'],
            'inflacion': ['inflacion', 'inflación', 'precio', 'poder adquisitivo'],
            'impuesto': ['impuesto', 'declaracion', 'dian', 'renta'],
            'seguro': ['seguro', 'poliza', 'proteccion', 'vida'],
            'pension': ['pension', 'pensión', 'jubilacion', 'retiro', 'colpensiones'],
            'criptomoneda': ['cripto', 'bitcoin', 'ethereum', 'crypto', 'blockchain'],
            'mis_datos': ['mis finanzas', 'mi balance', 'cuanto tengo', 'mis gastos', 'mi situacion', 'como estoy', 'mi dinero', 'mis datos'],
            'mis_metas': ['mis metas', 'mis objetivos', 'como van mis metas'],
            'simular': ['simular', 'simulacion', 'simulador', 'quiero simular', 'ver simulador'],
            'despedida': ['adios', 'hasta luego', 'chao', 'bye', 'gracias'],
            'ayuda': ['ayuda', 'help', 'que puedes hacer', 'para que sirves'],
            'nombre': ['me llamo', 'mi nombre es', 'soy '],
        }

        for intencion, palabras in intenciones.items():
            for palabra in palabras:
                if palabra in msg:
                    return intencion

        return 'desconocido'

    def _buscar_respuesta_conocimiento(self, mensaje):
        msg = mensaje.lower()
        claves = {
            'ahorro': ['ahorrar', 'ahorro', 'ahorrar desde cero', 'gastos hormiga', 'guardar dinero', 'págate a ti primero'],
            'presupuesto': ['50/30/20', 'presupuesto', 'regla 50/30/20', 'distribuir salario'],
            'deudas': ['deudas', 'deuda', 'salir de deudas', 'bola de nieve', 'avalancha'],
            'inversion': ['inversión', 'invertir', 'cdt', 'acciones', 'fondos de inversión', 'bvc'],
            'emergencia': ['fondo de emergencia', 'emergencia', 'imprevisto', 'colchón', 'reserva'],
            'interes': ['interés simple', 'interés compuesto', 'interes compuesto', 'interes simple', 'interes'],
            'pension': ['colpensiones', 'fondos privados', 'pensión', 'pension', 'jubilación'],
            'inflacion': ['inflación', 'inflacion', 'protegerte de la inflación', 'poder adquisitivo'],
            'cripto': ['criptomoneda', 'cripto', 'bitcoin', 'ethereum', 'crypto'],
        }
        for tema, palabras in claves.items():
            for palabra in palabras:
                if palabra in msg:
                    return self.conocimientos.get(tema)
        return None

    def responder_con_acciones(self, mensaje, contexto_financiero=None):
        self.contexto.append(mensaje)
        conocimiento = self._buscar_respuesta_conocimiento(mensaje)
        intencion = self.detectar_intencion(mensaje)

        # Detectar nombre
        msg_lower = mensaje.lower()
        for frase in ['me llamo ', 'mi nombre es ', 'soy ']:
            if frase in msg_lower:
                idx = msg_lower.find(frase) + len(frase)
                nombre = mensaje[idx:].split()[0].capitalize()
                self.nombre_usuario = nombre

        # Nombre del usuario
        if contexto_financiero and contexto_financiero.get('nombre'):
            nombre = contexto_financiero['nombre']
        elif self.nombre_usuario:
            nombre = self.nombre_usuario
        else:
            nombre = None

        saludo = f"¡Hola, {nombre}! " if nombre and intencion == 'saludo' else ""

        if conocimiento:
            acciones = [
                {'texto': '📚 Ver Aprende', 'link': 'aprende.html'},
                {'texto': '📈 Ir al Simulador', 'link': 'simulador.html'}
            ]
            return saludo + conocimiento, acciones

        # Generar respuesta y acciones
        respuesta, acciones = self._generar_respuesta(intencion, mensaje, contexto_financiero)

        return saludo + respuesta, acciones

    def _generar_respuesta(self, intencion, mensaje, ctx):
        acciones = []

        if intencion == 'saludo':
            if ctx:
                nombre = ctx.get('nombre', 'Usuario')
                balance = ctx.get('balance', 0)
                num_trans = ctx.get('num_transacciones', 0)
                resp = f"👋 ¡Hola, **{nombre}**! Me alegra verte.\n\n"
                if num_trans > 0:
                    resp += f"📊 Veo que tienes **{num_trans} transacciones** registradas y un balance de **${balance:,.0f}**.\n\n"
                else:
                    resp += "📝 Aún no tienes transacciones registradas. ¡Te ayudo a empezar!\n\n"
                resp += "¿En qué te puedo ayudar hoy?"
                acciones = [
                    {'texto': '📊 Ver mis finanzas', 'link': 'finanzas.html'},
                    {'texto': '💡 Ver recomendaciones', 'link': 'recomendaciones.html'}
                ]
            else:
                resp = "👋 ¡Hola! Soy **FinanBot**, tu asistente financiero.\n\n¿En qué te puedo ayudar hoy?\n\n💰 Ahorro · 📈 Inversiones · 📊 Presupuesto · 💳 Deudas"
                acciones = [
                    {'texto': '📈 Ver simulador', 'link': 'simulador.html'},
                    {'texto': '📝 Registrarme', 'link': 'registro.html'}
                ]

        elif intencion == 'mis_datos':
            if ctx:
                resp = f"📊 **Tu resumen financiero actual:**\n\n"
                resp += f"💰 Ingresos totales: **${ctx['total_ingresos']:,.0f}**\n"
                resp += f"💸 Gastos totales: **${ctx['total_gastos']:,.0f}**\n"
                resp += f"📈 Balance: **${ctx['balance']:,.0f}**\n"
                if ctx['balance'] < 0:
                    resp += f"\n⚠️ Tu balance es **negativo**. Estás gastando más de lo que ingresas. Te recomiendo revisar tus gastos."
                elif ctx['balance'] > 0:
                    resp += f"\n✅ ¡Vas bien! Tienes un balance positivo. Considera ahorrar o invertir el excedente."
                if ctx.get('categoria_mayor_gasto'):
                    resp += f"\n\n📌 Tu mayor gasto es en **{ctx['categoria_mayor_gasto']}** con **${ctx['monto_mayor_gasto']:,.0f}**."
                acciones = [
                    {'texto': '📊 Ver mis finanzas', 'link': 'finanzas.html'},
                    {'texto': '💡 Ver recomendaciones', 'link': 'recomendaciones.html'},
                    {'texto': '📈 Simular inversión', 'link': 'simulador.html'}
                ]
            else:
                resp = "Para ver tus datos financieros necesitas **iniciar sesión** primero."
                acciones = [{'texto': '🔑 Iniciar sesión', 'link': 'login.html'}]

        elif intencion == 'mis_metas':
            if ctx:
                num_metas = ctx.get('num_metas', 0)
                if num_metas > 0:
                    resp = f"🎯 Tienes **{num_metas} meta(s) de ahorro** activas. ¡Sigue así!\n\nPuedes ver el progreso detallado en tu perfil."
                else:
                    resp = "🎯 Aún no tienes metas de ahorro. ¡Te recomiendo crear una para tener un objetivo claro!"
                acciones = [{'texto': '🎯 Ver mis metas', 'link': 'perfil.html'}]
            else:
                resp = "Para ver tus metas necesitas **iniciar sesión** primero."
                acciones = [{'texto': '🔑 Iniciar sesión', 'link': 'login.html'}]

        elif intencion == 'simular':
            resp = "📈 **¡Perfecto! El simulador de inversiones te permite:**\n\n"
            resp += "• Ver cuánto crecería tu dinero con CDT, fondos o acciones\n"
            resp += "• Configurar capital, tasa de retorno y plazo\n"
            resp += "• Todo sin usar dinero real — es 100% educativo\n\n"
            resp += "Haz clic en el botón para ir directo al simulador 👇"
            acciones = [{'texto': '📈 Ir al Simulador', 'link': 'simulador.html'}]

        elif intencion == 'ahorro':
            resp = self._respuesta_ahorro()
            acciones = [
                {'texto': '📊 Registrar mis gastos', 'link': 'finanzas.html'},
                {'texto': '🎯 Crear meta de ahorro', 'link': 'perfil.html'}
            ]
            if ctx and ctx.get('categoria_mayor_gasto'):
                resp += f"\n\n💡 **Consejo personalizado:** Veo que tu mayor gasto es en **{ctx['categoria_mayor_gasto']}**. Reducirlo un 20% podría ahorrarte **${ctx['monto_mayor_gasto']*0.2:,.0f}** al mes."

        elif intencion == 'inversion':
            resp = self._respuesta_inversion()
            acciones = [
                {'texto': '📈 Ir al Simulador', 'link': 'simulador.html'},
                {'texto': '💡 Ver recomendaciones', 'link': 'recomendaciones.html'}
            ]

        elif intencion == 'deuda':
            resp = self._respuesta_deuda()
            acciones = [
                {'texto': '📊 Ver mis finanzas', 'link': 'finanzas.html'},
                {'texto': '💡 Ver recomendaciones', 'link': 'recomendaciones.html'}
            ]

        elif intencion == 'presupuesto':
            resp = self._respuesta_presupuesto()
            acciones = [
                {'texto': '📊 Registrar transacciones', 'link': 'finanzas.html'},
                {'texto': '🎯 Crear metas', 'link': 'perfil.html'}
            ]

        elif intencion == 'gastos':
            resp = self._respuesta_gastos()
            if ctx and ctx.get('categoria_mayor_gasto'):
                resp += f"\n\n📌 **Tu caso:** Tu mayor gasto es en **{ctx['categoria_mayor_gasto']}** con **${ctx['monto_mayor_gasto']:,.0f}**."
            acciones = [{'texto': '📊 Ver mis gastos', 'link': 'finanzas.html'}]

        elif intencion == 'emergencia':
            resp = self._respuesta_emergencia()
            acciones = [
                {'texto': '🎯 Crear fondo de emergencia', 'link': 'perfil.html'},
                {'texto': '📈 Simular inversión', 'link': 'simulador.html'}
            ]

        elif intencion == 'meta':
            resp = self._respuesta_meta()
            acciones = [{'texto': '🎯 Crear mi meta', 'link': 'perfil.html'}]

        elif intencion == 'inflacion':
            resp = self._respuesta_inflacion()
            acciones = [{'texto': '📈 Simular inversión', 'link': 'simulador.html'}]

        elif intencion == 'impuesto':
            resp = self._respuesta_impuesto()
            acciones = []

        elif intencion == 'seguro':
            resp = self._respuesta_seguro()
            acciones = []

        elif intencion == 'pension':
            resp = self._respuesta_pension()
            acciones = [{'texto': '📈 Simular mi pensión', 'link': 'simulador.html'}]

        elif intencion == 'criptomoneda':
            resp = self._respuesta_cripto()
            acciones = [{'texto': '📈 Ver simulador', 'link': 'simulador.html'}]

        elif intencion == 'despedida':
            resp = self._respuesta_despedida()
            acciones = []

        elif intencion == 'ayuda':
            resp = self._respuesta_ayuda()
            acciones = [
                {'texto': '📊 Mis Finanzas', 'link': 'finanzas.html'},
                {'texto': '📈 Simulador', 'link': 'simulador.html'},
                {'texto': '💡 Recomendaciones', 'link': 'recomendaciones.html'}
            ]

        elif intencion == 'nombre':
            resp = f"¡Mucho gusto, **{self.nombre_usuario or 'amigo'}**! 😊 Soy FinanBot. ¿En qué te puedo ayudar?"
            acciones = []

        else:
            resp = self._respuesta_desconocido(mensaje)
            acciones = [
                {'texto': '💬 Ver temas financieros', 'link': '#'},
                {'texto': '📊 Mis Finanzas', 'link': 'finanzas.html'}
            ]

        return resp, acciones

    # ============================================
    # RESPUESTAS DETALLADAS
    # ============================================
    def _respuesta_ahorro(self):
        return """💰 **Estrategias inteligentes para ahorrar más dinero:**

**🥇 Regla del 20%**
Apenas recibas tu salario, transfiere el 20% a una cuenta de ahorros antes de gastar cualquier cosa.

**📋 Método 50/30/20**
- 50% para necesidades básicas
- 30% para gustos y ocio
- 20% para ahorro e inversión

**🎯 Trucos prácticos:**
1. Anota TODOS tus gastos durante 30 días
2. Identifica gastos hormiga (café, snacks, apps)
3. Cancela suscripciones que no usas
4. Cocina en casa al menos 4 días a la semana
5. Espera 48 horas antes de compras no planeadas

**💡 Dato:** Ahorrando $10.000 diarios acumulas $3.600.000 al año."""

    def _respuesta_inversion(self):
        return """📈 **Guía de inversiones para colombianos:**

**Bajo riesgo:**
- CDT — 8% a 12% anual, dinero seguro

**Riesgo medio:**
- Fondos de inversión colectiva
- ETFs

**Alto riesgo:**
- Acciones en la Bolsa de Colombia (BVC)

**📌 Reglas de oro:**
1. Nunca inviertas dinero que necesitas pronto
2. Diversifica — no pongas todos los huevos en una canasta
3. Invierte a largo plazo (mínimo 3-5 años)
4. Primero ten un fondo de emergencia

**💡 Para empezar:** Con $100.000 ya puedes invertir en fondos como Daviplata Inversión."""

    def _respuesta_deuda(self):
        return """💳 **Plan para salir de deudas:**

**Método Bola de Nieve ⛄**
Paga primero la deuda más pequeña para ganar motivación.

**Método Avalancha 🌊**
Paga primero la deuda con mayor tasa de interés.

**🚨 Reglas importantes:**
- No adquieras nuevas deudas mientras pagas
- Cuidado con los "gota a gota" — son ilegales
- Si tienes deudas en mora, negocia con el banco

**📞 Superfinanciera: 01 8000 120 100**"""

    def _respuesta_presupuesto(self):
        return """📋 **La regla 50/30/20:**

**50% — Necesidades** 🟢
Arriendo, alimentación, transporte, servicios, salud.

**30% — Deseos** 🟡
Entretenimiento, ropa, restaurantes, viajes.

**20% — Ahorro e inversión** 🔵
Fondo de emergencia, inversiones, pago extra de deudas.

**Ejemplo con $2.000.000:**
- Necesidades: $1.000.000
- Deseos: $600.000
- Ahorro: $400.000"""

    def _respuesta_gastos(self):
        return """📊 **Cómo controlar tus gastos:**

**🔍 Identifica tus gastos hormiga:**
- Café diario: $3.000 × 30 = $90.000/mes
- Snacks: $5.000 × 20 = $100.000/mes
- Apps y suscripciones olvidadas

**📱 Pasos:**
1. Categoriza tus gastos
2. Fija límites por categoría
3. Revisa semanalmente
4. Reduce gradualmente los no esenciales"""

    def _respuesta_emergencia(self):
        return """🚨 **Fondo de emergencia:**

**¿Cuánto necesitas?**
- Mínimo: 3 meses de gastos básicos
- Ideal: 6 meses de gastos básicos

**¿Dónde guardarlo?**
- Cuenta de ahorros de fácil acceso
- Fondo de liquidez (Daviplata, Bancolombia)
- NO en inversiones de largo plazo

**⚠️ El fondo de emergencia va ANTES que cualquier inversión.**"""

    def _respuesta_meta(self):
        return """🎯 **Método SMART para metas financieras:**

- **S**pecífica — ¿Qué exactamente quieres?
- **M**edible — ¿Cuánto dinero necesitas?
- **A**lcanzable — ¿Es realista?
- **R**elevante — ¿Por qué es importante?
- **T**iempo — ¿Para cuándo?

**Ejemplo:** "Quiero ahorrar $3.000.000 para un computador en 6 meses ahorrando $500.000/mes" """

    def _respuesta_inflacion(self):
        return """📉 **Inflación y cómo proteger tu dinero:**

Si la inflación es del 10% anual, el dinero quieto PIERDE valor.

**✅ Opciones que vencen la inflación:**
- CDT con tasas superiores a la inflación
- Fondos de inversión en renta variable
- Finca raíz

**❌ Lo que NO debes hacer:**
- Dejar el dinero en efectivo por meses
- Guardar dinero "bajo el colchón" """

    def _respuesta_impuesto(self):
        return """🧾 **Impuestos en Colombia:**

**¿Quién debe declarar renta?**
Si tus ingresos brutos superaron $57.124.000 en el año.

**💡 Beneficios tributarios:**
- Aportes voluntarios a pensión
- Intereses de crédito hipotecario
- Medicina prepagada
- Dependientes económicos

**🌐 DIAN:** www.dian.gov.co"""

    def _respuesta_seguro(self):
        return """🛡️ **Seguros importantes en Colombia:**

**Obligatorios:**
- SOAT, EPS, ARL, pensión

**Muy recomendados:**
- Seguro de vida
- Seguro de salud complementario
- Seguro de desempleo

**💡 No gastes más del 5-10% de tus ingresos en seguros.**"""

    def _respuesta_pension(self):
        return """👴 **Pensión en Colombia:**

**Colpensiones (Prima Media)**
- El Estado administra tu dinero
- Requiere 1.300 semanas cotizadas

**Fondos privados (Porvenir, Protección, Colfondos)**
- Tu dinero va a una cuenta individual
- Puedes hacer aportes voluntarios

**💡 El 75% de los colombianos NO se pensiona. La mejor pensión es la que tú mismo construyes.**"""

    def _respuesta_cripto(self):
        return """₿ **Criptomonedas — Realidades:**

- Son extremadamente volátiles
- Puedes perder TODO tu dinero
- No están reguladas en Colombia
- Las estafas son muy comunes

**✅ Si decides invertir:**
1. Solo invierte lo que puedes perder
2. Máximo el 5% de tu portafolio
3. Usa plataformas reconocidas (Binance, Coinbase)
4. No sigas consejos de grupos de WhatsApp"""

    def _respuesta_despedida(self):
        return """😊 ¡Hasta pronto!

Recuerda que una buena salud financiera se construye con pequeños hábitos diarios:

💰 Ahorra antes de gastar
📊 Registra tus gastos
🎯 Ten metas claras
📈 Haz crecer tu dinero

¡Mucho éxito! 🚀"""

    def _respuesta_ayuda(self):
        return """🤖 **Soy FinanBot — Tu asistente financiero**

Puedo ayudarte con:

💰 **Ahorro** · 📈 **Inversiones** · 💳 **Deudas**
📋 **Presupuesto** · 📊 **Gastos** · 💼 **Ingresos**
🚨 **Fondo de emergencia** · 🎯 **Metas**
📉 **Inflación** · 🧾 **Impuestos** · 👴 **Pensión**

También puedo analizar **tus datos reales** si has iniciado sesión.

¿Por dónde empezamos? 🚀"""

    def _respuesta_desconocido(self, mensaje):
        return f"""🤔 Entiendo tu pregunta sobre: *"{mensaje}"*

Como asistente financiero puedo ayudarte con:

💰 Ahorro · 📈 Inversiones · 💳 Deudas · 📋 Presupuesto
📊 Gastos · 💼 Ingresos · 🚨 Emergencias · 🎯 Metas

¿Puedes reformular tu pregunta sobre alguno de estos temas? 😊"""


def obtener_respuesta(mensaje):
    bot = FinanBotIA()
    respuesta, _ = bot.responder_con_acciones(mensaje)
    return respuesta