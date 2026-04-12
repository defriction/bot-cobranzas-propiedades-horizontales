import asyncio
from services.groq_service import generate_felicitacion_with_groq, generate_cobro_with_groq

async def main():
    with open('test_output.txt', 'w', encoding='utf-8') as f:
        f.write(await generate_felicitacion_with_groq() + '\n---\n')
        f.write(await generate_cobro_with_groq('leve') + '\n')

asyncio.run(main())
