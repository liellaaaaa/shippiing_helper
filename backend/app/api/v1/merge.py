"""FR-3.x 数据关联 API — 合并查询端点（只读）"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.models.pi_contract import PiContract, PiContractItem
from app.services.merge_service import MergeService
from app.schemas.merge import OrderListResponse, OrderComparisonResponse
from app.api.deps import get_merge_service


router = APIRouter(prefix="/api/v1/merge", tags=["数据关联"])


@router.get("/orders", response_model=OrderListResponse)
async def get_merge_order_list(
    tab: str = Query("pending", description="pending / completed / all"),
    search: Optional[str] = Query(None, description="模糊搜索：订单号 / 客户名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    查询订单列表（含关联状态），支持 Tab 筛选和分页。

    - tab=pending：仅显示未关联 / 部分关联的订单
    - tab=completed：仅显示完全关联的订单
    - tab=all：显示全部订单
    - search：支持订单号、客户名称模糊匹配
    """
    return merge_service.get_order_list(
        tab=tab,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/orders/{order_id}/comparison", response_model=OrderComparisonResponse)
async def get_order_comparison(
    order_id: int,
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    获取指定订单的合并比对数据。

    返回每个 order_item 与对应的 pi_contract_item 的比对结果，
    包含 diff.status（一致 / 数量不符 / ...）和 flags 列表。
    """
    result = merge_service.get_order_comparison(order_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="订单不存在")
    return result


@router.get("/orders/{order_id}/pi-contracts")
async def get_order_pi_contracts(
    order_id: int,
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    获取指定订单关联的所有 PI 合同列表（用于文档编辑时选择 PI）。

    order_id 可能是 Order.id 或 OrderPiRecord.id（来自 Dashboard）；
    若传入的是 OrderPiRecord.id，则通过 order_no 查找所有 PI 合同。
    """
    from fastapi import HTTPException
    from app.models.order import Order, OrderItem
    from app.models.order_pi_record import OrderPiRecord

    db = merge_service.db

    # 优先：order_id 可能是 OrderPiRecord.id（来自 Dashboard）
    record = db.query(OrderPiRecord).filter(OrderPiRecord.id == order_id).first()
    if record:
        # 用 order_no 找出所有 OrderPiRecord，再找对应的 internal_codes
        all_records = db.query(OrderPiRecord).filter(
            OrderPiRecord.order_no == record.order_no
        ).all()
        internal_codes = list(set(r.internal_code for r in all_records if r.internal_code))
        if not internal_codes:
            return []
        # 查这些 internal_code 对应的 PiContractItem
        from app.models.pi_contract import PiContractItem, PiContract
        pi_items = db.query(PiContractItem).filter(
            PiContractItem.internal_code.in_(internal_codes)
        ).all()
        pi_contract_ids = list(set(item.pi_contract_id for item in pi_items))
        pi_contracts = db.query(PiContract).filter(PiContract.id.in_(pi_contract_ids)).all()
        return [
            {"pi_no": pc.pi_no, "consignee": pc.consignee_name, "destination": pc.destination}
            for pc in pi_contracts
        ]

    # 回退：按原始 Order.id 查找
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    items = db.query(OrderItem).filter_by(order_id=order_id).all()
    if not items:
        return []

    internal_codes = [item.internal_code for item in items]
    linked_items = db.query(PiContractItem).filter(
        PiContractItem.internal_code.in_(internal_codes)
    ).all()

    # 去重获取 pi_contract_ids
    pi_contract_ids = set(item.pi_contract_id for item in linked_items)
    if not pi_contract_ids:
        return []

    contracts = db.query(PiContract).filter(
        PiContract.id.in_(pi_contract_ids)
    ).all()

    return [{"pi_no": c.pi_no, "consignee": c.consignee_name, "destination": c.destination} for c in contracts]