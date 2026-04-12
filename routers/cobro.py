from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security
from fastapi.security import APIKeyQuery, APIKeyHeader
from services.cobro_service import procesar_recordatorios, procesar_cobros
from core.config import settings

router = APIRouter(tags=["Gestión"])

api_key_query = APIKeyQuery(name="token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_token(query_token: str = Security(api_key_query), header_token: str = Security(api_key_header)):
    token = query_token or header_token
    if not token or token != settings.API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Acceso denegado: Token de seguridad inválido o ausente.")
    return token

@router.get("/run-recordatorio", dependencies=[Depends(verify_token)])
@router.post("/run-recordatorio", dependencies=[Depends(verify_token)])
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

@router.get("/run-cobro", dependencies=[Depends(verify_token)])
@router.post("/run-cobro", dependencies=[Depends(verify_token)])
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

@router.get("/run-felicitacion", dependencies=[Depends(verify_token)])
@router.post("/run-felicitacion", dependencies=[Depends(verify_token)])
async def ejecutar_felicitacion(background_tasks: BackgroundTasks):
    """
    [FASE 3] Endpoint para disparar el proceso de felicitación a personas con saldo y mora en 0.
    Se dispara típicamente los días 20 de cada mes.
    """
    from services.cobro_service import procesar_felicitaciones
    print("Recibida petición al webhook /run-felicitacion. Añadiendo a tareas de fondo...")
    background_tasks.add_task(procesar_felicitaciones)
    
    return {
        "status": "success",
        "message": "Fase 3 iniciada. El envío de diplomas de felicitaciones se procesa al fondo."
    }
