from fastapi import APIRouter, BackgroundTasks
from services.cobro_service import procesar_cobros

router = APIRouter(tags=["Cobranza"])

@router.get("/run-cobro")
@router.post("/run-cobro")
async def ejecutar_cobro(background_tasks: BackgroundTasks):
    """
    Endpoint para disparar el proceso.
    Se ejecuta como BackgroundTask para devolver 200 OK inmediatamente al cliente/Cron de forma asíncrona.
    Soporta GET o POST para compatibilidad con crons básicos simples.
    """
    print("Recibida petición al webhook /run-cobro. Añadiendo procesamiento a tareas de fondo...")
    background_tasks.add_task(procesar_cobros)
    
    return {
        "status": "success",
        "message": "Solicitud recibida correctamente. El motor de cobranza se está procesando en segundo plano."
    }
