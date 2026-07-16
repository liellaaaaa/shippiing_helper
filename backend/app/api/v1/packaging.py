"""Packaging API endpoints — types, pallets, calculate."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.packaging_service import (
    get_package_types,
    get_pallet_types,
    calculate,
    calculate_all_schemes,
    calculate_order_packaging,
    PackageSpec,
    PalletSpec,
    OrderProductInput,
)
from app.schemas.order_pi_record import OrderPackagingResultSchema


router = APIRouter(prefix="/api/v1/packaging", tags=["包装计算"])


class CalculateRequest(BaseModel):
    packaging_name: str
    order_qty_kg: float
    use_pallet: bool = False
    pallet_name: Optional[str] = None
    actual_fill_kg: Optional[float] = None


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
    remainder: int = 0  # 余数桶数
    full_pallets: int = 0  # 整板数


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
            schemes = calculate_all_schemes(req.packaging_name, req.order_qty_kg, actual_fill_kg=req.actual_fill_kg)
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
                remainder=best.drums - best.full_pallets * best.drums_per_pallet if best.drums_per_pallet else 0,
                full_pallets=best.full_pallets,
            )
        else:
            r = calculate(req.packaging_name, req.order_qty_kg, use_pallet=False, actual_fill_kg=req.actual_fill_kg)
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
                remainder=0,
                full_pallets=0,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate-schemes", summary="计算所有包装方案")
def calculate_all_packaging_schemes(req: CalculateRequest):
    """返回所有可用方案（不打卡板 + 两种托盘）"""
    try:
        schemes = calculate_all_schemes(req.packaging_name, req.order_qty_kg, actual_fill_kg=req.actual_fill_kg)
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
                "remainder": s.drums - s.full_pallets * s.drums_per_pallet if s.drums_per_pallet else 0,
                "full_pallets": s.full_pallets,
            }
            for s in schemes
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class OrderProductItem(BaseModel):
    """订单中单个产品的输入"""
    product_name: str
    packaging_name: str
    quantity_kg: float
    specification_kg: float
    barrel_type: str = "胶桶"
    pallet_spec: str = "1.1*1.1m"
    actual_fill_kg: Optional[float] = None


class OrderPackagingRequest(BaseModel):
    products: list[OrderProductItem]


@router.post("/calculate-order", response_model=OrderPackagingResultSchema, summary="订单级别包装汇总计算")
def calculate_order_packaging_endpoint(req: OrderPackagingRequest):
    """
    订单级别包装汇总计算 — 支持多产品。

    输入订单中的多个产品，输出汇总后的：
    - 总桶数、总卡板数、总体积、总重量
    - 按卡板尺寸分组的详情
    - 各产品明细
    - 货柜适应性判断
    """
    try:
        products = [
            OrderProductInput(
                product_name=p.product_name,
                packaging_name=p.packaging_name,
                quantity_kg=p.quantity_kg,
                specification_kg=p.specification_kg,
                barrel_type=p.barrel_type,
                pallet_spec=p.pallet_spec,
                actual_fill_kg=p.actual_fill_kg,
            )
            for p in req.products
        ]
        result = calculate_order_packaging(products)
        return OrderPackagingResultSchema(
            total_drums=result.total_drums,
            total_pallets=result.total_pallets,
            total_volume_cbm=result.total_volume_cbm,
            total_weight_kg=result.total_weight_kg,
            total_net_weight_kg=result.total_net_weight_kg,
            pallet_details=[
                {
                    "pallet_spec": p.pallet_spec,
                    "pallet_count": p.pallet_count,
                    "drums_on_pallets": p.drums_on_pallets,
                    "volume_cbm": p.volume_cbm,
                    "weight_kg": p.weight_kg,
                }
                for p in result.pallet_details
            ],
            product_details=[
                {
                    "product_name": p.product_name,
                    "packaging_name": p.packaging_name,
                    "specification_kg": p.specification_kg,
                    "drums": p.drums,
                    "drums_per_pallet": p.drums_per_pallet,
                    "pallets": p.pallets,
                    "pallet_spec": p.pallet_spec,
                    "net_weight_kg": p.net_weight_kg,
                    "gross_weight_kg": p.gross_weight_kg,
                    "volume_cbm": p.total_volume_cbm,
                }
                for p in result.product_details
            ],
            container_20gp_fit=result.container_20gp_fit,
            container_40hq_fit=result.container_40hq_fit,
            recommended=result.recommended,
            load_rate_20gp=result.load_rate_20gp,
            load_rate_40hq=result.load_rate_40hq,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))