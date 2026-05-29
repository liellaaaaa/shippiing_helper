"""FR-4.x 包装计算 API — 海运/空运/陆运统一计算端点（只读）"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from app.services.calculation_service import CalculationService, CONTAINER_LIMITS
from app.models.order import PackagingType
from app.database import get_db


router = APIRouter(prefix="/api/v1/packages", tags=["包装计算"])


@router.get("/calculate")
async def calculate_package(
    mode: str = Query("manual", description="order / manual"),
    quantity_kg: float = Query(..., description="订单量 kg"),
    packaging_name: str = Query(..., description="包装类型名称"),
    pallet_spec: str = Query("1.1x1.1", description="1.0x1.0 / 1.1x1.1"),
    pallet_qty: int = Query(None, description="单板数量（默认取包装类型容量）"),
    no_pallet: bool = Query(False, description="不打卡板"),
    transport_mode: str = Query("sea", description="sea / air / land"),
    order_id: int = Query(None, description="订单ID（mode=order 时）"),
    internal_code: str = Query(None, description="内部编码（用于知识库匹配）"),
    db=Depends(get_db),
):
    """
    包装计算统一入口。

    - mode=manual：手动输入模式
    - mode=order：从订单带入数据，自动推荐包装类型
    - transport_mode=sea：返回桶数、卡板数、体积、毛重、集装箱推荐
    - transport_mode=air：返回计费重量对比（实重/IATA×167/航司÷6000）
    - transport_mode=land：返回总件数、毛重、体积、公路限重警告
    """
    service = CalculationService()

    # 查询包装类型信息
    packaging = db.query(PackagingType).filter_by(name=packaging_name).first()
    if not packaging:
        raise HTTPException(status_code=404, detail=f"未找到包装类型：{packaging_name}")

    # 确定单板容量
    if pallet_spec == "1.0x1.0":
        capacity = packaging.pallet_qty_1x1 or 0
    else:
        capacity = packaging.pallet_qty_1_1x1_1 or 0

    # 如果未指定单板数量，使用默认值
    if pallet_qty is None:
        pallet_qty = capacity

    # 基础计算（海运/共用）
    drums = service.calculate_drums(quantity_kg, packaging.net_kg)
    pallets = service.calculate_pallets(drums, pallet_qty, no_pallet)
    total_cbm = service.calculate_volume(drums, packaging.cbm, pallets, 0.15 if not no_pallet else 0.0)
    total_weight_kg = service.calculate_gross_weight(drums, packaging.gross_kg, pallets, 27.0)

    if transport_mode == "sea":
        container = service.judge_container(total_cbm, total_weight_kg)
        scheme = service.generate_packing_scheme(drums, pallets, pallet_qty, no_pallet)
        return {
            "drums": drums,
            "pallets": pallets,
            "total_cbm": round(total_cbm, 3),
            "total_weight_kg": round(total_weight_kg, 2),
            "packing_scheme": scheme,
            "container": {
                "recommended": container.recommended,
                "load_rate": container.load_rate,
                "volume_limit": container.volume_limit,
                "weight_limit": container.weight_limit,
                "status": container.status,
            },
            "packaging": {
                "name": packaging.name,
                "drum_cbm": packaging.cbm,
                "drum_tare_kg": packaging.tare_kg,
                "drum_gross_kg": packaging.gross_kg,
                "pallet_spec": pallet_spec,
                "pallet_capacity": pallet_qty,
            },
        }

    elif transport_mode == "air":
        vol_weight_167 = service.calculate_air_volume_weight(total_cbm, factor=167)
        vol_weight_6000 = service.calculate_air_volume_weight(total_cbm, factor=6000)
        chargeable = service.calculate_chargeable_weight(total_weight_kg, vol_weight_167, vol_weight_6000)
        return {
            "actual_weight_kg": round(total_weight_kg, 2),
            "vol_weight_167": round(vol_weight_167, 2),
            "vol_weight_6000": round(vol_weight_6000, 2),
            "chargeable_weight_kg": round(chargeable, 2),
            "chargeable_weight_note": "取大者",
        }

    else:  # land
        overweight = service.check_land_overweight(total_weight_kg)
        return {
            "total_drums": drums,
            "total_weight_kg": round(total_weight_kg, 2),
            "total_cbm": round(total_cbm, 3),
            "overweight_warning": overweight,
        }


@router.get("/types")
async def get_packaging_types(db=Depends(get_db)):
    """获取所有包装类型（用于下拉选择）"""
    types = db.query(PackagingType).all()
    return {
        "types": [
            {
                "id": t.id,
                "name": t.name,
                "net_kg": t.net_kg,
                "cbm": t.cbm,
                "pallet_1x1": t.pallet_qty_1x1,
                "pallet_1_1x1_1": t.pallet_qty_1_1x1_1,
            }
            for t in types
        ]
    }


@router.get("/recommend")
async def recommend_packaging(
    internal_code: str = Query(..., description="内部编码"),
    db=Depends(get_db),
):
    """
    根据 internal_code 查询产品知识库，推荐包装类型。
    """
    from app.models.order import ProductKnowledge

    knowledge = db.query(ProductKnowledge).filter_by(internal_code=internal_code).first()
    if not knowledge:
        return {
            "internal_code": internal_code,
            "recommended_packaging": None,
            "reason": None,
        }

    return {
        "internal_code": internal_code,
        "recommended_packaging": knowledge.recommended_packaging,
        "reason": "历史使用记录",
    }