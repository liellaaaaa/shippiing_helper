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
async def generate_booking(order_id: int = Query(...), template_type: str = Query("xls")):
    """
    生成订舱单，支持选择模板格式。
    template_type: "xls" (默认，使用 .xls 转换) 或 "xlsx" (直接使用 .xlsx)
    """
    svc = DocumentService()
    content, doc_key, _ = svc.generate_booking(order_id, template_type)
    # Create config first to get UUID, then save to DB (OnlyOffice fetches immediately on config load)
    token, config, safe_key = oo_svc.create_config(doc_key, "xlsx")
    _save_doc_to_db(doc_key, "booking", content, order_id=order_id, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    # Download URLs use safe_key (UUID) since that's what's stored in DB
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }


@router.get("/loi")
async def generate_loi(order_no: str = Query(...), pi_no: str = Query(...)):
    svc = DocumentService()
    content, doc_key, _ = svc.generate_loi(order_no, pi_no)
    token, config, safe_key = oo_svc.create_config(doc_key, "docx")
    _save_doc_to_db(doc_key, "loi", content, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }


@router.get("/msds")
async def generate_msds(product: str = Query(...)):
    svc = DocumentService()
    content, doc_key, _ = svc.generate_msds(product)
    token, config, safe_key = oo_svc.create_config(doc_key, "docx")
    _save_doc_to_db(doc_key, "msds", content, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }


@router.get("/msds/{msds_id}")
async def load_msds(msds_id: int):
    """
    加载指定的 MSDS 文件（从数据库索引中按 ID 查找原始文件，
    .doc → .docx 转换后交给 OnlyOffice 编辑）。
    """
    db = SessionLocal()
    try:
        from app.models.msds_index import MSDSIndex
        record = db.query(MSDSIndex).filter(MSDSIndex.id == msds_id).first()
        if not record:
            return {"error": "MSDS file not found"}
        svc = DocumentService()
        content, doc_key, _ = svc.load_msds_file(record)
        token, config, safe_key = oo_svc.create_config(doc_key, "docx")
        # Use safe_key (UUID) as doc_key so OnlyOffice can find it by documentKey
        _save_doc_to_db(safe_key, "msds", content, storage_key=safe_key)
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
        return {
            **config,
            "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
            "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
        }
    finally:
        db.close()


@router.get("/customs")
async def generate_customs(order_id: int | None = Query(None)):
    """
    生成出口报关资料工作簿（5个 sheet 的 xlsx）。
    order_id 暂不使用，为后续自动数据填充留扩展口。
    """
    svc = DocumentService()
    content, doc_key, _ = svc.generate_customs(order_id=order_id)
    token, config, safe_key = oo_svc.create_config(doc_key, "xlsx")
    _save_doc_to_db(doc_key, "customs", content, order_id=order_id, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
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
        file_ext = "xlsx" if template_type == "booking" else "docx"
        token, config, safe_key = oo_svc.create_config(doc_key, file_ext)
        _save_doc_to_db(doc_key, template_type, content, storage_key=safe_key)
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
        return {
            **config,
            "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
            "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
        }
    except FileNotFoundError as e:
        return {"error": str(e)}


def _save_doc_to_db(doc_key: str, doc_type: str, content: bytes, order_id: int = None, storage_key: str = None):
    """
    Save generated document to DB so OnlyOffice can download it.
    storage_key: if provided, store under this key (UUID) for OnlyOffice routing;
                 otherwise store under original doc_key.
    """
    db = SessionLocal()
    try:
        content_hash = hashlib.md5(content).hexdigest()
        # Use storage_key (UUID) as doc_key if provided, for OnlyOffice routing compatibility
        store_key = storage_key if storage_key else doc_key
        doc = ShipmentDoc(
            doc_key=store_key,
            doc_type=doc_type,
            order_id=order_id,
            file_blob=base64.b64encode(content).decode(),
            content_hash=content_hash,
            version=1,
            file_name=f"{doc_key}.{'xlsx' if doc_type in ('booking', 'customs') else 'docx'}",
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
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
        return [{
            "doc_key": d.doc_key,
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "version": d.version,
            "created_by": d.created_by,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "url": f"{callback_base}/api/v1/onlyoffice/download/{quote(d.doc_key, safe='')}",
            "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{quote(d.doc_key, safe='')}",
            "documentServerUrl": os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080"),
            "docType": "xlsx" if d.doc_type == "booking" else "docx",
        } for d in docs]
    finally:
        db.close()