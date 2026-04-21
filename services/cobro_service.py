import gspread
from oauth2client.service_account import ServiceAccountCredentials

from core.config import settings
from services.email_queue_service import enqueue_or_send_email
from services.groq_service import generate_cobro_with_groq, generate_recordatorio_with_groq
from services.whatsapp_service import send_whatsapp_message

LINK_PAGO_PSE = "https://web-conjuntos.jelpit.com/pagar-mi-administracion#/"
EMAIL_COMPROBANTE = "arboretoguayacan0@gmail.com"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


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
        await enqueue_or_send_email(correo, subject, message)
        enviado = True

    return enviado


# ===============================================
# FASE 1: PROCESAR RECORDATORIO PREVENTIVO
# ===============================================
async def procesar_recordatorios():
    """Logica Fase 1: Enviar recordatorio general de descuento, ignora las deudas."""
    try:
        data_rows = obtener_datos_sheet()

        print("Generando plantilla de Recordatorio con IA (1 sola vez)...")
        plantilla = await generate_recordatorio_with_groq()

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                print(f"Fila {idx} omitida (faltan datos basicos): {row}")
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()

            # Columna F: Enviar_Mensaje. Columna G: Correo_Electronico.
            enviar_mensaje = row[5].strip().upper() if len(row) > 5 else "FALSE"
            correo = row[6].strip() if len(row) > 6 else ""

            if enviar_mensaje != "TRUE":
                print(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                print(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: sin telefono ni Correo_Electronico.")
                continue

            print(f"Fase 1 (Recordatorio) -> Apto {apartamento} | {propietario}")

            saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacan.\n"

            mensaje_final = (
                f"{saludo}\n"
                f"{plantilla}\n\n"
                "* Fecha Limite: Hasta el dia 10 del mes\n"
                "* Beneficio: 10% de descuento\n\n"
                f"* Paga facil por PSE: {LINK_PAGO_PSE}\n"
                f"* Envia tu comprobante a: {EMAIL_COMPROBANTE}\n\n"
                "Atentamente, Administracion de Arboreto Guayacan y Tesoreria. (Este es un mensaje automatico, por favor no responder)"
            )

            asunto = f"Recordatorio de administracion - Apto {apartamento}"
            await enviar_notificaciones(telefono, correo, asunto, mensaje_final)

        print("Finalizado procesamiento de Fase 1 (Recordatorios).")

    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontro.")
    except Exception as exc:
        print(f"Error inesperado en Fase 1: {exc}")


# ===============================================
# FASE 2: PROCESAR COBRANZAS REALES
# ===============================================
async def procesar_cobros():
    """Logica Fase 2: Lee montos y mora. Envia solo a deudores."""
    try:
        data_rows = obtener_datos_sheet()

        print("Generando plantillas de Cobro con IA (Leve y Grave, solo 2 llamadas)...")
        plantilla_leve = await generate_cobro_with_groq("leve")
        plantilla_grave = await generate_cobro_with_groq("grave")

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 5:
                print(f"Fila {idx} omitida (datos incompletos basicos): {row}")
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()
            mora_str = row[4].strip()

            # Columna F: Enviar_Mensaje. Columna G: Correo_Electronico.
            enviar_mensaje = row[5].strip().upper() if len(row) > 5 else "FALSE"
            correo = row[6].strip() if len(row) > 6 else ""

            try:
                saldo_limpio = saldo_str.replace("$", "").replace(",", "").strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
                meses_mora = int(mora_str) if mora_str else 0
            except ValueError:
                print(f"Fila {idx} (Apto {apartamento}): Error numerico (Saldo: '{saldo_str}').")
                continue

            if saldo <= 0:
                continue

            if enviar_mensaje != "TRUE":
                print(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                print(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: debe ${saldo} y no tiene telefono ni Correo_Electronico.")
                continue

            print(f"Fase 2 (Cobro) -> Apto {apartamento} | Saldo: ${saldo} | Mora: {meses_mora}")

            plantilla_base = plantilla_leve if meses_mora <= 1 else plantilla_grave
            saldo_formateado = f"{saldo:,.2f}"

            saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacan.\n"

            mensaje_final = (
                f"{saludo}\n"
                f"{plantilla_base}\n\n"
                f"* Saldo Pendiente: ${saldo_formateado}\n"
                f"* Tiempo en Mora: {meses_mora} mes(es)\n\n"
                f"* Paga facil por PSE: {LINK_PAGO_PSE}\n"
                f"* Envia tu comprobante a: {EMAIL_COMPROBANTE}\n\n"
                "Atentamente, Administracion de Arboreto Guayacan y Tesoreria. (Este es un mensaje automatico, por favor no responder)"
            )

            asunto = f"Cobro de administracion - Apto {apartamento}"
            await enviar_notificaciones(telefono, correo, asunto, mensaje_final)

        print("Finalizado procesamiento de Fase 2 (Cobranza).")

    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontro.")
    except Exception as exc:
        print(f"Error inesperado en Fase 2: {exc}")


# ===============================================
# FASE 3: PROCESAR FELICITACIONES (Saldo 0)
# ===============================================
async def procesar_felicitaciones():
    """Logica Fase 3: Felicita a residentes con Saldo=0 y Mora=0."""
    try:
        data_rows = obtener_datos_sheet()

        print("Generando plantilla de Felicitacion con IA (1 sola vez)...")
        from services.groq_service import generate_felicitacion_with_groq

        plantilla = await generate_felicitacion_with_groq()

        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 5:
                continue

            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()
            mora_str = row[4].strip()

            # Columna F: Enviar_Mensaje. Columna G: Correo_Electronico.
            enviar_mensaje = row[5].strip().upper() if len(row) > 5 else "FALSE"
            correo = row[6].strip() if len(row) > 6 else ""

            try:
                saldo_limpio = saldo_str.replace("$", "").replace(",", "").strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
                meses_mora = int(mora_str) if mora_str else 0
            except ValueError:
                continue

            if saldo != 0 or meses_mora != 0:
                continue

            if enviar_mensaje != "TRUE":
                print(f"Fase 3: Fila {idx} (Apto {apartamento}) omitida: Enviar_Mensaje='{enviar_mensaje}'.")
                continue

            if not telefono and not correo:
                print(f"Fase 3: Fila {idx} (Apto {apartamento}) omitida: sin telefono ni Correo_Electronico.")
                continue

            print(f"Fase 3 (Felicitacion) -> Apto {apartamento} | {propietario}")

            saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacan.\n"

            mensaje_final = (
                f"{saludo}\n"
                f"{plantilla}\n\n"
                "* Estado de Cuenta: Al dia\n"
                "* Saldo Pendiente: $0.00\n"
                "* Tiempo en Mora: 0 mes(es)\n\n"
                "Atentamente, Administracion de Arboreto Guayacan y Tesoreria. (Este es un mensaje automatico, por favor no responder)"
            )

            asunto = f"Felicitacion por pago al dia - Apto {apartamento}"
            await enviar_notificaciones(telefono, correo, asunto, mensaje_final)

        print("Finalizado procesamiento de Fase 3 (Felicitaciones).")

    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontro.")
    except Exception as exc:
        print(f"Error inesperado en Fase 3: {exc}")
