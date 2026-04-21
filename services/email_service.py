import asyncio
import smtplib
from email.message import EmailMessage

from core.config import settings


def _send_email_sync(to_email: str, subject: str, text: str) -> bool:
    if not settings.SMTP_ENABLED:
        print("Email deshabilitado: SMTP_ENABLED no esta activo.")
        return False

    if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
        print("Email no configurado: faltan variables SMTP obligatorias.")
        return False

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    from_name = settings.SMTP_FROM_NAME or "Administracion"

    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        print(f"Email enviado correctamente a: {to_email}")
        return True
    except Exception as exc:
        print(f"Error enviando email a {to_email}: {exc}")
        return False


async def send_email_message(to_email: str, subject: str, text: str) -> bool:
    return await asyncio.to_thread(_send_email_sync, to_email, subject, text)
