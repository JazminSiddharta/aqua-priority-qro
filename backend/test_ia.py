import asyncio
from services.nlp import clasificar_reporte

async def main():
    print("--- INICIANDO MOTOR AQUA-PRIORITY ---\n")
    
    # El mensaje falso que nos mandaría un ciudadano por WhatsApp
    mensaje = "Hola, hay una fuga enorme frente al hospital del Niño y la Mujer, se está inundando la calle."
    print(f"Mensaje entrante: {mensaje}\n")
    
    print("Procesando con IA...\n")
    resultado = await clasificar_reporte(mensaje)
    
    print("Resultado final estructurado:")
    print(resultado)

if __name__ == "__main__":
    asyncio.run(main())