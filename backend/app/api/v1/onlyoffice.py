import os, hashlib, base64, logging
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import desc
from urllib.parse import quote, unquote
from app.database import SessionLocal
from app.models.shipment_doc import ShipmentDoc
from app.services.onlyoffice_service import OnlyOfficeService

router = APIRouter(prefix="/api/v1/onlyoffice", tags=["onlyoffice"])
oo_svc = OnlyOfficeService()
logger = logging.getLogger(__name__)


def infer_doc_type(doc_key: str) -> str:
    if doc_key.startswith("booking"): return "booking"
    if doc_key.startswith("loi"): return "loi"
    return "msds"


def extract_order_id_from_key(doc_key: str):
    parts = doc_key.split("_")
    if len(parts) >= 2:
        try: return int(parts[1])
        except ValueError: pass
    return None


@router.post("/jwt")
async def create_jwt(documentKey: str = Query(...), fileType: str = Query(...)):
    doc_key = unquote(documentKey)
    svc = OnlyOfficeService()
    token, config, safe_key = svc.create_config(doc_key, fileType)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }


@router.post("/callback")
async def onlyoffice_callback(
    doc_key: str = Query(...),
    user: str = Query(default="admin"),
    file: UploadFile = File(default=None),
):
    doc_key = unquote(doc_key)
    # Resolve safe_key (UUID) back to original doc_key for DB lookup
    resolved_key = oo_svc.resolve_safe_key(doc_key)
    if resolved_key:
        doc_key = resolved_key

    # OnlyOffice sends two types of callbacks:
    # 1. JSON status update (no file) — when document is saved/closed
    # 2. Multipart file upload (with file) — when Document Server sends the actual file
    if file is None:
        return {"error": 0}

    content = await file.read()
    logger.warning(f"[onlyoffice-callback] file size={len(content)} bytes, content_hash={hashlib.md5(content).hexdigest()}")
    if len(content) == 0:
        logger.warning(f"[onlyoffice-callback] empty file, ignoring")
        return {"error": 0}

    content_hash = hashlib.md5(content).hexdigest()
    db = SessionLocal()
    try:
        last_doc = db.query(ShipmentDoc).filter(
            ShipmentDoc.doc_key == doc_key
        ).order_by(desc(ShipmentDoc.version)).first()
        if last_doc and last_doc.content_hash == content_hash:
            return {"error": 0}
        version = (last_doc.version + 1) if last_doc else 1
        new_doc = ShipmentDoc(
            doc_key=doc_key,
            doc_type=infer_doc_type(doc_key),
            order_id=extract_order_id_from_key(doc_key),
            file_blob=base64.b64encode(content).decode(),
            content_hash=content_hash,
            version=version,
            file_name=f"{doc_key}_v{version}",
            created_by=user,
        )
        db.add(new_doc)
        db.commit()
        return {"error": 0}
    finally:
        db.close()


MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls":  "application/vnd.ms-excel",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc":  "application/msword",
    "pdf":  "application/pdf",
}


@router.get("/download/{doc_key}")
def download_doc(doc_key: str):
    doc_key = unquote(doc_key)
    db = SessionLocal()
    try:
        doc = db.query(ShipmentDoc).filter(
            ShipmentDoc.doc_key == doc_key
        ).order_by(desc(ShipmentDoc.version)).first()
        if not doc:
            return {"error": "Document not found"}
        content = base64.b64decode(doc.file_blob)
        suffix = doc.file_name.split(".")[-1].lower() if "." in doc.file_name else "bin"
        media_type = MEDIA_TYPES.get(suffix, "application/octet-stream")
        encoded_name = quote(doc.file_name, safe='')
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "content-disposition": f"attachment; filename*=UTF-8''{encoded_name}",
                "content-length": str(len(content)),
            }
        )
    finally:
        db.close()