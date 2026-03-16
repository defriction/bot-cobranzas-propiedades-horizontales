import gspread
from oauth2client.service_account import ServiceAccountCredentials
from core.config import settings
from services.groq_service import generate_message_with_groq
from services.whatsapp_service import send_whatsapp_message

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

async def procesar_cobros():
    """Lógica core que conecta Sheets, Groq y la simulación de WhatsApp."""
    if not settings.SHEET_ID:
        print("Error crítico: La variable de entorno SHEET_ID no está configurada.")
        return

    try:
        # Autenticar y conectar a Google Sheets usando credentials.json
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPES)
        client = gspread.authorize(creds)
        
        # Abrir el libro y seleccionar la pestaña específica
        sheet = client.open_by_key(settings.SHEET_ID).worksheet('Cartera_AG')
        
        # Obtener todos los valores (incluyendo cabecera)
        records = sheet.get_all_values()
        
        if len(records) <= 1:
            print("El documento Google Sheet está vacío o solo contiene la cabecera.")
            return

        # Ignorar la primera fila (encabezados)
        data_rows = records[1:]
        
        for idx, row in enumerate(data_rows, start=2):
            # Validar que existan las 5 columnas requeridas en la fila 
            if len(row) < 5:
                print(f"Fila {idx} omitida (datos incompletos): {row}")
                continue
                
            apartamento = row[0].strip()
            propietario = row[1].strip()
            telefono = row[2].strip()
            saldo_str = row[3].strip()
            mora_str = row[4].strip()
            
            try:
                # Limpiar caracteres comunes que impiden convertir a número
                saldo_limpio = saldo_str.replace('$', '').replace(',', '').strip()
                saldo = float(saldo_limpio) if saldo_limpio else 0.0
                
                meses_mora = int(mora_str) if mora_str else 0
            except ValueError:
                print(f"Fila {idx} (Apto {apartamento}): Error convirtiendo numéricos (Saldo: {saldo_str}, Mora: {mora_str})")
                continue
                
            # Solo procesar a los que deben más de $0
            if saldo > 0:
                print(f"Iniciando flujo para: Apto {apartamento} | Propietario: {propietario} | Saldo: ${saldo} | Mora: {meses_mora}")
                mensaje_generado = await generate_message_with_groq(apartamento, propietario, saldo, meses_mora)
                await send_whatsapp_message(telefono, mensaje_generado)
                
        print("Finalizada la lectura de Google Sheets y el procesamiento de cobros de este lote.")
        
    except FileNotFoundError:
        print("Error: El archivo 'credentials.json' no se encontró en el directorio actual. Es requerido para Google Sheets.")
    except Exception as e:
        print(f"Error inesperado procesando el sheet: {e}")
