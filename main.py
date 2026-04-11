from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from routers.cobro import router as cobro_router
from services.cobro_service import procesar_recordatorios, procesar_cobros

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar reloj asíncrono
    scheduler = AsyncIOScheduler()
    
    # =========================================================
    # TAREAS PROGRAMADAS AUTOMÁTICAS (CRON INTERNO)
    # =========================================================
    
    # Fase 1 (Recordatorios): Días 5 y 10 de cada mes a las 09:00 AM
    scheduler.add_job(
        procesar_recordatorios, 
        CronTrigger(day='5,10', hour='9', minute='0'),
        id="fase1_recordatorio",
        replace_existing=True
    )
    
    # Fase 2 (Cobranzas con multa/mora): Día 15 de cada mes a las 09:00 AM
    scheduler.add_job(
        procesar_cobros, 
        CronTrigger(day='15', hour='9', minute='0'),
        id="fase2_cobranza",
        replace_existing=True
    )
    
    scheduler.start()
    print("\n⏰ Servidor en línea. ¡Reloj automático interno (APScheduler) está activo!\n")
    yield
    
    # Apagar grácilmente el reloj cuando el servidor detenga su proceso
    scheduler.shutdown()
    print("\n⏰ Reloj automático interno apagado.\n")

# Se inyecta el ciclo de vida (lifespan) a la app de FastAPI
app = FastAPI(title="Bot de Cobro - Arboreto Guayacán", version="1.0.0", lifespan=lifespan)

# Registrar el router de cobros (engloba los endpoints asociados)
app.include_router(cobro_router)

if __name__ == "__main__":
    # Script para ejecutar localmente con propósitos de debug
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
