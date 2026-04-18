import asyncio
import random
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Datos de prueba para que el mapa se vea lleno en Querétaro
TWEETS = [
    ("fuga", "Tubo roto en Col. Cimatario, agua por toda la calle", 20.5721, -100.3966, "sur", "escuela"),
    ("corte", "Sin agua en zona norte desde las 6am, urge apoyo", 20.614, -100.401, "norte", "hospital"),
    ("fuga", "Fuga enorme cerca del IMSS en Constituyentes", 20.590, -100.392, "centro", "hospital"),
    ("corte", "Vecinos de Juriquilla reportan sin presión de agua", 20.658, -100.448, "norte", "urbana"),
    ("medicion", "Mi recibo llegó altísimo este mes en El Refugio", 20.635, -100.345, "norte", "urbana"),
]

async def main():
    # Conexión a la base de datos local
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["aqua_priority"]
    
    print("🚀 Simulador de Redes Sociales INICIADO...")
    print("Enviando reportes cada 10-20 segundos. Presiona Ctrl+C para detener.")

    while True:
        # Elegir un mensaje al azar
        msg = random.choice(TWEETS)
        
        # Variar tantito la ubicación para que no caigan todos en el mismo punto exacto
        lat = msg[2] + random.uniform(-.005, .005)
        lon = msg[3] + random.uniform(-.005, .005)
        
        nuevo_reporte = {
            "tipo": msg[0],
            "fuente": "redes",
            "texto": msg[1],
            "timestamp": datetime.utcnow().isoformat(),
            "ubicacion": {"lat": lat, "lon": lon},
            "zona": msg[4],
            "zona_tipo": msg[5],
            "prioridad": "media"
        }
        
        await db.reportes.insert_one(nuevo_reporte)
        print(f"✅ [SIM] {msg[0].upper()} en zona {msg[4].capitalize()}")
        
        # Esperar un tiempo aleatorio
        await asyncio.sleep(random.randint(10, 20))

if __name__ == "__main__":
    asyncio.run(main())