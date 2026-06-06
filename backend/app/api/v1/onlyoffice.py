import os, hashlib, base64
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import desc
from urllib.parse import unquote
from app.database import SessionLocal
from app.models.shipment_doc import ShipmentDoc
from app.services.onlyoffice_service import OnlyOfficeService

router = APIRouter(prefix="/api/v1/onlyoffice", tags=["onlyoffice"])


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
    token = svc.generate_jwt_token(doc_key, fileType)
    config = svc.build_editor_config(token, doc_key, fileType)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    encoded_key = quote(doc_key, safe="")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{encoded_key}"}


@router.post("/callback")
async def onlyoffice_callback(
    doc_key: str = Query(...),
    user: str = Query(default="admin"),
    file: UploadFile = File(default=None),
):
    import logging
    logger = logging.getLogger("uvicorn")
    doc_key = unquote(doc_key)
    logger.warning(f"[onlyoffice-callback] doc_key={doc_key} user={user}")

    # OnlyOffice sends two types of callbacks:
    # 1. JSON status update (no file) — when document is saved/closed
    # 2. Multipart file upload (with file) — when Document Server sends the actual file
    if file is None:
        # JSON status update — acknowledge without saving
        logger.warning(f"[onlyoffice-callback] status update (no file), doc_key={doc_key}")
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
async def download_doc(doc_key: str):
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
        from starlette.concurrency import iterate_in_threadpool
        async def content_generator(data):
            async for chunk in iterate_in_threadpool([data]):
                yield chunk
        return StreamingResponse(content_generator(content), media_type=media_type, headers={
            "content-disposition": f'attachment; filename="{doc.file_name}"'
        })
    finally:
        db.close()