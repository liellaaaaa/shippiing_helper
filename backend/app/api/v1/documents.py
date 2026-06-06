import hashlib, base64
import os
from fastapi import APIRouter, Query
from sqlalchemy import desc
from urllib.parse import quote
from app.database import SessionLocal
from app.models.shipment_doc import ShipmentDoc
from app.services.document_service import DocumentService
from app.services.onlyoffice_service import OnlyOfficeService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
oo_svc = OnlyOfficeService()


@router.get("/booking")
async def generate_booking(order_id: int = Query(...)):
    svc = DocumentService()
    content, doc_key, _ = svc.generate_booking(order_id)
    _save_doc_to_db(doc_key, "booking", content, order_id=order_id)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "xlsx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "xlsx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    # OnlyOffice 在 Docker 内下载文档用 callback_base，浏览器下载用 api_base
    encoded_key = quote(doc_key, safe="")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{encoded_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{encoded_key}",
    }


@router.get("/loi")
async def generate_loi(order_id: int = Query(...), pi_no: str = Query(...)):
    svc = DocumentService()
    content, doc_key, _ = svc.generate_loi(order_id, pi_no)
    _save_doc_to_db(doc_key, "loi", content, order_id=order_id)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "docx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "docx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    encoded_key = quote(doc_key, safe="")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{encoded_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{encoded_key}",
    }


@router.get("/msds")
async def generate_msds(product: str = Query(...)):
    svc = DocumentService()
    content, doc_key, _ = svc.generate_msds(product)
    _save_doc_to_db(doc_key, "msds", content)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "docx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "docx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    # URL-encode doc_key for safe transport in URLs
    encoded_key = quote(doc_key, safe="")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{encoded_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{encoded_key}",
    }


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


@router.get("/template/{template_type}")
async def open_blank_template(template_type: str):
    if template_type not in ("booking", "loi", "msds"):
        return {"error": "Invalid template type"}
    svc = DocumentService()
    try:
        content, doc_key, _ = svc.generate_template_instance(template_type)
        _save_doc_to_db(doc_key, template_type, content)
        file_ext = "xlsx" if template_type == "booking" else "docx"
        jwt_token = oo_svc.generate_jwt_token(doc_key, file_ext)
        config = oo_svc.build_editor_config(jwt_token, doc_key, file_ext)
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
        encoded_key = quote(doc_key, safe="")
        return {
            **config,
            "url": f"{callback_base}/api/v1/onlyoffice/download/{encoded_key}",
            "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{encoded_key}",
        }
    except FileNotFoundError as e:
        return {"error": str(e)}


def _save_doc_to_db(doc_key: str, doc_type: str, content: bytes, order_id: int = None):
    """Save generated document to DB so OnlyOffice can download it."""
    db = SessionLocal()
    try:
        content_hash = hashlib.md5(content).hexdigest()
        doc = ShipmentDoc(
            doc_key=doc_key,
            doc_type=doc_type,
            order_id=order_id,
            file_blob=base64.b64encode(content).decode(),
            content_hash=content_hash,
            version=1,
            file_name=f"{doc_key}.{'xlsx' if doc_type == 'booking' else 'docx'}",
            created_by="system",
        )
        db.add(doc)
        db.commit()
    finally:
        db.close()


@router.get("/my-templates")
async def list_my_templates():
    db = SessionLocal()
    try:
        docs = db.query(ShipmentDoc).filter(
            ShipmentDoc.order_id == None  # noqa: E711 — independent template instances
        ).order_by(desc(ShipmentDoc.created_at)).all()
        return [{
            "doc_key": d.doc_key,
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "version": d.version,
            "created_by": d.created_by,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        } for d in docs]
    finally:
        db.close()