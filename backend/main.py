from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Reporte(BaseModel):
    tipo: str
    zona_tipo: str

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.post("/reportes")
async def crear_reporte(data: Reporte):

    prioridad = "alta"

    return {
        "tipo": data.tipo,
        "zona": data.zona_tipo,
        "prioridad": prioridad
    }