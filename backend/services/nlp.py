import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# TRUCO: Usamos la misma librería de OpenAI, pero apuntando a los servidores gratuitos de Groq
client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

async def clasificar_reporte(texto_reporte: str) -> dict:
    """
    Analiza el reporte ciudadano usando el modelo gratuito Llama 3 en Groq.
    """
    prompt_sistema = """
    Eres el motor de Inteligencia Operativa de Aqua-Priority Qro.
    Tu tarea es analizar reportes ciudadanos sobre el servicio de agua en Querétaro.
    
    Reglas de clasificación:
    1. "tipo": Solo puede ser "fuga", "corte", "medicion" o "indefinido".
    2. "zona": Extrae la colonia, calle o referencia (ej. Hospitales, escuelas). Si no hay, pon "no especificada".
    3. "prioridad_nlp": Asigna "alta", "media" o "baja". (Hospitales, escuelas o fugas masivas = alta).
    
    Responde ÚNICAMENTE con un JSON válido.
    Ejemplo:
    {
      "tipo": "fuga",
      "zona": "Avenida Zaragoza",
      "prioridad_nlp": "alta",
      "resumen": "Tubo roto desperdiciando mucha agua"
    }
    """

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Reporte ciudadano: {texto_reporte}"}
            ],
            temperature=0.2
        )
        
        resultado_texto = response.choices[0].message.content
        return json.loads(resultado_texto)

    except Exception as e:
        print(f"Error en NLP: {e}")
        return {"tipo": "error", "zona": "error", "prioridad_nlp": "baja", "resumen": "Falla IA"}