import os, hashlib, base64
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc
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
    svc = OnlyOfficeService()
    token = svc.generate_jwt_token(documentKey, fileType)
    config = svc.build_editor_config(token, documentKey, fileType)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{documentKey}"}


@router.post("/callback")
async def onlyoffice_callback(doc_key: str = Query(...), user: str = Query(default="admin"), file: UploadFile = File(...)):
    content = await file.read()
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


@router.get("/download/{doc_key}")
async def download_doc(doc_key: str):
    db = SessionLocal()
    try:
        doc = db.query(ShipmentDoc).filter(
            ShipmentDoc.doc_key == doc_key
        ).order_by(desc(ShipmentDoc.version)).first()
        if not doc:
            return {"error": "Document not found"}
        content = base64.b64decode(doc.file_blob)
        suffix = doc.file_name.split(".")[-1] if "." in doc.file_name else "bin"
        return FileResponse(BytesIO(content), media_type="application/octet-stream", filename=doc.file_name)
    finally:
        db.close()