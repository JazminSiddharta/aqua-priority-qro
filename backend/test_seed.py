import pymongo

try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["aqua_db"]
    collection = db["Reportes"]

    # Creamos 60 reportes con los nombres que pide el mapa (lat, lon, prioridad)
    reportes_finales = []
    prioridades = ["alta", "media", "baja"]

    for i in range(60):
        nuevo = {
            "lat": 20.712 + (i * 0.001), # Coordenadas cerca de Juriquilla
            "lon": -100.444 + (i * 0.001),
            "prioridad": prioridades[i % 3],
            "tipo": "Fuga de Agua", # Campos extra por si acaso
            "estatus": "Pendiente"
        }
        reportes_finales.append(nuevo)

    # Limpiamos la base anterior para que no haya basura
    collection.delete_many({}) 
    res = collection.insert_many(reportes_finales)
    
    print(f"✅ ¡ÉXITO! Ahora tienes {len(res.inserted_ids)} reportes con el formato correcto.")

except Exception as e:
    print(f"❌ ERROR: {e}")