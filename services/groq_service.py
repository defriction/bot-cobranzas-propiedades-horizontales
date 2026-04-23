from groq import AsyncGroq

from core.config import settings


if settings.GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
else:
    groq_client = None


async def generate_recordatorio_with_groq() -> str:
    """
    Fase 1: Genera un mensaje de recordatorio general de pronto pago.
    """
    if not groq_client:
        return "Le recordamos pagar su administracion antes del dia 10 para disfrutar del beneficio."

    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacan'. "
        "Redacta textos amables, extremadamente concisos y al grano (maximo 1 sola oracion corta). "
        "Usa emojis amigables y variados para WhatsApp. "
        "Regla estricta 1: Nunca menciones saldos ni fechas. "
        "Regla estricta 2: Manten lenguaje institucional, corporativo y respetuoso."
    )

    user_prompt = (
        "Escribe una sola oracion persuasiva y muy amigable como recordatorio preventivo para aprovechar "
        "el beneficio de pronto pago de este mes. "
        "Prohibido: saludos, nombres, apartamentos, despedidas, listas y numeros."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=150,
        )
        return completion.choices[0].message.content.strip(' "\'')
    except Exception as exc:
        print(f"Error generando plantilla recordatorio con Groq: {exc}")
        return "Le recordamos amablemente que el pronto pago le permite mantener sus beneficios. Gracias."


async def generate_cobro_with_groq() -> str:
    """
    Fase 2: Genera un mensaje de cobro general (sin usar Meses_Mora).
    """
    if not groq_client:
        return "Le solicitamos amablemente revisar su estado de cuenta para ponerse al dia."

    system_prompt = (
        "Eres el asistente de 'Arboreto Guayacan'. "
        "Tus mensajes en WhatsApp deben ser extremadamente concisos (maximo 1 sola oracion directa). "
        "Usa un par de emojis pertinentes y manten un tono respetuoso y firme."
    )

    user_prompt = (
        "Escribe una sola oracion de aviso de cobro cordial, recordando que hay saldo pendiente de administracion. "
        "Prohibido: saludos, despedidas, nombres, apartamentos, numeros, saldos exactos o listas."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=150,
        )
        return completion.choices[0].message.content.strip(' "\'')
    except Exception as exc:
        print(f"Error generando plantilla de cobro con Groq: {exc}")
        return "Por favor, lo invitamos a ponerse al corriente con sus obligaciones administrativas."


async def generate_felicitacion_with_groq() -> str:
    """
    Fase 3: Genera un mensaje de felicitacion para residentes al dia (saldo cero).
    """
    if not groq_client:
        return "Le agradecemos profundamente por estar al dia con sus pagos."

    system_prompt = (
        "Eres el asistente de la Propiedad Horizontal 'Arboreto Guayacan'. "
        "Redacta textos breves, alegres y claros (maximo 1 sola oracion). "
        "Usa emojis de celebracion y manten lenguaje institucional y respetuoso."
    )

    user_prompt = (
        "Escribe una sola oracion de agradecimiento para un residente con saldo en cero. "
        "Resalta que su pago puntual ayuda al buen estado de la copropiedad. "
        "Prohibido: saludos, despedidas, nombres, apartamentos, numeros o firmas."
    )

    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=150,
        )
        return completion.choices[0].message.content.strip(' "\'')
    except Exception as exc:
        print(f"Error generando plantilla de felicitacion con Groq: {exc}")
        return "Agradecemos profundamente su compromiso; su puntualidad con la administracion es invaluable."
