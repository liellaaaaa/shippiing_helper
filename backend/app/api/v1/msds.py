from fastapi import APIRouter, Query
from app.database import SessionLocal
from app.models.msds_index import MSDSIndex
from app.services.msds_service import MSDSService
from app.core.config import MSDS_DIR

router = APIRouter(prefix="/api/v1/msds", tags=["msds"])


@router.get("")
async def list_msds(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str = Query("")):
    db = SessionLocal()
    try:
        q = db.query(MSDSIndex)
        if search:
            q = q.filter(MSDSIndex.product_name_cn.ilike(f"%{search}%"))
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return {"items": [{"id": m.id, "filename": m.filename, "product_name_cn": m.product_name_cn,
                             "physical_form": m.physical_form, "ion_type": m.ion_type, "ph": m.ph} for m in items],
                "total": total}
    finally:
        db.close()


@router.get("/{msds_id}/content")
async def get_msds_content(msds_id: int):
    db = SessionLocal()
    try:
        m = db.query(MSDSIndex).filter(MSDSIndex.id == msds_id).first()
        if not m:
            return {"error": "not found"}
        svc = MSDSService()
        text = svc.extract_text(m.file_path)
        composition = svc.extract_composition_table(text)
        props = svc.extract_physical_props(text)
        return {"composition": composition, "physical_props": props}
    finally:
        db.close()


@router.post("/reindex")
async def reindex_msds():
    svc = MSDSService()
    db = SessionLocal()
    try:
        count = svc.index_msds_directory(MSDS_DIR, db)
        return {"indexed": count}
    finally:
        db.close()