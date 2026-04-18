from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# ¡Aquí importamos TU código de IA!
from services.nlp import clasificar_reporte

load_dotenv()
app = FastAPI(title="Aqua Priority API")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup():
    app.mongodb = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    app.db = app.mongodb[os.getenv("DB_NAME", "aqua_priority")]
    print("✅ Conectado a la base de datos")

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Backend Aqua-Priority funcionando"}

# --- NUEVO: RUTA PARA LA IA ---

# Definimos cómo esperamos recibir el mensaje del ciudadano
class MensajeCiudadano(BaseModel):
    texto: str

@app.post("/api/procesar-ia")
async def procesar_mensaje(mensaje: MensajeCiudadano):
    """
    Recibe un texto simulando WhatsApp, lo pasa por tu IA y devuelve el JSON.
    """
    # Pasamos el texto a tu motor de NLP
    resultado_ia = await clasificar_reporte(mensaje.texto)
    
    # Devolvemos el resultado listo para que el Front lo dibuje o la DB lo guarde
    return {
        "status": "procesado",
        "datos_clasificados": resultado_ia
    }
