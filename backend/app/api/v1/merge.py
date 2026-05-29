"""FR-3.x 数据关联 API — 合并查询端点（只读）"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
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