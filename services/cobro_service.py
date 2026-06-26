import gspread
import asyncio
import math
import random
import logging
from datetime import datetime
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
# Limite diario estricto para evitar bloqueos (Sandbox de Meta)
MAX_MENSAJES_DIARIOS = 36  # Margen de seguridad: 36 mensajes para no tocar el techo de 40 y permitirte chatear a mano
LOTES_POR_DIA = 4  # 4 lotes al dia = 1 lote cada 6 horas
logger = logging.getLogger("uvicorn.error")
MESES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


async def sleep_con_conteo(segundos: int, tipo: str, fase: str):
    """
    Realiza un asyncio.sleep en intervalos, imprimiendo en los logs
    el tiempo restante para mayor visibilidad en la consola.
    """
    restante = segundos
    # Para pausas cortas (mensajes), loguea cada 30s. Para pausas largas (lotes), loguea cada 10 min (600s).
    paso = 30 if segundos <= 300 else 600

    while restante > 0:
        espera = min(restante, paso)
        await asyncio.sleep(espera)
        restante -= espera
        
        if restante > 0:
            if restante >= 3600:
                horas = restante // 3600
                minutos = (restante % 3600) // 60
                logger.info(f"{fase}: \u23f3 Timer ({tipo}) -> Faltan {horas}h {minutos}m...")
            elif restante >= 60:
                minutos = restante // 60
                segs = restante % 60
                logger.info(f"{fase}: \u23f3 Timer ({tipo}) -> Faltan {minutos}m {segs}s...")
            else:
                logger.info(f"{fase}: \u23f3 Timer ({tipo}) -> Faltan {restante}s...")

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
                        
                        mensaje_alerta = (
                            f"\U0001f6a8 SAFE MODE WhatsApp activado. Motivo={error_type} al intentar enviar a {telefono}. "
                            "Se continuara el proceso SOLO por EMAIL."
                        )
                        if error_type == "connection_closed":
                            mensaje_alerta += " \u26a0\ufe0f ACCI\u00d3N REQUERIDA: Ve a Evolution API y reconecta el c\u00f3digo QR. La instancia se desconect\u00f3."
                        elif error_type == "restricted":
                            mensaje_alerta += " \u26a0\ufe0f ALERTA GRAVE: Meta ha restringido la cuenta de WhatsApp. Ve a la app en el celular y presiona 'Solicitar Revisi\u00f3n'."
                            
                        logger.warning(mensaje_alerta)
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


def _mes_actual_es() -> str:
    return MESES_ES[datetime.now().month - 1]


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
        mes_beneficio = _mes_actual_es()

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                logger.warning(f"Fase 1: Fila {idx} omitida (faltan datos basicos): {row}")
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()

            # Columna D: Enviar_Mensaje (Index 3). Columna E: Correo_Electronico (Index 4).
            enviar_mensaje = row[3].strip().upper() if len(row) > 3 else "FALSE"
            correo = row[4].strip() if len(row) > 4 else ""

            if enviar_mensaje != "TRUE":
                logger.info(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                logger.warning(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: sin telefono ni Correo_Electronico.")
                continue

            saludo = f"Hola {propietario}, apto {apartamento}.\n"
            mensaje_final = (
                f"{saludo}{plantilla}\n\n"
                f"• Descuento ({mes_beneficio.title()}): 10% por pago el 10 antes de las 4:00 PM\n"
                "• Condicion: Debe estar al dia (saldo en $0) para aplicar el descuento\n"
                "• Importante: El descuento no aplica sobre deudas de periodos pasados\n\n"
                f"• Paga facil por PSE: {LINK_PAGO_PSE}\n"
                f"• Envia tu comprobante a: {EMAIL_COMPROBANTE}\n\n"
                "Atentamente, Administracion de Arboreto Guayacan.\n"
                "\U0001f449 *Este es un mensaje automatico. Por favor, responde con un 'Ok' o 'Recibido' para confirmar que leiste este aviso. \u00a1Gracias!*"
            )
            asunto = f"Recordatorio de administracion - Apto {apartamento}"

            pendientes.append((apartamento, propietario, telefono, correo, asunto, mensaje_final))

        total = len(pendientes)
        if total == 0:
            logger.warning("Fase 1: No hay destinatarios validos para enviar recordatorio.")
            return

        dias_necesarios = math.ceil(total / MAX_MENSAJES_DIARIOS)
        total_batches = min(total, dias_necesarios * LOTES_POR_DIA)
        batch_size = math.ceil(total / total_batches)

        # \U0001f6e1\ufe0f VALIDACION ESTRICTA: Garantizar que NUNCA supere el limite diario
        if (batch_size * LOTES_POR_DIA) > MAX_MENSAJES_DIARIOS:
            batch_size = max(1, MAX_MENSAJES_DIARIOS // LOTES_POR_DIA)
            total_batches = math.ceil(total / batch_size)

        espera_entre_lotes = int((24 * 3600) / LOTES_POR_DIA) if total_batches > 1 else 0

        logger.info(
            f"Fase 1: {total} envios calculados para {dias_necesarios} dia(s). "
            f"Se haran {total_batches} lotes de {batch_size} mensajes. "
            f"Espera entre lotes: {espera_entre_lotes} segundos ({espera_entre_lotes/3600:.1f} horas)."
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
                if not es_ultimo_del_lote:
                    espera_random = random.randint(90, 180)
                    logger.info(
                        f"Fase 1: Espera aleatoria de {espera_random}s "
                        f"antes del siguiente envio (lote {batch_index + 1}/{total_batches})."
                    )
                    await sleep_con_conteo(espera_random, "siguiente mensaje", "Fase 1")

            if batch_index < total_batches - 1 and espera_entre_lotes > 0:
                logger.info(
                    f"Fase 1: Espera entre lotes de {espera_entre_lotes}s "
                    f"antes del lote {batch_index + 2}/{total_batches}."
                )
                await sleep_con_conteo(espera_entre_lotes, "siguiente lote", "Fase 1")

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

        pendientes = []
        mes_beneficio = _mes_actual_es()

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                logger.warning(f"Fase 2: Fila {idx} omitida (datos incompletos basicos): {row}")
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()

            # Columna D: Enviar_Mensaje (Index 3). Columna E: Correo_Electronico (Index 4).
            enviar_mensaje = row[3].strip().upper() if len(row) > 3 else "FALSE"
            correo = row[4].strip() if len(row) > 4 else ""

            try:
                saldo_anterior = float(row[5].replace("$", "").replace(",", "").strip() or 0) if len(row) > 5 else 0.0
                intereses = float(row[6].replace("$", "").replace(",", "").strip() or 0) if len(row) > 6 else 0.0
                sanciones = float(row[7].replace("$", "").replace(",", "").strip() or 0) if len(row) > 7 else 0.0
                valor_mes = float(row[8].replace("$", "").replace(",", "").strip() or 0) if len(row) > 8 else 0.0
                valor_con_descuento = float(row[9].replace("$", "").replace(",", "").strip() or 0) if len(row) > 9 else 0.0
                valor_sin_descuento = float(row[10].replace("$", "").replace(",", "").strip() or 0) if len(row) > 10 else 0.0
            except ValueError:
                logger.warning(f"Fase 2: Fila {idx} (Apto {apartamento}): Error numerico en las nuevas columnas de saldo.")
                continue

            if valor_sin_descuento <= 0:
                continue

            if enviar_mensaje != "TRUE":
                logger.info(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                logger.warning(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: debe ${valor_sin_descuento} y no tiene telefono ni Correo_Electronico.")
                continue

            logger.info(f"Fase 2 (Cobro) -> Apto {apartamento} | Total SIN descuento: ${valor_sin_descuento:,.2f}")

            saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacan.\n"

            mensaje_final = (
                f"{saludo}\n"
                f"{plantilla_cobro}\n\n"
                f"• Beneficio de {mes_beneficio.title()}: aplica descuento pagando hasta el 10 a las 4:00 PM.\n\n"
                f"\U0001f4ca *Detalle de tu Estado de Cuenta:*\n"
                f"\u2022 Saldo Anterior: ${saldo_anterior:,.2f}\n"
                f"\u2022 Intereses: ${intereses:,.2f}\n"
                f"\u2022 Sanciones: ${sanciones:,.2f}\n"
                f"\u2022 Valor del Mes: ${valor_mes:,.2f}\n"
                f"--------------------------------\n"
                f"\U0001f4b0 *Total a pagar CON descuento (Hasta el 10):* ${valor_con_descuento:,.2f}\n"
                f"\U0001f534 *Total a pagar SIN descuento:* ${valor_sin_descuento:,.2f}\n\n"
                f"• Paga facil por PSE: {LINK_PAGO_PSE}\n"
                f"• Envia tu comprobante a: {EMAIL_COMPROBANTE}\n\n"
                "Atentamente, Administracion y Tesoreria.\n"
                "\U0001f449 *Este es un mensaje automatico. Para nuestros registros, por favor confirmanos con un 'Recibido' al leer este mensaje.*"
            )

            asunto = f"Cobro de administracion - Apto {apartamento}"
            pendientes.append((apartamento, propietario, telefono, correo, asunto, mensaje_final))

        total = len(pendientes)
        if total == 0:
            logger.warning("Fase 2: No hay destinatarios validos para enviar cobros.")
            return

        dias_necesarios = math.ceil(total / MAX_MENSAJES_DIARIOS)
        total_batches = min(total, dias_necesarios * LOTES_POR_DIA)
        batch_size = math.ceil(total / total_batches)

        # \U0001f6e1\ufe0f VALIDACION ESTRICTA: Garantizar que NUNCA supere el limite diario
        if (batch_size * LOTES_POR_DIA) > MAX_MENSAJES_DIARIOS:
            batch_size = max(1, MAX_MENSAJES_DIARIOS // LOTES_POR_DIA)
            total_batches = math.ceil(total / batch_size)

        espera_entre_lotes = int((24 * 3600) / LOTES_POR_DIA) if total_batches > 1 else 0

        logger.info(
            f"Fase 2: {total} envios calculados para {dias_necesarios} dia(s). "
            f"Se haran {total_batches} lotes de {batch_size} mensajes. "
            f"Espera larga entre lotes: {espera_entre_lotes} segundos ({espera_entre_lotes/3600:.1f} horas)."
        )

        for batch_index in range(total_batches):
            start = batch_index * batch_size
            end = start + batch_size
            lote = pendientes[start:end]

            logger.info(f"Fase 2: Enviando lote {batch_index + 1}/{total_batches} ({len(lote)} mensajes).")
            for item_index, (apartamento, propietario, telefono, correo, asunto, mensaje_final) in enumerate(lote):
                await enviar_notificaciones_safe_mode(telefono, correo, asunto, mensaje_final, estado_corrida)

                es_ultimo_del_lote = item_index == len(lote) - 1
                if not es_ultimo_del_lote:
                    espera_random = random.randint(90, 180)
                    logger.info(f"Fase 2: Espera aleatoria de {espera_random}s para proteger el numero...")
                    await sleep_con_conteo(espera_random, "siguiente mensaje", "Fase 2")

            if batch_index < total_batches - 1 and espera_entre_lotes > 0:
                logger.info(f"Fase 2: Descanso de {espera_entre_lotes}s antes del lote {batch_index + 2}/{total_batches}.")
                await sleep_con_conteo(espera_entre_lotes, "siguiente lote", "Fase 2")

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

        pendientes = []

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()

            # Columna D: Enviar_Mensaje (Index 3). Columna E: Correo_Electronico (Index 4).
            enviar_mensaje = row[3].strip().upper() if len(row) > 3 else "FALSE"
            correo = row[4].strip() if len(row) > 4 else ""

            try:
                # Columna F: Saldo_Anterior (Index 5)
                saldo_anterior = float(row[5].replace("$", "").replace(",", "").strip() or 0) if len(row) > 5 else 0.0
            except ValueError:
                continue

            if saldo_anterior != 0:
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
                "\u2022 Estado de Cuenta: Al dia\n"
                "\u2022 Saldo Anterior: $0.00\n"
                "Atentamente, Administracion y Tesoreria.\n"
                "\U0001f449 *Este es un mensaje automatico. \u00a1Responde con un 'Gracias' o cualquier emoji para saber que recibiste esta felicitacion!* \U0001f389"
            )

            asunto = f"Felicitacion por pago al dia - Apto {apartamento}"
            pendientes.append((apartamento, propietario, telefono, correo, asunto, mensaje_final))

        total = len(pendientes)
        if total == 0:
            logger.warning("Fase 3: No hay destinatarios validos para enviar felicitaciones.")
            return

        dias_necesarios = math.ceil(total / MAX_MENSAJES_DIARIOS)
        total_batches = min(total, dias_necesarios * LOTES_POR_DIA)
        batch_size = math.ceil(total / total_batches)

        # \U0001f6e1\ufe0f VALIDACION ESTRICTA: Garantizar que NUNCA supere el limite diario
        if (batch_size * LOTES_POR_DIA) > MAX_MENSAJES_DIARIOS:
            batch_size = max(1, MAX_MENSAJES_DIARIOS // LOTES_POR_DIA)
            total_batches = math.ceil(total / batch_size)

        espera_entre_lotes = int((24 * 3600) / LOTES_POR_DIA) if total_batches > 1 else 0

        logger.info(
            f"Fase 3: {total} envios calculados para {dias_necesarios} dia(s). "
            f"Se haran {total_batches} lotes de {batch_size} mensajes. "
            f"Espera larga entre lotes: {espera_entre_lotes} segundos ({espera_entre_lotes/3600:.1f} horas)."
        )

        for batch_index in range(total_batches):
            start = batch_index * batch_size
            end = start + batch_size
            lote = pendientes[start:end]

            logger.info(f"Fase 3: Enviando lote {batch_index + 1}/{total_batches} ({len(lote)} mensajes).")
            for item_index, (apartamento, propietario, telefono, correo, asunto, mensaje_final) in enumerate(lote):
                await enviar_notificaciones_safe_mode(telefono, correo, asunto, mensaje_final, estado_corrida)

                es_ultimo_del_lote = item_index == len(lote) - 1
                if not es_ultimo_del_lote:
                    espera_random = random.randint(90, 180)
                    logger.info(f"Fase 3: Espera aleatoria de {espera_random}s para proteger el numero...")
                    await sleep_con_conteo(espera_random, "siguiente mensaje", "Fase 3")

            if batch_index < total_batches - 1 and espera_entre_lotes > 0:
                logger.info(f"Fase 3: Descanso de {espera_entre_lotes}s antes del lote {batch_index + 2}/{total_batches}.")
                await sleep_con_conteo(espera_entre_lotes, "siguiente lote", "Fase 3")

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
