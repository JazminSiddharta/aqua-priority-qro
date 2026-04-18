from fastapi import APIRouter

router = APIRouter()

@router.post("/reportes")
async def crear_reporte():
    return {"ok": True}
