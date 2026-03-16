from fastapi import FastAPI
from routers.cobro import router as cobro_router

app = FastAPI(title="Bot de Cobro - Arboreto Guayacán", version="1.0.0")

# Registrar el router de cobros (engloba los endpoints asociados)
app.include_router(cobro_router)

if __name__ == "__main__":
    # Script para ejecutar localmente con propósitos de debug
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
