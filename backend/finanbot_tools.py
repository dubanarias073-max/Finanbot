# finanbot_tools.py
# ══════════════════════════════════════════════════════════════════
#  Herramientas que Gemini puede llamar (function calling).
#
#  Reglas de seguridad (no cambiar):
#   · El usuario (uid) y la sesión de BD los pone el SERVIDOR; el modelo
#     nunca los elige ni los recibe como argumento.
#   · Solo se crea, edita o borra dentro del MES ACTUAL.
#   · Borrar exige confirmado=True (el modelo debe haber preguntado antes).
#   · Cada herramienta valida sus argumentos: el modelo puede equivocarse.
#
#  Se evita importar routes.chat_route (import circular): la función que
#  normaliza categorías se recibe por parámetro desde chat_route.
# ══════════════════════════════════════════════════════════════════
from __future__ import annotations

from datetime import date

from application.services import metas_service
from models import Transaccion, MetaAhorro, eliminar_tiendas_sin_transacciones
from timezone import bogota_today

MONTO_MAX = 10 ** 12

DECLARACIONES = [
    {
        'name': 'registrar_movimiento',
        'description': 'Registra un gasto o ingreso con fecha de HOY. Úsala solo cuando la persona '
                       'dio un monto. Si no dijo la categoría, pregúntala antes de llamar.',
        'parameters': {
            'type': 'object',
            'properties': {
                'tipo': {'type': 'string', 'enum': ['gasto', 'ingreso']},
                'monto': {'type': 'number', 'description': 'Monto en pesos, sin símbolos.'},
                'categoria': {'type': 'string', 'description': 'Una de las categorías válidas.'},
                'descripcion': {'type': 'string', 'description': 'Opcional, texto corto.'},
            },
            'required': ['tipo', 'monto', 'categoria'],
        },
    },
    {
        'name': 'listar_movimientos',
        'description': 'Lista los movimientos del mes actual con su id. Llámala antes de editar o '
                       'eliminar para saber el id correcto.',
        'parameters': {
            'type': 'object',
            'properties': {
                'tipo': {'type': 'string', 'enum': ['gasto', 'ingreso']},
                'limite': {'type': 'integer', 'description': 'Máximo 20. Por defecto 10.'},
            },
        },
    },
    {
        'name': 'editar_movimiento',
        'description': 'Cambia el monto de un movimiento del mes actual (id sacado de listar_movimientos).',
        'parameters': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'monto': {'type': 'number'},
            },
            'required': ['id', 'monto'],
        },
    },
    {
        'name': 'eliminar_movimiento',
        'description': 'Elimina un movimiento del mes actual. Antes pregunta a la persona y solo '
                       'envía confirmado=true si ya confirmó en este chat.',
        'parameters': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'confirmado': {'type': 'boolean'},
            },
            'required': ['id', 'confirmado'],
        },
    },
    {
        'name': 'listar_metas',
        'description': 'Lista las metas de ahorro con id, objetivo y monto actual.',
        'parameters': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'crear_meta',
        'description': 'Crea una meta de ahorro. Manual: sin aportes automáticos. Automática: requiere '
                       'monto_automatico (aporte mensual) y dia_automatico (1-31).',
        'parameters': {
            'type': 'object',
            'properties': {
                'nombre': {'type': 'string'},
                'monto_objetivo': {'type': 'number'},
                'modo': {'type': 'string', 'enum': ['manual', 'automatico']},
                'monto_automatico': {'type': 'number'},
                'dia_automatico': {'type': 'integer'},
            },
            'required': ['nombre', 'monto_objetivo'],
        },
    },
    {
        'name': 'abonar_meta',
        'description': 'Suma dinero a una meta (solo suma, nunca resta) y lo descuenta del balance '
                       'como gasto. Usa el id de listar_metas.',
        'parameters': {
            'type': 'object',
            'properties': {
                'meta_id': {'type': 'integer'},
                'monto': {'type': 'number'},
            },
            'required': ['meta_id', 'monto'],
        },
    },
    {
        'name': 'editar_meta',
        'description': 'Edita una meta de ahorro existente (id de listar_metas). Envía SOLO los campos '
                       'que la persona quiere cambiar: nombre, monto_objetivo, fecha_limite (AAAA-MM-DD, '
                       'o "" para quitarla), prioridad, modo y, si es automático, monto_automatico y '
                       'dia_automatico. NO cambia lo ya ahorrado: para sumar usa abonar_meta.',
        'parameters': {
            'type': 'object',
            'properties': {
                'meta_id': {'type': 'integer'},
                'nombre': {'type': 'string'},
                'monto_objetivo': {'type': 'number'},
                'fecha_limite': {'type': 'string', 'description': 'AAAA-MM-DD, o "" para quitarla.'},
                'prioridad': {'type': 'string', 'enum': ['baja', 'media', 'alta']},
                'modo': {'type': 'string', 'enum': ['manual', 'automatico']},
                'monto_automatico': {'type': 'number'},
                'dia_automatico': {'type': 'integer'},
            },
            'required': ['meta_id'],
        },
    },
]

NOMBRES = {d['name'] for d in DECLARACIONES}


def _mes_actual() -> tuple[date, date]:
    hoy = bogota_today()
    inicio = hoy.replace(day=1)
    fin = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    return inicio, fin


class HerramientasFinanBot:
    def __init__(self, uid: int, db, ctx: dict | None, resolver_categoria):
        self.uid = uid
        self.db = db
        self.ctx = ctx or {}
        self.resolver_categoria = resolver_categoria
        self.ejecutadas: list[dict] = []   # solo acciones que cambiaron datos

    # ── Entrada única ────────────────────────────────────────────
    def ejecutar(self, nombre: str, args: dict | None) -> dict:
        if nombre not in NOMBRES:
            return {'error': 'Herramienta desconocida.'}
        try:
            return getattr(self, f'_t_{nombre}')(**(args or {}))
        except TypeError:
            return {'error': 'Argumentos inválidos.'}
        except ValueError as e:
            return {'error': str(e)}
        except Exception as e:
            self.db.rollback()
            print(f'[FinanBot tools] {nombre} falló: {e}')
            return {'error': 'No se pudo completar la acción.'}

    # ── Validaciones ─────────────────────────────────────────────
    @staticmethod
    def _monto(v) -> float:
        try:
            m = float(v)
        except (TypeError, ValueError):
            raise ValueError('El monto no es un número.')
        if not (0 < m <= MONTO_MAX):
            raise ValueError('El monto debe ser mayor que 0 y razonable.')
        return round(m, 2)

    def _movimiento_del_mes(self, id_) -> Transaccion:
        t = self.db.get(Transaccion, int(id_))
        if not t or t.usuario_id != self.uid:
            raise ValueError('No encontré ese movimiento.')
        inicio, fin = _mes_actual()
        if not (t.fecha and inicio <= t.fecha < fin):
            raise ValueError('Solo se pueden modificar movimientos del mes actual.')
        return t

    def _meta(self, id_) -> MetaAhorro:
        m = self.db.get(MetaAhorro, int(id_))
        if not m or m.usuario_id != self.uid:
            raise ValueError('No encontré esa meta.')
        return m

    def _ajustar(self, tipo: str, categoria: str, delta: float) -> None:
        """Mantiene al día los totales de ctx (el mismo dict que usa chat_route)
        para que el balance que se le muestra a la persona sea el de DESPUÉS."""
        c = self.ctx
        if not c:
            return
        if tipo == 'gasto':
            c['total_gastos'] = c.get('total_gastos', 0) + delta
            cats = c.setdefault('gastos_por_categoria', {})
            cats[categoria] = cats.get(categoria, 0) + delta
            if cats[categoria] <= 0:
                cats.pop(categoria, None)
        else:
            c['total_ingresos'] = c.get('total_ingresos', 0) + delta
        c['balance'] = c.get('total_ingresos', 0) - c.get('total_gastos', 0)

    # ── Movimientos ──────────────────────────────────────────────
    def _t_registrar_movimiento(self, tipo, monto, categoria, descripcion=None):
        if tipo not in ('gasto', 'ingreso'):
            raise ValueError('El tipo debe ser gasto o ingreso.')
        monto = self._monto(monto)
        cat = self.resolver_categoria(categoria, tipo, self.uid, self.db)
        u = self.ctx.get('ubicacion_actual') or {}
        ubic = ({'ubicacion_nombre': u.get('nombre'), 'latitud': u['lat'], 'longitud': u['lng']}
                if u.get('lat') is not None and u.get('lng') is not None else {})
        t = Transaccion(usuario_id=self.uid, categoria=cat, tipo=tipo, monto=monto,
                        descripcion=(descripcion or 'Registrado por FinanBot')[:100],
                        fecha=bogota_today(), **ubic)
        self.db.add(t)
        self.db.commit()
        accion = {'tipo': f'{tipo}_registrado', 'monto': monto, 'categoria': cat, 'id': t.id}
        if ubic:
            accion.update(ubic)
            if u.get('precision') is not None:
                accion['precision_m'] = u['precision']
        self.ejecutadas.append(accion)
        self._ajustar(tipo, cat, monto)
        return {'ok': True, 'id': t.id, 'tipo': tipo, 'monto': monto, 'categoria': cat,
                'con_ubicacion': bool(ubic), 'balance_actual': self.ctx.get('balance')}

    def _t_listar_movimientos(self, tipo=None, limite=10):
        inicio, fin = _mes_actual()
        q = self.db.query(Transaccion).filter(
            Transaccion.usuario_id == self.uid,
            Transaccion.fecha >= inicio, Transaccion.fecha < fin)
        if tipo in ('gasto', 'ingreso'):
            q = q.filter(Transaccion.tipo == tipo)
        limite = max(1, min(int(limite or 10), 20))
        filas = q.order_by(Transaccion.fecha.desc(), Transaccion.id.desc()).limit(limite).all()
        return {'movimientos': [{
            'id': t.id, 'tipo': t.tipo, 'categoria': t.categoria,
            'monto': float(t.monto), 'fecha': str(t.fecha),
            'descripcion': (t.descripcion or '')[:60],
        } for t in filas]}

    def _t_editar_movimiento(self, id, monto):
        t = self._movimiento_del_mes(id)
        monto = self._monto(monto)
        anterior = float(t.monto)
        t.monto = monto
        self.db.commit()
        self.ejecutadas.append({'tipo': f'{t.tipo}_editado', 'categoria': t.categoria,
                                'monto': monto, 'monto_anterior': anterior, 'id': t.id})
        self._ajustar(t.tipo, t.categoria, monto - anterior)
        return {'ok': True, 'id': t.id, 'categoria': t.categoria,
                'monto_anterior': anterior, 'monto_nuevo': monto,
                'balance_actual': self.ctx.get('balance')}

    def _t_eliminar_movimiento(self, id, confirmado=False):
        t = self._movimiento_del_mes(id)
        if confirmado is not True:
            return {'ok': False, 'pide_confirmacion': True,
                    'detalle': f'{t.tipo} de {t.categoria} por {float(t.monto):.0f}'}
        tipo, cat, monto, tienda_id = t.tipo, t.categoria, float(t.monto), t.tienda_id
        self.db.delete(t)
        eliminar_tiendas_sin_transacciones(self.db, [tienda_id])
        self.db.commit()
        self.ejecutadas.append({'tipo': f'{tipo}_eliminado', 'categoria': cat, 'monto': monto})
        self._ajustar(tipo, cat, -monto)
        return {'ok': True, 'eliminado': {'tipo': tipo, 'categoria': cat, 'monto': monto},
                'balance_actual': self.ctx.get('balance')}

    # ── Metas ────────────────────────────────────────────────────
    def _t_listar_metas(self):
        metas = self.db.query(MetaAhorro).filter_by(usuario_id=self.uid).all()
        return {'metas': [{
            'id': m.id, 'nombre': m.nombre,
            'objetivo': float(m.monto_objetivo), 'actual': float(m.monto_actual or 0),
            'modo': m.modo, 'completada': bool(m.completada),
            'fecha_limite': str(m.fecha_limite) if m.fecha_limite else None,
            'prioridad': m.prioridad or 'media',
            'monto_automatico': float(m.monto_automatico) if m.monto_automatico is not None else None,
            'dia_automatico': m.dia_automatico,
        } for m in metas if getattr(m, 'tipo', 'ahorro') == 'ahorro']}

    def _t_crear_meta(self, nombre, monto_objetivo, modo='manual',
                      monto_automatico=None, dia_automatico=None):
        nombre = str(nombre or '').strip()[:50]
        if len(nombre) < 2:
            raise ValueError('La meta necesita un nombre.')
        objetivo = self._monto(monto_objetivo)
        if modo == 'automatico':
            monto_automatico = self._monto(monto_automatico)
            dia = int(dia_automatico or 0)
            if not 1 <= dia <= 31:
                raise ValueError('El día del mes debe estar entre 1 y 31.')
        else:
            modo, monto_automatico, dia = 'manual', None, None
        m = MetaAhorro(usuario_id=self.uid, nombre=nombre.capitalize(),
                       monto_objetivo=objetivo, monto_actual=0, modo=modo,
                       monto_automatico=monto_automatico, dia_automatico=dia)
        self.db.add(m)
        self.db.commit()
        self.ejecutadas.append({'tipo': 'meta_creada', 'nombre': m.nombre, 'monto': objetivo,
                                'id': m.id, 'modo': modo, 'monto_automatico': monto_automatico,
                                'dia_automatico': dia})
        return {'ok': True, 'id': m.id, 'nombre': m.nombre, 'objetivo': objetivo, 'modo': modo}

    def _t_abonar_meta(self, meta_id, monto):
        m = self._meta(meta_id)
        monto = self._monto(monto)
        # mismo camino que "Añadir ahorro" en la web: suma a la meta y lo descuenta del balance
        try:
            r = metas_service.abonar(self.db, self.uid, m, monto)
        except metas_service.MetaError as e:
            raise ValueError(str(e))
        nuevo_total = r['nuevo_total']
        self.ejecutadas.append({'tipo': 'meta_abonada', 'nombre': m.nombre,
                                'monto_abonado': monto, 'nuevo_total': nuevo_total, 'id': m.id})
        return {'ok': True, 'nombre': m.nombre, 'abonado': monto, 'nuevo_total': nuevo_total,
                'completada': bool(m.completada)}

    def _t_editar_meta(self, meta_id, nombre=None, monto_objetivo=None, fecha_limite=None,
                       prioridad=None, modo=None, monto_automatico=None, dia_automatico=None):
        m = self._meta(meta_id)
        if (getattr(m, 'tipo', None) or 'ahorro') != 'ahorro':
            raise ValueError('Los límites de gasto se editan desde Mi Perfil.')
        cambios = {}

        if nombre is not None:
            nombre = str(nombre).strip()[:50]
            if len(nombre) < 2:
                raise ValueError('La meta necesita un nombre.')
            # Conserva el icono al inicio del nombre, como lo guarda Mi Perfil
            if m.icono and not nombre.startswith(m.icono):
                nombre = f'{m.icono} {nombre}'
            m.nombre = nombre
            cambios['nombre'] = nombre

        if monto_objetivo is not None:
            objetivo = self._monto(monto_objetivo)
            m.monto_objetivo = objetivo
            m.completada = float(m.monto_actual or 0) >= objetivo
            cambios['monto_objetivo'] = objetivo

        if fecha_limite is not None:
            if str(fecha_limite).strip():
                try:
                    fecha = date.fromisoformat(str(fecha_limite).strip())
                except ValueError:
                    raise ValueError('La fecha límite debe tener formato AAAA-MM-DD.')
                if fecha < bogota_today():
                    raise ValueError('La fecha límite no puede estar en el pasado.')
                m.fecha_limite = fecha
                cambios['fecha_limite'] = fecha.isoformat()
            else:
                m.fecha_limite = None
                cambios['fecha_limite'] = None

        if prioridad is not None:
            if prioridad not in ('baja', 'media', 'alta'):
                raise ValueError("La prioridad debe ser 'baja', 'media' o 'alta'.")
            m.prioridad = prioridad
            cambios['prioridad'] = prioridad

        modo_final = modo if modo is not None else (m.modo or 'manual')
        if modo is not None and modo not in ('manual', 'automatico'):
            raise ValueError("El modo debe ser 'manual' o 'automatico'.")
        if modo_final == 'automatico':
            aporte = monto_automatico if monto_automatico is not None else m.monto_automatico
            dia = dia_automatico if dia_automatico is not None else m.dia_automatico
            aporte = self._monto(aporte)
            dia = int(dia or 0)
            if not 1 <= dia <= 31:
                raise ValueError('El día del mes debe estar entre 1 y 31.')
            if modo is not None or monto_automatico is not None or dia_automatico is not None:
                m.modo, m.monto_automatico, m.dia_automatico = 'automatico', aporte, dia
                cambios.update(modo='automatico', monto_automatico=aporte, dia_automatico=dia)
        elif modo == 'manual':
            m.modo, m.monto_automatico, m.dia_automatico = 'manual', None, None
            cambios['modo'] = 'manual'

        if not cambios:
            raise ValueError('No indicaste qué cambiar de la meta.')

        self.db.commit()
        self.ejecutadas.append({'tipo': 'meta_editada', 'id': m.id, 'nombre': m.nombre,
                                'cambios': cambios})
        return {'ok': True, 'id': m.id, 'nombre': m.nombre, 'cambios': cambios,
                'objetivo': float(m.monto_objetivo), 'actual': float(m.monto_actual or 0),
                'completada': bool(m.completada)}