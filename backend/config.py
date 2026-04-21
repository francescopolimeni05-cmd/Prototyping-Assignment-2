"""
VoyageAI backend — configuration.

All runtime config is read from environment variables so the same code runs
locally (via .env) and on Railway (via the dashboard secrets).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env when running locally; on Railway env vars are already injected.
load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
# DATA_DIR holds SQLite file + Chroma persistence. On Railway this should be
# a mounted volume (e.g. /data) so state survives redeploys.
DATA_DIR = Path(os.environ.get("VOYAGEAI_DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "voyageai.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

CHROMA_DIR = os.environ.get("CHROMA_DIR", str(DATA_DIR / "chroma"))
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)

# ── Secrets ────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
AMADEUS_CLIENT_ID = os.environ.get("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET", "")

# ── App config ─────────────────────────────────────────────────────────────
# Comma-separated list of allowed frontend origins (Streamlit Cloud URL + local dev).
_default_origins = "http://localhost:8501,http://127.0.0.1:8501"
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

# Embedding + retrieval
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))

# Cookie name used by the Streamlit client to send the user id to the API.
USER_ID_HEADER = "X-VoyageAI-User"
