import logging

import httpx

from core.config import settings

logger = logging.getLogger("uvicorn.error")


def _classify_whatsapp_error(error_text: str) -> str:
    lowered = (error_text or "").lower()

    if "connection closed" in lowered:
        return "connection_closed"

    restricted_markers = [
        "cuenta esta restringida",
        "cuenta está restringida",
        "cuenta restringida",
        "no puedes iniciar nuevo chats",
        "account is restricted",
        "restricted",
    ]
    if any(marker in lowered for marker in restricted_markers):
        return "restricted"

    return "other"


async def send_whatsapp_message(phone: str, text: str) -> dict:
    """
    Envia mensaje de WhatsApp por Evolution API y retorna resultado estructurado.
    """
    base_url = settings.EVOLUTION_API_URL.rstrip("/")
    instance = settings.EVOLUTION_INSTANCE_NAME
    url = f"{base_url}/message/sendText/{instance}"

    headers = {
        "apikey": settings.EVOLUTION_API_TOKEN,
        "Content-Type": "application/json",
    }

    clean_phone = phone.replace("+", "").replace(" ", "")
    if not clean_phone.endswith("@s.whatsapp.net"):
        clean_phone = f"{clean_phone}@s.whatsapp.net"

    payload = {
        "number": clean_phone,
        "text": text,
        "textMessage": {"text": text},
    }

    logger.info(f"WhatsApp: Enviando a {phone} via Evolution URL={url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            logger.info(f"WhatsApp: envio exitoso a {phone}.")
            return {
                "ok": True,
                "error_type": None,
                "error_message": "",
                "status_code": response.status_code,
                "response": data,
            }
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text if exc.response is not None else str(exc)
        error_type = _classify_whatsapp_error(response_text)
        logger.error(f"WhatsApp: error HTTP enviando a {phone}. status={exc.response.status_code} body={response_text}")
        return {
            "ok": False,
            "error_type": error_type,
            "error_message": response_text,
            "status_code": exc.response.status_code if exc.response is not None else None,
            "response": None,
        }
    except Exception as exc:
        error_message = str(exc)
        error_type = _classify_whatsapp_error(error_message)
        logger.error(f"WhatsApp: error interno enviando a {phone}: {error_message}")
        return {
            "ok": False,
            "error_type": error_type,
            "error_message": error_message,
            "status_code": None,
            "response": None,
        }
