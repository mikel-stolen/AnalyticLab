
from pathlib import Path
import os

from dotenv import load_dotenv

# ==========================================================
# RUTAS DEL PROYECTO
# ==========================================================

# AnalyticLab/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Cargar variables de entorno
load_dotenv(PROJECT_ROOT / ".env")

# ==========================================================
# VARIABLES DE ENTORNO
# ==========================================================

ACCESS_TOKEN = os.getenv("IG_TOKEN")
IG_USER_ID = os.getenv("IG_ACCOUNT_ID")

if not ACCESS_TOKEN:
    raise ValueError(
        "No se ha encontrado la variable IG_ACCESS_TOKEN en el archivo .env"
    )

if not IG_USER_ID:
    raise ValueError(
        "No se ha encontrado la variable IG_USER_ID en el archivo .env"
    )

# ==========================================================
# API
# ==========================================================

GRAPH_URL = "https://graph.facebook.com/v23.0"

# ==========================================================
# DIRECTORIOS
# ==========================================================

DATA_DIR = PROJECT_ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"

INSTAGRAM_RAW_DIR = RAW_DATA_DIR / "instagram"
STORIES_DIR = INSTAGRAM_RAW_DIR / "stories"
ACCOUNT_DIR = INSTAGRAM_RAW_DIR / "account"
MEDIA_DIR = INSTAGRAM_RAW_DIR / "media"
INSIGHTS_DIR = INSTAGRAM_RAW_DIR / "insights"

# Crear automáticamente las carpetas necesarias
ACCOUNT_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
