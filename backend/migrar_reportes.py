import asyncio
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

from services.zonas import obtener_zona


async def main():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db = client[os.getenv("DB_NAME", "aqua_priority")]
    col = db["Reportes"]

    cursor = col.find({})
    total = 0
    migrados = 0
    async for doc in cursor:
        total += 1
        cambios = {}

        # Asegurar campos básicos del schema nuevo
        if "folio" not in doc:
            cambios["folio"] = "QRO-LEGACY-" + uuid.uuid4().hex[:4].upper()
        if "timestamp" not in doc:
            cambios["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "fuente" not in doc:
            cambios["fuente"] = doc.get("fuente", "Telegram Bot")

        # Normalizar tipo
        tipo_actual = doc.get("tipo", "").lower()
        if "fuga" in tipo_actual:
            cambios["tipo"] = "fuga"
        elif "corte" in tipo_actual:
            cambios["tipo"] = "corte"
        elif "medidor" in tipo_actual or "medicion" in tipo_actual:
            cambios["tipo"] = "medidor"
        else:
            cambios["tipo"] = doc.get("tipo", "fuga")

        # Prioridad por tipo
        prioridad_map = {"fuga": "alta", "corte": "media", "medidor": "baja"}
        cambios["prioridad"] = prioridad_map.get(cambios["tipo"], "media")

        # Normalizar lat/lon
        lat = doc.get("lat")
        lon = doc.get("lon")
        if lat is None and isinstance(doc.get("ubicacion"), dict):
            lat = doc["ubicacion"].get("lat")
            lon = doc["ubicacion"].get("lon")
            cambios["lat"] = lat
            cambios["lon"] = lon

        # Si hay GPS, calcular zona
        if lat is not None and lon is not None:
            info = obtener_zona(lat, lon)
            cambios["zona"] = info["zona"]
            cambios["zona_tipo"] = info["zona_tipo"]
        else:
            # El viejo tenía zona_tipo como texto de ubicación (ej "Centro de QRO"),
            # mejor lo movemos a ubicacion_texto y dejamos zona = "Otra"
            if "zona_tipo" in doc and not doc.get("zona"):
                cambios["ubicacion_texto"] = doc["zona_tipo"]
                cambios["zona"] = "Otra"
                cambios["zona_tipo"] = "urbana"

        if cambios:
            await col.update_one({"_id": doc["_id"]}, {"$set": cambios})
            migrados += 1
            print(f"  ✏️  Migrado: folio={cambios.get('folio', doc.get('folio'))}, tipo={cambios.get('tipo')}, zona={cambios.get('zona')}")

    print(f"\n✅ Total: {total} reportes revisados, {migrados} migrados.")


if __name__ == "__main__":
    asyncio.run(main())