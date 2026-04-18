import os
from fastapi import FastAPI
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- TU CONEXIÓN A MONGO ---
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
collection = db["Reportes"]

class Reporte(BaseModel):
    tipo: str
    zona_tipo: str

@app.get("/health")
async def health():
    return {"status":"ok"}

# --- RUTA QUE NECESITAS PARA EL MAPA ---
@app.get("/reportes/mapa")
async def mapa():
    cursor = collection.find({}, {"_id": 0})
    reportes = await cursor.to_list(length=1000)
    return reportes

@app.post("/reportes")
async def crear_reporte(data: Reporte):
    prioridad = "alta"
    
    # Guardamos en tu DB real
    nuevo_doc = {
        "tipo": data.tipo,
        "zona": data.zona_tipo,
        "prioridad": prioridad
    }
    await collection.insert_one(nuevo_doc)

    return nuevo_doc