# routes/exportar.py
from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Usuario, Transaccion, MetaAhorro, Simulacion
from datetime import datetime
from collections import defaultdict
import io
 
exportar_bp = Blueprint('exportar', __name__)
 
ICONOS_CAT = {
    'Alimentación':'🍔','Transporte':'🚌','Arriendo':'🏠','Salud':'💊',
    'Entretenimiento':'🎬','Educación':'📚','Ropa':'👗','Servicios':'⚡',
    'Tecnología':'💻','Médico':'🏥','Mascotas':'🐾','Regalos':'🎁',
    'Restaurantes':'🍕','Viajes':'✈️','Otros gastos':'📦','Salario':'💼',
    'Freelance':'🧑‍💻','Inversión':'📈','Negocio':'🏪','Regalo':'🎁',
    'Otros ingresos':'💵',
}
 
def get_icono(cat): return ICONOS_CAT.get(cat, '💸')
 
def tipo_sim(tasa):
    t = float(tasa)
    if t <= 5: return 'CDT Básico'
    if t <= 8: return 'CDT Premium'
    if t <= 10: return 'Fondo Inversión'
    if t <= 15: return 'Acciones BVC'
    if t <= 20: return 'Startups'
    return f'Personalizada {t}%'
 
# ══════════════════════════════════════════════════════════
#  PDF
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
        return jsonify({'mensaje': 'Instala reportlab'}), 500
 
    uid  = int(get_jwt_identity())
    user = Usuario.query.get(uid)
    if not user: return jsonify({'mensaje': 'No encontrado'}), 404
 
    trans = Transaccion.query.filter_by(usuario_id=uid).order_by(Transaccion.fecha.desc()).all()
    metas = MetaAhorro.query.filter_by(usuario_id=uid).all()
    sims  = Simulacion.query.filter_by(usuario_id=uid).order_by(Simulacion.fecha.desc()).all()
 
    def rgb(r,g,b): return colors.Color(r/255,g/255,b/255)
 
    BG     = rgb(31,31,58);   CARD  = rgb(26,26,78);   LINE  = rgb(45,27,105)
    MORADO = rgb(192,38,211); CYAN  = rgb(34,211,238);  VERDE = rgb(74,222,128)
    ROSA   = rgb(244,114,182);AMAR  = rgb(251,191,36);  BLANC = rgb(255,255,255)
    GRIS   = rgb(156,163,175);MUTED = rgb(107,114,128)
 
    def st(nm,**kw):
        b={'fontName':'Helvetica','textColor':BLANC,'leading':14}; b.update(kw)
        return ParagraphStyle(nm,**b)
 
    S_SEC = st('s',fontSize=13,fontName='Helvetica-Bold',textColor=CYAN,spaceAfter=4)
    S_TH  = st('th',fontSize=8,fontName='Helvetica-Bold',textColor=BLANC,alignment=TA_CENTER)
    S_TC  = st('tc',fontSize=8,textColor=GRIS,alignment=TA_LEFT)
    S_TCC = st('tcc',fontSize=8,textColor=GRIS,alignment=TA_CENTER)
    S_LAB = st('l',fontSize=9,textColor=GRIS,leading=11)
    S_FT  = st('ft',fontSize=7,textColor=MUTED,alignment=TA_CENTER)
 
    ingresos_t = sum(float(t.monto) for t in trans if t.tipo=='ingreso')
    gastos_t   = sum(float(t.monto) for t in trans if t.tipo=='gasto')
    balance    = ingresos_t - gastos_t
    ahorrado   = sum(float(m.monto_actual) for m in metas)
    pct_g      = round(gastos_t/ingresos_t*100) if ingresos_t>0 else 0
    gastos_cat = defaultdict(float)
    for t in trans:
        if t.tipo=='gasto': gastos_cat[t.categoria]+=float(t.monto)
    cat_mayor  = max(gastos_cat,key=gastos_cat.get) if gastos_cat else None
    ing_mens   = float(user.ingreso_mensual or 0)
    meta_mens  = float(user.meta_ahorro or 0)
 
    buf = io.BytesIO()
    W   = A4[0]-40*mm
    doc = SimpleDocTemplate(buf,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,
                             topMargin=18*mm,bottomMargin=18*mm)
 
    def mk_tabla(hdrs,filas,cws,ccolors=None):
        data=[[Paragraph(h,S_TH) for h in hdrs]]+filas
        ts=TableStyle([
            ('BACKGROUND',(0,0),(-1,0),LINE),('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),7),
            ('RIGHTPADDING',(0,0),(-1,-1),7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[CARD,BG]),
            ('GRID',(0,0),(-1,-1),0.3,LINE),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ])
        if ccolors:
            for ri,ci,col in ccolors: ts.add('TEXTCOLOR',(ci,ri),(ci,ri),col)
        t=Table(data,colWidths=cws,repeatRows=1); t.setStyle(ts); return t
 
    story=[]
 
    # Encabezado
    hd=Table([[
        Paragraph('FinanBot',st('logo',fontSize=24,fontName='Helvetica-Bold',textColor=MORADO)),
        Paragraph(f'<b>{user.nombre}</b><br/>{user.correo}<br/>'+
                  f'{datetime.now().strftime("%d/%m/%Y %H:%M")}',
                  st('r',fontSize=9,textColor=GRIS,alignment=TA_RIGHT))
    ]],colWidths=[W*0.5,W*0.5])
    hd.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),CARD),('TOPPADDING',(0,0),(-1,-1),12),
        ('BOTTOMPADDING',(0,0),(-1,-1),12),('LEFTPADDING',(0,0),(-1,-1),16),
        ('RIGHTPADDING',(0,0),(-1,-1),16),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LINEBELOW',(0,0),(-1,-1),1,LINE),
    ]))
    story.append(hd); story.append(Spacer(1,14))
 
    # Resumen 4 tarjetas
    story.append(Paragraph('Resumen financiero',S_SEC)); story.append(Spacer(1,4))
 
    def card(lbl,val,col):
        inn=Table([[Paragraph(lbl,S_LAB)],
                   [Paragraph(val,st('v',fontSize=15,fontName='Helvetica-Bold',textColor=col))]],
                  colWidths=[W/4-8])
        inn.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),CARD),('TOPPADDING',(0,0),(-1,-1),10),
            ('BOTTOMPADDING',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),12),
            ('RIGHTPADDING',(0,0),(-1,-1),12),('LINEABOVE',(0,0),(-1,0),3,col),
        ]))
        return inn
 
    bal_col=VERDE if balance>=0 else ROSA
    cards=Table([[card('INGRESOS TOTALES',f'${ingresos_t:,.0f}',CYAN),
                  card('GASTOS TOTALES',f'${gastos_t:,.0f}',MORADO),
                  card('BALANCE',f'${balance:,.0f}',bal_col),
                  card('TOTAL AHORRADO',f'${ahorrado:,.0f}',AMAR)]],
                colWidths=[W/4-4]*4,hAlign='LEFT')
    cards.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(cards); story.append(Spacer(1,14))
 
    # Análisis
    if ingresos_t>0:
        story.append(Paragraph('Análisis financiero',S_SEC)); story.append(Spacer(1,4))
        af=[]
        pct_col=VERDE if pct_g<70 else AMAR if pct_g<90 else ROSA
        af.append([Paragraph('% Gastos sobre ingresos',S_TC),
                   Paragraph(f'{pct_g}%',S_TCC),
                   Paragraph('✅ Bueno' if pct_g<70 else '⚠️ Ajustado' if pct_g<90 else '🚨 Crítico',S_TCC)])
        if cat_mayor:
            pm=round(gastos_cat[cat_mayor]/gastos_t*100) if gastos_t else 0
            af.append([Paragraph(f'Mayor categoría: {get_icono(cat_mayor)} {cat_mayor}',S_TC),
                       Paragraph(f'${gastos_cat[cat_mayor]:,.0f} ({pm}%)',S_TCC),
                       Paragraph('⚠️ Alta' if pm>40 else '✅ Normal',S_TCC)])
        if ing_mens>0:
            af.append([Paragraph('Ingreso mensual registrado',S_TC),
                       Paragraph(f'${ing_mens:,.0f}',S_TCC),
                       Paragraph(f'50%=${ing_mens*0.5:,.0f} | 30%=${ing_mens*0.3:,.0f} | 20%=${ing_mens*0.2:,.0f}',S_TCC)])
        if meta_mens>0:
            cumple=balance>=meta_mens
            af.append([Paragraph('Meta de ahorro mensual',S_TC),
                       Paragraph(f'${meta_mens:,.0f}',S_TCC),
                       Paragraph('✅ Cumplida' if cumple else f'⚠️ Brecha ${meta_mens-max(0,balance):,.0f}',S_TCC)])
        fondo_obj=ing_mens*3 if ing_mens>0 else ingresos_t*3
        pct_fondo=min(100,round(max(0,balance)/fondo_obj*100)) if fondo_obj>0 else 0
        af.append([Paragraph('Fondo de emergencia (3 meses)',S_TC),
                   Paragraph(f'{pct_fondo}%',S_TCC),
                   Paragraph('✅ Completo' if pct_fondo>=100 else f'Meta: ${fondo_obj:,.0f}',S_TCC)])
        story.append(mk_tabla(['Indicador','Valor','Estado/Detalle'],af,[W*0.42,W*0.24,W*0.34]))
        story.append(Spacer(1,14))
 
    # Transacciones
    if trans:
        story.append(Paragraph('Historial de transacciones',S_SEC)); story.append(Spacer(1,4))
        if gastos_cat:
            story.append(Paragraph('Gastos por categoría',
                         st('sub',fontSize=10,textColor=GRIS,fontName='Helvetica-Bold')))
            story.append(Spacer(1,4))
            cf=[]; cc=[]
            for i,(cat,m) in enumerate(sorted(gastos_cat.items(),key=lambda x:x[1],reverse=True)[:8],1):
                pm=round(m/gastos_t*100) if gastos_t else 0
                cf.append([Paragraph(f'{get_icono(cat)} {cat}',S_TC),
                            Paragraph(f'${m:,.0f}',S_TCC),
                            Paragraph(f'{pm}%',S_TCC),
                            Paragraph('▓'*int(pm/5)+'░'*(20-int(pm/5)),
                                      st('bar',fontSize=7,textColor=MORADO))])
                cc.append((i,1,ROSA))
            story.append(mk_tabla(['Categoría','Monto','%','Distribución'],cf,
                                   [W*0.35,W*0.2,W*0.1,W*0.35],cc))
            story.append(Spacer(1,8))
 
        # Detalle transacciones
        story.append(Paragraph('Detalle de movimientos',
                     st('sub',fontSize=10,textColor=GRIS,fontName='Helvetica-Bold')))
        story.append(Spacer(1,4))
        filas=[]; cc2=[]
        for i,t in enumerate(trans,1):
            tc=VERDE if t.tipo=='ingreso' else ROSA
            sgn='+' if t.tipo=='ingreso' else '-'
            fd=t.fecha.strftime('%d/%m/%Y') if t.fecha else '—'
            filas.append([Paragraph(str(i),S_TCC),Paragraph(fd,S_TCC),
                          Paragraph(t.tipo.capitalize(),S_TCC),
                          Paragraph(f'{get_icono(t.categoria)} {t.categoria or "—"}',S_TC),
                          Paragraph(t.descripcion or '—',S_TC),
                          Paragraph(f'{sgn}${float(t.monto):,.0f}',S_TCC)])
            cc2.append((i,5,tc)); cc2.append((i,2,tc))
        story.append(mk_tabla(['#','Fecha','Tipo','Categoría','Descripción','Monto'],filas,
                               [W*0.04,W*0.12,W*0.09,W*0.22,W*0.35,W*0.18],cc2))
        story.append(Spacer(1,14))
 
    # Metas
    if metas:
        story.append(Paragraph('Metas de ahorro',S_SEC)); story.append(Spacer(1,4))
        mf=[]; mc=[]
        for i,m in enumerate(metas,1):
            pct=round(float(m.monto_actual)/float(m.monto_objetivo)*100,1) if m.monto_objetivo else 0
            flt=max(0,float(m.monto_objetivo)-float(m.monto_actual))
            ec=VERDE if m.completada else AMAR
            fl=m.fecha_limite.strftime('%d/%m/%Y') if m.fecha_limite else '—'
            mf.append([Paragraph(str(i),S_TCC),Paragraph(m.nombre,S_TC),
                       Paragraph(f'${float(m.monto_actual):,.0f}',S_TCC),
                       Paragraph(f'${float(m.monto_objetivo):,.0f}',S_TCC),
                       Paragraph(f'${flt:,.0f}',S_TCC),Paragraph(f'{pct}%',S_TCC),
                       Paragraph('✅ Completa' if m.completada else '⏳ Progreso',S_TCC),
                       Paragraph(fl,S_TCC)])
            mc.append((i,6,ec)); mc.append((i,5,VERDE if m.completada else AMAR))
        story.append(mk_tabla(['#','Meta','Ahorrado','Objetivo','Faltante','%','Estado','Límite'],mf,
                               [W*0.04,W*0.22,W*0.12,W*0.12,W*0.12,W*0.07,W*0.15,W*0.16],mc))
        story.append(Spacer(1,14))
 
    # Simulaciones
    if sims:
        story.append(Paragraph('Simulaciones de inversión',S_SEC)); story.append(Spacer(1,4))
        sf=[]; sc=[]
        for i,s in enumerate(sims,1):
            cap=float(s.capital_inicial); res=float(s.resultado_final)
            gan=res-cap; ret=round(max(gan,0)*0.04,0); neto=res-ret
            pctg=round(gan/cap*100,1) if cap else 0
            fd=s.fecha.strftime('%d/%m/%Y') if s.fecha else '—'
            sf.append([Paragraph(str(i),S_TCC),Paragraph(fd,S_TCC),
                       Paragraph(tipo_sim(s.tasa_retorno),S_TC),
                       Paragraph(f'${cap:,.0f}',S_TCC),Paragraph(f'{s.tasa_retorno}%',S_TCC),
                       Paragraph(f'{s.plazo_meses}m',S_TCC),Paragraph(f'${res:,.0f}',S_TCC),
                       Paragraph(f'+${gan:,.0f}',S_TCC),Paragraph(f'${neto:,.0f}',S_TCC)])
            sc.append((i,7,VERDE)); sc.append((i,8,CYAN))
        story.append(mk_tabla(['#','Fecha','Tipo','Capital','Tasa','Plazo','Resultado','Ganancia','Neto'],sf,
                               [W*0.04,W*0.1,W*0.13,W*0.12,W*0.07,W*0.07,W*0.12,W*0.12,W*0.21],sc))
        story.append(Spacer(1,12))
 
    story.append(HRFlowable(width=W,thickness=0.5,color=LINE))
    story.append(Spacer(1,5))
    story.append(Paragraph(
        f'FinanBot · {user.nombre} · {datetime.now().strftime("%d/%m/%Y %H:%M")} · Confidencial',S_FT))
 
    def fondo(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(BG); canvas.rect(0,0,A4[0],A4[1],fill=1,stroke=0)
        canvas.setFillColor(MORADO); canvas.rect(0,A4[1]-4,A4[0],4,fill=1,stroke=0)
        canvas.restoreState()
 
    doc.build(story,onFirstPage=fondo,onLaterPages=fondo)
    buf.seek(0)
    nombre=f'FinanBot_{user.nombre.replace(" ","_")}_{datetime.now().strftime("%d-%m-%Y")}.pdf'
    return send_file(buf,mimetype='application/pdf',as_attachment=True,download_name=nombre)
 
 
