import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# --- 1. SALVAVIDAS: CLASIFICADOR POR KEYWORDS ---
KEYWORDS = {
    "fuga":    ["fuga", "gotea", "brotando", "derrame", "roto", "escape", "chorrea", "humedad", "tubo roto", "agua en calle"],
    "corte":   ["sin agua", "no hay agua", "cortaron", "sin servicio", "seca", "presion baja", "no sale", "sin presion"],
    "medidor": ["medidor", "lectura", "contrato", "cobro", "factura", "numero de medidor", "cargo incorrecto"]
}

def clasificar_keywords(texto: str) -> str:
    t = texto.lower()
    scores = {tipo: sum(1 for k in kws if k in t) for tipo, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "corte" # Fallback por defecto

# --- 2. SCORING DEMOGRÁFICO: ZONAS DE QUERÉTARO ---
ZONAS = [
  {"zona": "centro", "zona_tipo": "urbana", "lat_min": 20.57, "lat_max": 20.60, "lon_min": -100.41, "lon_max": -100.37},
  {"zona": "norte", "zona_tipo": "hospital", "lat_min": 20.60, "lat_max": 20.65, "lon_min": -100.42, "lon_max": -100.36},
  {"zona": "sur", "zona_tipo": "escuela", "lat_min": 20.54, "lat_max": 20.57, "lon_min": -100.41, "lon_max": -100.37},
]

def inferir_zona(lat: float, lon: float):
    for z in ZONAS:
        if z["lat_min"] <= lat <= z["lat_max"] and z["lon_min"] <= lon <= z["lon_max"]:
            return z["zona"], z["zona_tipo"]
    return "general", "casa"

# --- 3. MOTOR PRINCIPAL DE IA ---
async def clasificar_reporte(texto_reporte: str, lat: float = 0.0, lon: float = 0.0) -> dict:
    """
    Analiza el reporte usando IA, con salvavidas de keywords y cálculo de coordenadas.
    """
    # Calculamos la zona exacta con las coordenadas del WhatsApp
    zona_nombre, zona_tipo = inferir_zona(lat, lon)
    
    prompt_sistema = f"""
    Eres el motor NLP de Aqua-Priority Qro.
    Clasifica el reporte ciudadano.
    
    Reglas:
    1. "tipo": Solo "fuga", "corte", o "medicion".
    2. "prioridad_nlp": Asigna "alta" si es fuga masiva o si ocurre en un hospital/escuela. De lo contrario "media" o "baja".
    
    Contexto geográfico detectado: El reporte viene de la zona '{zona_nombre}', que es de tipo '{zona_tipo}'.
    
    Responde ÚNICAMENTE con un JSON válido. Ejemplo:
    {{"tipo": "fuga", "prioridad_nlp": "alta", "resumen": "Tubo roto"}}
    """

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_reporte}
            ],
            temperature=0.2,
            max_tokens=150,
            timeout=5.0 # Si tarda más de 5 seg, salta al salvavidas
        )
        
        resultado_ia = json.loads(response.choices[0].message.content)
        resultado_ia["zona"] = zona_nombre
        resultado_ia["zona_tipo"] = zona_tipo
        return resultado_ia

    except Exception as e:
        print(f"⚠️ API Falló. Usando salvavidas de keywords... Error: {e}")
        # Si algo explota, usamos el plan B sin que el usuario se dé cuenta
        tipo_fallback = clasificar_keywords(texto_reporte)
        prioridad_fallback = "alta" if zona_tipo in ["hospital", "escuela"] else "media"
        
        return {
            "tipo": tipo_fallback,
            "zona": zona_nombre,
            "zona_tipo": zona_tipo,
            "prioridad_nlp": prioridad_fallback,
            "resumen": "Clasificado por sistema de emergencia"
        }