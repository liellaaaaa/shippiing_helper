"""Declaration elements CRUD API."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.database import SessionLocal
from app.services.declaration_element_service import declaration_element_svc
from app.core.audit_decorator import audit_action

router = APIRouter(prefix="/api/v1/declaration-elements", tags=["declaration-elements"])


class ElementCreate(BaseModel):
    hs_code: str = Field(min_length=1, description="商品编码")
    declaration_name: str = Field(min_length=1, description="申报名称")
    elements_text: str = ""


class ElementUpdate(BaseModel):
    hs_code: Optional[str] = None
    declaration_name: Optional[str] = None
    elements_text: Optional[str] = None


def _to_dict(item):
    return {
        "id": item.id,
        "hs_code": item.hs_code or "",
        "declaration_name": item.declaration_name or "",
        "elements_text": item.elements_text or "",
    }


@router.get("")
async def list_elements(
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    db = SessionLocal()
    try:
        items, total = declaration_element_svc.list_elements(db, keyword, page, size)
        return {
            "items": [_to_dict(i) for i in items],
            "total": total,
            "page": page,
            "size": size,
        }
    finally:
        db.close()


@router.get("/{element_id}")
async def get_element(element_id: int):
    db = SessionLocal()
    try:
        item = declaration_element_svc.get_element(db, element_id)
        if not item:
            return {"error": "Not found"}
        return _to_dict(item)
    finally:
        db.close()


@router.post("")
@audit_action("element_create", "declaration-elements")
async def create_element(data: ElementCreate):
    db = SessionLocal()
    try:
        item = declaration_element_svc.create_element(db, data.model_dump())
        return _to_dict(item)
    except ValueError as e:
        return {"error": str(e)}
    finally:
        db.close()


@router.put("/{element_id}")
@audit_action("element_update", "declaration-elements")
async def update_element(element_id: int, data: ElementUpdate):
    db = SessionLocal()
    try:
        item = declaration_element_svc.update_element(db, element_id, data.model_dump(exclude_unset=True))
        if not item:
            return {"error": "Not found"}
        return _to_dict(item)
    finally:
        db.close()


@router.delete("/{element_id}")
@audit_action("element_delete", "declaration-elements")
async def delete_element(element_id: int):
    db = SessionLocal()
    try:
        ok = declaration_element_svc.delete_element(db, element_id)
        return {"success": ok}
    finally:
        db.close()
