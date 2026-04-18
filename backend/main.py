from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI(title="Aqua Priority API")

# Permitir que el Dashboard (Frontend) se conecte sin bloqueos
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup():
    # Conexión a MongoDB
    app.mongodb = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    app.db = app.mongodb[os.getenv("DB_NAME", "aqua_priority")]
    print("✅ Conectado a la base de datos")

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Backend Aqua-Priority funcionando"}

# 2. Importar los routers
from routes import reportes
from routes import telegram

# 3. Conectar los módulos a la aplicación principal
app.include_router(reportes.router)
app.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])