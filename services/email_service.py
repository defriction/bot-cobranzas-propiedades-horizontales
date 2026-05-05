import asyncio
import html
import logging
import re
import smtplib
from email.message import EmailMessage

from core.config import settings
from email_validator import EmailNotValidError, validate_email

logger = logging.getLogger("uvicorn.error")


def _normalize_email(to_email: str) -> str | None:
    try:
        valid = validate_email(to_email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError:
        return None


def _to_email_friendly_text(text: str) -> str:
    cleaned = text.replace("* ", "- ").replace("*", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def _to_simple_html(text: str) -> str:
    escaped = html.escape(text)
    with_breaks = escaped.replace("\n", "<br>")
    return (
        "<html><body style='font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;'>"
        f"{with_breaks}"
        "</body></html>"
    )


def _send_email_sync(to_email: str, subject: str, text: str) -> bool:
    if not settings.SMTP_ENABLED:
        logger.warning("Email deshabilitado: SMTP_ENABLED no esta activo.")
        return False

    if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
        logger.error("Email no configurado: faltan variables SMTP obligatorias.")
        return False

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    from_name = settings.SMTP_FROM_NAME or "Administracion"
    normalized_to = _normalize_email(to_email)

    if not normalized_to:
        logger.warning(f"Email invalido, se omite envio: {to_email}")
        return False

    email_text = _to_email_friendly_text(text)
    email_html = _to_simple_html(email_text)

    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = normalized_to
    msg["Subject"] = subject
    if settings.SMTP_REPLY_TO:
        msg["Reply-To"] = settings.SMTP_REPLY_TO
    if settings.SMTP_LIST_UNSUBSCRIBE_EMAIL:
        msg["List-Unsubscribe"] = f"<mailto:{settings.SMTP_LIST_UNSUBSCRIBE_EMAIL}?subject=unsubscribe>"
    msg.set_content(email_text)
    msg.add_alternative(email_html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email enviado correctamente a: {normalized_to}")
        return True
    except Exception as exc:
        logger.error(f"Error enviando email a {to_email}: {exc}")
        return False


async def send_email_message(to_email: str, subject: str, text: str) -> bool:
    return await asyncio.to_thread(_send_email_sync, to_email, subject, text)
