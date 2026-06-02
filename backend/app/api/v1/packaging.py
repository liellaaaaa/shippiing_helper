"""Packaging API endpoints — types, pallets, calculate."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.packaging_service import (
    get_package_types,
    get_pallet_types,
    calculate,
    calculate_all_schemes,
    PackageSpec,
    PalletSpec,
)


router = APIRouter(prefix="/api/v1/packaging", tags=["包装计算"])


class CalculateRequest(BaseModel):
    packaging_name: str
    order_qty_kg: float
    use_pallet: bool = False
    pallet_name: Optional[str] = None


class PackingScheme(BaseModel):
    drums: int
    pallets: int
    drums_per_pallet: int
    pallet_type: Optional[str]
    total_cbm: float
    total_weight_kg: float
    fits_20gp: bool
    fits_40gp: bool
    recommended: str


@router.get("/types", summary="获取所有包装种类")
def list_packaging_types():
    """返回所有包装种类（含规格参数）"""
    packages = get_package_types()
    return [
        {
            "name": p.name,
            "dims": p.dims,
            "cbm": p.cbm,
            "tare_kg": p.tare_kg,
            "gross_kg": p.gross_kg,
            "net_kg": p.net_kg,
            "barrel_type": p.barrel_type,
            "is_palletizable": p.is_palletizable,
            "no_pallet_qty": p.no_pallet_qty,
            "pallet_qty_1x1": p.pallet_qty_1x1,
            "pallet_qty_1_1x1_1": p.pallet_qty_1_1x1_1,
        }
        for p in packages
    ]


@router.get("/pallets", summary="获取所有托盘种类")
def list_pallet_types():
    """返回所有托盘种类"""
    pallets = get_pallet_types()
    return [{"name": p.name, "dims": p.dims, "weight_kg": p.weight_kg, "cbm": p.cbm} for p in pallets]


@router.post("/calculate", response_model=PackingScheme, summary="计算包装方案")
def calculate_packaging(req: CalculateRequest):
    """
    输入包装种类+数量+是否打卡板 → 返回计算结果

    不打卡板时返回单个结果；打卡板时同时返回所有可用托盘方案。
    """
    try:
        if req.use_pallet:
            # 返回所有打卡板方案
            schemes = calculate_all_schemes(req.packaging_name, req.order_qty_kg)
            schemes = [s for s in schemes if s.use_pallet or s.pallets == 0]
            if not schemes:
                raise ValueError("无可用方案")
            # 返回推荐的第一个方案（优先20GP可装的）
            best = next((s for s in schemes if s.fits_20gp), schemes[0])
            return PackingScheme(
                drums=best.drums,
                pallets=best.pallets,
                drums_per_pallet=best.drums_per_pallet,
                pallet_type=best.pallet_type,
                total_cbm=best.total_cbm,
                total_weight_kg=best.total_weight_kg,
                fits_20gp=best.fits_20gp,
                fits_40gp=best.fits_40gp,
                recommended=best.recommended,
            )
        else:
            r = calculate(req.packaging_name, req.order_qty_kg, use_pallet=False)
            return PackingScheme(
                drums=r.drums,
                pallets=r.pallets,
                drums_per_pallet=0,
                pallet_type=None,
                total_cbm=r.total_cbm,
                total_weight_kg=r.total_weight_kg,
                fits_20gp=r.fits_20gp,
                fits_40gp=r.fits_40gp,
                recommended=r.recommended,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate-schemes", summary="计算所有包装方案")
def calculate_all_packaging_schemes(req: CalculateRequest):
    """返回所有可用方案（不打卡板 + 两种托盘）"""
    try:
        schemes = calculate_all_schemes(req.packaging_name, req.order_qty_kg)
        return [
            {
                "drums": s.drums,
                "pallets": s.pallets,
                "drums_per_pallet": s.drums_per_pallet,
                "pallet_type": s.pallet_type,
                "use_pallet": s.pallet_type is not None,
                "total_cbm": s.total_cbm,
                "total_weight_kg": s.total_weight_kg,
                "fits_20gp": s.fits_20gp,
                "fits_40gp": s.fits_40gp,
                "recommended": s.recommended,
            }
            for s in schemes
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))