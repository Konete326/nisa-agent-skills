import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "skills"

load_dotenv(BASE_DIR / ".env")

AGENT_NAME = os.getenv("AGENT_NAME", "Nisa")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/nisa")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_SKILLS_REPO = os.getenv("GITHUB_SKILLS_REPO", "").strip()
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "").strip()
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()
VOICE_VOLUME = int(os.getenv("VOICE_VOLUME", "90"))
VOICE_RATE = int(os.getenv("VOICE_RATE", "1"))

VOICE_MAP = {
    "UR": "ur-PK-UzmaNeural",
    "EN": "en-US-JennyNeural",
    "HI": "hi-IN-SwaraNeural"
}
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "UR")

mongo_client_instance = None

def get_mongo_client():
    global mongo_client_instance
    if mongo_client_instance is None:
        mongo_client_instance = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=4000)
    return mongo_client_instance

def get_database(db_name="nisa"):
    client = get_mongo_client()
    try:
        return client.get_default_database() or client[db_name]
    except Exception:
        return client[db_name]

def get_collection(collection_name):
    db = get_database()
    return db[collection_name]
