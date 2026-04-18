import requests

BASE_URL = "http://localhost:8000"

def test_flujo_telegram():
    print("Probando Flujo: Simulación de Webhook de Telegram...")
    
    # Este es el esqueleto real de un JSON de Telegram
    payload_telegram = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 987654321, 
                "is_bot": False, 
                "first_name": "Usuario Test"
            },
            "chat": {
                "id": 987654321, 
                "type": "private"
            },
            "date": 1713420000,
            "text": "Fuga de agua tremenda enfrente de la UAQ, el agua sale a chorros",
            "location": {
                "latitude": 20.5931,
                "longitude": -100.3927
            }
        }
    }

    try:
        # Nota: El backend tiene que crear esta ruta específica para escuchar a Telegram
        res = requests.post(f"{BASE_URL}/healthy", json=payload_telegram)
        
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("¡Éxito! El backend recibió el mensaje de Telegram correctamente.")
        else:
            print(f"Hubo un detalle. Respuesta: {res.text}")
            
    except Exception as e:
        print(f"El endpoint de Telegram aún no está listo o falló la conexión: {e}")

if __name__ == "__main__":
    test_flujo_telegram()