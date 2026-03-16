import asyncio
from core.config import settings

async def send_whatsapp_message(phone: str, text: str):
    """
    Función placeholder asíncrona para enviar el mensaje de WhatsApp.
    Se implementará en el futuro usando Evolution API o similar.
    """
    print(f"\n{'='*50}")
    print(f"Simulando envío de WhatsApp a: {phone}")
    print(f"URL Evolution API (configurada): {settings.EVOLUTION_API_URL}")
    print(f"Mensaje a enviar:\n{text}")
    print(f"{'='*50}\n")
    
    # Simula latencia de red en la llamada HTTP a la API de WhatsApp
    await asyncio.sleep(1)
