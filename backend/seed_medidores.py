import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MEDIDORES = [
    {"id": "MED-001", "zona": "Centro",         "lat": 20.5895, "lon": -100.3920, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-002", "zona": "Centro",         "lat": 20.5880, "lon": -100.3935, "estado": "alerta",     "requiere_revision": True},
    {"id": "MED-003", "zona": "Centro",         "lat": 20.5910, "lon": -100.3900, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-004", "zona": "Cimatario",      "lat": 20.5730, "lon": -100.3970, "estado": "falla",      "requiere_revision": True},
    {"id": "MED-005", "zona": "Cimatario",      "lat": 20.5755, "lon": -100.3945, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-006", "zona": "Juriquilla",     "lat": 20.6580, "lon": -100.4480, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-007", "zona": "Juriquilla",     "lat": 20.6600, "lon": -100.4500, "estado": "alerta",     "requiere_revision": True},
    {"id": "MED-008", "zona": "Juriquilla",     "lat": 20.6620, "lon": -100.4460, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-009", "zona": "El Refugio",     "lat": 20.6350, "lon": -100.3450, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-010", "zona": "El Refugio",     "lat": 20.6380, "lon": -100.3480, "estado": "falla",      "requiere_revision": True},
    {"id": "MED-011", "zona": "El Refugio",     "lat": 20.6320, "lon": -100.3420, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-012", "zona": "Constituyentes", "lat": 20.6000, "lon": -100.3920, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-013", "zona": "Constituyentes", "lat": 20.6020, "lon": -100.3940, "estado": "alerta",     "requiere_revision": True},
    {"id": "MED-014", "zona": "Norte",          "lat": 20.6150, "lon": -100.4020, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-015", "zona": "Norte",          "lat": 20.6170, "lon": -100.4000, "estado": "falla",      "requiere_revision": True},
    {"id": "MED-016", "zona": "Norte",          "lat": 20.6180, "lon": -100.4040, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-017", "zona": "Centro",         "lat": 20.5870, "lon": -100.3910, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-018", "zona": "Cimatario",      "lat": 20.5710, "lon": -100.3960, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-019", "zona": "Juriquilla",     "lat": 20.6650, "lon": -100.4470, "estado": "operativo",  "requiere_revision": False},
    {"id": "MED-020", "zona": "Norte",          "lat": 20.6160, "lon": -100.4010, "estado": "alerta",     "requiere_revision": True},
]

async def main():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db = client[os.getenv("DB_NAME", "aqua_priority")]
    col = db["medidores"]

    deleted = await col.delete_many({})
    print(f"🧹 Borrados {deleted.deleted_count} medidores previos.")

    result = await col.insert_many(MEDIDORES)
    print(f"✅ Insertados {len(result.inserted_ids)} medidores en la colección 'medidores'.")

if __name__ == "__main__":
    asyncio.run(main())