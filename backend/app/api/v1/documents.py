import os
from fastapi import APIRouter, Query
from sqlalchemy import desc
from app.database import SessionLocal
from app.models.shipment_doc import ShipmentDoc
from app.services.document_service import DocumentService
from app.services.onlyoffice_service import OnlyOfficeService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
oo_svc = OnlyOfficeService()


@router.get("/booking")
async def generate_booking(order_id: int = Query(...)):
    svc = DocumentService()
    _, doc_key, _ = svc.generate_booking(order_id)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "xlsx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "xlsx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}


@router.get("/loi")
async def generate_loi(order_id: int = Query(...), pi_no: str = Query(...)):
    svc = DocumentService()
    _, doc_key, _ = svc.generate_loi(order_id, pi_no)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "docx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "docx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}


@router.get("/msds")
async def generate_msds(product: str = Query(...)):
    svc = DocumentService()
    _, doc_key, _ = svc.generate_msds(product)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "docx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "docx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}


@router.get("/history/{order_id}")
async def get_doc_history(order_id: int):
    db = SessionLocal()
    try:
        docs = db.query(ShipmentDoc).filter(
            ShipmentDoc.order_id == order_id
        ).order_by(desc(ShipmentDoc.created_at)).all()
        return [{"doc_key": d.doc_key, "doc_type": d.doc_type, "version": d.version,
                  "file_name": d.file_name, "created_by": d.created_by,
                  "created_at": d.created_at.isoformat() if d.created_at else None} for d in docs]
    finally:
        db.close()