import re
import unicodedata
from pathlib import Path
from urllib.parse import quote


def borrar_archivo(ruta: Path) -> bool:
    """Borra un archivo sin romper la petición si no existe o si Windows
    lo tiene bloqueado (PermissionError / WinError 32 cuando otro proceso
    lo tiene abierto). Devuelve True si se borró."""
    try:
        ruta.unlink(missing_ok=True)
        return True
    except PermissionError:
        print(f'[FinanBot] No se pudo borrar {ruta}: el archivo está en uso.')
        return False


def cabecera_descarga(nombre: str) -> dict:
    """Cabecera Content-Disposition que funciona con tildes, ñ y emojis.

    Las cabeceras HTTP solo aceptan ASCII: 'FinanBot_Ana_María.xlsx' daba error 500.
    Se manda un nombre ASCII de respaldo (filename) y el nombre real codificado
    (filename*, RFC 6266) que usan todos los navegadores actuales."""
    respaldo = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('ascii')
    respaldo = re.sub(r'[^A-Za-z0-9._-]+', '_', respaldo).strip('_') or 'FinanBot'
    return {'Content-Disposition': f"attachment; filename=\"{respaldo}\"; filename*=UTF-8''{quote(nombre)}"}
