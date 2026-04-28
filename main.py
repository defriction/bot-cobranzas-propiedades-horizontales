import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from routers.cobro import router as cobro_router
from services.cobro_service import procesar_cobros, procesar_felicitaciones, procesar_recordatorios


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()

    # Fase 1 (Recordatorios): dias 5 y 10 de cada mes a las 09:00 AM (Hora Colombia).
    scheduler.add_job(
        procesar_recordatorios,
        CronTrigger(day="5,9", hour="9", minute="0", timezone="America/Bogota"),
        id="fase1_recordatorio",
        replace_existing=True,
    )

    # Fase 2 (Cobranzas): Dia 15 de cada mes a las 09:00 AM (Hora Colombia)
    # scheduler.add_job(
    #     procesar_cobros,
    #     CronTrigger(day="15", hour="9", minute="0", timezone="America/Bogota"),
    #     id="fase2_cobranza",
    #     replace_existing=True,
    # )

    # Fase 2 EXTRA (Corrida especial): Dia 12 del mes a las 12:00 PM (Mediodia Hora Colombia)
    # scheduler.add_job(
    #     procesar_cobros,
    #     CronTrigger(day="12", hour="12", minute="0", timezone="America/Bogota"),
    #     id="fase2_cobranza_test_hoy",
    #     replace_existing=True,
    # )

    # Fase 3 (Felicitaciones por estar al dia): Dia 20 de cada mes a las 09:00 AM (Hora Colombia)
    # scheduler.add_job(
    #     procesar_felicitaciones,
    #     CronTrigger(day="20", hour="9", minute="0", timezone="America/Bogota"),
    #     id="fase3_felicitacion",
    #     replace_existing=True,
    # )

    scheduler.start()

    logger = logging.getLogger("uvicorn.error")
    logger.info("Servidor en linea. APScheduler activo.")

    yield

    scheduler.shutdown()
    logger.info("APScheduler apagado.")


app = FastAPI(title="Bot de Cobro - Arboreto Guayacan", version="1.0.0", lifespan=lifespan)
app.include_router(cobro_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
