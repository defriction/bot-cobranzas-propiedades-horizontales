from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

from core.config import settings
from services.cobro_service import procesar_cobros, procesar_recordatorios

router = APIRouter(tags=["Gestion"])

api_key_query = APIKeyQuery(name="token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_token(query_token: str = Security(api_key_query), header_token: str = Security(api_key_header)):
    token = query_token or header_token
    if not token or token != settings.API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Acceso denegado: Token de seguridad invalido o ausente.")
    return token


@router.get("/run-recordatorio", dependencies=[Depends(verify_token)])
@router.post("/run-recordatorio", dependencies=[Depends(verify_token)])
async def ejecutar_recordatorio(background_tasks: BackgroundTasks):
    """
    [FASE 1] Endpoint para enviar recordatorio preventivo con el beneficio de descuento.
    """
    print("Recibida peticion al webhook /run-recordatorio. Anadiendo a tareas de fondo...")
    background_tasks.add_task(procesar_recordatorios)

    return {
        "status": "success",
        "message": "Fase 1 iniciada. Los recordatorios preventivos se procesan en segundo plano.",
    }


@router.get("/run-cobro", dependencies=[Depends(verify_token)])
@router.post("/run-cobro", dependencies=[Depends(verify_token)])
async def ejecutar_cobro(background_tasks: BackgroundTasks):
    """
    [FASE 2] Endpoint para disparar el proceso de cobranza real a personas con deuda > 0.
    """
    print("Recibida peticion al webhook /run-cobro. Anadiendo a tareas de fondo...")
    background_tasks.add_task(procesar_cobros)

    return {
        "status": "success",
        "message": "Fase 2 iniciada. El motor de cobranza se esta procesando en segundo plano.",
    }


@router.get("/run-felicitacion", dependencies=[Depends(verify_token)])
@router.post("/run-felicitacion", dependencies=[Depends(verify_token)])
async def ejecutar_felicitacion(background_tasks: BackgroundTasks):
    """
    [FASE 3] Endpoint para disparar el proceso de felicitacion a personas con saldo en 0.
    """
    from services.cobro_service import procesar_felicitaciones

    print("Recibida peticion al webhook /run-felicitacion. Anadiendo a tareas de fondo...")
    background_tasks.add_task(procesar_felicitaciones)

    return {
        "status": "success",
        "message": "Fase 3 iniciada. El envio de felicitaciones se procesa al fondo.",
    }
