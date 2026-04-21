import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import settings
from services.email_service import send_email_message


def _ensure_parent_dir(file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _load_json(file_path: Path, default_value: Any) -> Any:
    if not file_path.exists():
        return default_value
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default_value


def _save_json(file_path: Path, payload: Any) -> None:
    _ensure_parent_dir(file_path)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def _today_bogota() -> str:
    return datetime.now(settings.APP_TIMEZONE).strftime("%Y-%m-%d")


def _queue_path() -> Path:
    return Path(settings.EMAIL_QUEUE_FILE)


def _quota_path() -> Path:
    return Path(settings.EMAIL_QUOTA_FILE)


def _load_quota_state() -> dict[str, Any]:
    return _load_json(_quota_path(), {"date": "", "sent_count": 0})


def _save_quota_state(state: dict[str, Any]) -> None:
    _save_json(_quota_path(), state)


def _reset_quota_if_needed(state: dict[str, Any]) -> dict[str, Any]:
    today = _today_bogota()
    if state.get("date") != today:
        state = {"date": today, "sent_count": 0}
    return state


async def enqueue_email(to_email: str, subject: str, text: str) -> None:
    queue = _load_json(_queue_path(), [])
    queue.append({"to_email": to_email, "subject": subject, "text": text})
    _save_json(_queue_path(), queue)
    print(f"Email encolado para envio posterior: {to_email}")


async def enqueue_or_send_email(to_email: str, subject: str, text: str) -> bool:
    if not settings.SMTP_ENABLED:
        print("SMTP deshabilitado, correo omitido.")
        return False

    state = _reset_quota_if_needed(_load_quota_state())
    if state["sent_count"] >= settings.EMAIL_DAILY_LIMIT:
        await enqueue_email(to_email, subject, text)
        _save_quota_state(state)
        print(f"Limite diario alcanzado ({settings.EMAIL_DAILY_LIMIT}). Email en cola: {to_email}")
        return False

    sent_ok = await send_email_message(to_email, subject, text)
    if sent_ok:
        state["sent_count"] += 1
        _save_quota_state(state)
        return True

    # Si falla, lo dejamos en cola para reintento.
    await enqueue_email(to_email, subject, text)
    _save_quota_state(state)
    return False


async def procesar_cola_emails() -> dict[str, int]:
    if not settings.SMTP_ENABLED:
        print("SMTP deshabilitado, no se procesa cola de emails.")
        return {"processed": 0, "remaining": len(_load_json(_queue_path(), []))}

    queue = _load_json(_queue_path(), [])
    if not queue:
        return {"processed": 0, "remaining": 0}

    state = _reset_quota_if_needed(_load_quota_state())
    available = settings.EMAIL_DAILY_LIMIT - state["sent_count"]
    if available <= 0:
        print("Sin cupo diario disponible para procesar cola de emails.")
        _save_quota_state(state)
        return {"processed": 0, "remaining": len(queue)}

    processed = 0
    failed_items = []

    for item in queue:
        if processed >= available:
            failed_items.append(item)
            continue

        sent_ok = await send_email_message(item["to_email"], item["subject"], item["text"])
        if sent_ok:
            processed += 1
            state["sent_count"] += 1
        else:
            failed_items.append(item)

    _save_json(_queue_path(), failed_items)
    _save_quota_state(state)

    print(
        f"Cola de emails procesada. Enviados: {processed} | "
        f"Pendientes: {len(failed_items)} | Cupo diario: {settings.EMAIL_DAILY_LIMIT}"
    )
    return {"processed": processed, "remaining": len(failed_items)}
