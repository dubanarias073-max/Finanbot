# routes/exportar.py
from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Transaccion, MetaAhorro, Simulacion
from datetime import datetime
from collections import defaultdict
import io

# ⚡ OPTIMIZACIÓN: ReportLab se importa aquí arriba para que la descarga responda de inmediato
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
except ImportError:
    # Se maneja preventivamente para que no rompa el hilo principal si falta la librería
    pass

exportar_bp = Blueprint('exportar', __name__)

# ── CATEGORÍAS SINCRONIZADAS con finanzas.html ────────────
ICONOS_CAT = {
    # GASTOS
    'Alimentación':    '🍔',
    'Transporte':      '🚌',
    'Arriendo':        '🏠',
    'Salud':           '💊',
    'Entretenimiento': '🎬',
    'Educación':       '📚',
    'Ropa':            '👗',
    'Servicios':       '⚡',
    'Mascotas':        '🐾',
    'Regalos':         '🎁',
    'Restaurantes':    '🍽️',
    'Viajes':          '✈️',
    # INGRESOS
    'Salario':         '💼',
    'Freelance':       '💻',
    'Inversión':       '📈',
    'Negocio':         '🏪',
    'Regalo':          '🎁',
    'Otros ingresos':  '💵',
}

# Emojis no son confiables en reportlab — usamos texto limpio para PDF
TEXTO_CAT = {
    'Alimentación':    'Alimentacion',
    'Transporte':      'Transporte',
    'Arriendo':        'Arriendo',
    'Salud':           'Salud',
    'Entretenimiento': 'Entretenimiento',
    'Educación':       'Educacion',
    'Ropa':            'Ropa',
    'Servicios':       'Servicios',
    'Mascotas':        'Mascotas',
    'Regalos':         'Regalos',
    'Restaurantes':    'Restaurantes',
    'Viajes':          'Viajes',
    'Salario':         'Salario',
    'Freelance':       'Freelance',
    'Inversión':       'Inversion',
    'Negocio':         'Negocio',
    'Regalo':          'Regalo',
    'Otros ingresos':  'Otros ingresos',
}

def limpiar(texto):
    """
    Elimina tildes, eñes y caracteres fuera de latin-1 básico
    para que Helvetica de reportlab los muestre sin problemas.
    """
    if not texto:
        return 'Sin categoria'
    import unicodedata
    # Normalizar y quitar diacríticos
    nfkd = unicodedata.normalize('NFKD', str(texto))
    ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Eliminar cualquier carácter que no sea imprimible ASCII estándar
    return ''.join(c for c in ascii_str if 32 <= ord(c) <= 126)

def get_texto_cat(cat):
    """Devuelve nombre limpio (sin emojis ni tildes) para usar en reportlab."""
    if not cat:
        return 'Sin categoria'
    # Primero intentar el mapeo explícito (ya limpio)
    en_mapa = TEXTO_CAT.get(cat)
    if en_mapa:
        return en_mapa
    # Si no está en el mapa, limpiar el string tal como viene
    return limpiar(cat)

def tipo_sim(tasa):
    t = float(tasa)
    if t <= 5:  return 'CDT Basico'
    if t <= 8:  return 'CDT Premium'
    if t <= 10: return 'Fondo Inversion'
    if t <= 15: return 'Acciones BVC'
    if t <= 20: return 'Startups'
    return f'Personalizada {t}%'


# ══════════════════════════════════════════════════════════
#  PDF  — tema oscuro profesional
# ══════════════════════════════════════════════════════════
@exportar_bp.route('/pdf', methods=['GET'])
@jwt_required()
def exportar_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    except ImportError:
        return jsonify({'mensaje': 'Instala reportlab: pip install reportlab'}), 500

    uid  = int(get_jwt_identity())
    user = Usuario.query.get(uid)
    if not user:
        return jsonify({'mensaje': 'Usuario no encontrado'}), 404

    trans = Transaccion.query.filter_by(usuario_id=uid).order_by(Transaccion.fecha.desc()).all()
    metas = MetaAhorro.query.filter_by(usuario_id=uid).all()
    sims  = Simulacion.query.filter_by(usuario_id=uid).order_by(Simulacion.fecha.desc()).all()

    # ── COLORES ───────────────────────────────────────────
    def rgb(r, g, b): return colors.Color(r/255, g/255, b/255)

    BG     = rgb(15,  15,  45)    # fondo página
    CARD   = rgb(26,  26,  78)    # fondo tarjeta
    CARD2  = rgb(20,  20,  60)    # fondo fila alt
    LINE   = rgb(45,  27,  105)   # bordes/líneas
    HEADER = rgb(35,  20,  80)    # cabecera tabla

    MORADO = rgb(168, 85,  247)
    CYAN   = rgb(34,  211, 238)
    VERDE  = rgb(74,  222, 128)
    ROSA   = rgb(244, 114, 182)
    AMAR   = rgb(251, 191, 36)
    BLANC  = rgb(255, 255, 255)
    GRIS   = rgb(196, 181, 253)   # texto secundario (violeta claro)
    MUTED  = rgb(107, 114, 128)

    # ── ESTILOS ───────────────────────────────────────────
    def st(nm, **kw):
        base = {'fontName': 'Helvetica', 'textColor': BLANC, 'leading': 14}
        base.update(kw)
        return ParagraphStyle(nm, **base)

    S_TITULO  = st('titulo',  fontSize=22, fontName='Helvetica-Bold', textColor=MORADO, leading=26)
    S_SUBTIT  = st('subtit',  fontSize=11, textColor=GRIS, leading=13)
    S_SEC     = st('sec',     fontSize=12, fontName='Helvetica-Bold', textColor=CYAN, spaceAfter=4, leading=16)
    S_SUBSEC  = st('subsec',  fontSize=10, fontName='Helvetica-Bold', textColor=GRIS, spaceAfter=3, leading=13)
    S_TH      = st('th',      fontSize=8,  fontName='Helvetica-Bold', textColor=BLANC, alignment=TA_CENTER, leading=11)
    S_THL     = st('thl',     fontSize=8,  fontName='Helvetica-Bold', textColor=BLANC, alignment=TA_LEFT,   leading=11)
    S_TC      = st('tc',      fontSize=8,  textColor=BLANC,           alignment=TA_LEFT,   leading=11)
    S_TCC     = st('tcc',     fontSize=8,  textColor=BLANC,           alignment=TA_CENTER, leading=11)
    S_LABEL   = st('lbl',     fontSize=8,  textColor=GRIS,  leading=11)
    S_VAL     = st('val',     fontSize=14, fontName='Helvetica-Bold', textColor=BLANC, leading=17)
    S_FOOT    = st('ft',      fontSize=7,  textColor=MUTED, alignment=TA_CENTER)
    S_BADGE_G = st('bg',      fontSize=8,  fontName='Helvetica-Bold', textColor=VERDE,  alignment=TA_CENTER)
    S_BADGE_R = st('br',      fontSize=8,  fontName='Helvetica-Bold', textColor=ROSA,   alignment=TA_CENTER)
    S_BADGE_A = st('ba',      fontSize=8,  fontName='Helvetica-Bold', textColor=AMAR,   alignment=TA_CENTER)
    S_BADGE_C = st('bc',      fontSize=8,  fontName='Helvetica-Bold', textColor=CYAN,   alignment=TA_CENTER)

    # ── MÉTRICAS ──────────────────────────────────────────
    ingresos_t = sum(float(t.monto) for t in trans if t.tipo == 'ingreso')
    gastos_t   = sum(float(t.monto) for t in trans if t.tipo == 'gasto')
    balance    = ingresos_t - gastos_t
    ahorrado   = sum(float(m.monto_actual)   for m in metas)
    obj_total  = sum(float(m.monto_objetivo) for m in metas)
    pct_g      = round(gastos_t / ingresos_t * 100) if ingresos_t > 0 else 0
    ing_mens   = float(user.ingreso_mensual or 0)
    meta_mens  = float(user.meta_ahorro     or 0)

    def extraer_cat(t):
        """Extrae la categoría como string limpio, sea ORM u objeto."""
        c = t.categoria
        if c is None:
            return 'Sin categoria'
        # Si es string directo (guardado así en BD)
        if isinstance(c, str):
            return get_texto_cat(c)
        # Si es objeto ORM con atributo .nombre
        nombre = getattr(c, 'nombre', None)
        if nombre:
            return get_texto_cat(nombre)
        return limpiar(str(c))

    gastos_cat   = defaultdict(float)
    ingresos_cat = defaultdict(float)
    for t in trans:
        cat = extraer_cat(t)
        if t.tipo == 'gasto':   gastos_cat[cat]   += float(t.monto)
        else:                    ingresos_cat[cat] += float(t.monto)

    cat_mayor       = max(gastos_cat, key=gastos_cat.get) if gastos_cat else None
    monto_cat_mayor = gastos_cat[cat_mayor] if cat_mayor else 0

    # ── HELPERS ───────────────────────────────────────────
    buf = io.BytesIO()
    W   = A4[0] - 40 * mm
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm,  bottomMargin=20*mm,
    )

    def mk_tabla(hdrs, filas, cws, extra_styles=None):
        """Crea tabla con estilo oscuro estándar."""
        cabecera = [Paragraph(h, S_TH) for h in hdrs]
        data = [cabecera] + filas
        ts = TableStyle([
            ('BACKGROUND',    (0, 0), (-1,  0), HEADER),
            ('BACKGROUND',    (0, 1), (-1, -1), CARD),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [CARD, CARD2]),
            ('GRID',          (0, 0), (-1, -1), 0.4, LINE),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW',     (0, 0), (-1,  0), 1.5, MORADO),
        ])
        if extra_styles:
            for s in extra_styles:
                ts.add(*s)
        t = Table(data, colWidths=cws, repeatRows=1)
        t.setStyle(ts)
        return t

    def barra_progreso(pct, color=MORADO):
        """Devuelve texto visual de barra de progreso."""
        filled = int(pct / 5)
        empty  = 20 - filled
        return '|' * filled + '.' * empty + f'  {pct}%'

    def badge_estado(ok_text, warn_text, ok, warn=False):
        if ok:   return Paragraph(ok_text,   S_BADGE_G)
        if warn: return Paragraph(warn_text,  S_BADGE_A)
        return Paragraph(warn_text, S_BADGE_R)

    story = []

       # ══════════════════════════════════════════════════════
    #  ENCABEZADO (Modificado)
    # ══════════════════════════════════════════════════════
    fecha_str  = datetime.now().strftime('%d/%m/%Y  %H:%M')
    nombre_pdf = limpiar(user.nombre)
    correo_pdf = limpiar(user.correo)

    # 1. Creamos la tabla interna con 4 filas individuales en vez de una sola celda
    tabla_detalles = Table([
        [Paragraph(f'<b>{nombre_pdf}</b>', st('un', fontSize=11, textColor=BLANC, fontName='Helvetica-Bold'))],
        [Paragraph(correo_pdf,              st('uc', fontSize=9,  textColor=GRIS ))],
        [Paragraph(fecha_str,                st('ud', fontSize=9,  textColor=MUTED))],
        [Paragraph('Reporte Financiero Personal', st('ur', fontSize=8, textColor=MORADO))],
    ], colWidths=[W * 0.6])

    # 2. Le quitamos los márgenes por defecto a la tabla interna para que se pegue a la izquierda
    tabla_detalles.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 0), # Quita el espacio izquierdo por completo
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 1), # Controla la separación vertical entre líneas
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1),
    ]))

    # 3. Tu tabla principal se queda exactamente igual, pero llamando a la nueva 'tabla_detalles'
    hd = Table([[
        Paragraph('FinanBot', S_TITULO),
        tabla_detalles # Insertamos la tabla interna ya corregida
    ]], colWidths=[W * 0.4, W * 0.6])

    hd.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), CARD),
        ('TOPPADDING',   (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 14),
        ('LEFTPADDING',  (0, 0), (-1, -1), 18),
        ('RIGHTPADDING', (0, 0), (-1, -1), 18),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW',    (0, 0), (-1, -1), 2, MORADO),
        ('LINEABOVE',    (0, 0), (-1,  0), 3, CYAN),
    ]))
    story.append(hd)
    story.append(Spacer(1, 16))

    # ══════════════════════════════════════════════════════
    #  TARJETAS DE RESUMEN (4 métricas)
    # ══════════════════════════════════════════════════════
    story.append(Paragraph('Resumen financiero', S_SEC))
    story.append(Spacer(1, 6))

    def tarjeta(label, valor, color, sub=''):
        content = [
            [Paragraph(label, S_LABEL)],
            [Paragraph(valor, st('tv', fontSize=16, fontName='Helvetica-Bold', textColor=color, leading=19))],
        ]
        if sub:
            content.append([Paragraph(sub, st('ts', fontSize=7, textColor=MUTED, leading=10))])
        inn = Table(content, colWidths=[W / 4 - 10])
        inn.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, -1), CARD),
            ('TOPPADDING',   (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
            ('LEFTPADDING',  (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('LINEABOVE',    (0, 0), (-1,  0), 3, color),
        ]))
        return inn

    bal_col  = VERDE if balance >= 0 else ROSA
    bal_sub  = 'Balance positivo' if balance >= 0 else 'Balance negativo'
    meta_sub = f'{round(ahorrado/obj_total*100)}% de {f"${obj_total:,.0f}"}' if obj_total > 0 else 'Sin metas'

    tarjetas = Table([[
        tarjeta('INGRESOS TOTALES', f'${ingresos_t:,.0f}', CYAN,   f'{len([t for t in trans if t.tipo=="ingreso"])} registros'),
        tarjeta('GASTOS TOTALES',   f'${gastos_t:,.0f}',   MORADO, f'{len([t for t in trans if t.tipo=="gasto"])} registros'),
        tarjeta('BALANCE ACTUAL',   f'${balance:,.0f}',    bal_col, bal_sub),
        tarjeta('TOTAL AHORRADO',   f'${ahorrado:,.0f}',   AMAR,   meta_sub),
    ]], colWidths=[W / 4 - 4] * 4, hAlign='LEFT')
    tarjetas.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(tarjetas)
    story.append(Spacer(1, 18))

    # ══════════════════════════════════════════════════════
    #  ANÁLISIS FINANCIERO
    # ══════════════════════════════════════════════════════
    if ingresos_t > 0:
        story.append(Paragraph('Analisis financiero', S_SEC))
        story.append(Spacer(1, 6))

        filas_af = []

        # % gastos
        pct_col   = VERDE if pct_g < 70 else AMAR if pct_g < 90 else ROSA
        estado_pct = 'Excelente (<70%)' if pct_g < 70 else 'Ajustado (70-90%)' if pct_g < 90 else 'Critico (>90%)'
        filas_af.append([
            Paragraph('Gastos sobre ingresos', S_TC),
            Paragraph(f'{pct_g}%', st('v2', fontSize=9, fontName='Helvetica-Bold', textColor=pct_col, alignment=TA_CENTER)),
            Paragraph(barra_progreso(pct_g, pct_col), st('bar', fontSize=7, textColor=pct_col, fontName='Courier')),
            Paragraph(estado_pct, st('e', fontSize=8, textColor=pct_col, alignment=TA_CENTER)),
        ])

        # Categoría mayor
        if cat_mayor and gastos_t > 0:
            pm = round(monto_cat_mayor / gastos_t * 100)
            filas_af.append([
                Paragraph(f'Mayor categoria de gasto', S_TC),
                Paragraph(f'{pm}%', st('v2', fontSize=9, fontName='Helvetica-Bold',
                          textColor=ROSA if pm > 40 else AMAR, alignment=TA_CENTER)),
                Paragraph(cat_mayor, st('cm', fontSize=8, textColor=BLANC)),
                Paragraph(f'${monto_cat_mayor:,.0f} de ${gastos_t:,.0f} totales',
                          st('cs', fontSize=8, textColor=GRIS, alignment=TA_CENTER)),
            ])

        # Ingreso mensual registrado
        if ing_mens > 0:
            filas_af.append([
                Paragraph('Ingreso mensual (perfil)', S_TC),
                Paragraph(f'${ing_mens:,.0f}', st('v2', fontSize=9, fontName='Helvetica-Bold', textColor=CYAN, alignment=TA_CENTER)),
                Paragraph(f'50% necesidades: ${ing_mens*0.5:,.0f}', st('r5', fontSize=8, textColor=GRIS)),
                Paragraph(f'20% ahorro ideal: ${ing_mens*0.2:,.0f}', st('r2', fontSize=8, textColor=VERDE, alignment=TA_CENTER)),
            ])

        # Meta de ahorro mensual
        if meta_mens > 0:
            ahorro_real = max(0, balance)
            cumple      = ahorro_real >= meta_mens
            brecha      = max(0, meta_mens - ahorro_real)
            filas_af.append([
                Paragraph('Meta de ahorro mensual', S_TC),
                Paragraph(f'${meta_mens:,.0f}', st('v2', fontSize=9, fontName='Helvetica-Bold', textColor=AMAR, alignment=TA_CENTER)),
                Paragraph(f'Actual: ${ahorro_real:,.0f}', st('ma', fontSize=8, textColor=GRIS)),
                Paragraph('Cumplida' if cumple else f'Brecha: ${brecha:,.0f}',
                          st('ms', fontSize=8, textColor=VERDE if cumple else ROSA, alignment=TA_CENTER)),
            ])

        # Fondo de emergencia
        base_fondo = ing_mens if ing_mens > 0 else (ingresos_t / max(1, len(set(
            t.fecha.month for t in trans if t.fecha
        ))))
        fondo_obj  = base_fondo * 3
        pct_fondo  = min(100, round(max(0, balance) / fondo_obj * 100)) if fondo_obj > 0 else 0
        filas_af.append([
            Paragraph('Fondo de emergencia (3 meses)', S_TC),
            Paragraph(f'{pct_fondo}%', st('v2', fontSize=9, fontName='Helvetica-Bold',
                      textColor=VERDE if pct_fondo >= 100 else AMAR if pct_fondo >= 50 else ROSA, alignment=TA_CENTER)),
            Paragraph(barra_progreso(pct_fondo), st('bar2', fontSize=7, textColor=CYAN, fontName='Courier')),
            Paragraph(f'Meta: ${fondo_obj:,.0f}',
                      st('fobj', fontSize=8, textColor=VERDE if pct_fondo >= 100 else GRIS, alignment=TA_CENTER)),
        ])

        story.append(mk_tabla(
            ['Indicador', '%  / Valor', 'Detalle', 'Estado'],
            filas_af,
            [W*0.30, W*0.15, W*0.32, W*0.23]
        ))
        story.append(Spacer(1, 18))

    # ══════════════════════════════════════════════════════
    #  GASTOS POR CATEGORÍA
    # ══════════════════════════════════════════════════════
    if gastos_cat:
        story.append(Paragraph('Gastos por categoria', S_SEC))
        story.append(Spacer(1, 6))

        filas_cat = []
        for cat, monto in sorted(gastos_cat.items(), key=lambda x: x[1], reverse=True):
            pm     = round(monto / gastos_t * 100) if gastos_t > 0 else 0
            col    = ROSA if pm > 40 else AMAR if pm > 25 else VERDE
            barra  = barra_progreso(pm, col)
            filas_cat.append([
                Paragraph(cat, S_TC),
                Paragraph(f'${monto:,.0f}', st('mc', fontSize=8, textColor=BLANC, alignment=TA_CENTER)),
                Paragraph(f'{pm}%', st('pc', fontSize=8, fontName='Helvetica-Bold', textColor=col, alignment=TA_CENTER)),
                Paragraph(barra, st('bc', fontSize=7, textColor=col, fontName='Courier')),
            ])

        story.append(mk_tabla(
            ['Categoria', 'Monto', '%', 'Distribucion'],
            filas_cat,
            [W*0.28, W*0.18, W*0.10, W*0.44]
        ))
        story.append(Spacer(1, 18))

    # ══════════════════════════════════════════════════════
    #  HISTORIAL DE TRANSACCIONES
    # ══════════════════════════════════════════════════════
    if trans:
        story.append(Paragraph('Historial de transacciones', S_SEC))
        story.append(Spacer(1, 6))

        filas_tr  = []
        estilos_tr = []
        for i, t in enumerate(trans, 1):
            col_tipo = VERDE if t.tipo == 'ingreso' else ROSA
            sgn      = '+' if t.tipo == 'ingreso' else '-'
            fd       = t.fecha.strftime('%d/%m/%Y') if t.fecha else '---'
            cat_txt  = extraer_cat(t)

            filas_tr.append([
                Paragraph(str(i),               st('fn', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
                Paragraph(fd,                   S_TCC),
                Paragraph(t.tipo.capitalize(),  st('ft2', fontSize=8, textColor=col_tipo, alignment=TA_CENTER, fontName='Helvetica-Bold')),
                Paragraph(cat_txt,              S_TC),
                Paragraph(limpiar(t.descripcion) if t.descripcion else '---', st('fd', fontSize=8, textColor=GRIS)),
                Paragraph(f'{sgn}${float(t.monto):,.0f}',
                           st('fm', fontSize=8, fontName='Helvetica-Bold', textColor=col_tipo, alignment=TA_RIGHT)),
            ])

        story.append(mk_tabla(
            ['#', 'Fecha', 'Tipo', 'Categoria', 'Descripcion', 'Monto'],
            filas_tr,
            [W*0.04, W*0.11, W*0.09, W*0.20, W*0.36, W*0.20]
        ))
        story.append(Spacer(1, 18))

    # ══════════════════════════════════════════════════════
    #  METAS DE AHORRO
    # ══════════════════════════════════════════════════════
    if metas:
        story.append(Paragraph('Metas de ahorro', S_SEC))
        story.append(Spacer(1, 6))

        # Mini resumen
        comp     = len([m for m in metas if m.completada])
        activas  = len(metas) - comp
        res_data = [[
            Paragraph(f'{len(metas)} metas totales', st('mr', fontSize=9, textColor=BLANC)),
            Paragraph(f'{comp} completadas',         st('mc2', fontSize=9, textColor=VERDE, fontName='Helvetica-Bold')),
            Paragraph(f'{activas} en progreso',      st('ma2', fontSize=9, textColor=AMAR, fontName='Helvetica-Bold')),
            Paragraph(f'${ahorrado:,.0f} ahorrados', st('ms2', fontSize=9, textColor=CYAN, fontName='Helvetica-Bold')),
        ]]
        res_t = Table(res_data, colWidths=[W/4]*4)
        res_t.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, -1), CARD),
            ('TOPPADDING',   (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
            ('LEFTPADDING',  (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('GRID',         (0, 0), (-1, -1), 0.4, LINE),
            ('LINEABOVE',    (0, 0), (-1,  0), 2, AMAR),
        ]))
        story.append(res_t)
        story.append(Spacer(1, 8))

        filas_mt = []
        for i, m in enumerate(metas, 1):
            pct_m  = round(float(m.monto_actual) / float(m.monto_objetivo) * 100, 1) if m.monto_objetivo else 0
            flt    = max(0, float(m.monto_objetivo) - float(m.monto_actual))
            fl     = m.fecha_limite.strftime('%d/%m/%Y') if m.fecha_limite else '---'
            col_m  = VERDE if m.completada else AMAR if pct_m >= 50 else ROSA
            barra  = barra_progreso(int(pct_m), col_m)

            filas_mt.append([
                Paragraph(str(i),                                 st('mi', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
                Paragraph(limpiar(m.nombre),                      S_TC),
                Paragraph(f'${float(m.monto_actual):,.0f}',      st('mav', fontSize=8, textColor=VERDE,  alignment=TA_CENTER)),
                Paragraph(f'${float(m.monto_objetivo):,.0f}',    st('mob', fontSize=8, textColor=BLANC,  alignment=TA_CENTER)),
                Paragraph(f'${flt:,.0f}',                        st('mfl', fontSize=8, textColor=ROSA if flt>0 else VERDE, alignment=TA_CENTER)),
                Paragraph(barra,                                  st('mpb', fontSize=7, textColor=col_m, fontName='Courier')),
                Paragraph('Completa' if m.completada else 'En progreso',
                           st('mes', fontSize=8, fontName='Helvetica-Bold',
                              textColor=VERDE if m.completada else AMAR, alignment=TA_CENTER)),
                Paragraph(fl,                                     st('mfl2', fontSize=8, textColor=GRIS, alignment=TA_CENTER)),
            ])

        story.append(mk_tabla(
            ['#', 'Meta', 'Ahorrado', 'Objetivo', 'Faltante', 'Progreso', 'Estado', 'Limite'],
            filas_mt,
            [W*0.04, W*0.22, W*0.11, W*0.11, W*0.10, W*0.22, W*0.11, W*0.09]
        ))
        story.append(Spacer(1, 18))

    # ══════════════════════════════════════════════════════
    #  SIMULACIONES
    # ══════════════════════════════════════════════════════
    if sims:
        story.append(Paragraph('Simulaciones de inversion', S_SEC))
        story.append(Spacer(1, 6))

        filas_sim = []
        for i, s in enumerate(sims, 1):
            cap   = float(s.capital_inicial)
            res   = float(s.resultado_final)
            gan   = res - cap
            # Retención 4% sobre ganancia (Colombia)
            ret   = round(max(gan, 0) * 0.04)
            neto  = res - ret
            pctg  = round(gan / cap * 100, 1) if cap else 0
            fd    = s.fecha.strftime('%d/%m/%Y') if s.fecha else '---'

            filas_sim.append([
                Paragraph(str(i),          st('si', fontSize=8, textColor=MUTED, alignment=TA_CENTER)),
                Paragraph(fd,              S_TCC),
                Paragraph(tipo_sim(s.tasa_retorno), S_TC),
                Paragraph(f'${cap:,.0f}',  st('sc', fontSize=8, textColor=BLANC, alignment=TA_CENTER)),
                Paragraph(f'{s.tasa_retorno}%', st('st', fontSize=8, textColor=AMAR, alignment=TA_CENTER)),
                Paragraph(f'{s.plazo_meses}m', st('sp', fontSize=8, textColor=GRIS, alignment=TA_CENTER)),
                Paragraph(f'${res:,.0f}',  st('sr', fontSize=8, textColor=CYAN, alignment=TA_CENTER, fontName='Helvetica-Bold')),
                Paragraph(f'+${gan:,.0f}', st('sg', fontSize=8, textColor=VERDE, alignment=TA_CENTER, fontName='Helvetica-Bold')),
                Paragraph(f'{pctg}%',      st('spct', fontSize=8, textColor=MORADO, alignment=TA_CENTER)),
                Paragraph(f'${neto:,.0f}', st('sn', fontSize=8, textColor=BLANC, alignment=TA_CENTER)),
            ])

        story.append(mk_tabla(
            ['#', 'Fecha', 'Tipo', 'Capital', 'Tasa', 'Plazo', 'Resultado', 'Ganancia', 'Rendim.', 'Neto'],
            filas_sim,
            [W*0.04, W*0.09, W*0.13, W*0.11, W*0.06, W*0.06, W*0.11, W*0.10, W*0.08, W*0.22]
        ))
        story.append(Spacer(1, 14))

    # ── PIE DE PÁGINA ─────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=LINE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'FinanBot  |  {nombre_pdf}  |  {fecha_str}  |  Documento confidencial',
        S_FOOT
    ))

    # ── FONDO OSCURO EN CADA PÁGINA ───────────────────────
    def fondo_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        # Barra superior morado → cyan
        canvas.setFillColor(MORADO)
        canvas.rect(0, A4[1] - 5, A4[0] * 0.5, 5, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.rect(A4[0] * 0.5, A4[1] - 5, A4[0] * 0.5, 5, fill=1, stroke=0)
        # Número de página
        canvas.setFillColor(MUTED)
        canvas.setFont('Helvetica', 7)
        canvas.drawRightString(A4[0] - 20*mm, 12*mm, f'Pag. {doc.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=fondo_pagina, onLaterPages=fondo_pagina)
    buf.seek(0)

    nombre_archivo = (
        f'FinanBot_{nombre_pdf.replace(" ", "_")}'
        f'_{datetime.now().strftime("%d-%m-%Y")}.pdf'
    )
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=nombre_archivo)