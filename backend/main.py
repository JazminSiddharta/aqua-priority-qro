import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Librerías de Telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

app = FastAPI()

# --- CONEXIÓN A TU BASE DE DATOS LOCAL ---
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
collection = db["Reportes"]

# Modelo para la API
class Reporte(BaseModel):
    tipo: str
    zona_tipo: str

# --- DICCIONARIO TEMPORAL PARA EL FLUJO DEL BOT ---
user_data_temp = {}

# --- LÓGICA DEL CHATBOT (PASO A PASO) ---
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    texto = update.message.text

    # Si el usuario no ha iniciado un reporte o saluda
    if user_id not in user_data_temp:
        if any(palabra in texto.lower() for palabra in ["hola", "reportar", "buenos días", "fuga"]):
            user_data_temp[user_id] = {"paso": 1}
            await update.message.reply_text(
                "👋 ¡Hola! Soy el asistente de Aqua Priority QRO.\n\n"
                "Vamos a registrar tu reporte de forma ordenada.\n"
                "1️⃣ **¿Qué tipo de problema quieres reportar?**\n"
                "(Ejemplo: Fuga de agua, Falta de suministro, Tubería rota)"
            )
        else:
            await update.message.reply_text("Para iniciar un reporte, por favor escribe 'Hola' o 'Reportar'.")
        return

    # PASO 1: Recibir el TIPO de reporte
    if user_data_temp[user_id]["paso"] == 1:
        user_data_temp[user_id]["tipo"] = texto
        user_data_temp[user_id]["paso"] = 2
        await update.message.reply_text(
            f"Entendido: *{texto}*.\n\n"
            "2️⃣ **¿En qué ubicación o colonia se encuentra el problema?**",
            parse_mode="Markdown"
        )
        return

    # PASO 2: Recibir UBICACIÓN y Guardar en MongoDB
    if user_data_temp[user_id]["paso"] == 2:
        tipo_reporte = user_data_temp[user_id]["tipo"]
        ubicacion = texto
        
        # --- NUEVO CONTRATO API (QA / PM) ---
        nuevo_doc = {
            "fuente": "Telegram",
            "tipo": tipo_reporte,
            "descripcion": ubicacion, # Lo que el usuario escribió
            "ubicacion": {
                "lat": 20.5888, # Coordenada base (Juriquilla/Querétaro)
                "lon": -100.3899,
                "zona_tipo": ubicacion
            },
            # Campos vacíos que la IA y Enrique van a llenar/actualizar después
            "prioridad_score": 0.0,
            "metadata": {
                "zona_sensible": "Por evaluar", # Hospital/Escuela/Urbana
                "frecuencia_redes": 0
            }
        }
        
        # Insertar en la colección "Reportes" de tu MongoDB
        await collection.insert_one(nuevo_doc)
        
        # Limpiar el estado del usuario para que pueda reportar de nuevo después
        del user_data_temp[user_id]
        
        await update.message.reply_text(
            "✅ **¡Reporte registrado con éxito!**\n\n"
            f"📋 **Resumen:**\n"
            f"• Problema: {tipo_reporte}\n"
            f"• Ubicación: {ubicacion}\n\n"
            "Gracias por ayudar a cuidar el agua en Querétaro. Ya puedes ver este reporte en el mapa del sistema.",
            parse_mode="Markdown"
        )

# --- RUTAS DE LA API ---
@app.get("/health")
async def health():
    return {"status": "ok", "database": "connected"}

@app.get("/reportes/mapa")
async def mapa():
    # Trae todos los reportes
    cursor = collection.find