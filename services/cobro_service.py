import gspread
from oauth2client.service_account import ServiceAccountCredentials
from core.config import settings
from services.groq_service import generate_recordatorio_with_groq, generate_cobro_with_groq
from services.whatsapp_service import send_whatsapp_message

LINK_PAGO_PSE = "https://web-conjuntos.jelpit.com/pagar-mi-administracion?utm_source=Plataforma&utm_medium=Mailing&utm_campaign=HOME_JELPIT&utm_content=Conjuntos#/"
EMAIL_COMPROBANTE = "arboretoguayacan0@gmail.com"

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def obtener_datos_sheet():
    """Función helper para conectar y traer datos del Sheet."""
    if not settings.SHEET_ID:
        raise ValueError("Error crítico: La variable de entorno SHEET_ID no está configurada.")
        
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(settings.SHEET_ID).worksheet('Cartera_AG')
    records = sheet.get_all_values()
    
    if len(records) <= 1:
        return []
    
    return records[1:] # Saltar encabezados

# ===============================================
# FASE 1: PROCESAR RECORDATORIO PREVENTIVO
# ===============================================
async def procesar_recordatorios():
    """Lógica Fase 1: Enviar recordatorio general de descuento, ignora las deudas."""
    try:
        data_rows = obtener_datos_sheet()
        
        print("Generando Plantilla de Recordatorio con IA (1 Sola vez)...")
        plantilla = await generate_recordatorio_with_groq()
        
        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                print(f"Fila {idx} omitida (faltan datos básicos): {row}")
                continue
                
            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            
            # La columna F (Enviar_Mensaje) corresponde al índice 5
            enviar_mensaje = row[5].strip().upper() if len(row) > 5 else "FALSE"
            
            if telefono and enviar_mensaje == 'TRUE':
                print(f"Fase 1 (Recordatorio) -> Apto {apartamento} | {propietario}")
                
                saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacán. 👋\n"
                
                mensaje_final = f"{saludo}\n" \
                                f"{plantilla}\n\n" \
                                "• *Fecha Límite:* Hasta el día 10 del mes\n" \
                                "• *Beneficio:* 10% de descuento\n\n" \
                                f"🔗 *Paga fácil por PSE:* {LINK_PAGO_PSE}\n" \
                                f"📧 *Envía tu comprobante a:* {EMAIL_COMPROBANTE}\n\n" \
                                "Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)"
                
                await send_whatsapp_message(telefono, mensaje_final)
            else:
                print(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: Sin teléfono o 'Enviar_Mensaje' es '{enviar_mensaje}'.")
                
        print("Finalizado procesamiento de Fase 1 (Recordatorios).")
        
    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontró.")
    except Exception as e:
        print(f"Error inesperado en Fase 1: {e}")

# ===============================================
# FASE 2: PROCESAR COBRANZAS REALES
# ===============================================
async def procesar_cobros():
    """Lógica Fase 2: Lee montos y mora. Envía solo a deudores."""
    try:
        data_rows = obtener_datos_sheet()
        
        print("Generando Plantillas de Cobro con IA (Leve y Grave, solo 2 llamadas)...")
        plantilla_leve = await generate_cobro_with_groq("leve")
        plantilla_grave = await generate_cobro_with_groq("grave")
        
        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 5:
                print(f"Fila {idx} omitida (datos incompletos básicos): {row}")
                continue
                
            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()
            mora_str = row[4].strip()
            
            # La columna F (Enviar_Mensaje) corresponde al índice 5
            enviar_mensaje = row[5].strip().upper() if len(row) > 5 else "FALSE"
            
            try:
                saldo_limpio = saldo_str.replace('$', '').replace(',', '').strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
                meses_mora = int(mora_str) if mora_str else 0
            except ValueError:
                print(f"Fila {idx} (Apto {apartamento}): Error numérico (Saldo: '{saldo_str}').")
                continue
                
            if saldo > 0 and telefono and enviar_mensaje == 'TRUE':
                print(f"Fase 2 (Cobro) -> Apto {apartamento} | Saldo: ${saldo} | Mora: {meses_mora}")
                
                plantilla_base = plantilla_leve if meses_mora <= 1 else plantilla_grave
                saldo_formateado = f"{saldo:,.2f}"
                
                saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacán. 👋\n"
                
                mensaje_final = f"{saludo}\n" \
                                f"{plantilla_base}\n\n" \
                                f"• *Saldo Pendiente:* ${saldo_formateado}\n" \
                                f"• *Tiempo en Mora:* {meses_mora} mes(es)\n\n" \
                                f"🔗 *Paga fácil por PSE:* {LINK_PAGO_PSE}\n" \
                                f"📧 *Envía tu comprobante a:* {EMAIL_COMPROBANTE}\n\n" \
                                "Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)"
                                              
                await send_whatsapp_message(telefono, mensaje_final)
            elif enviar_mensaje != 'TRUE':
                print(f"Fase 2: Fila {idx} (Apto {apartamento}) omitida: La columna 'Enviar_Mensaje' dice '{enviar_mensaje}'.")    
            elif not telefono and saldo > 0:
                print(f"Fase 2: Fila {idx} omitida: Debe ${saldo} pero no tiene teléfono.")
                
        print("Finalizado procesamiento de Fase 2 (Cobranza).")
        
    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontró.")
    except Exception as e:
        print(f"Error inesperado en Fase 2: {e}")

# ===============================================
# FASE 3: PROCESAR FELICITACIONES (Saldo 0)
# ===============================================
async def procesar_felicitaciones():
    """Lógica Fase 3: Felicita a residentes con Saldo=0 y Mora=0."""
    try:
        data_rows = obtener_datos_sheet()
        
        print("Generando Plantilla de Felicitación con IA (1 Sola vez)...")
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
            
            # La columna F (Enviar_Mensaje) corresponde al índice 5
            enviar_mensaje = row[5].strip().upper() if len(row) > 5 else "FALSE"
            
            try:
                saldo_limpio = saldo_str.replace('$', '').replace(',', '').strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
                meses_mora = int(mora_str) if mora_str else 0
            except ValueError:
                continue
                
            if saldo == 0 and meses_mora == 0 and telefono and enviar_mensaje == 'TRUE':
                print(f"Fase 3 (Felicitación) -> Apto {apartamento} | {propietario}")
                
                saludo = f"Hola {propietario}, propietario(a) del apartamento {apartamento} en el Conjunto Residencial Arboreto Guayacán. 👋\n"
                
                mensaje_final = f"{saludo}\n" \
                                f"{plantilla}\n\n" \
                                "• *Estado de Cuenta:* Al día ✅\n" \
                                "• *Saldo Pendiente:* $0.00\n" \
                                "• *Tiempo en Mora:* 0 mes(es)\n\n" \
                                "Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)"
                                              
                await send_whatsapp_message(telefono, mensaje_final)
            elif enviar_mensaje != 'TRUE' and saldo == 0 and meses_mora == 0:
                print(f"Fase 3: Fila {idx} omitida por bandera 'FALSE'.")
                
        print("Finalizado procesamiento de Fase 3 (Felicitaciones).")
        
    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontró.")
    except Exception as e:
        print(f"Error inesperado en Fase 3: {e}")
