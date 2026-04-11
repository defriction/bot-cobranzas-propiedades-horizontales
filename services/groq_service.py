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
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán' (la cual está conformada por múltiples torres y edificios). "
        "Redacta textos amables y bien estructurados (de 1 a 2 párrafos cortos). "
        "Usa emojis amigables y variados en WhatsApp (ej. 👋, 🏢, ✨, 📱, 🌿, 🚀). "
        "Regla estricta 1: NUNCA menciones montos de dinero ni meses de mora, es un recordatorio general preventivo para toda la copropiedad. "
        "Regla estricta 2: Mantén un lenguaje institucional, corporativo y respetuoso. NUNCA asumas situaciones personales ni propongas qué hacer con el dinero ahorrado (cero menciones a viajes, cine, playa, etc)."
    )
    
    user_prompt = (
        f"Saluda amablemente a {propietario} (Apto {apartamento}). "
        "Escríbele un mensaje persuasivo (con varios emojis divertidos) recordándole que si paga su cuota de administración "
        "antes o el mismo día 10 del mes, obtendrá un 10% de descuento. "
        "Explica los beneficios de esto de forma ESTRICTAMENTE ADMINISTRATIVA (por ejemplo, el ahorro financiero y el apoyo para el mantenimiento de nuestro patrimonio en común). "
        "PROHIBIDO: No le des consejos de vida, ni hables de vacaciones, tiempo libre o películas. Limítate a ser un asesor corporativo. "
        "IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)'."
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
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán' (conformada por múltiples torres y edificios). "
        "Tus mensajes en WhatsApp deben ser bien estructurados y educados (de 1 a 2 párrafos cortos). "
        "Mete varios emojis pertinentes (ej. 🏢, 💡, 📅, 💳, ⚠️, 🤝) para que el texto sea dinámico y no aburrido. "
        "NUNCA seas grosero, mantén un tono relajado pero firme al hablar de multas o mora."
    )
    
    if meses_mora == 0 or meses_mora == 1:
        user_prompt = (
            f"Saluda de forma cordial y estructurada a {propietario} (Inmueble: {apartamento}). "
            f"Avísale amigablemente con varios emojis que su estado actual de mora es de {meses_mora} mes(es) por un saldo de ${saldo:,.2f}. "
            f"Tómate un par de oraciones para recordarle lo importante que es pagar a tiempo para mantener hermosa la copropiedad y sus torres. "
            f"IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)'."
        )
    else:
        user_prompt = (
            f"Contacta seriamente pero con amabilidad a {propietario} (Inmueble: {apartamento}). "
            f"Notifícale de manera clara (inyectando algunos emojis) que presenta {meses_mora} meses de mora, con un acumulado a pagar de ${saldo:,.2f}. "
            f"Explícale la urgencia de regularizar su situación y las ventajas de estar al día para el buen funcionamiento de la Propiedad Horizontal. "
            f"IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)'."
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
