# routes/exportar.py
from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Transaccion, MetaAhorro, Simulacion
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from collections import defaultdict
from datetime import datetime
import io

exportar_bp = Blueprint('exportar', __name__)

# COLORES
MORADO = colors.HexColor('#a855f7')
MORADO_OSCURO = colors.HexColor('#7c3aed')
CYAN = colors.HexColor('#22d3ee')
VERDE = colors.HexColor('#4ade80')
ROJO = colors.HexColor('#f472b6')
FONDO = colors.HexColor('#1a1a4e')
GRIS = colors.HexColor('#9ca3af')
BLANCO = colors.white
NEGRO = colors.HexColor('#1f2937')

@exportar_bp.route('/pdf', methods=['GET'])
@jwt_required()
def exportar_pdf():
    usuario_id = int(get_jwt_identity())

    # Obtener datos
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    transacciones = Transaccion.query.filter_by(usuario_id=usuario_id).order_by(Transaccion.fecha.desc()).all()
    metas = MetaAhorro.query.filter_by(usuario_id=usuario_id).all()
    simulaciones = Simulacion.query.filter_by(usuario_id=usuario_id).order_by(Simulacion.fecha.desc()).limit(5).all()

    # Calcular totales
    total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
    total_gastos = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')
    balance = total_ingresos - total_gastos

    # Gastos por categoría
    gastos_cat = defaultdict(float)
    for t in transacciones:
        if t.tipo == 'gasto':
            gastos_cat[t.categoria.nombre if t.categoria else 'Otros'] += float(t.monto)

    # Recomendaciones basadas en datos
    recomendaciones = []
    if balance < 0:
        recomendaciones.append('⚠️ Tu balance es negativo. Estás gastando más de lo que ingresas.')
    elif balance > 0:
        recomendaciones.append(f'✅ Tienes un balance positivo de ${balance:,.0f}. Considera invertir el excedente.')

    if gastos_cat:
        cat_mayor = max(gastos_cat, key=gastos_cat.get)
        porcentaje = (gastos_cat[cat_mayor] / total_gastos * 100) if total_gastos > 0 else 0
        if porcentaje > 30:
            recomendaciones.append(f'📊 El {porcentaje:.0f}% de tus gastos van a {cat_mayor}. Considera reducirlo.')

    if total_ingresos > 0:
        porc_gasto = (total_gastos / total_ingresos) * 100
        if porc_gasto > 80:
            recomendaciones.append(f'⚠️ Gastas el {porc_gasto:.0f}% de tus ingresos. La regla 50/30/20 recomienda máximo 80%.')
        else:
            recomendaciones.append(f'✅ Usas el {porc_gasto:.0f}% de tus ingresos en gastos. ¡Buen control!')

    if not recomendaciones:
        recomendaciones.append('📝 Registra más transacciones para recibir recomendaciones personalizadas.')

    # Crear PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Estilos personalizados
    estilo_titulo_principal = ParagraphStyle(
        'TituloPrincipal',
        parent=styles['Title'],
        fontSize=28,
        textColor=MORADO,
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=12,
        textColor=CYAN,
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )

    estilo_info = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        textColor=GRIS,
        spaceAfter=3,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )

    estilo_seccion = ParagraphStyle(
        'Seccion',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=BLANCO,
        spaceAfter=8,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        backColor=MORADO_OSCURO,
        leftIndent=-10,
        rightIndent=-10,
        borderPadding=(8, 10, 8, 10),
    )

    estilo_normal = ParagraphStyle(
        'Normal2',
        parent=styles['Normal'],
        fontSize=10,
        textColor=NEGRO,
        spaceAfter=5,
        fontName='Helvetica'
    )

    estilo_rec = ParagraphStyle(
        'Rec',
        parent=styles['Normal'],
        fontSize=10,
        textColor=NEGRO,
        spaceAfter=8,
        leftIndent=10,
        fontName='Helvetica'
    )

    contenido = []

    # ============================================
    # ENCABEZADO
    # ============================================
    contenido.append(Paragraph('🤖 FINANBOT', estilo_titulo_principal))
    contenido.append(Paragraph('Reporte Financiero Personal', estilo_subtitulo))
    contenido.append(Paragraph(
        f'Generado el {datetime.now().strftime("%d de %B de %Y a las %H:%M")}',
        estilo_info
    ))
    contenido.append(Paragraph(f'Usuario: {usuario.nombre} | {usuario.correo}', estilo_info))
    contenido.append(Spacer(1, 0.3*cm))
    contenido.append(HRFlowable(width='100%', thickness=2, color=MORADO))
    contenido.append(Spacer(1, 0.5*cm))

    # ============================================
    # 1. RESUMEN FINANCIERO
    # ============================================
    contenido.append(Paragraph('📊  RESUMEN FINANCIERO', estilo_seccion))
    contenido.append(Spacer(1, 0.3*cm))

    resumen_data = [
        ['Concepto', 'Monto'],
        ['💰 Total Ingresos', f'${total_ingresos:,.0f}'],
        ['💸 Total Gastos', f'${total_gastos:,.0f}'],
        ['📊 Balance Actual', f'${balance:,.0f}'],
        ['🎯 Meta de ahorro mensual', f'${float(usuario.meta_ahorro or 0):,.0f}'],
        ['💼 Ingreso mensual registrado', f'${float(usuario.ingreso_mensual or 0):,.0f}'],
    ]

    tabla_resumen = Table(resumen_data, colWidths=[10*cm, 7*cm])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), MORADO),
        ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 11),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8f4ff'), BLANCO]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9d5ff')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
        # Color especial para balance
        ('TEXTCOLOR', (1,3), (1,3), VERDE if balance >= 0 else ROJO),
        ('FONTNAME', (1,3), (1,3), 'Helvetica-Bold'),
        ('FONTSIZE', (1,3), (1,3), 13),
    ]))
    contenido.append(tabla_resumen)
    contenido.append(Spacer(1, 0.5*cm))

    # ============================================
    # 2. GASTOS POR CATEGORÍA
    # ============================================
    if gastos_cat:
        contenido.append(Paragraph('📂  GASTOS POR CATEGORÍA', estilo_seccion))
        contenido.append(Spacer(1, 0.3*cm))

        cat_data = [['Categoría', 'Monto', '% del total']]
        for cat, monto in sorted(gastos_cat.items(), key=lambda x: x[1], reverse=True):
            porcentaje = (monto / total_gastos * 100) if total_gastos > 0 else 0
            cat_data.append([cat, f'${monto:,.0f}', f'{porcentaje:.1f}%'])

        tabla_cat = Table(cat_data, colWidths=[9*cm, 5*cm, 3*cm])
        tabla_cat.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), CYAN),
            ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 10),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f0fafb'), BLANCO]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#a5f3fc')),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ]))
        contenido.append(tabla_cat)
        contenido.append(Spacer(1, 0.5*cm))

    # ============================================
    # 3. TRANSACCIONES RECIENTES
    # ============================================
    if transacciones:
        contenido.append(Paragraph('💳  TRANSACCIONES RECIENTES', estilo_seccion))
        contenido.append(Spacer(1, 0.3*cm))

        trans_data = [['Fecha', 'Categoría', 'Tipo', 'Descripción', 'Monto']]
        for t in transacciones[:15]:
            trans_data.append([
                str(t.fecha),
                t.categoria.nombre if t.categoria else 'Otros',
                'Ingreso' if t.tipo == 'ingreso' else 'Gasto',
                (t.descripcion or '-')[:20],
                f'${float(t.monto):,.0f}'
            ])

        tabla_trans = Table(trans_data, colWidths=[2.5*cm, 3.5*cm, 2.5*cm, 4*cm, 3*cm])
        tabla_trans.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), MORADO_OSCURO),
            ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (4,0), (4,-1), 'RIGHT'),
            ('ALIGN', (0,0), (3,-1), 'LEFT'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#faf5ff'), BLANCO]),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e9d5ff')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))

        # Colorear filas según tipo
        for i, t in enumerate(transacciones[:15], start=1):
            color_texto = colors.HexColor('#166534') if t.tipo == 'ingreso' else colors.HexColor('#9f1239')
            tabla_trans.setStyle(TableStyle([
                ('TEXTCOLOR', (4,i), (4,i), color_texto),
                ('FONTNAME', (4,i), (4,i), 'Helvetica-Bold'),
            ]))

        contenido.append(tabla_trans)
        if len(transacciones) > 15:
            contenido.append(Paragraph(
                f'* Se muestran las 15 transacciones más recientes de {len(transacciones)} en total.',
                ParagraphStyle('nota', parent=styles['Normal'], fontSize=8, textColor=GRIS, spaceBefore=5)
            ))
        contenido.append(Spacer(1, 0.5*cm))

    # ============================================
    # 4. METAS DE AHORRO
    # ============================================
    if metas:
        contenido.append(Paragraph('🎯  METAS DE AHORRO', estilo_seccion))
        contenido.append(Spacer(1, 0.3*cm))

        metas_data = [['Meta', 'Objetivo', 'Ahorrado', 'Progreso', 'Estado']]
        for m in metas:
            porcentaje = min(round((float(m.monto_actual) / float(m.monto_objetivo)) * 100), 100) if m.monto_objetivo > 0 else 0
            estado = '✅ Completada' if m.completada else f'{porcentaje}%'
            metas_data.append([
                m.nombre,
                f'${float(m.monto_objetivo):,.0f}',
                f'${float(m.monto_actual):,.0f}',
                f'{porcentaje}%',
                estado
            ])

        tabla_metas = Table(metas_data, colWidths=[5*cm, 3.5*cm, 3.5*cm, 2.5*cm, 3*cm])
        tabla_metas.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), VERDE),
            ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 10),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f0fdf4'), BLANCO]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bbf7d0')),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        contenido.append(tabla_metas)
        contenido.append(Spacer(1, 0.5*cm))

    # ============================================
    # 5. SIMULACIONES RECIENTES
    # ============================================
    if simulaciones:
        contenido.append(Paragraph('📈  ÚLTIMAS SIMULACIONES', estilo_seccion))
        contenido.append(Spacer(1, 0.3*cm))

        sim_data = [['Fecha', 'Capital inicial', 'Tasa anual', 'Plazo', 'Resultado final', 'Ganancia']]
        for s in simulaciones:
            ganancia = float(s.resultado_final) - float(s.capital_inicial)
            sim_data.append([
                s.fecha.strftime('%d/%m/%Y'),
                f'${float(s.capital_inicial):,.0f}',
                f'{float(s.tasa_retorno)}%',
                f'{s.plazo_meses} meses',
                f'${float(s.resultado_final):,.0f}',
                f'+${ganancia:,.0f}'
            ])

        tabla_sim = Table(sim_data, colWidths=[2.5*cm, 3*cm, 2.5*cm, 2.5*cm, 3.5*cm, 3*cm])
        tabla_sim.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#fffbeb'), BLANCO]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#fde68a')),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TEXTCOLOR', (5,1), (5,-1), VERDE),
            ('FONTNAME', (5,1), (5,-1), 'Helvetica-Bold'),
        ]))
        contenido.append(tabla_sim)
        contenido.append(Spacer(1, 0.5*cm))

    # ============================================
    # 6. RECOMENDACIONES
    # ============================================
    contenido.append(Paragraph('💡  RECOMENDACIONES PERSONALIZADAS', estilo_seccion))
    contenido.append(Spacer(1, 0.3*cm))

    for rec in recomendaciones:
        contenido.append(Paragraph(rec, estilo_rec))

    contenido.append(Spacer(1, 0.5*cm))
    contenido.append(HRFlowable(width='100%', thickness=1, color=MORADO))
    contenido.append(Spacer(1, 0.3*cm))
    contenido.append(Paragraph(
        f'Reporte generado por FinanBot · {datetime.now().strftime("%d/%m/%Y %H:%M")} · Proyecto SENA Ficha 3407184',
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=8, textColor=GRIS, alignment=TA_CENTER)
    ))

    # Generar PDF
    doc.build(contenido)
    buffer.seek(0)

    nombre_archivo = f'FinanBot_Reporte_{usuario.nombre.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf'

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=nombre_archivo
    )