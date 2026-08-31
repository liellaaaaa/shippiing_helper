from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.declaration_ledger_service import DeclarationLedgerService
from app.schemas.declaration import (
    HsCodeDetailResponse,
    HsCodeListItem,
    ProductCreate,
    ProductUpdate,
    ValuesUpdate,
    FieldCreate,
    FieldUpdate,
    HsCodeFieldResponse,
    DeclarationProductResponse
)
from app.core.audit_decorator import audit_action

router = APIRouter(prefix="/api/v1/declaration-ledger", tags=["declaration-ledger"])


@router.get("/hs-codes", response_model=list[HsCodeListItem])
def list_hs_codes(
    keyword: Optional[str] = Query(None, description="搜索关键字"),
    db: Session = Depends(get_db)
):
    """获取 HS Code 列表"""
    svc = DeclarationLedgerService(db)
    return svc.list_hs_codes(keyword)


@router.get("/hs-codes/{hs_code}", response_model=HsCodeDetailResponse)
def get_hs_code_detail(
    hs_code: str,
    db: Session = Depends(get_db)
):
    """获取 HS Code 详情（字段定义 + 产品列表 + 值）"""
    svc = DeclarationLedgerService(db)
    result = svc.get_hs_code_detail(hs_code)
    if not result:
        raise HTTPException(status_code=404, detail=f"HS Code {hs_code} not found")
    return result


@router.post("/hs-codes/{hs_code}/products", response_model=DeclarationProductResponse)
@audit_action("declaration_product_create", "declaration-ledger")
def create_product(
    hs_code: str,
    data: ProductCreate,
    db: Session = Depends(get_db)
):
    """新增产品"""
    svc = DeclarationLedgerService(db)
    try:
        return svc.create_product(
            hs_code=hs_code,
            product_name=data.product_name,
            website_name=data.website_name,
            product_description=data.product_description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/products/{product_id}", response_model=DeclarationProductResponse)
@audit_action("declaration_product_update", "declaration-ledger")
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db)
):
    """更新产品信息"""
    svc = DeclarationLedgerService(db)
    try:
        return svc.update_product(
            product_id=product_id,
            product_name=data.product_name,
            website_name=data.website_name,
            product_description=data.product_description
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/products/{product_id}")
@audit_action("declaration_product_delete", "declaration-ledger")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """删除产品"""
    svc = DeclarationLedgerService(db)
    success = svc.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {"message": "Product deleted successfully"}


@router.put("/products/{product_id}/values", response_model=DeclarationProductResponse)
@audit_action("declaration_values_update", "declaration-ledger")
def update_values(
    product_id: int,
    data: ValuesUpdate,
    db: Session = Depends(get_db)
):
    """批量更新产品要素值"""
    svc = DeclarationLedgerService(db)
    try:
        return svc.update_values(product_id=product_id, values=data.values)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/fields", response_model=HsCodeFieldResponse)
@audit_action("declaration_field_create", "declaration-ledger")
def create_field(
    hs_code: str = Query(..., description="HS Code"),
    data: FieldCreate = ...,
    db: Session = Depends(get_db)
):
    """新增字段定义"""
    svc = DeclarationLedgerService(db)
    try:
        return svc.create_field(
            hs_code=hs_code,
            field_name=data.field_name,
            field_type=data.field_type,
            sort_order=data.sort_order,
            is_required=data.is_required
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/fields/{field_id}", response_model=HsCodeFieldResponse)
@audit_action("declaration_field_update", "declaration-ledger")
def update_field(
    field_id: int,
    data: FieldUpdate,
    db: Session = Depends(get_db)
):
    """更新字段定义"""
    svc = DeclarationLedgerService(db)
    try:
        return svc.update_field(
            field_id=field_id,
            field_name=data.field_name,
            field_type=data.field_type,
            sort_order=data.sort_order,
            is_required=data.is_required
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/fields/{field_id}")
@audit_action("declaration_field_delete", "declaration-ledger")
def delete_field(
    field_id: int,
    db: Session = Depends(get_db)
):
    """删除字段定义"""
    svc = DeclarationLedgerService(db)
    success = svc.delete_field(field_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found")
    return {"message": "Field deleted successfully"}
