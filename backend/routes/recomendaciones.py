# routes/recomendaciones.py
# ════════════════════════════════════════════════════════════
#  Recomendaciones personalizadas de FinanBot
#
#  - Analiza el MES ACTUAL (hasta hoy), igual que Dashboard y
#    Mis Finanzas, y lo compara con el MES ANTERIOR.
#  - Nunca cuenta movimientos con fecha futura (siguen "en espera").
#  - Los aportes a metas (__auto_meta__, __manual_meta__,
#    __ajuste_meta__) se cuentan como AHORRO, no como consumo.
#  - Los retiros de ahorro no se cuentan como ingreso nuevo.
#  - Usa la regla de distribución del usuario (?nec=&des=&aho=),
#    la que se personaliza en Recomendaciones / Mi Perfil.
#  - Tiene en cuenta los lugares (tiendas) del mapa, el ritmo de
#    gasto para proyectar el fin de mes, gastos hormiga y las
#    fechas límite de las metas.
# ════════════════════════════════════════════════════════════
import calendar
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from extensions import obtener_usuario_id_requerido
from models import Transaccion, MetaAhorro, Usuario, Tienda
from routes.metas import obtener_metas_calculadas
from timezone import bogota_today

router = APIRouter()


# =========================================================
# CONFIGURACIÓN
# =========================================================

# Cómo se reparte cada categoría de gasto en la regla nec/des/aho
CATEGORIAS_NECESIDAD = {
    'Alimentación', 'Transporte', 'Arriendo', 'Salud', 'Educación', 'Servicios', 'Mascotas',
}
CATEGORIAS_DESEO = {
    'Entretenimiento', 'Ropa', 'Regalos', 'Viajes', 'Restaurantes', 'Otros gastos',
}

RE_TAG_META = re.compile(r'__(auto|manual|ajuste)_meta_(\d+)__')
TAG_SALARIO = '__auto_salario__'

MONTO_HORMIGA = 20_000         # gastos pequeños que se acumulan
MIN_GASTOS_HORMIGA = 8
DIAS_SIN_REGISTRAR = 5
MAX_RECOMENDACIONES = 12

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


# =========================================================
# UTILIDADES
# =========================================================

def _pesos(valor: float) -> str:
    """$1.234.567 (formato colombiano)."""
    return '$' + f'{round(valor):,.0f}'.replace(',', '.')


def _fecha(valor) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor.split(' ', 1)[0])
        except ValueError:
            return None
    return None


def filtrar_transacciones_recientes(transacciones, dias=7):
    if not transacciones:
        return []

    limite = bogota_today() - timedelta(days=dias)
    resultado = []
    for transaccion in transacciones:
        valor_fecha = (
            transaccion.get('fecha')
            if isinstance(transaccion, dict)
            else getattr(transaccion, 'fecha', None)
        )
        fecha = _fecha(valor_fecha)
        if fecha and fecha >= limite:
            resultado.append(transaccion)
    return resultado


def _nombre_categoria(t) -> str:
    cat = t.categoria
    if isinstance(cat, str):
        return cat
    return getattr(cat, 'nombre', None) or 'Otros gastos'


def _es_aporte_meta(t) -> bool:
    return bool(t.descripcion and RE_TAG_META.search(t.descripcion))


def _mes_anterior(hoy: date):
    return (hoy.year - 1, 12) if hoy.month == 1 else (hoy.year, hoy.month - 1)


class Resumen:
    """Totales de un conjunto de transacciones, separando consumo,
    ahorro en metas e ingresos reales."""

    def __init__(self, transacciones):
        self.ingresos = 0.0           # ingresos reales (sin retiros de ahorro)
        self.retiros_ahorro = 0.0     # plata que volvió desde metas
        self.gastos = 0.0             # consumo real (sin aportes a metas)
        self.ahorro_metas = 0.0       # aportes netos a metas
        self.por_categoria = defaultdict(float)
        self.cantidad_por_categoria = defaultdict(int)
        self.gastos_lista = []
        self.n = 0

        for t in transacciones:
            self.n += 1
            monto = float(t.monto)
            if _es_aporte_meta(t):
                # gasto positivo = aporte; gasto negativo o ingreso = retiro
                if t.tipo == 'gasto':
                    self.ahorro_metas += monto
                else:
                    self.ahorro_metas -= monto
                    self.retiros_ahorro += monto
                continue
            if t.tipo == 'ingreso':
                self.ingresos += monto
            else:
                cat = _nombre_categoria(t)
                self.gastos += monto
                self.por_categoria[cat] += monto
                self.cantidad_por_categoria[cat] += 1
                self.gastos_lista.append(t)

    @property
    def balance(self) -> float:
        """Lo que sobra después de consumo y ahorro en metas."""
        return self.ingresos + self.retiros_ahorro - self.gastos - self.ahorro_metas

    @property
    def ahorro_total(self) -> float:
        """Ahorro real del periodo: lo que quedó libre + lo que fue a metas."""
        return max(0.0, self.ingresos - self.gastos)

    def necesidades(self) -> float:
        return sum(v for c, v in self.por_categoria.items() if c in CATEGORIAS_NECESIDAD)

    def deseos(self) -> float:
        return sum(v for c, v in self.por_categoria.items() if c not in CATEGORIAS_NECESIDAD)


def _nueva(tipo, prioridad, icono, titulo, descripcion, accion, link,
           beneficios=None, dato_clave=None, ahorro_potencial=0, progreso=None, key=None):
    r = {
        'tipo': tipo, 'prioridad': prioridad, 'icono': icono,
        'titulo': titulo, 'descripcion': descripcion,
        'beneficios': beneficios or [], 'accion': accion, 'link': link,
        'completada': False, 'ahorro_potencial': max(0, round(ahorro_potencial or 0)),
    }
    if dato_clave:
        r['dato_clave'] = dato_clave
    if progreso is not None:
        r['progreso'] = max(0, min(100, round(progreso)))
    if key:
        r['key'] = key
    return r


# =========================================================
# ENDPOINT
# =========================================================

@router.get('/')
def obtener_recomendaciones(
    nec: int = Query(50, ge=0, le=100, description='% necesidades de la regla del usuario'),
    des: int = Query(30, ge=0, le=100, description='% deseos'),
    aho: int = Query(20, ge=0, le=100, description='% ahorro'),
    usuario_id: str = Depends(obtener_usuario_id_requerido),
    db: Session = Depends(get_db),
):
    uid = int(usuario_id)
    usuario = db.get(Usuario, uid)
    if not usuario:
        return []

    if nec + des + aho != 100:
        nec, des, aho = 50, 30, 20

    hoy = bogota_today()
    dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    anio_ant, mes_ant = _mes_anterior(hoy)

    todas = db.query(Transaccion).filter_by(usuario_id=uid).all()
    pasadas = [t for t in todas if (_fecha(t.fecha) or hoy) <= hoy]       # sin fechas futuras
    futuras = [t for t in todas if (_fecha(t.fecha) or hoy) > hoy]
    del_mes = [t for t in pasadas if _fecha(t.fecha).year == hoy.year and _fecha(t.fecha).month == hoy.month]
    mes_pasado = [t for t in pasadas if _fecha(t.fecha).year == anio_ant and _fecha(t.fecha).month == mes_ant]
    # mismo tramo del mes pasado (día 1 → mismo día de hoy) para comparar justo
    tramo_pasado = [t for t in mes_pasado if _fecha(t.fecha).day <= hoy.day]

    metas = db.query(MetaAhorro).filter_by(usuario_id=uid).all()
    metas_ahorro = [m for m in metas if (m.tipo or 'ahorro') == 'ahorro']
    metas_activas = [
        m for m in metas_ahorro
        if not m.completada and float(m.monto_actual or 0) < float(m.monto_objetivo or 0)
    ]
    metas_completas = [
        m for m in metas_ahorro
        if m.completada or float(m.monto_actual or 0) >= float(m.monto_objetivo or 0)
    ]
    limites_gasto = [
        meta for meta in obtener_metas_calculadas(uid, db, hoy)
        if meta['tipo'] in ('gasto_mensual', 'gasto_anual')
    ]

    act = Resumen(del_mes)
    ant = Resumen(tramo_pasado)
    ant_completo = Resumen(mes_pasado)

    ing_perfil = float(usuario.ingreso_mensual or 0)
    meta_ahorro_perfil = float(usuario.meta_ahorro or 0)
    # base de ingresos para la regla: lo registrado o, si aún no llega el salario, el del perfil
    base_ingreso = act.ingresos if act.ingresos > 0 else ing_perfil
    nombre_mes = MESES[hoy.month - 1]

    recs = []

    for limite in limites_gasto:
        if not limite['excedida']:
            continue
        periodo = 'mensual' if limite['tipo'] == 'gasto_mensual' else 'anual'
        excedente = max(0, limite['monto_actual'] - limite['monto_objetivo'])
        recs.append(_nueva(
            'alerta', 'Alta', '🚨',
            f'Límite de gasto {periodo} alcanzado: {limite["nombre"]}',
            f'Has gastado {_pesos(limite["monto_actual"])} de un máximo de '
            f'{_pesos(limite["monto_objetivo"])} para {limite["periodo"]}. '
            + ('Ya superaste el límite por ' + _pesos(excedente) + '. ' if excedente else '')
            + 'Es una señal de alerta, no un logro de ahorro. Pausa gastos no esenciales y revisa tus movimientos.',
            'Revisar mis gastos', 'finanzas.html',
            ['Evita compras no esenciales hasta el próximo periodo',
             'Revisa la categoría que más aumentó',
             'Consulta tu límite y ajusta el plan en Mi Perfil'],
            dato_clave=f'🚨 Tope {periodo}: {_pesos(limite["monto_objetivo"])} · '
            f'Gastado: {_pesos(limite["monto_actual"])}',
            progreso=limite['porcentaje'],
        ))

    # ─────────────────────────────────────────────────────
    # 0. SIN NINGÚN DATO
    # ─────────────────────────────────────────────────────
    if not todas:
        return [_finalizar(_nueva(
            'info', 'Alta', '📝', 'Registra tu primera transacción',
            'Aún no tienes movimientos. Con solo uno FinanBot empieza a analizar '
            'tus finanzas y a darte consejos reales para tu bolsillo.',
            'Ir a Mis Finanzas', 'finanzas.html',
            ['Análisis automático de tus finanzas', 'Recomendaciones según tus datos',
             'Gráficas y mapa de tus movimientos'],
            '💡 Registra lo de hoy, toma 30 segundos. También puedes decírselo al Chat FinanBot.',
        ), 1)]

    # ─────────────────────────────────────────────────────
    # 1. SALARIO NO CONFIGURADO
    # ─────────────────────────────────────────────────────
    if ing_perfil <= 0:
        recs.append(_nueva(
            'advertencia', 'Alta', '💼', 'Configura tu ingreso mensual',
            'No tienes un ingreso mensual en tu perfil. Con él, FinanBot registra tu salario '
            'automáticamente cada mes y calcula tu distribución ideal de gastos.',
            'Ir a Mi Perfil', 'perfil.html',
            ['Salario registrado solo, el día de pago', 'Cálculo de tu regla de distribución',
             'Recomendaciones más precisas'],
        ))

    # ─────────────────────────────────────────────────────
    # 2. MES SIN MOVIMIENTOS (pero con historial)
    # ─────────────────────────────────────────────────────
    if act.n == 0:
        recs.append(_nueva(
            'info', 'Alta', '🗓️', f'Aún no registras nada en {nombre_mes}',
            f'Tu historial está guardado, pero este mes no tiene movimientos. '
            f'Registra tus gastos e ingresos de {nombre_mes} para mantener el análisis al día.',
            'Registrar movimiento', 'finanzas.html',
            ['El Dashboard se actualiza con cada registro', 'Podrás comparar con el mes pasado'],
            (f'💡 El mes pasado gastaste {_pesos(ant_completo.gastos)}.' if ant_completo.gastos else None),
        ))

    # ─────────────────────────────────────────────────────
    # 3. FALTA UN TIPO DE MOVIMIENTO
    # ─────────────────────────────────────────────────────
    elif act.ingresos == 0 and act.gastos > 0:
        salario_pendiente = any(t.descripcion == TAG_SALARIO for t in futuras) or (
            ing_perfil > 0 and getattr(usuario, 'fecha_salario', None))
        recs.append(_nueva(
            'advertencia', 'Alta', '💰',
            'Tu salario de este mes aún no llega' if salario_pendiente else 'Este mes no has registrado ingresos',
            f'Llevas {_pesos(act.gastos)} en gastos en {nombre_mes} '
            + ('y tu salario se sumará automáticamente el día de pago. Mientras tanto, cuida tu ritmo de gasto.'
               if salario_pendiente else
               'y ningún ingreso. Sin ingresos FinanBot no puede calcular tu balance real.'),
            'Ver Mis Finanzas', 'finanzas.html',
            ['Registra ingresos extra (freelance, ventas, regalos)', 'Revisa tu día de pago en Mi Perfil'],
        ))

    # ─────────────────────────────────────────────────────
    # 4. BALANCE NEGATIVO DEL MES
    # ─────────────────────────────────────────────────────
    cat_top = max(act.por_categoria, key=act.por_categoria.get) if act.por_categoria else None
    monto_top = act.por_categoria.get(cat_top, 0) if cat_top else 0

    if act.ingresos > 0 and act.gastos > act.ingresos:
        deficit = act.gastos - act.ingresos
        recs.append(_nueva(
            'alerta', 'Alta', '🚨', f'En {nombre_mes} gastas más de lo que ganas',
            f'Tus gastos ({_pesos(act.gastos)}) superan tus ingresos ({_pesos(act.ingresos)}) '
            f'por {_pesos(deficit)}. Lo que más pesa es "{cat_top}" con {_pesos(monto_top)}.',
            'Ver mis gastos', 'finanzas.html',
            [f'Recortar 20% en "{cat_top}" libera {_pesos(monto_top * 0.2)}',
             'Pausa compras no esenciales hasta fin de mes',
             'Revisa suscripciones y pagos automáticos'],
            f'🎯 Meta inmediata: reducir {_pesos(deficit)} para volver a $0.',
            ahorro_potencial=deficit,
        ))

    # ─────────────────────────────────────────────────────
    # 5. PROYECCIÓN AL CIERRE DEL MES (ritmo de gasto diario)
    # ─────────────────────────────────────────────────────
    alerta_ritmo = False
    if act.gastos > 0 and hoy.day >= 5 and hoy.day < dias_mes and base_ingreso > 0:
        ritmo_diario = act.gastos / hoy.day
        proyectado = ritmo_diario * dias_mes
        limite = base_ingreso * (nec + des) / 100
        if proyectado > limite and not (act.ingresos > 0 and act.gastos > act.ingresos):
            alerta_ritmo = True
            exceso = proyectado - limite
            dias_rest = dias_mes - hoy.day
            disponible = max(0, limite - act.gastos)
            recs.append(_nueva(
                'advertencia', 'Alta', '📉', f'A este ritmo cerrarás {nombre_mes} gastando {_pesos(proyectado)}',
                f'Gastas en promedio {_pesos(ritmo_diario)} al día. Si sigues así, superarás en '
                f'{_pesos(exceso)} el límite de tu regla ({nec + des}% de tus ingresos = {_pesos(limite)}).',
                'Ver mis gastos', 'finanzas.html',
                [f'Para cumplir, gasta máximo {_pesos(disponible / dias_rest if dias_rest else 0)} al día los próximos {dias_rest} días',
                 'Agrupa compras de mercado en una sola salida semanal'],
                f'⏳ Te quedan {_pesos(disponible)} para el resto del mes.',
                ahorro_potencial=exceso,
                progreso=act.gastos / limite * 100 if limite else 0,
            ))

    # ─────────────────────────────────────────────────────
    # 6. TU REGLA PERSONALIZADA (necesidades / deseos / ahorro)
    # ─────────────────────────────────────────────────────
    if base_ingreso > 0 and act.gastos > 0:
        pct_nec = act.necesidades() / base_ingreso * 100
        pct_des = act.deseos() / base_ingreso * 100
        if pct_des > des:
            exceso = act.deseos() - base_ingreso * des / 100
            top_deseo = max(((c, v) for c, v in act.por_categoria.items() if c not in CATEGORIAS_NECESIDAD),
                            key=lambda x: x[1], default=(None, 0))
            recs.append(_nueva(
                'advertencia', 'Media', '🛍️', f'Tus deseos ya son el {round(pct_des)}% de tus ingresos',
                f'Tu regla {nec}/{des}/{aho} permite hasta {des}% ({_pesos(base_ingreso * des / 100)}) en deseos '
                f'y llevas {_pesos(act.deseos())}'
                + (f', sobre todo en "{top_deseo[0]}" ({_pesos(top_deseo[1])}).' if top_deseo[0] else '.'),
                'Ver mis gastos', 'finanzas.html',
                [f'Te pasaste {_pesos(exceso)} en deseos', 'Espera 48 horas antes de compras no planeadas'],
                ahorro_potencial=exceso, progreso=pct_des / des * 100 if des else 100,
            ))
        if pct_nec > nec:
            recs.append(_nueva(
                'info', 'Media', '🏠', f'Tus necesidades son el {round(pct_nec)}% de tus ingresos',
                f'Tu regla reserva {nec}% ({_pesos(base_ingreso * nec / 100)}) para necesidades '
                f'y llevas {_pesos(act.necesidades())}. Si pasa cada mes, quizá tu regla deba ser más '
                f'conservadora (por ejemplo 60/20/20).',
                'Ajustar mi regla', '#reglaSection',
                ['Compara precios de servicios (internet, celular, seguros)',
                 'Mercado con lista y en tiendas de descuento'],
            ))

    # ─────────────────────────────────────────────────────
    # 7. COMPARACIÓN CON EL MES ANTERIOR (mismo tramo)
    # ─────────────────────────────────────────────────────
    if act.gastos > 0 and ant.gastos > 0 and len(ant_completo.gastos_lista) >= 3:
        variacion = (act.gastos - ant.gastos) / ant.gastos * 100
        if variacion >= 20 and act.gastos - ant.gastos >= 50_000:
            texto_var = (f'{act.gastos / ant.gastos:.1f} veces lo del mes pasado'.replace('.', ',')
                         if variacion >= 200 else f'{round(variacion)}% más que el mes pasado')
            recs.append(_nueva(
                'advertencia', 'Media', '📈', f'Gastas {texto_var}',
                f'Del 1 al {hoy.day} de {nombre_mes} llevas {_pesos(act.gastos)}; en el mismo tramo '
                f'de {MESES[mes_ant - 1]} llevabas {_pesos(ant.gastos)}.',
                'Ver mis gastos', 'finanzas.html',
                ['Mira en el calendario qué días gastaste más'],
                ahorro_potencial=act.gastos - ant.gastos,
            ))
        elif variacion <= -10:
            recs.append(_nueva(
                'exito', 'Baja', '👏', f'¡Gastas {abs(round(variacion))}% menos que el mes pasado!',
                f'Del 1 al {hoy.day} llevas {_pesos(act.gastos)} contra {_pesos(ant.gastos)} '
                f'en {MESES[mes_ant - 1]}. Vas ahorrando {_pesos(ant.gastos - act.gastos)}.',
                'Mover el ahorro a una meta', 'perfil.html#tab-metas',
                ['Aparta esa diferencia antes de que se gaste'],
            ))

        # categoría que más se disparó
        subidas = []
        for cat, monto in act.por_categoria.items():
            previo = ant_completo.por_categoria.get(cat, 0)
            if previo == 0:
                continue          # categoría nueva o pago fijo que el mes pasado no se registró
            if monto - previo >= 50_000 and monto / previo >= 1.4:
                subidas.append((cat, monto, previo))
        if subidas:
            cat, monto, previo = max(subidas, key=lambda x: x[1] - x[2])
            recs.append(_nueva(
                'advertencia', 'Media', '🔺', f'"{cat}" se disparó este mes',
                f'Llevas {_pesos(monto)} en {cat} y aún no termina el mes; en todo '
                f'{MESES[mes_ant - 1]} gastaste {_pesos(previo)}.',
                'Ver mis gastos', 'finanzas.html',
                [f'Ponle un tope a {cat} de {_pesos(max(previo, monto * 0.8))} el resto del mes'],
                ahorro_potencial=monto - previo,
            ))

    # ─────────────────────────────────────────────────────
    # 8. CATEGORÍA DOMINANTE
    # ─────────────────────────────────────────────────────
    if cat_top and act.gastos > 0 and len(act.gastos_lista) >= 5:
        pct_top = monto_top / act.gastos * 100
        if pct_top >= 45 and cat_top != 'Arriendo':
            recs.append(_nueva(
                'info', 'Media', '📊', f'"{cat_top}" es el {round(pct_top)}% de tus gastos',
                f'{_pesos(monto_top)} en {act.cantidad_por_categoria[cat_top]} movimientos. '
                f'Bajarla un 15% libera {_pesos(monto_top * 0.15)} sin cambiar tu estilo de vida.',
                'Ver mis gastos', 'finanzas.html',
                [f'Define un tope mensual para {cat_top}', 'Compara precios antes de cada compra'],
                ahorro_potencial=monto_top * 0.15, progreso=100 - pct_top,
            ))

    # ─────────────────────────────────────────────────────
    # 9. GASTOS HORMIGA
    # ─────────────────────────────────────────────────────
    hormiga = [t for t in act.gastos_lista if float(t.monto) <= MONTO_HORMIGA]
    if len(hormiga) >= MIN_GASTOS_HORMIGA:
        total_h = sum(float(t.monto) for t in hormiga)
        anual = total_h / hoy.day * 365
        recs.append(_nueva(
            'advertencia', 'Media', '🐜', f'{len(hormiga)} gastos hormiga suman {_pesos(total_h)}',
            f'Compras pequeñas de menos de {_pesos(MONTO_HORMIGA)} (tintos, snacks, domicilios) '
            f'parecen inofensivas, pero a este ritmo serían {_pesos(anual)} al año.',
            'Ver mis gastos', 'finanzas.html',
            ['Fija un presupuesto semanal para "gustos"', 'Lleva el tinto o el almuerzo de casa 2 días por semana'],
            f'💡 Reducirlos a la mitad = {_pesos(anual / 2)} ahorrados en un año.',
            ahorro_potencial=total_h / 2,
        ))

    # ─────────────────────────────────────────────────────
    # 10. LUGAR DONDE MÁS GASTAS (mapa)
    # ─────────────────────────────────────────────────────
    por_lugar = defaultdict(lambda: {'monto': 0.0, 'n': 0})
    for t in act.gastos_lista:
        clave = t.tienda_id or (t.ubicacion_nombre or '').strip() or None
        if clave:
            por_lugar[clave]['monto'] += float(t.monto)
            por_lugar[clave]['n'] += 1
    if por_lugar:
        clave, datos = max(por_lugar.items(), key=lambda x: x[1]['monto'])
        if datos['n'] >= 2 and act.gastos > 0:
            if isinstance(clave, int):
                tienda = db.get(Tienda, clave)
                nombre_lugar = tienda.nombre if tienda and tienda.nombre else 'un mismo lugar'
            else:
                nombre_lugar = clave
            pct_lugar = datos['monto'] / act.gastos * 100
            recs.append(_nueva(
                'info', 'Baja', '📍', f'Donde más gastas: {nombre_lugar[:60]}',
                f'Este mes fuiste {datos["n"]} veces y dejaste {_pesos(datos["monto"])} '
                f'({round(pct_lugar)}% de tus gastos).',
                'Ver en el mapa', 'finanzas.html#cardMapa',
                ['Revisa si hay una opción más económica cerca en el mapa',
                 'Pregunta por planes de puntos o descuentos del lugar'],
            ))
    else:
        sin_ubic = sum(1 for t in act.gastos_lista if t.latitud is None)
        if sin_ubic >= 5:
            recs.append(_nueva(
                'info', 'Baja', '🗺️', 'Agrega la ubicación a tus gastos',
                'Tus gastos de este mes no tienen lugar. Si los ubicas en el mapa, FinanBot te dice '
                'en qué tiendas dejas más dinero.',
                'Ir al mapa', 'finanzas.html#cardMapa',
                ['Usa "Mi ubicación" o "Elegir en mapa" al registrar',
                 'En el chat, activa el GPS 📍 y se guarda solo'],
            ))

    # ─────────────────────────────────────────────────────
    # 11. AHORRO DEL MES vs META DEL PERFIL / REGLA
    # ─────────────────────────────────────────────────────
    objetivo_ahorro = meta_ahorro_perfil or (base_ingreso * aho / 100)
    if act.ingresos > 0 and objetivo_ahorro > 0:
        ahorrado = act.ahorro_total
        pct = ahorrado / objetivo_ahorro * 100
        if pct >= 100 and not alerta_ritmo:
            recs.append(_nueva(
                'exito', 'Baja', '✅', f'¡Cumpliste tu meta de ahorro de {nombre_mes}!',
                f'Objetivo: {_pesos(objetivo_ahorro)} · Llevas {_pesos(ahorrado)} '
                f'(incluye {_pesos(max(0, act.ahorro_metas))} que enviaste a tus metas).',
                'Simular inversión', 'simulador.html',
                [f'Excedente: {_pesos(ahorrado - objetivo_ahorro)}', 'Considera subir tu meta un 10%'],
                progreso=100,
            ))
        elif pct < 100 and hoy.day >= 10:
            recs.append(_nueva(
                'info', 'Media', '🎯', f'Vas al {round(pct)}% de tu ahorro del mes',
                f'Tu objetivo es ahorrar {_pesos(objetivo_ahorro)} y por ahora te quedan libres '
                f'{_pesos(ahorrado)}. Faltan {_pesos(objetivo_ahorro - ahorrado)}.',
                'Ajustar mis gastos', 'finanzas.html',
                ['Separa el ahorro el mismo día que te pagan',
                 'Activa un aporte automático en una meta'],
                ahorro_potencial=objetivo_ahorro - ahorrado, progreso=pct,
            ))

    # ─────────────────────────────────────────────────────
    # 12. METAS: fecha límite, casi listas, completadas
    # ─────────────────────────────────────────────────────
    for m in metas_activas:
        objetivo = float(m.monto_objetivo or 0)
        actual = float(m.monto_actual or 0)
        if objetivo <= 0:
            continue
        faltante = max(0.0, objetivo - actual)
        pct_m = actual / objetivo * 100
        limite = _fecha(getattr(m, 'fecha_limite', None))
        aporte_auto = float(getattr(m, 'monto_automatico', 0) or 0) if getattr(m, 'modo', '') == 'automatico' else 0

        if limite:
            if limite < hoy:
                recs.append(_nueva(
                    'alerta', 'Alta', '⏰', f'Venció la fecha de "{m.nombre}"',
                    f'La fecha límite era el {limite.strftime("%d/%m/%Y")} y vas al {round(pct_m)}%. '
                    f'Faltan {_pesos(faltante)}. Ajusta la fecha o el monto para no abandonarla.',
                    'Ir a mis metas', 'perfil.html#tab-metas', progreso=pct_m,
                ))
                continue
            meses_rest = max(1, (limite.year - hoy.year) * 12 + limite.month - hoy.month)
            necesario = faltante / meses_rest
            if aporte_auto and aporte_auto + 1 < necesario:
                recs.append(_nueva(
                    'advertencia', 'Media', '⏳', f'"{m.nombre}" no llegará a tiempo',
                    f'Para completarla antes del {limite.strftime("%d/%m/%Y")} necesitas {_pesos(necesario)}/mes, '
                    f'pero tu aporte automático es de {_pesos(aporte_auto)}.',
                    'Ajustar aporte', 'perfil.html#tab-metas',
                    [f'Sube el aporte a {_pesos(necesario)}', 'O mueve la fecha límite unos meses'],
                    progreso=pct_m,
                ))
                continue
            if not aporte_auto and (limite - hoy).days <= 60 and pct_m < 80:
                recs.append(_nueva(
                    'advertencia', 'Media', '⏳', f'Quedan {(limite - hoy).days} días para "{m.nombre}"',
                    f'Vas al {round(pct_m)}%. Necesitas {_pesos(necesario)} por mes para lograrlo a tiempo.',
                    'Añadir ahorro', 'perfil.html#tab-metas',
                    ['Activa el modo automático para no olvidarlo'], progreso=pct_m,
                ))
                continue

        if pct_m >= 80:
            recs.append(_nueva(
                'exito', 'Baja', '🚀', f'¡Casi lo logras! "{m.nombre}" al {round(pct_m)}%',
                f'Solo faltan {_pesos(faltante)} para completar esta meta.',
                'Añadir ahorro', 'perfil.html#tab-metas',
                [f'Con dos abonos de {_pesos(faltante / 2)} la cierras'], progreso=pct_m,
            ))

    if metas_completas:
        total = sum(float(m.monto_actual or 0) for m in metas_completas)
        nombres = ', '.join(f'"{m.nombre}"' for m in metas_completas[:2])
        recs.append(_nueva(
            'exito', 'Media', '🏆',
            f'¡Completaste {nombres}!' if len(metas_completas) <= 2 else f'¡{len(metas_completas)} metas completadas!',
            f'Tienes {_pesos(total)} listos. Puedes retirarlos a tu balance o dejarlos guardados '
            f'y crear una meta nueva más ambiciosa.',
            'Ir a mis metas', 'perfil.html#tab-metas',
            ['"Retirar dinero" devuelve el ahorro a tu sueldo', f'Siguiente reto: {_pesos(total * 1.5)}'],
        ))

    # ─────────────────────────────────────────────────────
    # 13. SIN METAS / FONDO DE EMERGENCIA
    # ─────────────────────────────────────────────────────
    gasto_mensual = max(ant_completo.gastos, act.gastos / hoy.day * dias_mes if act.gastos else 0)
    tiene_fondo = any(re.search(r'emergencia|imprevisto', (m.nombre or ''), re.I) for m in metas_ahorro)
    if not metas_ahorro and len(pasadas) >= 3:
        recs.append(_nueva(
            'advertencia', 'Media', '🎯', 'Crea tu primera meta de ahorro',
            'El dinero sin destino se gasta solo. Una meta concreta le da propósito a cada peso, '
            'y en modo automático FinanBot aporta por ti cada mes.',
            'Crear meta', 'perfil.html#tab-metas',
            ['Elige un objetivo alcanzable en 3 a 6 meses', 'Te avisamos al 75% y al 100%'],
        ))
    elif not tiene_fondo and gasto_mensual > 0:
        fondo = gasto_mensual * 3
        recs.append(_nueva(
            'info', 'Media', '🛡️', 'Arma tu fondo de emergencia',
            f'Con tus gastos actuales, tu fondo ideal es de {_pesos(fondo)} (3 meses). '
            f'Es lo primero que debes tener antes de invertir.',
            'Crear meta de emergencia', 'perfil.html#tab-metas',
            ['Protección ante despido o imprevistos de salud', 'Evitas endeudarte con tarjeta al 28% EA'],
            f'🎯 Con {_pesos(fondo / 12)} al mes lo completas en un año.',
        ))

    # ─────────────────────────────────────────────────────
    # 14. INVERTIR (si las cuentas están sanas)
    # ─────────────────────────────────────────────────────
    if act.ingresos > 0 and act.balance > 0 and act.gastos <= act.ingresos * 0.7:
        capital = round(act.balance * 0.5)
        if capital >= 100_000:
            recs.append(_nueva(
                'exito', 'Baja', '📈', f'Tu mes va bien: te sobran {_pesos(act.balance)}',
                f'Si pones {_pesos(capital)} en un CDT o fondo al 10% anual, en 5 años serían '
                f'{_pesos(capital * 1.10 ** 5)} sin hacer nada más.',
                'Ir al simulador', 'simulador.html',
                [f'En 1 año: {_pesos(capital * 1.10)}', 'En Colombia hay CDT desde $100.000',
                 'Los CDT están asegurados por Fogafín'],
                ahorro_potencial=capital * (1.10 ** 5 - 1), key='simulador',
            ))

    # ─────────────────────────────────────────────────────
    # 15. HACE DÍAS QUE NO REGISTRAS
    # ─────────────────────────────────────────────────────
    manuales = [t for t in pasadas if t.descripcion != TAG_SALARIO and not _es_aporte_meta(t)]
    if manuales:
        ultimo = max(_fecha(t.fecha) for t in manuales)
        dias = (hoy - ultimo).days
        if dias >= DIAS_SIN_REGISTRAR:
            recs.append(_nueva(
                'info', 'Media', '🔔', f'Llevas {dias} días sin registrar movimientos',
                f'Tu último registro fue el {ultimo.strftime("%d/%m")}. Si no anotas los gastos '
                f'del día a día, el análisis pierde precisión.',
                'Registrar ahora', 'finanzas.html',
                ['Dile al Chat FinanBot: "gasté 15 mil en almuerzo"', 'Toma 30 segundos al final del día'],
            ))

    # ─────────────────────────────────────────────────────
    # 16. MOVIMIENTOS PROGRAMADOS (fecha futura)
    # ─────────────────────────────────────────────────────
    if futuras:
        neto = sum(float(t.monto) if t.tipo == 'ingreso' else -float(t.monto) for t in futuras)
        recs.append(_nueva(
            'info', 'Baja', '⏳',
            f'{len(futuras)} movimiento{"s" if len(futuras) != 1 else ""} programado{"s" if len(futuras) != 1 else ""}',
            'Tienen fecha futura, así que aún no cuentan en tu balance; se sumarán solos el día que lleguen.',
            'Ver calendario', 'calendario.html',
            dato_clave=f'💡 Efecto neto en camino: {"+" if neto >= 0 else "-"}{_pesos(abs(neto))}',
        ))

    # ── ORDENAR Y NUMERAR ─────────────────────────────────
    orden_tipo = {'alerta': 0, 'advertencia': 1, 'info': 2, 'exito': 3}
    orden_prio = {'Alta': 0, 'Media': 1, 'Baja': 2}
    recs.sort(key=lambda r: (orden_tipo.get(r['tipo'], 4), orden_prio.get(r['prioridad'], 3)))
    return [_finalizar(r, i) for i, r in enumerate(recs[:MAX_RECOMENDACIONES], start=1)]


def _finalizar(r: dict, rid: int) -> dict:
    r['id'] = rid
    return r