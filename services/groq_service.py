from groq import AsyncGroq
from core.config import settings

# Inicializar cliente de Groq de forma asíncrona
if settings.GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
else:
    groq_client = None

async def generate_message_with_groq(apartamento: str, propietario: str, saldo: float, meses_mora: int) -> str:
    """
    Genera un mensaje de cobro dinámico utilizando el modelo de Groq.
    Dependiendo de los meses de mora se usa un enfoque distinto (recordatorio vs mora).
    """
    if not groq_client:
        return f"Estimado(a) {propietario} del apto {apartamento}, recuerde su saldo de ${saldo}."
        
    # Prompt del sistema para establecer la personalidad y lineamientos
    system_prompt = (
        "Eres el asistente administrativo automatizado del conjunto residencial 'Arboreto Guayacán'. "
        "Tu objetivo es redactar mensajes de cobro de administración a los propietarios de manera profesional, "
        "clara, concisa y respetuosa, adecuada para una copropiedad. "
        "Bajo NINGUNA circunstancia debes ser grosero ni amenazante. Usa un tono cordial pero firme cuando haya mora."
    )
    
    # Construcción del prompt del usuario según el caso
    if meses_mora == 0:
        user_prompt = (
            f"El propietario {propietario} del apartamento {apartamento} tiene un saldo pendiente de ${saldo:,.2f} "
            f"correspondiente al mes actual (0 meses de mora). Redacta un mensaje de 'pronto pago' muy cordial y corto, "
            f"agradeciendo su atención y recordando el pago oportuno para el correcto mantenimiento de nuestro conjunto."
        )
    else:
        user_prompt = (
            f"El propietario {propietario} del apartamento {apartamento} tiene un saldo acumulado de ${saldo:,.2f} "
            f"y presenta {meses_mora} mes(es) de mora. Redacta un mensaje firme pero sumamente respetuoso y profesional "
            f"solicitando la regularización inmediata de la obligación. Recuerda que el pago oportuno ayuda al bienestar de "
            f"todos en 'Arboreto Guayacán'. Menciona explícitamente el apartamento, el saldo total y los meses de mora."
        )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3, # Temperatura baja para mantener el texto consistente
            max_tokens=250
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generando mensaje con Groq para apto {apartamento}: {e}")
        # Fallback en caso de error de la API
        return (f"Estimado(a) {propietario} (Apto {apartamento}), presenta un saldo pendiente de "
                f"${saldo:,.2f}. Por favor, agradecemos su pronto pago.")
