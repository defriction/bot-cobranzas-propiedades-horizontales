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
        "Escríbele un párrafo persuasivo y con emojis recordando el beneficio de pronto pago de forma corporativa. "
        "PROHIBIDO: No le des consejos de vida, no hables de vacaciones, y NUNCA generes listas ni números, ni firmas. Solo devuelve el saludo inicial y el párrafo persuasivo."
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
            "Escribe un breve párrafo recordándole amablemente la importancia de pagar la administración a tiempo para mantener hermosa la copropiedad. Agrega emojis variados. "
            "PROHIBIDO: NUNCA incluyas números, saldos, meses de mora, listas o firmas finales. Tu única tarea es devolver el saludo inicial y el párrafo amigable."
        )
    else:
        user_prompt = (
            "Contacta seriamente y con amabilidad usando EXACTAMENTE la palabra [PROPIETARIO] y menciona el inmueble como [APARTAMENTO]. "
            "Escribe un párrafo explicándole URGENTEMENTE la necesidad de regularizar su situación de deudas para el funcionamiento de la Propiedad Horizontal y evitar molestias mayores. "
            "PROHIBIDO: NUNCA incluyas números, saldos, meses de mora, listas o firmas finales. Tu única tarea es devolver el saludo inicial y el párrafo contundente con algunos emojis serios."
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

# ===============================================
# FASE 3: FELICITACIÓN (SALDO CERO)
# ===============================================
async def generate_felicitacion_with_groq() -> str:
    """
    Fase 3: Genera un mensaje de felicitación a usar como plantilla.
    """
    if not groq_client:
        return "Estimado(a) [PROPIETARIO] del apto [APARTAMENTO], felicitaciones por estar al día con sus pagos."
        
    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán'. "
        "Redacta textos muy amables, felices y concisos (máximo 1 párrafo corto o 3 oraciones). "
        "Usa emojis amigables y de celebración en WhatsApp (ej. 🎉, 🏢, ✨, 🙌). "
        "Regla estricta: Mantén un lenguaje institucional y respetuoso. NUNCA asumas situaciones personales."
    )
    
    user_prompt = (
        "Saluda muy cálidamente usando EXACTAMENTE el marcador [PROPIETARIO] y menciona su inmueble como [APARTAMENTO]. No modifiques estos marcadores. "
        "Escríbele un párrafo agradeciéndole sinceramente por estar al día con sus aportes de administración (cero mora). Resalta cómo su pago puntual ayuda a mantener hermosa la copropiedad. "
        "PROHIBIDO: NUNCA incluyas números, saldos, meses, listas o firmas finales. Tu única tarea es devolver el saludo inicial y el párrafo de agradecimiento."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generando plantilla de felicitación con Groq: {e}")
        return (f"Estimado(a) [PROPIETARIO] del Apto [APARTAMENTO], le agradecemos profundamente por estar al día "
                f"con sus obligaciones. Su puntualidad ayuda a nuestra Propiedad Horizontal. ¡Gracias!")
