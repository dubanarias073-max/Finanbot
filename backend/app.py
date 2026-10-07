from pathlib import Path
from dotenv import load_dotenv

# Carga backend/.env antes de importar el resto de la app
load_dotenv(Path(__file__).resolve().parent / ".env")

from presentation.api import create_app

app = create_app()