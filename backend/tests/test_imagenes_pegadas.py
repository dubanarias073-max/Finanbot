"""Pruebas de la importación de imágenes de internet al chat (pegar enlace/imagen)."""
from io import BytesIO
from pathlib import Path
import socket
import sys

from PIL import Image
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import settings  # noqa: E402
from database import Base  # noqa: E402
from models import ChatAdjunto, Usuario  # noqa: E402
import routes.archivos as archivos  # noqa: E402


def _png_bytes() -> bytes:
    salida = BytesIO()
    Image.new('RGB', (10, 6), color='teal').save(salida, format='PNG')
    return salida.getvalue()


class RespuestaFalsa:
    def __init__(self, status=200, tipo='image/png', cuerpo=None, ubicacion=None, longitud=None):
        self.status_code = status
        self.headers = {'Content-Type': tipo}
        if ubicacion:
            self.headers['Location'] = ubicacion
        if longitud is not None:
            self.headers['Content-Length'] = str(longitud)
        self._cuerpo = _png_bytes() if cuerpo is None else cuerpo

    def iter_content(self, tamano):
        for i in range(0, len(self._cuerpo), tamano):
            yield self._cuerpo[i:i + tamano]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SesionFalsa:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.urls = []

    def get(self, url, **kwargs):
        assert kwargs['allow_redirects'] is False
        self.urls.append(url)
        return self.respuestas.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _dns(monkeypatch, ip='93.184.216.34'):
    def falso(host, puerto, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, puerto))]
    monkeypatch.setattr(archivos.socket, 'getaddrinfo', falso)


def _sesion(monkeypatch, *respuestas):
    sesion = SesionFalsa(respuestas)
    monkeypatch.setattr(archivos.requests, 'Session', lambda: sesion)
    return sesion


@pytest.mark.parametrize('ip,esperado', [
    ('8.8.8.8', True),
    ('127.0.0.1', False),
    ('10.0.0.5', False),
    ('192.168.1.20', False),
    ('169.254.169.254', False),
    ('::1', False),
    ('::ffff:127.0.0.1', False),
])
def test_solo_direcciones_publicas(ip, esperado):
    assert archivos._ip_es_publica(ip) is esperado


@pytest.mark.parametrize('url', [
    'file:///etc/passwd',
    'ftp://ejemplo.com/a.png',
    'http://usuario:clave@ejemplo.com/a.png',
    'http:///sin-host.png',
    'http://ejemplo.com:abc/a.png',
])
def test_rechaza_esquemas_y_urls_invalidas(url):
    with pytest.raises(HTTPException) as error:
        archivos._validar_url_publica(url)
    assert error.value.status_code == 400


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.1.2.3', '169.254.169.254'])
def test_rechaza_hosts_que_resuelven_a_red_interna(monkeypatch, ip):
    _dns(monkeypatch, ip)
    with pytest.raises(HTTPException) as error:
        archivos._validar_url_publica('http://interno.example/a.png')
    assert error.value.status_code == 400


def test_descarga_imagen_publica_y_nombra_con_extension(monkeypatch):
    _dns(monkeypatch)
    sesion = _sesion(monkeypatch, RespuestaFalsa())
    nombre, contenido = archivos._descargar_imagen('https://cdn.example.com/fotos/recibo.php?id=3')
    assert nombre == 'recibo.png'
    assert Image.open(BytesIO(contenido)).size == (10, 6)
    assert sesion.urls == ['https://cdn.example.com/fotos/recibo.php?id=3']


def test_rechaza_contenido_que_no_es_imagen(monkeypatch):
    _dns(monkeypatch)
    _sesion(monkeypatch, RespuestaFalsa(tipo='text/html', cuerpo=b'<html></html>'))
    with pytest.raises(HTTPException) as error:
        archivos._descargar_imagen('https://ejemplo.com/pagina')
    assert error.value.status_code == 415


def test_rechaza_imagen_demasiado_grande(monkeypatch):
    _dns(monkeypatch)
    _sesion(monkeypatch, RespuestaFalsa(longitud=archivos.MAX_ARCHIVO_BYTES + 1))
    with pytest.raises(HTTPException) as error:
        archivos._descargar_imagen('https://ejemplo.com/enorme.png')
    assert error.value.status_code == 413

    _sesion(monkeypatch, RespuestaFalsa(cuerpo=b'0' * (archivos.MAX_ARCHIVO_BYTES + 1)))
    with pytest.raises(HTTPException) as error:
        archivos._descargar_imagen('https://ejemplo.com/enorme.png')
    assert error.value.status_code == 413


def test_sigue_redirecciones_pero_revalida_cada_destino(monkeypatch):
    destinos = {'cdn.example.com': '93.184.216.34', 'interno.local': '127.0.0.1'}

    def falso(host, puerto, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (destinos[host], puerto))]
    monkeypatch.setattr(archivos.socket, 'getaddrinfo', falso)

    _sesion(monkeypatch,
            RespuestaFalsa(status=302, ubicacion='/final.png'),
            RespuestaFalsa())
    nombre, _ = archivos._descargar_imagen('https://cdn.example.com/inicio')
    assert nombre == 'final.png'

    _sesion(monkeypatch, RespuestaFalsa(status=302, ubicacion='http://interno.local/secreto.png'))
    with pytest.raises(HTTPException) as error:
        archivos._descargar_imagen('https://cdn.example.com/inicio')
    assert error.value.status_code == 400


def test_limita_las_redirecciones(monkeypatch):
    _dns(monkeypatch)
    _sesion(monkeypatch, *[RespuestaFalsa(status=301, ubicacion='/otra') for _ in range(5)])
    with pytest.raises(HTTPException) as error:
        archivos._descargar_imagen('https://ejemplo.com/bucle')
    assert error.value.status_code == 400


def test_importar_desde_url_guarda_la_imagen_del_usuario(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    sesion_db = sessionmaker(bind=engine)()
    monkeypatch.setattr(settings, 'UPLOADS_DIR', tmp_path)
    usuario = Usuario(nombre='Luis', correo='luis-url@example.com', contrasena_hash='hash')
    sesion_db.add(usuario)
    sesion_db.commit()
    _dns(monkeypatch)
    _sesion(monkeypatch, RespuestaFalsa())

    try:
        resultado = archivos.importar_adjunto_desde_url(
            archivos.ImagenUrl(url='https://cdn.example.com/factura.png'),
            usuario_id=str(usuario.id),
            db=sesion_db,
        )
        assert resultado['mime_type'] == 'image/jpeg'
        guardado = sesion_db.get(ChatAdjunto, resultado['id'])
        assert guardado.usuario_id == usuario.id
        assert (tmp_path / guardado.ruta).is_file()
    finally:
        sesion_db.close()
        engine.dispose()
