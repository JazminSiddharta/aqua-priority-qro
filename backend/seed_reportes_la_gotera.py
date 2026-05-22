"""
Generador de 1000 reportes sintéticos para La Gotera, Querétaro.
- Ventana temporal: 18 marzo - 29 abril 2026 (6 semanas)
- Distribución: 60% fugas, 25% cortes, 15% medidores
- Geografía: ~1km de radio alrededor del centro de La Gotera
- Cada reporte tiene una dirección (calle + número) dentro de La Gotera
"""
import asyncio
import random
import math
import uuid
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
TOTAL_REPORTES = 1000

CENTRO_LAT = 20.8636
CENTRO_LON = -100.3767
RADIO_KM = 1.0

FECHA_INICIO = datetime(2026, 3, 18, 0, 0, 0, tzinfo=timezone.utc)
FECHA_FIN = datetime(2026, 4, 29, 23, 59, 59, tzinfo=timezone.utc)

DIST_TIPOS = ["fuga"] * 60 + ["corte"] * 25 + ["medidor"] * 15

PRIORIDAD_POR_TIPO = {"fuga": "alta", "corte": "media", "medidor": "baja"}

# Calles típicas de un pueblo rural en La Gotera, Querétaro
CALLES = [
    "Av. Hidalgo", "Av. Juárez", "Av. Morelos", "Av. Revolución", "Av. Reforma",
    "Calle 5 de Mayo", "Calle 16 de Septiembre", "Calle 20 de Noviembre",
    "Calle Independencia", "Calle Libertad", "Calle Constitución",
    "Calle Allende", "Calle Aldama", "Calle Galeana", "Calle Guerrero", "Calle Zaragoza",
    "Calle de la Cruz", "Calle del Sol", "Calle de la Luna", "Calle de los Pinos",
    "Calle El Mirador", "Calle La Cañada", "Calle La Cima", "Calle El Llano",
    "Calle Las Flores", "Calle Los Olivos", "Calle Los Sauces", "Calle Las Palmas",
    "Andador Margarita", "Andador Las Rosas", "Andador Jazmín", "Andador Bugambilia",
    "Privada del Carmen", "Privada San José", "Privada Guadalupe", "Privada Santa Rosa",
    "Camino Real", "Camino a Palo Alto", "Camino a Santa Rosa", "Camino al Cerro",
    "Cerrada Lirio", "Cerrada Tulipán", "Cerrada Geranio", "Cerrada Violeta",
    "Prol. Hidalgo", "Prol. Juárez", "Prol. Reforma",
    "Calle Niños Héroes", "Calle Emiliano Zapata", "Calle Francisco Villa",
    "Calle Cuauhtémoc", "Calle Insurgentes", "Calle Vicente Guerrero",
]

# Algunas direcciones usan Mz/Lt (manzana/lote, típico en pueblos)
TIPO_REFERENCIA = ["numero", "numero", "numero", "manzana_lote"]


def generar_direccion():
    """Devuelve un string tipo 'Calle Hidalgo #45' o 'Calle Lirio Mz 3 Lt 12'."""
    calle = random.choice(CALLES)
    tipo_ref = random.choice(TIPO_REFERENCIA)
    if tipo_ref == "numero":
        # Número de casa entre 1 y 350
        numero = random.randint(1, 350)
        return f"{calle} #{numero}, La Gotera"
    else:
        mz = random.randint(1, 25)
        lt = random.randint(1, 30)
        return f"{calle} Mz {mz} Lt {lt}, La Gotera"


def punto_aleatorio_en_radio(lat_centro, lon_centro, radio_km):
    radio_lat = radio_km / 111.0
    radio_lon = radio_km / (111.0 * math.cos(math.radians(lat_centro)))
    r = math.sqrt(random.random())
    theta = random.uniform(0, 2 * math.pi)
    lat = lat_centro + r * radio_lat * math.cos(theta)
    lon = lon_centro + r * radio_lon * math.sin(theta)
    return round(lat, 6), round(lon, 6)


def fecha_aleatoria(inicio, fin):
    delta = fin - inicio
    segundos = random.randint(0, int(delta.total_seconds()))
    return inicio + timedelta(seconds=segundos)


def generar_reporte():
    tipo = random.choice(DIST_TIPOS)
    lat, lon = punto_aleatorio_en_radio(CENTRO_LAT, CENTRO_LON, RADIO_KM)
    timestamp = fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
    direccion = generar_direccion()

    reporte = {
        "folio": "QRO-LG-" + uuid.uuid4().hex[:6].upper(),
        "fuente": "Telegram Bot",
        "timestamp": timestamp.isoformat(),
        "user_id": random.randint(100000000, 999999999),

        "tipo": tipo,
        "lat": lat,
        "lon": lon,
        "ubicacion_texto": direccion,
        "personas_domicilio": random.randint(1, 8),
        "horas_problema": random.randint(1, 72),
        "toma_compartida": random.choice([True, False]),

        "zona": "La Gotera",
        "zona_tipo": "rural",
        "prioridad": PRIORIDAD_POR_TIPO[tipo],
    }

    if tipo == "fuga":
        reporte["fuga_flujo"] = random.choice(["goteo", "chorro_pequeno", "chorro_grande", "ruptura"])
        reporte["fuga_destino"] = random.choice(["calle", "domicilio"])
        reporte["fuga_metros_mancha"] = random.randint(1, 30)
        reporte["fuga_ya_reportada"] = random.choice([True, False])
    elif tipo == "corte":
        reporte["corte_tinaco"] = random.choice([True, False])
        reporte["corte_dias_sin_servicio"] = random.randint(1, 15)
        reporte["corte_vecinos_afectados"] = random.choice([True, False])
    elif tipo == "medidor":
        lectura_recibo = random.randint(800, 1500)
        reporte["medidor_lectura_actual"] = lectura_recibo + random.randint(50, 500)
        reporte["medidor_lectura_recibo"] = lectura_recibo
        reporte["medidor_meses_problema"] = random.randint(1, 12)

    return reporte


async def main():
    random.seed(42)

    client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db = client[os.getenv("DB_NAME", "aqua_priority")]
    col = db["Reportes"]

    # Borrar reportes sintéticos previos de La Gotera
    deleted = await col.delete_many({
        "zona": "La Gotera",
        "folio": {"$regex": "^QRO-LG-"}
    })
    print(f"🧹 Borrados {deleted.deleted_count} reportes previos de La Gotera.")

    reportes = [generar_reporte() for _ in range(TOTAL_REPORTES)]
    result = await col.insert_many(reportes)
    print(f"✅ Insertados {len(result.inserted_ids)} reportes en La Gotera.")

    tipos_count = {}
    for r in reportes:
        tipos_count[r["tipo"]] = tipos_count.get(r["tipo"], 0) + 1
    print(f"\n📊 Distribución por tipo:")
    for tipo, count in sorted(tipos_count.items()):
        pct = 100.0 * count / TOTAL_REPORTES
        print(f"   {tipo:8s}: {count:4d} ({pct:.1f}%)")

    # Algunas direcciones de muestra
    print(f"\n📍 Muestra de 5 direcciones:")
    for r in random.sample(reportes, 5):
        print(f"   {r['ubicacion_texto']}")

    print(f"\n📅 Rango temporal: {FECHA_INICIO.date()} → {FECHA_FIN.date()}")
    print(f"📍 Centro geográfico: ({CENTRO_LAT}, {CENTRO_LON}) ± {RADIO_KM} km")


if __name__ == "__main__":
    asyncio.run(main())