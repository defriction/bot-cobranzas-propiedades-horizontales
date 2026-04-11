from groq import AsyncGroq
from core.config import settings

# Inicializar cliente de Groq de forma asíncrona
if settings.GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
else:
    groq_client = None

# ===============================================
# FASE 1: RECORDATORIO PREVENTIVO (DESCUENTO)
# ===============================================
async def generate_recordatorio_with_groq(apartamento: str, propietario: str) -> str:
    """
    Fase 1: Genera un mensaje de recordatorio general de pronto pago.
    No se mencionan montos de deuda.
    """
    if not groq_client:
        return f"Estimado(a) {propietario} del apto {apartamento}, recuerde pagar su administración antes del día 10 para disfrutar de un 10% de descuento."
        
    system_prompt = (
        "Eres el asistente administrativo automatizado del conjunto residencial 'Arboreto Guayacán'. "
        "Tu objetivo es redactar un mensaje recordatorio cordial, profesional, corto y amigable para fomentar la cultura de pronto pago. "
        "Usa siempre emojis para que el mensaje se sienta ameno y humano (ej. 👋, 🏢, ✨, 📱), sin exagerar. "
        "Bajo ninguna circunstancia debes mencionar valores específicos de saldo o meses de mora, ya que esta es una comunicación general preventiva."
    )
    
    user_prompt = (
        f"Redacta un mensaje muy amable dirigido a {propietario}, residente del apartamento {apartamento}. "
        "El mensaje debe recordarle que si realiza el pago de la cuota de administración "
        "antes o incluso el mismo día 10 de este mes, se beneficiará de un 10% de descuento por pronto pago. "
        "No uses placeholders como [Mes] o [Año], queremos que suene natural. Invítalo amablemente a aprovechar este beneficio. "
        "IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración Arboreto Guayacán. (Este es un mensaje automático, por favor no responder)'."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generando recordatorio con Groq para apto {apartamento}: {e}")
        return (f"Estimado(a) {propietario} del Apto {apartamento}, le recordamos amablemente que si realiza "
                f"su pago de administración antes del 10 del presente mes, podrá disfrutar del 10% de descuento. ¡Gracias!")

# ===============================================
# FASE 2: GESTIÓN DE COBRANZA Y MORA
# ===============================================
async def generate_cobro_with_groq(apartamento: str, propietario: str, saldo: float, meses_mora: int) -> str:
    """
    Fase 2: Genera un mensaje de cobro dinámico según la mora.
    """
    if not groq_client:
        return f"Estimado(a) {propietario} del apto {apartamento}, recuerde su saldo de ${saldo}."
        
    system_prompt = (
        "Eres el asistente administrativo automatizado del conjunto residencial 'Arboreto Guayacán'. "
        "Tu objetivo es redactar mensajes de cobro de administración a los propietarios de manera profesional, "
        "clara, concisa y respetuosa, adecuada para una copropiedad. "
        "Acompaña el mensaje de algunos emojis pertinentes (ej. 🏢, 💡, 📅, 💳) para mantener un aspecto amigable. "
        "Bajo NINGUNA circunstancia debes ser grosero ni amenazante. Usa un tono cordial pero firme cuando haya mora acumulada."
    )
    
    if meses_mora == 0 or meses_mora == 1:
        user_prompt = (
            f"El propietario {propietario} del apartamento {apartamento} tiene un saldo pendiente de ${saldo:,.2f} "
            f"correspondiente a una mora reciente ({meses_mora} meses). Redacta un mensaje de 'recordatorio' cordial y corto, "
            f"informándole su saldo actual, agradeciendo su atención y recordando que el pago oportuno es vital "
            f"para el mantenimiento del conjunto residencial. "
            f"IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración Arboreto Guayacán. (Este es un mensaje automático, por favor no responder)'."
        )
    else:
        user_prompt = (
            f"El propietario {propietario} del apartamento {apartamento} tiene un saldo acumulado de ${saldo:,.2f} "
            f"y presenta {meses_mora} mes(es) de mora. Redacta un mensaje firme pero respetuoso y profesional "
            f"solicitando la regularización inmediata de la obligación. Menciona explícitamente el apartamento, el saldo a pagar y los meses de mora. "
            f"IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración Arboreto Guayacán. (Este es un mensaje automático, por favor no responder)'."
        )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generando cobro con Groq para apto {apartamento}: {e}")
        return (f"Estimado(a) {propietario} (Apto {apartamento}), presenta un saldo pendiente de "
                f"${saldo:,.2f}. Por favor, agradecemos su pronto pago.")
