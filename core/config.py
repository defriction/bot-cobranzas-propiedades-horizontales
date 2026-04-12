import os
from dotenv import load_dotenv

# Cargar variables desde el archivo .env si existe
load_dotenv()

class Settings:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    SHEET_ID = os.environ.get("SHEET_ID", "")
    EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "http://localhost:8080")
    EVOLUTION_API_TOKEN = os.environ.get("EVOLUTION_API_TOKEN", "")
    EVOLUTION_INSTANCE_NAME = os.environ.get("EVOLUTION_INSTANCE_NAME", "")
    API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "super_secreto_local")

settings = Settings()
