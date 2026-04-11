import gspread
from oauth2client.service_account import ServiceAccountCredentials
from core.config import settings
from services.groq_service import generate_recordatorio_with_groq, generate_cobro_with_groq
from services.whatsapp_service import send_whatsapp_message

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
        
        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                print(f"Fila {idx} omitida (faltan datos): {row}")
                continue
                
            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            
            if telefono:
                print(f"Fase 1 (Recordatorio) -> Apto {apartamento} | {propietario}")
                mensaje_generado = await generate_recordatorio_with_groq(apartamento, propietario)
                await send_whatsapp_message(telefono, mensaje_generado)
            else:
                print(f"Fase 1: Fila {idx} (Apto {apartamento}) omitida: Sin teléfono.")
                
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
        
        for idx, row in enumerate(data_rows, start=2):
            if len(row) < 5:
                print(f"Fila {idx} omitida (datos incompletos): {row}")
                continue
                
            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()
            mora_str = row[4].strip()
            
            try:
                saldo_limpio = saldo_str.replace('$', '').replace(',', '').strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
                meses_mora = int(mora_str) if mora_str else 0
            except ValueError:
                print(f"Fila {idx} (Apto {apartamento}): Error numérico (Saldo: '{saldo_str}').")
                continue
                
            if saldo > 0 and telefono:
                print(f"Fase 2 (Cobro) -> Apto {apartamento} | Saldo: ${saldo} | Mora: {meses_mora}")
                mensaje_generado = await generate_cobro_with_groq(apartamento, propietario, saldo, meses_mora)
                await send_whatsapp_message(telefono, mensaje_generado)
            elif not telefono and saldo > 0:
                print(f"Fase 2: Fila {idx} omitida: Debe ${saldo} pero no tiene teléfono.")
                
        print("Finalizado procesamiento de Fase 2 (Cobranza).")
        
    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontró.")
    except Exception as e:
        print(f"Error inesperado en Fase 2: {e}")
