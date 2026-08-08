import os
import chromadb
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

config = dotenv_values(".env")

# helper functions
def _env(key, default=""):
    return os.environ.get(key, default)

def _env_bool(key, default):
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "yes", "true", "on")

def _env_int(key, default):
    try:
        return int(os.environ[key])
    except (KeyError, ValueError):
        return default


# environment variables
DATA_DIR = Path(_env("DATA_DIR", str(REPO_ROOT / "data")))
CREDS_DIR = Path(_env("CREDS_DIR", str(REPO_ROOT / "creds")))
CHROMA_PATH = Path(_env("CHROMA_PATH", str(DATA_DIR / "chroma")))
OUTPUT_DIR = Path(_env("OUTPUT_DIR", str(Path.home() / "cloud/Documents/vault_cloud/50 - Daily")))

COLLECTION = _env("COLLECTION", "emails")

ALLOW_BROWSER = _env_bool("ALLOW_BROWSER", False)
BRIEF_HOUR = _env_int("BRIEF_HOUR", 7)
LOOKBACK_DAYS = _env_int("LOOKBACK_DAYS", 1)

DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

RCLONE_REMOTE = _env("RCLONE_REMOTE")

ACCOUNTS = [
        (_env("EMAIL_ADDRESS_1"), _env("EMAIL_PASSWORD_1"), DATA_DIR / "last_poll.txt"),
        (_env("EMAIL_ADDRESS_2"), _env("EMAIL_PASSWORD_2"), DATA_DIR / "last_poll_2.txt")
]

# chroma setup
_collection = None
def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(name=COLLECTION)
    return _collection
