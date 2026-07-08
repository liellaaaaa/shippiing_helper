"""MSDS ledger API endpoints."""
import re
import random
import zipfile
from io import BytesIO
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.database import SessionLocal
from app.services.msds_ledger_service import msds_ledger_svc


router = APIRouter(prefix="/api/v1/msds-ledger", tags=["msds-ledger"])

BATCH_LIMIT = 50


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


class BatchGenerateRequest(BaseModel):
    ledger_ids: list[int]
    overrides: dict = {}  # {ledger_id: {msds_number, revision_date}}


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


@router.post("/batch-generate")
async def batch_generate(request: BatchGenerateRequest):
    """Batch generate MSDS for multiple products. Returns ZIP file."""
    from app.services.msds_generator_service import MSDSGeneratorService

    if len(request.ledger_ids) == 0:
        return {"error": "请至少选择一个产品"}
    if len(request.ledger_ids) > BATCH_LIMIT:
        return {"error": f"单次最多生成{BATCH_LIMIT}个产品"}

    db = SessionLocal()
    try:
        gen_svc = MSDSGeneratorService()
        generated_files = []  # [(content_bytes, filename), ...]
        errors = []  # [(ledger_id, product_name, error_msg), ...]
        used_numbers = set()  # Track numbers used in this batch

        for ledger_id in request.ledger_ids:
            try:
                item = msds_ledger_svc.get_ledger(db, ledger_id)
                if not item:
                    errors.append((ledger_id, str(ledger_id), "Ledger not found"))
                    continue

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

                # Resolve MSDS number
                override = request.overrides.get(str(ledger_id), {})
                if override.get("msds_number"):
                    msds_number = override["msds_number"]
                    revision_date = override.get("revision_date", "")
                else:
                    msds_number, revision_date = _auto_generate_msds_number()

                # Check collision in DB and within this batch
                msds_number = _check_number_collision(db, msds_number)
                while msds_number in used_numbers:
                    suffix = msds_number.split("-")[-1]
                    if suffix.isdigit():
                        msds_number = f"HHJS-{msds_number[5:-len(suffix)]}{int(suffix)+1}"
                    else:
                        msds_number = f"{msds_number}-2"
                    msds_number = _check_number_collision(db, msds_number)
                used_numbers.add(msds_number)

                # Generate CN MSDS
                cn_bytes, cn_key = gen_svc.generate_msds_from_template(
                    ledger_data=ledger_data,
                    language="cn",
                    msds_number=msds_number,
                    revision_date=revision_date,
                )
                cn_filename = _make_filename(
                    ledger_data["customs_name"],
                    ledger_data["appearance"],
                    "cn"
                )
                generated_files.append((cn_bytes, cn_filename))

                # Generate EN MSDS
                en_bytes, en_key = gen_svc.generate_msds_from_template(
                    ledger_data=ledger_data,
                    language="en",
                    msds_number=msds_number,
                    revision_date=revision_date,
                )
                en_filename = _make_filename(
                    ledger_data["customs_name"],
                    ledger_data["appearance"],
                    "en"
                )
                generated_files.append((en_bytes, en_filename))

            except Exception as e:
                product_name = ""
                try:
                    item = msds_ledger_svc.get_ledger(db, ledger_id)
                    product_name = item.customs_name if item else str(ledger_id)
                except:
                    product_name = str(ledger_id)
                errors.append((ledger_id, product_name, str(e)))

        # Package ZIP
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for content, filename in generated_files:
                zf.writestr(filename, content)

            # Add errors.txt if there are errors
            if errors:
                error_lines = [f"Ledger ID: {lid}, Product: {name}, Error: {err}" for lid, name, err in errors]
                zf.writestr("errors.txt", "\n".join(error_lines))

        zip_buf.seek(0)

        # Generate ZIP filename (ASCII only — latin-1 can't encode Chinese)
        today = datetime.now().strftime("%Y%m%d")
        product_count = len(generated_files) // 2
        zip_filename = f"MSDS_{today}_{product_count}products.zip"

        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
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


def _auto_generate_msds_number() -> tuple[str, str]:
    """Generate MSDS number with random month offset 3-5 months back.
    Returns (msds_number, revision_date)."""
    now = datetime.now()
    year = now.strftime("%y")
    month_offset = random.randint(3, 5)
    past = now - timedelta(days=month_offset * 30)
    mm = past.strftime("%m")
    day = random.randint(1, 28)
    msds_number = f"HHJS-{year}{mm}"
    revision_date = f"{past.year}/{mm}/{day:02d}"
    return msds_number, revision_date


def _check_number_collision(db, msds_number: str) -> str:
    """Check if MSDS number already exists in DB, append suffix if collision."""
    from app.models.shipment_doc import ShipmentDoc
    existing = db.query(ShipmentDoc).filter(
        ShipmentDoc.file_name.like(f"%{msds_number}%")
    ).count()
    if existing == 0:
        return msds_number
    suffix = 2
    while True:
        candidate = f"{msds_number}-{suffix}"
        exists = db.query(ShipmentDoc).filter(
            ShipmentDoc.file_name.like(f"%{candidate}%")
        ).count()
        if exists == 0:
            return candidate
        suffix += 1


def _make_filename(customs_name: str, appearance: str, lang: str) -> str:
    """Generate filename: {产品名}-{外观性状}-{中/英文}MSDS.docx"""
    safe_name = re.sub(r'[\\/:*?"<>|]', '', customs_name)[:30]
    safe_appearance = re.sub(r'[\\/:*?"<>|]', '', appearance)[:20] if appearance else "无资料"
    lang_label = "中文" if lang == "cn" else "英文"
    return f"{safe_name}-{safe_appearance}-{lang_label}MSDS.docx"
