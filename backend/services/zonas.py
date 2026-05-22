import json
import os
from pathlib import Path
from shapely.geometry import shape, Point

# Carga el geojson una sola vez al importar el módulo
_GEOJSON_PATH = Path(__file__).resolve().parent.parent / "data" / "zonas_qro.geojson"

with open(_GEOJSON_PATH, "r", encoding="utf-8") as f:
    _data = json.load(f)

_ZONAS = []
for feature in _data["features"]:
    _ZONAS.append({
        "zona": feature["properties"]["zona"],
        "zona_tipo": feature["properties"]["zona_tipo"],
        "polygon": shape(feature["geometry"]),
    })


def obtener_zona(lat: float, lon: float) -> dict:
    """
    Dado un par lat/lon, devuelve la zona y el zona_tipo donde cae.
    Si no cae en ninguna zona definida, devuelve 'Otra' / 'urbana'.
    """
    point = Point(lon, lat)  # GeoJSON usa (lon, lat), ojo con el orden
    for z in _ZONAS:
        if z["polygon"].contains(point):
            return {"zona": z["zona"], "zona_tipo": z["zona_tipo"]}
    return {"zona": "Otra", "zona_tipo": "urbana"}