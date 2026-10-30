import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models import Base, Categoria, CategoriaUsuario, Chat, ChatAdjunto, Transaccion, Usuario, sembrar_categorias
import routes.chat_route as chat_routes
from routes.chat_route import (
    _actualizar_contexto,
    _conversacion_ia_id,
    _categoria_activa_mencionada,
    _es_comando_categoria,
    _resolver_contexto,
    _texto_respuesta_local,
    ejecutar_accion,
    _guardar_chat,
)
from routes.chat_historial import obtener_mensajes
from routes.transacciones import eliminar_mi_categoria


def _crear_sesion_con_usuario():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    usuario = Usuario(
        nombre='Usuario de prueba',
        correo='categoria-chat@example.com',
        contrasena_hash='hash',
    )
    db.add(usuario)
    sembrar_categorias(db)
    db.add(Categoria(nombre='Fondo de emergencia', tipo='gasto', icono='🏷️'))
    db.commit()
    db.add(CategoriaUsuario(
        usuario_id=usuario.id,
        nombre='Fondo de emergencia',
        tipo='gasto',
        icono='🏷️',
        personalizada=True,
    ))
    db.commit()
    return engine, db, usuario


def test_siembra_categorias_y_es_idempotente():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        sembrar_categorias(db)
        total = db.query(Categoria).count()
        sembrar_categorias(db)

        categoria = db.query(Categoria).filter_by(nombre='Alimentación').one()
        assert categoria.tipo == 'gasto'
        assert categoria.icono == '🍔'
        assert db.query(Categoria).count() == total
    finally:
        db.close()


def test_chat_crea_categoria_personalizada():
    engine, db, usuario = _crear_sesion_con_usuario()
    try:
        accion = ejecutar_accion(
            'Crea la categoría Gimnasio para gastos',
            usuario.id,
            {},
            db,
        )

        assert accion['tipo'] == 'categoria_creada'
        assert db.query(Categoria).filter_by(nombre='Gimnasio', tipo='gasto').one()
    finally:
        db.close()
        engine.dispose()

def test_chat_pregunta_tipo_si_no_se_especifica_al_crear_categoria():
    engine, db, usuario = _crear_sesion_con_usuario()
    try:
        accion = ejecutar_accion('Crea la categoría Gimnasio', usuario.id, {}, db)

        assert accion == {'tipo': 'pide_tipo_categoria', 'nombre': 'Gimnasio'}
        _actualizar_contexto('categoria-tipo', accion, 'Crea la categoría Gimnasio')
        respuesta = _resolver_contexto('gasto', usuario.id, {}, 'categoria-tipo', db)

        assert respuesta['tipo'] == 'categoria_creada'
        assert db.query(Categoria).filter_by(nombre='Gimnasio', tipo='gasto').one()
    finally:
        db.close()
        engine.dispose()


def test_chat_elimina_categoria_y_conserva_movimientos():
    engine, db, usuario = _crear_sesion_con_usuario()
    try:
        db.add(Transaccion(
            usuario_id=usuario.id,
            categoria='Fondo de emergencia',
            tipo='gasto',
            monto=25000,
            fecha=date(2026, 10, 14),
        ))
        db.commit()

        accion = ejecutar_accion(
            'Elimina la categoría Fondo de emergencia',
            usuario.id,
            {},
            db,
        )

        assert accion['tipo'] == 'categoria_eliminada'
        assert accion['movidos'] == 1
        assert accion['destino'] == 'Otros gastos'
        assert db.query(Transaccion).filter_by(
            usuario_id=usuario.id, categoria='Otros gastos',
        ).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_chat_reconoce_categoria_personalizada_activa():
    engine, db, usuario = _crear_sesion_con_usuario()
    try:
        assert _categoria_activa_mencionada(
            'Registra un gasto en Fondo de emergencia',
            'gasto',
            usuario.id,
            db,
        ) == 'Fondo de emergencia'
    finally:
        db.close()
        engine.dispose()


def test_chat_no_confunde_crear_un_gasto_con_crear_una_categoria():
    assert not _es_comando_categoria('Crea un gasto en la categoría Alimentación')


def test_chat_no_sugiere_categoria_personalizada_oculta():
    engine, db, usuario = _crear_sesion_con_usuario()
    try:
        db.query(CategoriaUsuario).filter_by(
            usuario_id=usuario.id, nombre='Fondo de emergencia',
        ).one().oculta = True
        db.commit()

        assert _categoria_activa_mencionada(
            'Fondo de emergencia',
            'gasto',
            usuario.id,
            db,
        ) is None
    finally:
        db.close()
        engine.dispose()


def test_chat_lista_categorias_activas_tras_eliminacion():
    engine, db, usuario = _crear_sesion_con_usuario()
    try:
        eliminar_mi_categoria('Alimentación', str(usuario.id), db)

        accion = ejecutar_accion(
            'Qué categorías tengo en gastos e ingresos',
            usuario.id,
            {},
            db,
        )
        respuesta = _texto_respuesta_local(accion)

        assert accion['tipo'] == 'categorias_disponibles'
        assert 'Alimentación' not in respuesta
        assert 'Fondo de emergencia' in respuesta
        assert 'Otros gastos' in respuesta
        assert 'Salario' in respuesta
    finally:
        db.close()
        engine.dispose()


def test_chat_pasa_el_id_de_conversacion_a_la_ia(monkeypatch):
    engine, db, usuario = _crear_sesion_con_usuario()
    conv_id = str(uuid.uuid4())
    recibido = {}
    acciones_locales = []

    class FinanBotFalso:
        def responder_con_acciones(self, mensaje, ctx, accion, conversacion_id=None):
            recibido['conversacion_id'] = conversacion_id
            return 'Respuesta de prueba', []

    monkeypatch.setattr(chat_routes, 'sesiones', {})
    monkeypatch.setattr(chat_routes, 'FinanBotIA', FinanBotFalso)
    monkeypatch.setattr(chat_routes, '_cargar_contexto', lambda uid, session: {'usuario_id': uid})
    monkeypatch.setattr(chat_routes, '_actualizar_contexto', lambda *args: None)
    monkeypatch.setattr(chat_routes, '_resolver_contexto', lambda *args: None)
    monkeypatch.setattr(chat_routes, 'ejecutar_accion', lambda *args: acciones_locales.append(args))
    monkeypatch.setattr(chat_routes, '_agregar_disclaimers_si_necesario', lambda respuesta, mensaje: respuesta)
    monkeypatch.setattr(chat_routes, '_agregar_avisos_metas', lambda respuesta, ctx, accion: respuesta)
    monkeypatch.setattr(chat_routes, '_guardar_chat', lambda *args: conv_id)

    try:
        resultado = chat_routes.mensaje(
            {'mensaje': 'Crea un documento de presupuesto mensual', 'conversacion_id': conv_id},
            str(usuario.id),
            db,
        )

        assert resultado['respuesta'] == 'Respuesta de prueba'
        assert recibido['conversacion_id'] == conv_id
        assert resultado['documento'] is None
        assert acciones_locales == []
        assert f'user:{usuario.id}:conversation:{conv_id}' in chat_routes.sesiones
    finally:
        db.close()
        engine.dispose()


def test_documento_generado_se_conserva_en_el_historial_del_chat():
    engine, db, usuario = _crear_sesion_con_usuario()
    conversacion_id = str(uuid.uuid4())
    documento = {
        'titulo': 'Presupuesto mensual',
        'formato': 'pdf',
        'contenido': '# Resumen\nAhorro recomendado',
    }
    try:
        _guardar_chat(
            db, int(usuario.id), conversacion_id, 'Crea el documento',
            'Documento listo.', documento,
        )

        mensajes = obtener_mensajes(conversacion_id, str(usuario.id), db)

        assert mensajes[0]['documento'] == documento
    finally:
        db.close()
        engine.dispose()


def test_migracion_agrega_documento_a_tabla_de_chat_existente(monkeypatch):
    from presentation import api as api_routes

    engine = create_engine('sqlite:///:memory:')
    tablas = [tabla for tabla in Base.metadata.sorted_tables if tabla.name != 'chats']
    Base.metadata.create_all(bind=engine, tables=tablas)
    with engine.begin() as conexion:
        conexion.execute(text(
            'CREATE TABLE chats ('
            'id INTEGER PRIMARY KEY, usuario_id INTEGER, conversacion_id VARCHAR(36) NOT NULL, '
            'titulo VARCHAR(100) NOT NULL, mensaje TEXT NOT NULL, respuesta TEXT NOT NULL, '
            'es_invitado BOOLEAN, fecha DATETIME)'
        ))
    monkeypatch.setattr(api_routes, 'engine', engine)
    try:
        api_routes._migrar_esquema()

        columnas = {columna['name'] for columna in inspect(engine).get_columns('chats')}

        assert 'documento' in columnas
    finally:
        engine.dispose()


def test_solicitud_de_documento_devuelve_archivo_y_lo_guarda(monkeypatch):
    engine, db, usuario = _crear_sesion_con_usuario()
    conversacion_id = str(uuid.uuid4())
    documento = {
        'titulo': 'Presupuesto mensual',
        'formato': 'docx',
        'contenido': '# Resumen\nAhorro recomendado',
    }

    class FinanBotFalso:
        def responder_con_acciones(self, mensaje, ctx, accion, conversacion_id=None):
            self._documento_generado = documento
            return 'Documento preparado.', []

    monkeypatch.setattr(chat_routes, 'sesiones', {})
    monkeypatch.setattr(chat_routes, 'FinanBotIA', FinanBotFalso)
    monkeypatch.setattr(chat_routes, '_cargar_contexto', lambda uid, session: {'usuario_id': uid})
    monkeypatch.setattr(chat_routes, '_actualizar_contexto', lambda *args: None)
    monkeypatch.setattr(chat_routes, '_resolver_contexto', lambda *args: None)
    monkeypatch.setattr(chat_routes, '_agregar_disclaimers_si_necesario', lambda respuesta, mensaje: respuesta)
    monkeypatch.setattr(chat_routes, '_agregar_avisos_metas', lambda respuesta, ctx, accion: respuesta)

    try:
        resultado = chat_routes.mensaje(
            {'mensaje': 'Créame un documento de presupuesto mensual', 'conversacion_id': conversacion_id},
            str(usuario.id),
            db,
        )

        historial = obtener_mensajes(conversacion_id, str(usuario.id), db)

        assert resultado['documento'] == documento
        assert historial[0]['documento'] == documento
    finally:
        db.close()
        engine.dispose()


def test_documento_en_chat_conserva_referencia_a_foto_adjunta(monkeypatch):
    engine, db, usuario = _crear_sesion_con_usuario()
    conversacion_id = str(uuid.uuid4())
    adjunto_id = str(uuid.uuid4())
    db.add(ChatAdjunto(
        id=adjunto_id,
        usuario_id=usuario.id,
        nombre='foto presupuesto.png',
        ruta=f'chat/{usuario.id}/{adjunto_id}.png',
        mime_type='image/png',
        texto_extraido='',
    ))
    db.commit()
    documento = {
        'titulo': 'Presupuesto visual',
        'formato': 'pdf',
        'contenido': '# Resumen\nPresupuesto con foto adjunta.',
        'graficos': [],
    }

    class FinanBotFalso:
        def responder_con_acciones(
            self, mensaje, ctx, accion, conversacion_id=None, imagenes=None,
        ):
            self._documento_generado = documento
            return 'Documento preparado.', []

    monkeypatch.setattr(chat_routes, 'sesiones', {})
    monkeypatch.setattr(chat_routes, 'FinanBotIA', FinanBotFalso)
    monkeypatch.setattr(
        chat_routes, 'preparar_adjuntos_chat',
        lambda *args: ('', [{'mime_type': 'image/png', 'data': b'foto'}]),
    )
    monkeypatch.setattr(chat_routes, '_cargar_contexto', lambda uid, session: {'usuario_id': uid})
    monkeypatch.setattr(chat_routes, '_actualizar_contexto', lambda *args: None)
    monkeypatch.setattr(chat_routes, '_resolver_contexto', lambda *args: None)
    monkeypatch.setattr(chat_routes, '_agregar_disclaimers_si_necesario', lambda respuesta, mensaje: respuesta)
    monkeypatch.setattr(chat_routes, '_agregar_avisos_metas', lambda respuesta, ctx, accion: respuesta)

    try:
        resultado = chat_routes.mensaje(
            {
                'mensaje': 'Incluye las fotos adjuntas en el documento',
                'adjuntos': [adjunto_id],
                'conversacion_id': conversacion_id,
            },
            str(usuario.id),
            db,
        )

        assert resultado['documento']['imagenes'] == [adjunto_id]
        assert obtener_mensajes(conversacion_id, str(usuario.id), db)[0]['documento'] == resultado['documento']
    finally:
        db.close()
        engine.dispose()


def test_ia_no_reutiliza_contexto_de_una_conversacion_ajena():
    engine, db, usuario = _crear_sesion_con_usuario()
    otro_usuario = Usuario(
        nombre='Otro usuario',
        correo='otro-chat@example.com',
        contrasena_hash='hash',
    )
    conv_id = str(uuid.uuid4())
    db.add(otro_usuario)
    db.commit()
    db.add(Chat(
        usuario_id=otro_usuario.id,
        conversacion_id=conv_id,
        titulo='Conversación ajena',
        mensaje='Mensaje privado',
        respuesta='Respuesta privada',
    ))
    db.commit()
    try:
        assert _conversacion_ia_id(db, usuario.id, conv_id) is None
    finally:
        db.close()
        engine.dispose()
