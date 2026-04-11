from fastapi import APIRouter, BackgroundTasks
from services.cobro_service import procesar_recordatorios, procesar_cobros

router = APIRouter(tags=["Gestión"])

@router.get("/run-recordatorio")
@router.post("/run-recordatorio")
async def ejecutar_recordatorio(background_tasks: BackgroundTasks):
    """
    [FASE 1] Endpoint para enviar recordatorio preventivo con el beneficio de descuento.
    Se dispara típicamente los días 5 de cada mes.
    """
    print("Recibida petición al webhook /run-recordatorio. Añadiendo a tareas de fondo...")
    background_tasks.add_task(procesar_recordatorios)
    
    return {
        "status": "success",
        "message": "Fase 1 iniciada. Los recordatorios preventivos se procesan en segundo plano."
    }

@router.get("/run-cobro")
@router.post("/run-cobro")
async def ejecutar_cobro(background_tasks: BackgroundTasks):
    """
    [FASE 2] Endpoint para disparar el proceso de cobranza real a personas con deuda > 0.
    Se dispara típicamente los días 15 de cada mes.
    """
    print("Recibida petición al webhook /run-cobro. Añadiendo a tareas de fondo...")
    background_tasks.add_task(procesar_cobros)
    
    return {
        "status": "success",
        "message": "Fase 2 iniciada. El motor de cobranza se está procesando en segundo plano."
    }
