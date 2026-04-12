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
        return "Le recordamos pagar su administración antes del día 10 para disfrutar de su beneficio."
        
    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán'. "
        "Redacta textos amables, EXTREMADAMENTE concisos y al grano (MÁXIMO 1 sola oración corta). "
        "Usa emojis amigables y variados en WhatsApp (ej. 👋, 🏢, ✨). "
        "Regla estricta 1: NUNCA menciones saldos ni fechas. "
        "Regla estricta 2: Mantén un lenguaje institucional, corporativo y respetuoso."
    )
    
    user_prompt = (
        "Escribe un solo párrafo persuasivo y con emojis recordando el beneficio de pronto pago de forma corporativa. "
        "PROHIBIDO: No incluyas saludos (Hola, Estimado), nombres de propietarios, apartamentos, despedidas, listas ni números. Tu única tarea es escribir el texto central persuasivo."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=60
        )
        return completion.choices[0].message.content.strip(' "\'”“')
    except Exception as e:
        print(f"Error generando plantilla recordatorio con Groq: {e}")
        return "Le recordamos amablemente que si realiza su pago de administración a tiempo podrá disfrutar del descuento. ¡Gracias!"

# ===============================================
# FASE 2: GESTIÓN DE COBRANZA Y MORA
# ===============================================
async def generate_cobro_with_groq(tipo: str) -> str:
    """
    Fase 2: Genera un mensaje de cobro dinámico según la mora en formato plantilla.
    tipo puede ser 'leve' (0-1 meses) o 'grave' (2+ meses).
    """
    if not groq_client:
        return "Le solicitamos amablemente revisar su estado de cuenta para ponerse al día."
        
    system_prompt = (
        "Eres el asistente de 'Arboreto Guayacán'. "
        "Tus mensajes en WhatsApp deben ser EXTREMADAMENTE concisos (MÁXIMO 1 sola oración directa). "
        "Mete un par de emojis pertinentes (ej. 🏢, ⚠️, 🤝) para no aburrir. "
        "NUNCA seas grosero, mantén un tono relajado pero firme al hablar de multas o mora."
    )
    
    if tipo == "leve":
        user_prompt = (
            "Escribe un solo párrafo recordándole amablemente a un deudor la importancia de pagar la administración a tiempo para mantener hermosa la copropiedad. Agrega emojis variados. "
            "PROHIBIDO: NUNCA incluyas saludos iniciales, despedidas, nombres, apartamentos, números, saldos o listas. Ve directo al grano con el pequeño párrafo."
        )
    else:
        user_prompt = (
            "Escribe un solo párrafo explicándole URGENTEMENTE a un deudor moroso la necesidad de regularizar su situación financiera para el mantenimiento de la Propiedad Horizontal y evitar problemas. "
            "PROHIBIDO: NUNCA incluyas saludos iniciales, despedidas, nombres, apartamentos, números, saldos o listas. Escribe solo el texto estricto."
        )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=60
        )
        return completion.choices[0].message.content.strip(' "\'”“')
    except Exception as e:
        print(f"Error generando plantilla de cobro con Groq ({tipo}): {e}")
        return "Por favor, lo invitamos a ponerse al corriente con sus obligaciones administrativas."

# ===============================================
# FASE 3: FELICITACIÓN (SALDO CERO)
# ===============================================
async def generate_felicitacion_with_groq() -> str:
    """
    Fase 3: Genera un mensaje de felicitación a usar como plantilla.
    """
    if not groq_client:
        return "Le agradecemos profundamente por estar al día con sus pagos."
        
    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacán'. "
        "Redacta textos EXTREMADAMENTE felices pero muy al grano (MÁXIMO 1 sola oración corta). "
        "Usa emojis de celebración (ej. 🎉, 🏢, ✨, 🙌). "
        "Regla estricta: Mantén un lenguaje institucional y respetuoso. NUNCA asumas situaciones personales."
    )
    
    user_prompt = (
        "Escribe un solo párrafo agradeciéndole sinceramente a un residente por estar perfectamente al día con sus aportes de administración (cero mora). Resalta cómo su pago puntual ayuda a mantener en excelentes condiciones la copropiedad. "
        "PROHIBIDO: NUNCA incluyas saludos iniciales, despedidas, nombres, apartamentos, números o firmas finales. Entra directo al párrafo de celebración."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=60
        )
        return completion.choices[0].message.content.strip(' "\'”“')
    except Exception as e:
        print(f"Error generando plantilla de felicitación con Groq: {e}")
        return "Agradecemos profundamente su compromiso; su puntualidad con la administración es invaluable."
