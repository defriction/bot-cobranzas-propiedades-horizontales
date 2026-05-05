import gspread
import asyncio
import math
import random
import logging
from oauth2client.service_account import ServiceAccountCredentials

from core.config import settings
from services.email_service import send_email_message
from services.groq_service import generate_cobro_with_groq, generate_recordatorio_with_groq
from services.whatsapp_service import send_whatsapp_message

LINK_PAGO_PSE = "https://web-conjuntos.jelpit.com/zona-publica-pagos"
EMAIL_COMPROBANTE = "arboretoguayacan.contable@gmail.com"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
RECORDATORIO_DISTRIBUTION_HOURS = 6
RECORDATORIO_MAX_LOTES = 3
logger = logging.getLogger("uvicorn.error")


def obtener_datos_sheet():
    """Funcion helper para conectar y traer datos del Sheet."""
    if not settings.SHEET_ID:
        raise ValueError("Error critico: La variable de entorno SHEET_ID no esta configurada.")

    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(settings.SHEET_ID).worksheet("Cartera_AG")
    records = sheet.get_all_values()

    if len(records) <= 1:
        return []

    return records[1:]  # Saltar encabezados


async def enviar_notificaciones(telefono: str, correo: str, subject: str, message: str):
    enviado = False

    if telefono:
        await send_whatsapp_message(telefono, message)
        enviado = True

    if correo:
        await send_email_message(correo, subject, message)
        enviado = True

    return enviado


def _crear_estado_corrida() -> dict:
    return {
        "whatsapp_enabled_in_run": True,
        "safe_mode_activated": False,
        "safe_mode_reason": "",
        "safe_mode_phone": "",
        "whatsapp_sent": 0,
        "whatsapp_failed": 0,
        "whatsapp_skipped_safe_mode": 0,
        "email_sent": 0,
        "email_failed": 0,
    }


async def enviar_notificaciones_safe_mode(
    telefono: str,
    correo: str,
    subject: str,
    message: str,
    estado_corrida: dict,
):
    enviado = False

    if telefono:
        if estado_corrida["whatsapp_enabled_in_run"]:
            wa_result = await send_whatsapp_message(telefono, message)
            if wa_result.get("ok"):
                estado_corrida["whatsapp_sent"] += 1
                enviado = True
            else:
                estado_corrida["whatsapp_failed"] += 1
                error_type = wa_result.get("error_type", "other")
                if error_type in {"restricted", "connection_closed"}:
                    estado_corrida["whatsapp_enabled_in_run"] = False
                    if not estado_corrida["safe_mode_activated"]:
                        estado_corrida["safe_mode_activated"] = True
                        estado_corrida["safe_mode_reason"] = error_type
                        estado_corrida["safe_mode_phone"] = telefono
                        logger.warning(
                            "SAFE MODE WhatsApp activado en esta corrida. "
                            f"Motivo={error_type} primer_numero={telefono}. "
                            "Se continuara solo por email."
                        )
        else:
            estado_corrida["whatsapp_skipped_safe_mode"] += 1

    if correo:
        email_ok = await send_email_message(correo, subject, message)
        if email_ok:
            estado_corrida["email_sent"] += 1
            enviado = True
        else:
            estado_corrida["email_failed"] += 1

    return enviado


# ===============================================
# FASE 1: PROCESAR RECORDATORIO PREVENTIVO
# ===============================================
async def procesar_recordatorios():
    """Logica Fase 1: Enviar recordatorio general de descuento, ignora las deudas."""
    try:
        data_rows = obtener_datos_sheet()
        estado_corrida = _crear_estado_corrida()

        logger.info("Fase 1: Generando plantilla de Recordatorio con IA (1 sola vez)...")
        plantilla = await generate_recordatorio_with_groq()

        pendientes = []

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                logger.warning(f"Fase 1: Fila {idx} omitida (faltan datos basicos): {row}")
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()

            # Columna E: Enviar_Mensaje. Columna F: Correo_Electronico.
            enviar_mensaje = row[4].strip().upper() if len(row) > 4 else "FALSE"
            correo = row[5].strip() if len(row) > 5 else ""

            if enviar_mensaje != "TRUE":
                logger.info(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                logger.warning(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: sin telefono ni Correo_Electronico.")
                continue

            saludo = f"Hola {propietario}, apto {apartamento}.\n"
            mensaje_final = (
                f"{saludo}{plantilla}\n\n"
                "* Descuento: 10% por pago el 10 de cada mes antes de las 4:00 PM\n"
                "* Condicion: Debe estar al dia (saldo en $0) para aplicar el descuento\n"
                "* Importante: El descuento no aplica sobre deudas de periodos pasados\n\n"
                f"* Paga facil por PSE: {LINK_PAGO_PSE}\n"
                f"* Envia tu comprobante a: {EMAIL_COMPROBANTE}\n\n"
                "Atentamente, Administracion de Arboreto Guayacan y Tesoreria. (Este es un mensaje automatico, por favor no responder)"
            )
            asunto = f"Recordatorio de administracion - Apto {apartamento}"

            pendientes.append((apartamento, propietario, telefono, correo, asunto, mensaje_final))

        total = len(pendientes)
        if total == 0:
            logger.warning("Fase 1: No hay destinatarios validos para enviar recordatorio.")
            return

        # Usamos maximo 3 lotes por corrida para evitar fragmentar demasiado el envio.
        total_batches = min(RECORDATORIO_MAX_LOTES, total)
        batch_size = math.ceil(total / total_batches)
        ventana_horas = max(1.0, RECORDATORIO_DISTRIBUTION_HOURS)
        ventana_segundos = int(ventana_horas * 3600)
        espera_entre_lotes = int(ventana_segundos / max(1, total_batches - 1)) if total_batches > 1 else 0

        logger.info(
            f"Fase 1: {total} envios en {total_batches} lotes de {batch_size}. "
            f"Espera entre lotes: {espera_entre_lotes} segundos."
        )

        for batch_index in range(total_batches):
            start = batch_index * batch_size
            end = start + batch_size
            lote = pendientes[start:end]

            logger.info(f"Fase 1: Enviando lote {batch_index + 1}/{total_batches} ({len(lote)} mensajes).")
            for item_index, (apartamento, propietario, telefono, correo, asunto, mensaje_final) in enumerate(lote):
                logger.info(f"Fase 1 (Recordatorio) -> Apto {apartamento} | {propietario}")
                await enviar_notificaciones_safe_mode(telefono, correo, asunto, mensaje_final, estado_corrida)

                # Pausa aleatoria para que el patron de envios se vea mas organico.
                es_ultimo_del_lote = item_index == len(lote) - 1
                es_ultimo_lote = batch_index == total_batches - 1
                if not (es_ultimo_del_lote and es_ultimo_lote):
                    espera_random = random.randint(10, 20)
                    logger.info(
                        f"Fase 1: Espera aleatoria de {espera_random}s "
                        f"antes del siguiente envio (lote {batch_index + 1}/{total_batches})."
                    )
                    await asyncio.sleep(espera_random)

            if batch_index < total_batches - 1 and espera_entre_lotes > 0:
                logger.info(
                    f"Fase 1: Espera entre lotes de {espera_entre_lotes}s "
                    f"antes del lote {batch_index + 2}/{total_batches}."
                )
                await asyncio.sleep(espera_entre_lotes)

        logger.info(
            "Finalizado procesamiento de Fase 1 (Recordatorios). "
            f"WA enviados={estado_corrida['whatsapp_sent']} "
            f"WA fallidos={estado_corrida['whatsapp_failed']} "
            f"WA omitidos_safe_mode={estado_corrida['whatsapp_skipped_safe_mode']} "
            f"Email enviados={estado_corrida['email_sent']} "
            f"Email fallidos={estado_corrida['email_failed']} "
            f"safe_mode={estado_corrida['safe_mode_activated']} "
            f"motivo={estado_corrida['safe_mode_reason']}"
        )

    except FileNotFoundError:
        logger.exception("Fase 1: Error: El archivo 'credentials.json' no se encontro.")
    except Exception as exc:
        logger.exception(f"Error inesperado en Fase 1: {exc}")


# ===============================================
# FASE 2: PROCESAR COBRANZAS REALES (Con Saldo > 0, sin Meses_Mora)
# ===============================================
async def procesar_cobros():
    """Logica Fase 2: Lee montos y envia solo a deudores (sin Meses_Mora)."""
    try:
        data_rows = obtener_datos_sheet()
        estado_corrida = _crear_estado_corrida()

        logger.info("Fase 2: Generando plantilla de Cobro con IA (1 sola llamada)...")
        plantilla_cobro = await generate_cobro_with_groq()

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 4:
                logger.warning(f"Fase 2: Fila {idx} omitida (datos incompletos basicos): {row}")
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()

            # Columna E: Enviar_Mensaje. Columna F: Correo_Electronico.
            enviar_mensaje = row[4].strip().upper() if len(row) > 4 else "FALSE"
            correo = row[5].strip() if len(row) > 5 else ""

            try:
                saldo_limpio = saldo_str.replace("$", "").replace(",", "").strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
            except ValueError:
                logger.warning(f"Fase 2: Fila {idx} (Apto {apartamento}): Error numerico (Saldo: '{saldo_str}').")
                continue

            if saldo <= 0:
                continue

            if enviar_mensaje != "TRUE":
                logger.info(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                logger.warning(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: debe ${saldo} y no tiene telefono ni Correo_Electronico.")
                continue

            logger.info(f"Fase 2 (Cobro) -> Apto {apartamento} | Saldo: ${saldo}")
            saldo_formateado = f"{saldo:,.2f}"

            saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacan.\n"

            mensaje_final = (
                f"{saludo}\n"
                f"{plantilla_cobro}\n\n"
                f"* Saldo Pendiente: ${saldo_formateado}\n"
                f"* Paga facil por PSE: {LINK_PAGO_PSE}\n"
                f"* Envia tu comprobante a: {EMAIL_COMPROBANTE}\n\n"
                "Atentamente, Administracion de Arboreto Guayacan y Tesoreria. (Este es un mensaje automatico, por favor no responder)"
            )

            asunto = f"Cobro de administracion - Apto {apartamento}"
            await enviar_notificaciones_safe_mode(telefono, correo, asunto, mensaje_final, estado_corrida)

        logger.info(
            "Finalizado procesamiento de Fase 2 (Cobranza). "
            f"WA enviados={estado_corrida['whatsapp_sent']} "
            f"WA fallidos={estado_corrida['whatsapp_failed']} "
            f"WA omitidos_safe_mode={estado_corrida['whatsapp_skipped_safe_mode']} "
            f"Email enviados={estado_corrida['email_sent']} "
            f"Email fallidos={estado_corrida['email_failed']} "
            f"safe_mode={estado_corrida['safe_mode_activated']} "
            f"motivo={estado_corrida['safe_mode_reason']}"
        )

    except FileNotFoundError:
        logger.exception("Fase 2: Error: El archivo 'credentials.json' no se encontro.")
    except Exception as exc:
        logger.exception(f"Error inesperado en Fase 2: {exc}")


# ===============================================
# FASE 3: PROCESAR FELICITACIONES (Saldo 0, sin Meses_Mora)
# ===============================================
async def procesar_felicitaciones():
    """Logica Fase 3: Felicita a residentes con Saldo=0."""
    try:
        data_rows = obtener_datos_sheet()
        estado_corrida = _crear_estado_corrida()

        logger.info("Fase 3: Generando plantilla de Felicitacion con IA (1 sola vez)...")
        from services.groq_service import generate_felicitacion_with_groq

        plantilla = await generate_felicitacion_with_groq()

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 4:
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()

            # Columna E: Enviar_Mensaje. Columna F: Correo_Electronico.
            enviar_mensaje = row[4].strip().upper() if len(row) > 4 else "FALSE"
            correo = row[5].strip() if len(row) > 5 else ""

            try:
                saldo_limpio = saldo_str.replace("$", "").replace(",", "").strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
            except ValueError:
                continue

            if saldo != 0:
                continue

            if enviar_mensaje != "TRUE":
                logger.info(f"Fase 3: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                logger.warning(f"Fase 3: Fila {idx} (Apto {apartamento}) omitida: sin telefono ni Correo_Electronico.")
                continue

            logger.info(f"Fase 3 (Felicitacion) -> Apto {apartamento} | {propietario}")

            saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacan.\n"

            mensaje_final = (
                f"{saludo}\n"
                f"{plantilla}\n\n"
                "* Estado de Cuenta: Al dia\n"
                "* Saldo Pendiente: $0.00\n"
                "Atentamente, Administracion de Arboreto Guayacan y Tesoreria. (Este es un mensaje automatico, por favor no responder)"
            )

            asunto = f"Felicitacion por pago al dia - Apto {apartamento}"
            await enviar_notificaciones_safe_mode(telefono, correo, asunto, mensaje_final, estado_corrida)

        logger.info(
            "Finalizado procesamiento de Fase 3 (Felicitaciones). "
            f"WA enviados={estado_corrida['whatsapp_sent']} "
            f"WA fallidos={estado_corrida['whatsapp_failed']} "
            f"WA omitidos_safe_mode={estado_corrida['whatsapp_skipped_safe_mode']} "
            f"Email enviados={estado_corrida['email_sent']} "
            f"Email fallidos={estado_corrida['email_failed']} "
            f"safe_mode={estado_corrida['safe_mode_activated']} "
            f"motivo={estado_corrida['safe_mode_reason']}"
        )

    except FileNotFoundError:
        logger.exception("Fase 3: Error: El archivo 'credentials.json' no se encontro.")
    except Exception as exc:
        logger.exception(f"Error inesperado en Fase 3: {exc}")
