import os
import asyncio # Importante para las tareas del bot
from fastapi import FastAPI
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

app = FastAPI()

# Conexión usando tus variables del .env
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
collection = db["Reportes"]

class Reporte(BaseModel):
    tipo: str
    zona_tipo: str

# --- LÓGICA DE TELEGRAM ---
async def handle_telegram_message(update, context):
    texto = update.message.text
    # Creamos el reporte para el mapa
    nuevo_reporte = {
        "lat": 20.5888, # Coordenada base
        "lon": -100.3899,
        "prioridad": "alta" if "fuga" in texto.lower() else "media",
        "texto": texto
    }
    # Guardamos en la misma colección de tus 60 reportes
    await collection.insert_one(nuevo_reporte)
    await update.message.reply_text("✅ ¡Gracias! Tu reporte ha sido registrado en Aqua Priority QRO.")

# --- RUTA PARA EL MAPA ---
@app.get("/reportes/mapa")
async def mapa():
    # Traemos todos los reportes (los 60 del seed + los nuevos de Telegram)
    cursor = collection.find({}, {"_id": 0})
    reportes = await cursor.to_list(length=1000)
    return reportes