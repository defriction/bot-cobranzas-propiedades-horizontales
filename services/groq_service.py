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
async def generate_recordatorio_with_groq() -> str:
    """
    Fase 1: Genera un mensaje de recordatorio general de pronto pago usando plantilla.
    """
    if not groq_client:
        return "Estimado(a) [PROPIETARIO] del apto [APARTAMENTO], recuerde pagar su administración antes del día 10 para disfrutar de un 10% de descuento."
        
    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán' (la cual está conformada por múltiples torres y edificios). "
        "Redacta textos amables, concisos y bien estructurados (máximo 1 párrafo corto o 3 oraciones). "
        "Usa emojis amigables y variados en WhatsApp (ej. 👋, 🏢, ✨, 📱). "
        "Regla estricta 1: El descuento es EXACTAMENTE del 10% y la fecha límite es EXACTAMENTE el día 10 del mes. PROHIBIDO alterar estos números. NUNCA menciones saldos. "
        "Regla estricta 2: Mantén un lenguaje institucional, corporativo y respetuoso. NUNCA asumas situaciones personales ni propongas qué hacer con el dinero ahorrado (cero menciones a viajes, cine, playa, etc)."
    )
    
    user_prompt = (
        "Saluda amablemente a la persona usando EXACTAMENTE la palabra [PROPIETARIO] y menciona su inmueble usando EXACTAMENTE la palabra [APARTAMENTO]. No modifiques estos corchetes. "
        "Escríbele un mensaje persuasivo y con emojis recordando el beneficio de pronto pago. "
        "REGLA DE FORMATO: Resalta los números EXACTOS en negritas (asteriscos) EN FORMA DE LISTA:\n"
        "• *Fecha Límite:* Hasta el día 10 del mes\n"
        "• *Beneficio:* 10% de descuento\n\n"
        "Explica los beneficios de forma ESTRICTAMENTE ADMINISTRATIVA. PROHIBIDO MODIFICAR LOS NÚMEROS: SIEMPRE es el día 10 y SIEMPRE es un 10% de descuento. Limítate a ser un asesor corporativo. "
        "IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)'."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=180
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generando plantilla recordatorio con Groq: {e}")
        return (f"Estimado(a) [PROPIETARIO] del Apto [APARTAMENTO], le recordamos amablemente que si realiza "
                f"su pago de administración antes del 10 del presente mes, podrá disfrutar del 10% de descuento. ¡Gracias!")

# ===============================================
# FASE 2: GESTIÓN DE COBRANZA Y MORA
# ===============================================
async def generate_cobro_with_groq(tipo: str) -> str:
    """
    Fase 2: Genera un mensaje de cobro dinámico según la mora en formato plantilla.
    tipo puede ser 'leve' (0-1 meses) o 'grave' (2+ meses).
    """
    if not groq_client:
        return f"Estimado(a) [PROPIETARIO] del apto [APARTAMENTO], recuerde su saldo de $[SALDO]."
        
    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán' (conformada por múltiples torres y edificios). "
        "Tus mensajes en WhatsApp deben ser bien estructurados y concisos (máximo 1 párrafo corto o 4 oraciones). "
        "Mete varios emojis pertinentes (ej. 🏢, 💡, 📅, 💳, ⚠️, 🤝) para que el texto sea dinámico y no aburrido. "
        "NUNCA seas grosero, mantén un tono relajado pero firme al hablar de multas o mora."
    )
    
    if tipo == "leve":
        user_prompt = (
            "Saluda de forma cordial usando EXACTAMENTE el marcador [PROPIETARIO] y refiérete al inmueble usando el marcador [APARTAMENTO]. "
            "Notifícale su estado actual usando negritas de WhatsApp (encerra en asteriscos) y EN FORMA DE LISTA, usando estos marcadores obligatoriamente (NO inventes números):\n"
            "• *Saldo Pendiente:* $[SALDO]\n"
            "• *Tiempo en Mora:* [MESES_MORA] mes(es)\n\n"
            f"Recuérdale en una breve oración lo importante que es pagar a tiempo para mantener hermosa la copropiedad. Agrega emojis variados. "
            f"IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)'."
        )
    else:
        user_prompt = (
            "Contacta seriamente y con amabilidad usando EXACTAMENTE la palabra [PROPIETARIO] y menciona el inmueble como [APARTAMENTO]. "
            "Notifícale la deuda usando negritas de WhatsApp (asteriscos) y EN FORMA DE LISTA CLARA, usando estos marcadores (NO inventes números):\n"
            "• *Saldo Acumulado:* $[SALDO]\n"
            "• *Meses de Mora:* [MESES_MORA] mes(es)\n\n"
            f"Explícale urgentemente la necesidad de regularizar la situación para el funcionamiento de la Propiedad Horizontal y evitar molestias posteriores. "
            f"IMPORTANTE: Firma siempre el mensaje al final exactamente como: 'Atentamente, Administración de Arboreto Guayacán y Tesorería. (Este es un mensaje automático, por favor no responder)'."
        )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=180
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generando plantilla de cobro con Groq ({tipo}): {e}")
        return (f"Estimado(a) [PROPIETARIO] (Apto [APARTAMENTO]), presenta un saldo pendiente de "
                f"${saldo:,.2f}. Por favor, agradecemos su pronto pago.")
