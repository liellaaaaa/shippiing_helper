from fastapi import APIRouter, Query
from app.services.export_codes_service import ExportCodesService

router = APIRouter(prefix="/api/v1/export-codes", tags=["export_codes"])
svc = ExportCodesService()


@router.get("/")
async def get_export_codes(internal_code: str = Query("")):
    if not internal_code:
        return {"error": "internal_code is required"}
    result = svc.find_by_internal_code(internal_code)
    return result or {"error": "not found"}