# routes/excel.py
from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Transaccion, MetaAhorro, Simulacion
from extensions import db
from datetime import datetime
import io

excel_bp = Blueprint('excel', __name__)

@excel_bp.route('/excel', methods=['GET'])
@jwt_required()
def exportar_excel():
    try:
        import openpyxl
        from openpyxl.styles import (
            PatternFill, Font, Alignment, Border, Side, GradientFill
        )
        from openpyxl.chart import BarChart, PieChart, LineChart, Reference
        from openpyxl.chart.series import DataPoint
        from openpyxl.utils import get_column_letter
    except ImportError:
        return jsonify({'mensaje': 'Instala openpyxl: pip install openpyxl'}), 500

    usuario_id = int(get_jwt_identity())
    usuario    = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'mensaje': 'Usuario no encontrado'}), 404

    transacciones = Transaccion.query.filter_by(usuario_id=usuario_id)\
                               .order_by(Transaccion.fecha.desc()).all()
    metas         = MetaAhorro.query.filter_by(usuario_id=usuario_id).all()
    simulaciones  = Simulacion.query.filter_by(usuario_id=usuario_id)\
                               .order_by(Simulacion.fecha.desc()).all()

    wb = openpyxl.Workbook()

    # ── Paleta ──────────────────────────────────────────────
    MORADO      = 'C026D3'
    MORADO_OSC  = '7E22CE'
    CYAN        = '22D3EE'
    VERDE       = '4ADE80'
    ROSA        = 'F472B6'
    FONDO_OSC   = '0F0F2D'
    FONDO_CARD  = '1A1A4E'
    BLANCO      = 'FFFFFF'
    GRIS        = '9CA3AF'
    AMARILLO    = 'FCD34D'
    ROJO        = 'EF4444'

    def fill(hex_color):
        return PatternFill('solid', fgColor=hex_color)

    def font(hex_color=BLANCO, bold=False, size=11, italic=False):
        return Font(color=hex_color, bold=bold, size=size, italic=italic,
                    name='Segoe UI')

    def center():
        return Alignment(horizontal='center', vertical='center', wrap_text=True)

    def left():
        return Alignment(horizontal='left', vertical='center', wrap_text=True)

    def border_thin(color='4C1D95'):
        s = Side(style='thin', color=color)
        return Border(left=s, right=s, top=s, bottom=s)

    def set_col_width(ws, col, width):
        ws.column_dimensions[get_column_letter(col)].width = width

    def header_row(ws, row, cols, bg=MORADO_OSC, fg=BLANCO, size=11):
        for col, txt in enumerate(cols, 1):
            c = ws.cell(row=row, column=col, value=txt)
            c.fill      = fill(bg)
            c.font      = font(fg, bold=True, size=size)
            c.alignment = center()
            c.border    = border_thin()

    def data_cell(ws, row, col, val, bg=FONDO_CARD, fg=BLANCO,
                  bold=False, align='center', size=10):
        c = ws.cell(row=row, column=col, value=val)
        c.fill      = fill(bg)
        c.font      = font(fg, bold=bold, size=size)
        c.alignment = center() if align == 'center' else left()
        c.border    = border_thin('2D1B69')
        return c

    def titulo_hoja(ws, texto, subtexto='', span=8):
        ws.row_dimensions[1].height = 45
        ws.row_dimensions[2].height = 22
        ws.merge_cells(f'A1:{get_column_letter(span)}1')
        c = ws['A1']
        c.value     = texto
        c.fill      = fill(MORADO)
        c.font      = font(BLANCO, bold=True, size=18)
        c.alignment = center()

        if subtexto:
            ws.merge_cells(f'A2:{get_column_letter(span)}2')
            s = ws['A2']
            s.value     = subtexto
            s.fill      = fill(MORADO_OSC)
            s.font      = font(GRIS, size=10, italic=True)
            s.alignment = center()

    # ════════════════════════════════════════════
    # HOJA 1 — RESUMEN GENERAL
    # ════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = '📊 Resumen'
    ws1.sheet_view.showGridLines = False
    ws1.sheet_properties.tabColor = MORADO

    # Fondo general
    for row in ws1.iter_rows(min_row=1, max_row=50, min_col=1, max_col=10):
        for cell in row:
            cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws1, '📊 FinanBot — Reporte Financiero',
                f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")} | Usuario: {usuario.nombre}', 8)

    # Estadísticas
    ingresos_total = sum(t.monto for t in transacciones if t.tipo == 'ingreso')
    gastos_total   = sum(t.monto for t in transacciones if t.tipo == 'gasto')
    balance        = ingresos_total - gastos_total
    ahorrado_total = sum(m.monto_actual for m in metas)

    stats = [
        ('💰 Ingresos totales',  f'${ingresos_total:,.0f}', VERDE),
        ('💸 Gastos totales',    f'${gastos_total:,.0f}',   ROSA),
        ('📈 Balance actual',    f'${balance:,.0f}',        CYAN if balance >= 0 else ROJO),
        ('🎯 Ahorro en metas',   f'${ahorrado_total:,.0f}', AMARILLO),
        ('📋 Transacciones',     str(len(transacciones)),   MORADO),
        ('🎯 Metas activas',     str(len(metas)),           VERDE),
        ('📈 Simulaciones',      str(len(simulaciones)),    CYAN),
    ]

    ws1.row_dimensions[4].height = 20
    ws1.merge_cells('A4:H4')
    t4 = ws1['A4']
    t4.value     = '  MÉTRICAS PRINCIPALES'
    t4.fill      = fill(MORADO_OSC)
    t4.font      = font(BLANCO, bold=True, size=12)
    t4.alignment = left()

    for i, (label, valor, color) in enumerate(stats, 5):
        ws1.row_dimensions[i].height = 28
        # Etiqueta
        c1 = ws1.cell(row=i, column=1, value=label)
        c1.fill      = fill('1A1A4E')
        c1.font      = font(GRIS, size=10)
        c1.alignment = left()
        c1.border    = border_thin()
        ws1.merge_cells(f'A{i}:D{i}')

        # Valor
        c2 = ws1.cell(row=i, column=5, value=valor)
        c2.fill      = fill('2D1B69')
        c2.font      = font(color, bold=True, size=13)
        c2.alignment = center()
        c2.border    = border_thin()
        ws1.merge_cells(f'E{i}:H{i}')

    # Columnas
    for col, w in enumerate([14,14,14,14,14,14,14,14], 1):
        set_col_width(ws1, col, w)

    # Gráfico de barras ingresos vs gastos
    if transacciones:
        # Datos auxiliares para el gráfico (columnas J-K)
        ws1['J1'] = 'Categoría'
        ws1['K1'] = 'Monto'
        ws1['J1'].font = font(BLANCO, bold=True)
        ws1['K1'].font = font(BLANCO, bold=True)

        cat_gastos = {}
        for t in transacciones:
            if t.tipo == 'gasto':
                cat = t.categoria or 'Otros'
                cat_gastos[cat] = cat_gastos.get(cat, 0) + t.monto

        fila_g = 2
        for cat, monto in sorted(cat_gastos.items(), key=lambda x: x[1], reverse=True)[:8]:
            ws1[f'J{fila_g}'] = cat
            ws1[f'K{fila_g}'] = round(monto, 2)
            ws1[f'J{fila_g}'].fill = fill(FONDO_CARD)
            ws1[f'K{fila_g}'].fill = fill(FONDO_CARD)
            ws1[f'J{fila_g}'].font = font(BLANCO)
            ws1[f'K{fila_g}'].font = font(BLANCO)
            fila_g += 1

        if fila_g > 2:
            bar = BarChart()
            bar.type    = 'col'
            bar.title   = 'Gastos por Categoría'
            bar.style   = 10
            bar.y_axis.title = 'Monto ($)'
            bar.x_axis.title = 'Categoría'
            bar.width   = 22
            bar.height  = 14

            data_ref  = Reference(ws1, min_col=11, min_row=1, max_row=fila_g-1)
            cats_ref  = Reference(ws1, min_col=10, min_row=2, max_row=fila_g-1)
            bar.add_data(data_ref, titles_from_data=True)
            bar.set_categories(cats_ref)
            bar.series[0].graphicalProperties.solidFill = MORADO
            ws1.add_chart(bar, 'A14')

    # ════════════════════════════════════════════
    # HOJA 2 — TRANSACCIONES
    # ════════════════════════════════════════════
    ws2 = wb.create_sheet('💳 Transacciones')
    ws2.sheet_view.showGridLines = False
    ws2.sheet_properties.tabColor = CYAN

    for row in ws2.iter_rows(min_row=1, max_row=len(transacciones)+10, min_col=1, max_col=7):
        for cell in row:
            cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws2, '💳 Historial de Transacciones',
                f'{len(transacciones)} registros | {usuario.nombre}', 7)

    # Filtro rápido (fila 4)
    ws2.row_dimensions[4].height = 18
    resumen_txt = (f'  ✅ Ingresos: ${ingresos_total:,.0f}   |   '
                   f'💸 Gastos: ${gastos_total:,.0f}   |   '
                   f'📊 Balance: ${balance:,.0f}')
    ws2.merge_cells('A4:G4')
    r4 = ws2['A4']
    r4.value     = resumen_txt
    r4.fill      = fill('2D1B69')
    r4.font      = font(CYAN, bold=True, size=10)
    r4.alignment = center()

    cols = ['#', 'Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto ($)', 'Estado']
    header_row(ws2, 5, cols, bg=MORADO_OSC)
    ws2.row_dimensions[5].height = 22

    widths2 = [5, 14, 11, 18, 30, 15, 12]
    for i, w in enumerate(widths2, 1):
        set_col_width(ws2, i, w)

    for idx, t in enumerate(transacciones, 1):
        r = idx + 5
        ws2.row_dimensions[r].height = 20
        bg_row = FONDO_CARD if idx % 2 == 0 else '1E1B4B'
        col_tipo = VERDE if t.tipo == 'ingreso' else ROSA

        data_cell(ws2, r, 1, idx,                                   bg_row, GRIS)
        data_cell(ws2, r, 2, t.fecha.strftime('%d/%m/%Y') if t.fecha else '', bg_row, GRIS)
        data_cell(ws2, r, 3, t.tipo.capitalize(),                    bg_row, col_tipo, bold=True)
        data_cell(ws2, r, 4, t.categoria or '—',                    bg_row, BLANCO, align='left')
        data_cell(ws2, r, 5, t.descripcion or '—',                  bg_row, GRIS, align='left')
        monto_txt = f'+${t.monto:,.2f}' if t.tipo == 'ingreso' else f'-${t.monto:,.2f}'
        data_cell(ws2, r, 6, monto_txt,                              bg_row, col_tipo, bold=True)
        data_cell(ws2, r, 7, '✅ OK',                                bg_row, VERDE)

    # Gráfico de torta — distribución de gastos
    if cat_gastos and fila_g > 2:
        # Copiar datos a columnas I-J de ws2
        ws2['I1'] = 'Categoría'; ws2['J1'] = 'Monto'
        fila_p = 2
        for cat, monto in sorted(cat_gastos.items(), key=lambda x: x[1], reverse=True)[:6]:
            ws2[f'I{fila_p}'] = cat
            ws2[f'J{fila_p}'] = round(monto, 2)
            ws2[f'I{fila_p}'].fill = fill(FONDO_CARD)
            ws2[f'J{fila_p}'].fill = fill(FONDO_CARD)
            fila_p += 1

        pie = PieChart()
        pie.title  = 'Distribución de Gastos'
        pie.style  = 10
        pie.width  = 18
        pie.height = 13

        pie_data = Reference(ws2, min_col=10, min_row=1, max_row=fila_p-1)
        pie_cats = Reference(ws2, min_col=9,  min_row=2, max_row=fila_p-1)
        pie.add_data(pie_data, titles_from_data=True)
        pie.set_categories(pie_cats)
        pie.dataLabels              = openpyxl.chart.label.DataLabelList()
        pie.dataLabels.showPercent  = True
        ws2.add_chart(pie, f'A{len(transacciones)+8}')

    ws2.auto_filter.ref = f'A5:G5'

    # ════════════════════════════════════════════
    # HOJA 3 — METAS DE AHORRO
    # ════════════════════════════════════════════
    ws3 = wb.create_sheet('🎯 Metas')
    ws3.sheet_view.showGridLines = False
    ws3.sheet_properties.tabColor = VERDE

    for row in ws3.iter_rows(min_row=1, max_row=len(metas)+15, min_col=1, max_col=8):
        for cell in row:
            cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws3, '🎯 Metas de Ahorro', f'{len(metas)} metas | {usuario.nombre}', 8)

    cols3 = ['Meta', 'Categoría', 'Ahorrado ($)', 'Objetivo ($)', 'Faltante ($)', 'Progreso', 'Estado', 'Fecha límite']
    header_row(ws3, 4, cols3, bg='065F46')
    ws3.row_dimensions[4].height = 22

    widths3 = [28, 15, 16, 16, 16, 12, 14, 16]
    for i, w in enumerate(widths3, 1):
        set_col_width(ws3, i, w)

    for idx, m in enumerate(metas, 1):
        r = idx + 4
        ws3.row_dimensions[r].height = 22
        bg_row  = FONDO_CARD if idx % 2 == 0 else '1E1B4B'
        pct     = round((m.monto_actual / m.monto_objetivo * 100), 1) if m.monto_objetivo else 0
        faltante = max(0, m.monto_objetivo - m.monto_actual)
        estado  = '✅ Completada' if m.completada else '🔄 En progreso'
        col_est = VERDE if m.completada else AMARILLO

        data_cell(ws3, r, 1, m.nombre,                             bg_row, BLANCO, align='left')
        data_cell(ws3, r, 2, getattr(m, 'categoria', '—') or '—', bg_row, GRIS)
        data_cell(ws3, r, 3, f'${m.monto_actual:,.2f}',           bg_row, VERDE, bold=True)
        data_cell(ws3, r, 4, f'${m.monto_objetivo:,.2f}',         bg_row, CYAN)
        data_cell(ws3, r, 5, f'${faltante:,.2f}',                 bg_row, ROSA)
        data_cell(ws3, r, 6, f'{pct}%',                           bg_row, AMARILLO, bold=True)
        data_cell(ws3, r, 7, estado,                               bg_row, col_est, bold=True)
        fecha_l = m.fecha_limite.strftime('%d/%m/%Y') if m.fecha_limite else '—'
        data_cell(ws3, r, 8, fecha_l,                             bg_row, GRIS)

    # Gráfico de barras — progreso metas
    if metas:
        ws3[f'J1'] = 'Meta';     ws3[f'K1'] = 'Ahorrado'; ws3[f'L1'] = 'Objetivo'
        for col in ['J1', 'K1', 'L1']:
            ws3[col].fill = fill(FONDO_CARD)
            ws3[col].font = font(BLANCO, bold=True)

        for i, m in enumerate(metas[:8], 2):
            ws3[f'J{i}'] = m.nombre[:20]
            ws3[f'K{i}'] = round(m.monto_actual, 2)
            ws3[f'L{i}'] = round(m.monto_objetivo, 2)
            for col in [f'J{i}', f'K{i}', f'L{i}']:
                ws3[col].fill = fill(FONDO_CARD)
                ws3[col].font = font(BLANCO)

        bar2 = BarChart()
        bar2.type    = 'col'
        bar2.title   = 'Progreso de Metas de Ahorro'
        bar2.style   = 10
        bar2.y_axis.title = 'Monto ($)'
        bar2.width   = 22
        bar2.height  = 14

        data_m  = Reference(ws3, min_col=11, max_col=12, min_row=1, max_row=min(len(metas)+1, 9))
        cats_m  = Reference(ws3, min_col=10, min_row=2, max_row=min(len(metas)+1, 9))
        bar2.add_data(data_m, titles_from_data=True)
        bar2.set_categories(cats_m)
        bar2.series[0].graphicalProperties.solidFill = VERDE
        bar2.series[1].graphicalProperties.solidFill = MORADO
        ws3.add_chart(bar2, f'A{len(metas)+7}')

    # ════════════════════════════════════════════
    # HOJA 4 — SIMULACIONES
    # ════════════════════════════════════════════
    ws4 = wb.create_sheet('📈 Simulaciones')
    ws4.sheet_view.showGridLines = False
    ws4.sheet_properties.tabColor = CYAN

    for row in ws4.iter_rows(min_row=1, max_row=len(simulaciones)+15, min_col=1, max_col=8):
        for cell in row:
            cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws4, '📈 Historial de Simulaciones',
                f'{len(simulaciones)} simulaciones | {usuario.nombre}', 8)

    cols4 = ['#', 'Fecha', 'Capital ($)', 'Tasa (%)', 'Plazo (meses)', 'Resultado ($)', 'Ganancia ($)', 'Tipo']
    header_row(ws4, 4, cols4, bg='1E3A5F')
    ws4.row_dimensions[4].height = 22

    widths4 = [5, 14, 16, 12, 16, 18, 16, 14]
    for i, w in enumerate(widths4, 1):
        set_col_width(ws4, i, w)

    for idx, s in enumerate(simulaciones, 1):
        r = idx + 4
        ws4.row_dimensions[r].height = 20
        bg_row  = FONDO_CARD if idx % 2 == 0 else '1E1B4B'
        ganancia = (s.resultado - s.capital) if s.resultado and s.capital else 0

        data_cell(ws4, r, 1, idx,                                      bg_row, GRIS)
        data_cell(ws4, r, 2, s.fecha.strftime('%d/%m/%Y') if s.fecha else '', bg_row, GRIS)
        data_cell(ws4, r, 3, f'${s.capital:,.2f}',                    bg_row, BLANCO, bold=True)
        data_cell(ws4, r, 4, f'{s.tasa}%',                            bg_row, AMARILLO)
        data_cell(ws4, r, 5, str(s.plazo),                            bg_row, GRIS)
        data_cell(ws4, r, 6, f'${s.resultado:,.2f}',                  bg_row, CYAN, bold=True)
        data_cell(ws4, r, 7, f'+${ganancia:,.2f}',                    bg_row, VERDE, bold=True)
       # routes/excel.py
from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Transaccion, MetaAhorro, Simulacion
from extensions import db
from datetime import datetime
import io

excel_bp = Blueprint('excel', __name__)

@excel_bp.route('/excel', methods=['GET'])
@jwt_required()
def exportar_excel():
    try:
        import openpyxl
        from openpyxl.styles import (
            PatternFill, Font, Alignment, Border, Side
        )
        from openpyxl.chart import BarChart, PieChart, LineChart, Reference
        from openpyxl.utils import get_column_letter
    except ImportError:
        return jsonify({'mensaje': 'Instala openpyxl: pip install openpyxl'}), 500

    usuario_id = int(get_jwt_identity())
    usuario    = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'mensaje': 'Usuario no encontrado'}), 404

    transacciones = Transaccion.query.filter_by(usuario_id=usuario_id)\
                               .order_by(Transaccion.fecha.desc()).all()
    metas         = MetaAhorro.query.filter_by(usuario_id=usuario_id).all()
    simulaciones  = Simulacion.query.filter_by(usuario_id=usuario_id)\
                               .order_by(Simulacion.fecha.desc()).all()

    wb = openpyxl.Workbook()

    # ── Paleta de Colores ───────────────────────────────────
    MORADO      = 'C026D3'
    MORADO_OSC  = '7E22CE'
    CYAN        = '22D3EE'
    VERDE       = '4ADE80'
    ROSA        = 'F472B6'
    FONDO_OSC   = '0F0F2D'
    FONDO_CARD  = '1A1A4E'
    BLANCO      = 'FFFFFF'
    GRIS        = '9CA3AF'
    AMARILLO    = 'FCD34D'
    ROJO        = 'EF4444'

    def fill(hex_color):
        return PatternFill('solid', fgColor=hex_color)

    def font(hex_color=BLANCO, bold=False, size=11, italic=False):
        return Font(color=hex_color, bold=bold, size=size, italic=italic, name='Segoe UI')

    def center():
        return Alignment(horizontal='center', vertical='center', wrap_text=True)

    def left():
        return Alignment(horizontal='left', vertical='center', wrap_text=True)

    def border_thin(color='4C1D95'):
        s = Side(style='thin', color=color)
        return Border(left=s, right=s, top=s, bottom=s)

    def set_col_width(ws, col, width):
        ws.column_dimensions[get_column_letter(col)].width = width

    def header_row(ws, row, cols, bg=MORADO_OSC, fg=BLANCO, size=11):
        for col, txt in enumerate(cols, 1):
            c = ws.cell(row=row, column=col, value=txt)
            c.fill      = fill(bg)
            c.font      = font(fg, bold=True, size=size)
            c.alignment = center()
            c.border    = border_thin()

    def data_cell(ws, row, col, val, bg=FONDO_CARD, fg=BLANCO, bold=False, align='center', size=10):
        c = ws.cell(row=row, column=col, value=val)
        c.fill      = fill(bg)
        c.font      = font(fg, bold=bold, size=size)
        c.alignment = center() if align == 'center' else left()
        c.border    = border_thin('2D1B69')
        return c

    def titulo_hoja(ws, texto, subtexto='', span=8):
        ws.row_dimensions[1].height = 45
        ws.row_dimensions[2].height = 22
        ws.merge_cells(f'A1:{get_column_letter(span)}1')
        c = ws['A1']
        c.value     = texto
        c.fill      = fill(MORADO)
        c.font      = font(BLANCO, bold=True, size=18)
        c.alignment = center()

        if subtexto:
            ws.merge_cells(f'A2:{get_column_letter(span)}2')
            s = ws['A2']
            s.value     = subtexto
            s.fill      = fill(MORADO_OSC)
            s.font      = font(GRIS, size=10, italic=True)
            s.alignment = center()

    # ════════════════════════════════════════════
    # HOJA 1 — RESUMEN GENERAL
    # ════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = '📊 Resumen'
    ws1.sheet_view.showGridLines = False
    ws1.sheet_properties.tabColor = MORADO

    for row in ws1.iter_rows(min_row=1, max_row=50, min_col=1, max_col=10):
        for cell in row:
            cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws1, '📊 FinanBot — Reporte Financiero',
                f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")} | Usuario: {usuario.nombre}', 8)

    ingresos_total = sum(t.monto for t in transacciones if t.tipo == 'ingreso')
    gastos_total   = sum(t.monto for t in transacciones if t.tipo == 'gasto')
    balance        = ingresos_total - gastos_total
    ahorrado_total = sum(m.monto_actual for m in metas)

    stats = [
        ('💰 Ingresos totales',  f'${ingresos_total:,.0f}', VERDE),
        ('💸 Gastos totales',    f'${gastos_total:,.0f}',   ROSA),
        ('📈 Balance actual',    f'${balance:,.0f}',        CYAN if balance >= 0 else ROJO),
        ('🎯 Ahorro en metas',   f'${ahorrado_total:,.0f}', AMARILLO),
        ('📋 Transacciones',     str(len(transacciones)),   MORADO),
        ('🎯 Metas activas',     str(len(metas)),           VERDE),
        ('📈 Simulaciones',      str(len(simulaciones)),    CYAN),
    ]

    ws1.row_dimensions[4].height = 20
    ws1.merge_cells('A4:H4')
    t4 = ws1['A4']
    t4.value     = '  MÉTRICAS PRINCIPALES'
    t4.fill      = fill(MORADO_OSC)
    t4.font      = font(BLANCO, bold=True, size=12)
    t4.alignment = left()

    for i, (label, valor, color) in enumerate(stats, 5):
        ws1.row_dimensions[i].height = 28
        c1 = ws1.cell(row=i, column=1, value=label)
        c1.fill, c1.font, c1.alignment, c1.border = fill('1A1A4E'), font(GRIS, size=10), left(), border_thin()
        ws1.merge_cells(f'A{i}:D{i}')

        c2 = ws1.cell(row=i, column=5, value=valor)
        c2.fill, c2.font, c2.alignment, c2.border = fill('2D1B69'), font(color, bold=True, size=13), center(), border_thin()
        ws1.merge_cells(f'E{i}:H{i}')

    for col, w in enumerate([14]*8, 1): set_col_width(ws1, col, w)

    # Gráfico de barras ingresos vs gastos
    cat_gastos = {}
    if transacciones:
        ws1['J1'] = 'Categoría'; ws1['K1'] = 'Monto'
        ws1['J1'].font = ws1['K1'].font = font(BLANCO, bold=True)

        for t in transacciones:
            if t.tipo == 'gasto':
                # CORRECCIÓN: Usar .nombre si es objeto
                nom_c = t.categoria.nombre if hasattr(t.categoria, 'nombre') else str(t.categoria or 'Otros')
                cat_gastos[nom_c] = cat_gastos.get(nom_c, 0) + t.monto

        fila_g = 2
        for cat_nom, monto in sorted(cat_gastos.items(), key=lambda x: x[1], reverse=True)[:8]:
            ws1[f'J{fila_g}'] = cat_nom
            ws1[f'K{fila_g}'] = round(monto, 2)
            ws1[f'J{fila_g}'].fill = ws1[f'K{fila_g}'].fill = fill(FONDO_CARD)
            ws1[f'J{fila_g}'].font = ws1[f'K{fila_g}'].font = font(BLANCO)
            fila_g += 1

        if fila_g > 2:
            bar = BarChart()
            bar.title, bar.width, bar.height = 'Gastos por Categoría', 22, 14
            data_ref = Reference(ws1, min_col=11, min_row=1, max_row=fila_g-1)
            cats_ref = Reference(ws1, min_col=10, min_row=2, max_row=fila_g-1)
            bar.add_data(data_ref, titles_from_data=True)
            bar.set_categories(cats_ref)
            ws1.add_chart(bar, 'A14')

    # ════════════════════════════════════════════
    # HOJA 2 — TRANSACCIONES
    # ════════════════════════════════════════════
    ws2 = wb.create_sheet('💳 Transacciones')
    ws2.sheet_view.showGridLines = False
    ws2.sheet_properties.tabColor = CYAN

    for row in ws2.iter_rows(min_row=1, max_row=len(transacciones)+10, min_col=1, max_col=7):
        for cell in row: cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws2, '💳 Historial de Transacciones', f'{len(transacciones)} registros | {usuario.nombre}', 7)

    cols = ['#', 'Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto ($)', 'Estado']
    header_row(ws2, 5, cols)
    for i, w in enumerate([5, 14, 11, 18, 30, 15, 12], 1): set_col_width(ws2, i, w)

    for idx, t in enumerate(transacciones, 1):
        r = idx + 5
        bg_row = FONDO_CARD if idx % 2 == 0 else '1E1B4B'
        col_tipo = VERDE if t.tipo == 'ingreso' else ROSA
        
        # CORRECCIÓN: Acceder al nombre de la categoría
        cat_nom = t.categoria.nombre if hasattr(t.categoria, 'nombre') else str(t.categoria or '—')

        data_cell(ws2, r, 1, idx, bg_row, GRIS)
        data_cell(ws2, r, 2, t.fecha.strftime('%d/%m/%Y') if t.fecha else '', bg_row, GRIS)
        data_cell(ws2, r, 3, t.tipo.capitalize(), bg_row, col_tipo, bold=True)
        data_cell(ws2, r, 4, cat_nom, bg_row, BLANCO, align='left')
        data_cell(ws2, r, 5, t.descripcion or '—', bg_row, GRIS, align='left')
        monto_txt = f'+${t.monto:,.2f}' if t.tipo == 'ingreso' else f'-${t.monto:,.2f}'
        data_cell(ws2, r, 6, monto_txt, bg_row, col_tipo, bold=True)
        data_cell(ws2, r, 7, '✅ OK', bg_row, VERDE)

    if cat_gastos:
        ws2['I1'], ws2['J1'] = 'Categoría', 'Monto'
        fila_p = 2
        for c_nom, m_val in sorted(cat_gastos.items(), key=lambda x: x[1], reverse=True)[:6]:
            ws2[f'I{fila_p}'], ws2[f'J{fila_p}'] = c_nom, round(m_val, 2)
            ws2[f'I{fila_p}'].fill = ws2[f'J{fila_p}'].fill = fill(FONDO_CARD)
            fila_p += 1
        pie = PieChart()
        pie.title, pie.width, pie.height = 'Distribución de Gastos', 18, 13
        pie.add_data(Reference(ws2, min_col=10, min_row=1, max_row=fila_p-1), titles_from_data=True)
        pie.set_categories(Reference(ws2, min_col=9, min_row=2, max_row=fila_p-1))
        ws2.add_chart(pie, f'A{len(transacciones)+8}')

    # ════════════════════════════════════════════
    # HOJA 3 — METAS DE AHORRO
    # ════════════════════════════════════════════
    ws3 = wb.create_sheet('🎯 Metas')
    ws3.sheet_view.showGridLines, ws3.sheet_properties.tabColor = False, VERDE

    for row in ws3.iter_rows(min_row=1, max_row=len(metas)+15, min_col=1, max_col=8):
        for cell in row: cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws3, '🎯 Metas de Ahorro', f'{len(metas)} metas | {usuario.nombre}', 8)
    header_row(ws3, 4, ['Meta', 'Categoría', 'Ahorrado ($)', 'Objetivo ($)', 'Faltante ($)', 'Progreso', 'Estado', 'Fecha límite'], bg='065F46')
    for i, w in enumerate([28, 15, 16, 16, 16, 12, 14, 16], 1): set_col_width(ws3, i, w)

    for idx, m in enumerate(metas, 1):
        r = idx + 4
        bg_row = FONDO_CARD if idx % 2 == 0 else '1E1B4B'
        pct = round((m.monto_actual / m.monto_objetivo * 100), 1) if m.monto_objetivo else 0
        
        # CORRECCIÓN: Categoria en Metas
        m_cat = m.categoria.nombre if hasattr(m, 'categoria') and hasattr(m.categoria, 'nombre') else '—'

        data_cell(ws3, r, 1, m.nombre, bg_row, BLANCO, align='left')
        data_cell(ws3, r, 2, m_cat, bg_row, GRIS)
        data_cell(ws3, r, 3, f'${m.monto_actual:,.2f}', bg_row, VERDE, bold=True)
        data_cell(ws3, r, 4, f'${m.monto_objetivo:,.2f}', bg_row, CYAN)
        data_cell(ws3, r, 5, f'${max(0, m.monto_objetivo-m.monto_actual):,.2f}', bg_row, ROSA)
        data_cell(ws3, r, 6, f'{pct}%', bg_row, AMARILLO, bold=True)
        data_cell(ws3, r, 7, '✅ Completada' if m.completada else '🔄 En progreso', bg_row, VERDE if m.completada else AMARILLO, bold=True)
        data_cell(ws3, r, 8, m.fecha_limite.strftime('%d/%m/%Y') if m.fecha_limite else '—', bg_row, GRIS)

    # ════════════════════════════════════════════
    # HOJA 4 — SIMULACIONES
    # ════════════════════════════════════════════
    ws4 = wb.create_sheet('📈 Simulaciones')
    ws4.sheet_view.showGridLines, ws4.sheet_properties.tabColor = False, CYAN

    for row in ws4.iter_rows(min_row=1, max_row=len(simulaciones)+15, min_col=1, max_col=8):
        for cell in row: cell.fill = fill(FONDO_OSC)

    titulo_hoja(ws4, '📈 Historial de Simulaciones', f'{len(simulaciones)} simulaciones | {usuario.nombre}', 8)
    header_row(ws4, 4, ['#', 'Fecha', 'Capital ($)', 'Tasa (%)', 'Plazo (meses)', 'Resultado ($)', 'Ganancia ($)', 'Tipo'], bg='1E3A5F')
    for i, w in enumerate([5, 14, 16, 12, 16, 18, 16, 14], 1): set_col_width(ws4, i, w)

    for idx, s in enumerate(simulaciones, 1):
        r = idx + 4
        bg_row = FONDO_CARD if idx % 2 == 0 else '1E1B4B'
        ganancia = (s.resultado - s.capital) if s.resultado and s.capital else 0
        
        # CORRECCIÓN: tipo_simulacion
        t_sim = str(getattr(s, 'tipo_simulacion', 'CDT'))

        data_cell(ws4, r, 1, idx, bg_row, GRIS)
        data_cell(ws4, r, 2, s.fecha.strftime('%d/%m/%Y') if s.fecha else '', bg_row, GRIS)
        data_cell(ws4, r, 3, f'${s.capital:,.2f}', bg_row, BLANCO, bold=True)
        data_cell(ws4, r, 4, f'{s.tasa}%', bg_row, AMARILLO)
        data_cell(ws4, r, 5, str(s.plazo), bg_row, GRIS)
        data_cell(ws4, r, 6, f'${s.resultado:,.2f}', bg_row, CYAN, bold=True)
        data_cell(ws4, r, 7, f'+${ganancia:,.2f}', bg_row, VERDE, bold=True)
        data_cell(ws4, r, 8, t_sim, bg_row, MORADO)

    # ── Exportación Final ────────────────────────
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    nombre_archivo = f"FinanBot_{usuario.nombre.replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nombre_archivo
    )
