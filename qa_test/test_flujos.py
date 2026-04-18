import requests
import time

BASE_URL = "http://localhost:8000"

def test_flujo_prioridad_zona():
    print("Probando Flujo 2: Prioridad por zona...")
    
    # Simular reporte en hospital (debería dar alta)
    payload_hospital = {
        "tipo": "fuga", "texto": "Fuga de prueba",
        "ubicacion": {"lat": 20.6140, "lon": -100.4012},
        "fuente": "whatsapp", "zona": "norte", "zona_tipo": "hospital"
    }
    
    try:
        res = requests.post(f"{BASE_URL}/reportes", json=payload_hospital)
        data = res.json()
        assert data.get("prioridad") == "alta", f"Error: Prioridad fue {data.get('prioridad')}"
        print("Test Hospital: Prioridad ALTA correcta")
    except Exception as e:
        print(f"El backend aún no está listo o falló: {e}")

if __name__ == "__main__":
    test_flujo_prioridad_zona()