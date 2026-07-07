"""MSDS ledger API endpoints."""
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from typing import Optional
from app.database import SessionLocal
from app.services.msds_ledger_service import msds_ledger_svc


router = APIRouter(prefix="/api/v1/msds-ledger", tags=["msds-ledger"])


class LedgerCreate(BaseModel):
    internal_code: str = ""
    customs_name: str = ""
    appearance: str = ""
    ion_type: str = ""
    ph: str = ""
    composition: list = []
    product_name_en: str = ""
    appearance_en: str = ""
    ion_type_en: str = ""


class LedgerUpdate(BaseModel):
    internal_code: Optional[str] = None
    customs_name: Optional[str] = None
    appearance: Optional[str] = None
    ion_type: Optional[str] = None
    ph: Optional[str] = None
    composition: Optional[list] = None
    product_name_en: Optional[str] = None
    appearance_en: Optional[str] = None
    ion_type_en: Optional[str] = None


class GenerateRequest(BaseModel):
    ledger_id: int
    language: str = "cn"
    msds_number: str = ""
    revision_date: str = ""


@router.get("")
async def list_ledger(keyword: Optional[str] = None, internal_code: Optional[str] = None):
    db = SessionLocal()
    try:
        items = msds_ledger_svc.list_ledger(db, keyword, internal_code)
        return {"items": [_to_dict(i) for i in items]}
    finally:
        db.close()


@router.get("/{ledger_id}")
async def get_ledger(ledger_id: int):
    db = SessionLocal()
    try:
        item = msds_ledger_svc.get_ledger(db, ledger_id)
        if not item:
            return {"error": "Not found"}
        return _to_dict(item)
    finally:
        db.close()


@router.post("")
async def create_ledger(data: LedgerCreate):
    db = SessionLocal()
    try:
        item = msds_ledger_svc.create_ledger(db, data.model_dump())
        return _to_dict(item)
    finally:
        db.close()


@router.put("/{ledger_id}")
async def update_ledger(ledger_id: int, data: LedgerUpdate):
    db = SessionLocal()
    try:
        item = msds_ledger_svc.update_ledger(db, ledger_id, data.model_dump(exclude_unset=True))
        if not item:
            return {"error": "Not found"}
        return _to_dict(item)
    finally:
        db.close()


@router.delete("/{ledger_id}")
async def delete_ledger(ledger_id: int):
    db = SessionLocal()
    try:
        ok = msds_ledger_svc.delete_ledger(db, ledger_id)
        return {"success": ok}
    finally:
        db.close()


@router.post("/generate")
async def generate_msds(request: GenerateRequest):
    """Generate MSDS from template."""
    import os
    import base64
    from app.services.msds_generator_service import MSDSGeneratorService
    from app.services.onlyoffice_service import OnlyOfficeService
    from app.models.shipment_doc import ShipmentDoc
    
    db = SessionLocal()
    try:
        item = msds_ledger_svc.get_ledger(db, request.ledger_id)
        if not item:
            return {"error": "Ledger not found"}
        
        # Prepare ledger data
        ledger_data = {
            "customs_name": item.customs_name or "",
            "appearance": item.appearance or "",
            "ion_type": item.ion_type or "",
            "ph": item.ph or "",
            "composition": item.composition or [],
            "product_name_en": item.product_name_en or "",
            "appearance_en": item.appearance_en or "",
            "ion_type_en": item.ion_type_en or "",
        }
        
        # Generate MSDS
        gen_svc = MSDSGeneratorService()
        content_bytes, doc_key = gen_svc.generate_msds_from_template(
            ledger_data=ledger_data,
            language=request.language,
            msds_number=request.msds_number,
            revision_date=request.revision_date,
        )
        
        # Save to database
        import hashlib
        content_hash = hashlib.md5(content_bytes).hexdigest()
        existing = db.query(ShipmentDoc).filter(ShipmentDoc.content_hash == content_hash).first()
        if existing:
            safe_key = existing.doc_key
        else:
            oo_svc = OnlyOfficeService()
            _, _, safe_key = oo_svc.create_config(doc_key, "docx")

            doc = ShipmentDoc(
                doc_key=safe_key,
                doc_type="msds",
                file_blob=base64.b64encode(content_bytes).decode(),
                content_hash=content_hash,
                version=1,
                file_name=f"{doc_key}.docx",
                created_by="system",
            )
            db.add(doc)
            db.commit()

        # Build OnlyOffice config — reuse the same safe_key stored in DB
        oo_svc = OnlyOfficeService()
        token, config, _ = oo_svc.create_config(doc_key, "docx", existing_safe_key=safe_key)

        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")

        return {
            **config,
            "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
            "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
            "callbackUrl": f"{callback_base}/api/v1/onlyoffice/callback?doc_key={safe_key}",
        }
    finally:
        db.close()


def _to_dict(item):
    return {
        "id": item.id,
        "internal_code": item.internal_code,
        "customs_name": item.customs_name or "",
        "appearance": item.appearance or "",
        "ion_type": item.ion_type or "",
        "ph": item.ph or "",
        "composition": item.composition or [],
        "product_name_en": item.product_name_en or "",
        "appearance_en": item.appearance_en or "",
        "ion_type_en": item.ion_type_en or "",
        "version": item.version or 1,
    }
