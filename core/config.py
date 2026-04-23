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
    SMTP_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp-relay.brevo.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Administracion Arboreto Guayacan")
    SMTP_REPLY_TO = os.environ.get("SMTP_REPLY_TO", "")
    SMTP_LIST_UNSUBSCRIBE_EMAIL = os.environ.get("SMTP_LIST_UNSUBSCRIBE_EMAIL", "")

settings = Settings()
