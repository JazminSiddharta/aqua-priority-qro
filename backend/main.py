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
@app.get("/reportes/mapa")
async def mapa():

    return [
        {
            "lat":20.5888,
            "lon":-100.3899,
            "prioridad":"alta"
        },
        {
            "lat":20.5930,
            "lon":-100.3920,
            "prioridad":"media"
        }
    ]
@app.get("/rutas")
async def rutas():

    return [
        {
            "zona":"centro",
            "ruta":[
                [20.5888,-100.3899],
                [20.5930,-100.3920]
            ]
        }
    ]
@app.post("/telegram")
@app.post("/webhook/telegram")
async def telegram():

    return {
        "mensaje":"Reporte recibido desde Telegram"
    }