import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Librerías de Telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

# ¡Aquí importamos TU código de IA!
from services.nlp import clasificar_reporte

# --- CONEXIÓN A TU BASE DE DATOS LOCAL ---
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
collection = db["Reportes"]

# Modelo para la API
class Reporte(BaseModel):
    tipo: str
    zona_tipo: str

# --- DICCIONARIO TEMPORAL PARA EL FLUJO DEL BOT ---
# Guarda en qué paso va cada usuario (ID de Telegram)
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
                "¡Hola! Soy el asistente de Aqua Priority QRO y te ayudare a registrar tu problema para que podamos ayudarte.\n\n"
                "Vamos a comenzar de forma ordenada.\n"
                "1️⃣ ¿Qué tipo de problema quieres reportar?\n"
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
        
        # Estructura final para tu base de datos
        nuevo_doc = {
            "tipo": tipo_reporte,
            "zona_tipo": ubicacion,
            "prioridad": "alta" if "fuga" in tipo_reporte.lower() else "media",
            "fuente": "Telegram Bot",
            "lat": 20.5888, # Coordenada base (Juriquilla/Querétaro)
            "lon": -100.3899
        }
        
        # Insertar en la colección "Reportes" de tu MongoDB
        await collection.insert_one(nuevo_doc)
        
        # Limpiar el estado del usuario para que pueda reportar de nuevo después
        del user_data_temp[user_id]
        
        await update.message.reply_text(
            "**¡Reporte registrado con éxito!**\n\n"
            f" **Resumen:**\n"
            f"• Problema: {tipo_reporte}\n"
            f"• Ubicación: {ubicacion}\n\n"
            "Gracias por ayudar a cuidar el agua en Querétaro.",
            parse_mode="Markdown"
        )

# --- RUTAS DE LA API ---
@app.get("/health")
async def health():
    return {"status": "ok", "database": "connected"}

@app.get("/reportes/mapa")
async def mapa():
    # Trae todos los reportes (incluyendo los nuevos de Telegram)
    cursor = collection.find({}, {"_id": 0})
    reportes = await cursor.to_list(length=1000)
    return reportes

# --- INICIO Y APAGADO DEL BOT ---
@app.on_event("startup")
async def startup_event():
    token = os.getenv("TELEGRAM_TOKEN")
    if token:
        # Configurar la aplicación del bot
        application = Application.builder().token(token).build()
        
        # Añadir el manejador de mensajes de texto
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
        
        # Iniciar el bot en segundo plano
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Guardar la instancia para poder cerrarla después
        app.state.tg_app = application
        print("🤖 Bot de Telegram encendido y listo.")

@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "tg_app"):
        await app.state.tg_app.updater.stop()
        await app.state.tg_app.stop()
        await app.state.tg_app.shutdown()
        print("🤖 Bot de Telegram apagado.")
