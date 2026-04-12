import httpx
from core.config import settings

async def send_whatsapp_message(phone: str, text: str):
    """
    Función asíncrona para enviar mensajes reales de WhatsApp usando Evolution API.
    """
    # 1. Construir la URL completa (limpiando slashes al final)
    base_url = settings.EVOLUTION_API_URL.rstrip('/')
    instance = settings.EVOLUTION_INSTANCE_NAME
    url = f"{base_url}/message/sendText/{instance}"
    
    # 2. Construir cabeceras obligatorias de Evolution API
    headers = {
        "apikey": settings.EVOLUTION_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Asegurarnos de que el número sea formato Jid de WhatsApp (Ej: 573001234567@s.whatsapp.net)
    clean_phone = phone.replace("+", "").replace(" ", "")
    if not clean_phone.endswith("@s.whatsapp.net"):
        clean_phone = f"{clean_phone}@s.whatsapp.net"
        
    payload = {
        "number": clean_phone, 
        "text": text,
        "textMessage": {
            "text": text
        }
    }
    
    print(f"\n==================================================")
    print(f"📡 Enviando WhatsApp a: {phone} a través de Evolution...")
    print(f"URL destino: {url}")
    print(f"==================================================\n")
    
    # 4. Enviar la petición de forma asíncrona
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status() 
            data = response.json()
            print(f"✅ ¡Petición HTTP a Evolution Exitosa!")
            print(f"📝 Respuesta cruda del servidor: {data}")
            return data
            
    except httpx.HTTPStatusError as e:
        print(f"❌ Error HTTP de Evolution API al enviar a {phone}: {e.response.text}")
    except Exception as e:
        print(f"❌ Error interno de conexión con Evolution API al enviar a {phone}: {e}")
