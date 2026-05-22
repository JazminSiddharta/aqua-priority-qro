import os
import asyncio
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from dotenv import load_dotenv

# Librerías de Telegram
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

load_dotenv()

# Servicio para calcular zona a partir de lat/lon
from services.zonas import obtener_zona

# --- CONEXIÓN A MONGO ---
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
collection = db["Reportes"]

# --- FASTAPI ---
app = FastAPI(title="Aqua Priority QRO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
#  MÁQUINA DE ESTADOS DEL BOT
# ============================================================

# Cada usuario tiene un diccionario con:
#   { "step": str, "intentos": int, "data": {...} }
user_state = {}

PRIORIDAD_POR_TIPO = {"fuga": "alta", "corte": "media", "medidor": "baja"}

MAX_INTENTOS = 3


def _nuevo_estado():
    return {"step": "tipo", "intentos": 0, "data": {}}


def _limpiar(user_id):
    user_state.pop(user_id, None)


async def _enviar(update, texto, teclado=None):
    """Helper para mandar mensajes con o sin teclado custom."""
    if teclado is not None:
        await update.message.reply_text(texto, reply_markup=teclado, parse_mode="HTML")
    else:
        await update.message.reply_text(texto, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

def _parse_entero(texto: str):
    """Devuelve int si el texto es un entero válido, None si no."""
    try:
        return int(texto.strip())
    except (ValueError, AttributeError):
        return None


async def _validar_opcion(update, valor, opciones_validas):
    """
    Valida que valor (int) esté en opciones_validas.
    Devuelve True si es válido, False si no (y maneja intentos).
    """
    user_id = update.message.from_user.id
    if valor is not None and valor in opciones_validas:
        user_state[user_id]["intentos"] = 0
        return True

    user_state[user_id]["intentos"] += 1
    intentos_restantes = MAX_INTENTOS - user_state[user_id]["intentos"]

    if intentos_restantes <= 0:
        await _enviar(update, "❌ Demasiados intentos inválidos. Reporte cancelado.\n\nEscribe <b>hola</b> cuando quieras intentar de nuevo.")
        _limpiar(user_id)
        return False

    await _enviar(update, f"⚠️ Respuesta inválida. Te quedan <b>{intentos_restantes}</b> intentos. Intenta de nuevo:")
    return False


# --- Preguntas (cada step sabe cuál es la siguiente) ---

PREGUNTAS = {
    "tipo": "1️⃣ ¿Qué tipo de problema reportas?\n  <b>1</b> = Fuga\n  <b>2</b> = Corte\n  <b>3</b> = Medidor",
    "ubicacion": "2️⃣ Comparte tu ubicación con el botón de abajo 📍\n<i>(o escribe tu colonia si no puedes)</i>",
    "personas": "3️⃣ ¿Cuántas personas viven en tu domicilio? <i>(número)</i>",
    "horas": "4️⃣ ¿Hace cuántas horas notaste el problema? <i>(número)</i>",
    "compartida": "5️⃣ ¿Compartes toma de agua con otros domicilios?\n  <b>1</b> = Sí\n  <b>2</b> = No",
    # Bloque fuga
    "fuga_flujo": "💧 ¿Cómo describes el flujo?\n  <b>1</b> = Goteo\n  <b>2</b> = Chorro pequeño\n  <b>3</b> = Chorro grande\n  <b>4</b> = Ruptura",
    "fuga_destino": "💧 ¿El agua sale a la calle o se queda en tu domicilio?\n  <b>1</b> = Calle\n  <b>2</b> = Domicilio",
    "fuga_metros": "💧 ¿Cuántos metros aprox. tiene la mancha de agua? <i>(número)</i>",
    "fuga_reportada": "💧 ¿Ya habías reportado esta misma fuga antes?\n  <b>1</b> = Sí\n  <b>2</b> = No",
    # Bloque corte
    "corte_tinaco": "🚱 ¿Tienes tinaco o cisterna con reserva?\n  <b>1</b> = Sí\n  <b>2</b> = No",
    "corte_dias": "🚱 ¿Cuántos días llevas sin servicio? <i>(número)</i>",
    "corte_vecinos": "🚱 ¿Tus vecinos también están sin agua?\n  <b>1</b> = Sí\n  <b>2</b> = No",
    # Bloque medidor
    "medidor_actual": "📊 ¿Cuál es tu lectura actual del medidor? <i>(número)</i>",
    "medidor_recibo": "📊 ¿Cuál es la lectura que marca tu último recibo? <i>(número)</i>",
    "medidor_meses": "📊 ¿Cuántos meses llevas con el problema? <i>(número)</i>",
    "confirmar": None,
}

# Cómo se enlazan los pasos
SIGUIENTE_BLOQUE0 = ["tipo", "ubicacion", "personas", "horas", "compartida"]
SIGUIENTE_POR_TIPO = {
    "fuga":    ["fuga_flujo", "fuga_destino", "fuga_metros", "fuga_reportada"],
    "corte":   ["corte_tinaco", "corte_dias", "corte_vecinos"],
    "medidor": ["medidor_actual", "medidor_recibo", "medidor_meses"],
}

TIPO_DESDE_NUM = {1: "fuga", 2: "corte", 3: "medidor"}


def _siguiente_paso(state):
    """Determina cuál es el step después del actual."""
    actual = state["step"]
    tipo = state["data"].get("tipo")

    # En Bloque 0
    if actual in SIGUIENTE_BLOQUE0:
        idx = SIGUIENTE_BLOQUE0.index(actual)
        if idx + 1 < len(SIGUIENTE_BLOQUE0):
            return SIGUIENTE_BLOQUE0[idx + 1]
        # Termina bloque 0 → primer paso del bloque específico
        return SIGUIENTE_POR_TIPO[tipo][0]

    # En bloque específico
    if tipo and actual in SIGUIENTE_POR_TIPO[tipo]:
        bloque = SIGUIENTE_POR_TIPO[tipo]
        idx = bloque.index(actual)
        if idx + 1 < len(bloque):
            return bloque[idx + 1]
        # Terminó el flujo → confirmación
        return "confirmar"

    return None


def _construir_resumen(data):
    """Texto resumen para la pantalla de confirmación."""
    lines = ["📋 <b>Resumen de tu reporte:</b>\n"]
    lines.append(f"• Tipo: <b>{data.get('tipo', '?').capitalize()}</b>")
    if data.get("lat") is not None:
        lines.append(f"• Ubicación: GPS ({data['lat']:.4f}, {data['lon']:.4f})")
    elif data.get("ubicacion_texto"):
        lines.append(f"• Ubicación: {data['ubicacion_texto']}")
    lines.append(f"• Zona detectada: {data.get('zona', '?')}")
    lines.append(f"• Personas en domicilio: {data.get('personas_domicilio', '?')}")
    lines.append(f"• Horas con el problema: {data.get('horas_problema', '?')}")
    lines.append(f"• Toma compartida: {'Sí' if data.get('toma_compartida') else 'No'}")

    tipo = data.get("tipo")
    if tipo == "fuga":
        lines.append(f"• Flujo: {data.get('fuga_flujo', '?')}")
        lines.append(f"• Destino: {data.get('fuga_destino', '?')}")
        lines.append(f"• Mancha: {data.get('fuga_metros_mancha', '?')} m")
        lines.append(f"• Reportada antes: {'Sí' if data.get('fuga_ya_reportada') else 'No'}")
    elif tipo == "corte":
        lines.append(f"• Tinaco/cisterna: {'Sí' if data.get('corte_tinaco') else 'No'}")
        lines.append(f"• Días sin servicio: {data.get('corte_dias_sin_servicio', '?')}")
        lines.append(f"• Vecinos afectados: {'Sí' if data.get('corte_vecinos_afectados') else 'No'}")
    elif tipo == "medidor":
        lines.append(f"• Lectura actual: {data.get('medidor_lectura_actual', '?')}")
        lines.append(f"• Lectura recibo: {data.get('medidor_lectura_recibo', '?')}")
        lines.append(f"• Meses con problema: {data.get('medidor_meses_problema', '?')}")

    lines.append(f"\n<b>Prioridad asignada: {data.get('prioridad', '?').upper()}</b>")
    lines.append("\n¿Confirmas el reporte?\n  <b>1</b> = Sí, guardar\n  <b>2</b> = Empezar de nuevo")
    return "\n".join(lines)


async def _preguntar(update, step, user_id=None):
    """Envía la pregunta correspondiente al step."""
    if step == "ubicacion":
        teclado = ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Compartir ubicación", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await _enviar(update, PREGUNTAS["ubicacion"], teclado)
    elif step == "confirmar":
        state = user_state[user_id]
        await _enviar(update, _construir_resumen(state["data"]))
    else:
        await _enviar(update, PREGUNTAS[step])


# ============================================================
#  HANDLERS
# ============================================================

async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_state:
        _limpiar(user_id)
        await _enviar(update, "Reporte cancelado. Escribe <b>hola</b> cuando quieras iniciar uno nuevo.")
    else:
        await _enviar(update, "No hay reporte activo. Escribe <b>hola</b> para iniciar uno.")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cuando el usuario toca el botón de compartir ubicación."""
    user_id = update.message.from_user.id

    if user_id not in user_state or user_state[user_id]["step"] != "ubicacion":
        # Ubicación fuera de contexto, ignorar
        await _enviar(update, "Recibí tu ubicación, pero no hay un reporte activo. Escribe <b>hola</b> para iniciar.")
        return

    loc = update.message.location
    state = user_state[user_id]
    state["data"]["lat"] = loc.latitude
    state["data"]["lon"] = loc.longitude
    state["data"]["ubicacion_texto"] = None

    # Calcular zona automáticamente
    info_zona = obtener_zona(loc.latitude, loc.longitude)
    state["data"]["zona"] = info_zona["zona"]
    state["data"]["zona_tipo"] = info_zona["zona_tipo"]

    state["step"] = _siguiente_paso(state)
    await _preguntar(update, state["step"], user_id)


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    texto = (update.message.text or "").strip()

    # Comando explícito de cancelar
    if texto.lower() in ("cancelar", "/cancelar"):
        await cmd_cancelar(update, context)
        return



    # Si no hay flujo activo → solo arranca con saludos
    if user_id not in user_state:
        if any(p in texto.lower() for p in ["hola", "reportar", "buenas", "buenos días", "fuga", "corte"]):
            user_state[user_id] = _nuevo_estado()
            await _enviar(update, "¡Hola! Soy el asistente de <b>Aqua Priority QRO</b>.\nTe haré algunas preguntas para registrar tu reporte.\n\nEn cualquier momento puedes escribir <b>cancelar</b> para abortar.\n")
            await _preguntar(update, "tipo")
        else:
            await _enviar(update, "Para iniciar un reporte, escribe <b>hola</b>.")
        return

    state = user_state[user_id]
    step = state["step"]
    data = state["data"]

    # --- BLOQUE 0 ---
    if step == "tipo":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2, 3]):
            return
        data["tipo"] = TIPO_DESDE_NUM[valor]
        data["prioridad"] = PRIORIDAD_POR_TIPO[data["tipo"]]
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "ubicacion":
        # El usuario escribió texto en lugar de tocar el botón de ubicación
        data["ubicacion_texto"] = texto
        data["lat"] = None
        data["lon"] = None
        data["zona"] = "Otra"
        data["zona_tipo"] = "urbana"
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "personas":
        valor = _parse_entero(texto)
        if valor is None or valor < 1:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["personas_domicilio"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "horas":
        valor = _parse_entero(texto)
        if valor is None or valor < 0:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["horas_problema"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "compartida":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2]):
            return
        data["toma_compartida"] = (valor == 1)
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    # --- BLOQUE FUGA ---
    if step == "fuga_flujo":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2, 3, 4]):
            return
        data["fuga_flujo"] = {1: "goteo", 2: "chorro_pequeno", 3: "chorro_grande", 4: "ruptura"}[valor]
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "fuga_destino":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2]):
            return
        data["fuga_destino"] = {1: "calle", 2: "domicilio"}[valor]
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "fuga_metros":
        valor = _parse_entero(texto)
        if valor is None or valor < 0:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["fuga_metros_mancha"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "fuga_reportada":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2]):
            return
        data["fuga_ya_reportada"] = (valor == 1)
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"], user_id)
        return

    # --- BLOQUE CORTE ---
    if step == "corte_tinaco":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2]):
            return
        data["corte_tinaco"] = (valor == 1)
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "corte_dias":
        valor = _parse_entero(texto)
        if valor is None or valor < 0:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["corte_dias_sin_servicio"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "corte_vecinos":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2]):
            return
        data["corte_vecinos_afectados"] = (valor == 1)
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"], user_id)
        return

    # --- BLOQUE MEDIDOR ---
    if step == "medidor_actual":
        valor = _parse_entero(texto)
        if valor is None or valor < 0:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["medidor_lectura_actual"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "medidor_recibo":
        valor = _parse_entero(texto)
        if valor is None or valor < 0:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["medidor_lectura_recibo"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"])
        return

    if step == "medidor_meses":
        valor = _parse_entero(texto)
        if valor is None or valor < 0:
            if not await _validar_opcion(update, None, []):
                return
            return
        data["medidor_meses_problema"] = valor
        state["intentos"] = 0
        state["step"] = _siguiente_paso(state)
        await _preguntar(update, state["step"], user_id)
        return

    # --- CONFIRMACIÓN ---
    if step == "confirmar":
        valor = _parse_entero(texto)
        if not await _validar_opcion(update, valor, [1, 2]):
            return
        if valor == 2:
            user_state[user_id] = _nuevo_estado()
            await _enviar(update, "🔄 Empecemos de nuevo.")
            await _preguntar(update, "tipo")
            return
        # valor == 1: GUARDAR
        data["folio"] = "QRO-" + uuid.uuid4().hex[:6].upper()
        data["fuente"] = "Telegram Bot"
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["user_id"] = user_id

        await collection.insert_one(data)
        _limpiar(user_id)

        await _enviar(update, f"✅ <b>Reporte registrado con éxito.</b> \nFolio: <code>{data['folio']}</code>\n\nGracias por ayudar a cuidar el agua en Querétaro. 💧")
        return


# ============================================================
#  RUTAS DE LA API
# ============================================================

def _normalizar_reporte(r):
    """Asegura que el reporte tenga lat/lon en raíz."""
    if "lat" not in r and "ubicacion" in r and isinstance(r["ubicacion"], dict):
        r["lat"] = r["ubicacion"].get("lat")
        r["lon"] = r["ubicacion"].get("lon")
    r.setdefault("prioridad", "media")
    r.setdefault("tipo", "otro")
    r.setdefault("zona", "Centro")
    return r


@app.get("/health")
async def health():
    return {"status": "ok", "database": "connected"}


@app.get("/reportes/mapa")
async def mapa():
    cursor = collection.find({}, {"_id": 0})
    reportes = await cursor.to_list(length=1000)
    return [_normalizar_reporte(r) for r in reportes]


@app.get("/rutas")
async def rutas():
    cursor = collection.find({}, {"_id": 0})
    reportes = [_normalizar_reporte(r) for r in await cursor.to_list(length=1000)]
    orden = {"alta": 3, "media": 2, "baja": 1}
    zonas = {}
    for r in reportes:
        if r.get("lat") is None or r.get("lon") is None:
            continue
        zonas.setdefault(r.get("zona", "Centro"), []).append(r)
    resultado = []
    for zona, lista in zonas.items():
        lista.sort(key=lambda r: orden.get(r.get("prioridad", "media"), 2), reverse=True)
        puntos = [
            {
                "reporte_id": str(r.get("folio", i)),
                "lat": r["lat"],
                "lon": r["lon"],
                "orden": i + 1,
                "prioridad": r.get("prioridad", "media"),
            }
            for i, r in enumerate(lista)
        ]
        resultado.append({"zona": zona, "puntos": puntos})
    return resultado


@app.get("/medidores")
async def medidores():
    col_med = db["medidores"]
    cursor = col_med.find({}, {"_id": 0})
    return await cursor.to_list(length=1000)


# ============================================================
#  STARTUP / SHUTDOWN DEL BOT
# ============================================================

@app.on_event("startup")
async def startup_event():
    token = os.getenv("TELEGRAM_TOKEN")
    if token:
        # Workaround SSL para redes con proxy/firewall (UAQ, etc.)
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(connection_pool_size=8, httpx_kwargs={"verify": False})
        updates_request = HTTPXRequest(connection_pool_size=8, httpx_kwargs={"verify": False})

        application = (
            Application.builder()
            .token(token)
            .request(request)
            .get_updates_request(updates_request)
            .build()
        )
        application.add_handler(CommandHandler("cancelar", cmd_cancelar))
        application.add_handler(MessageHandler(filters.LOCATION, handle_location))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        app.state.tg_app = application
        print("🤖 Bot de Telegram encendido (versión 2.0 con bloques).")
        print("⚠️  ATENCIÓN: SSL verification DESACTIVADA (workaround para red UAQ)")

@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "tg_app"):
        await app.state.tg_app.updater.stop()
        await app.state.tg_app.stop()
        await app.state.tg_app.shutdown()
        print("🤖 Bot de Telegram apagado.")