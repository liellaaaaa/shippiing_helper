"""FR-5.x 数据看板 API — 合并数据查询与导出，以及 Phase 1 落库"""

import io
import json
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from app.services.export_service import ExportService
from app.services.merge_service import MergeService
from app.services.save_service import SaveService
from app.api.deps import get_merge_service, get_save_service
from app.schemas.order_pi_record import (
    SaveRecordRequest,
    SaveRecordResponse,
    OrderPiRecordResponse,
    RecordListResponse,
)


router = APIRouter(prefix="/api/v1/dashboard", tags=["数据看板"])


@router.get("/orders")
async def get_dashboard_orders(
    search: Optional[str] = Query(None, description="模糊搜索：订单号 / 客户编码"),
    status: Optional[str] = Query(None, description="关联状态筛选，逗号分隔：full,partial,none"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    获取数据看板合并数据（支持分页和筛选）。

    - search：支持订单号、客户编码模糊匹配
    - status：关联状态筛选，支持多选（如 'partial,none'）
    - 默认按关联状态降序排列（问题数据置顶）
    """
    # 获取订单列表（不限状态，获取全部用于导出）
    all_orders = merge_service.get_order_list(tab="all", search=search, page=1, page_size=10000)

    # 状态筛选
    if status:
        status_list = [s.strip() for s in status.split(",")]
        filtered_orders = [
            o for o in all_orders.orders
            if o.association_status in status_list
        ]
    else:
        filtered_orders = all_orders.orders

    # 按关联状态降序排列（none > partial > full）
    status_order = {"none": 0, "partial": 1, "full": 2}
    filtered_orders.sort(key=lambda x: status_order.get(x.association_status, 2))

    # 分页
    total = len(filtered_orders)
    start = (page - 1) * page_size
    end = start + page_size
    page_orders = filtered_orders[start:end]

    # 聚合每个订单的 items
    rows = []
    for order in page_orders:
        comparison = merge_service.get_order_comparison(order.id)
        if not comparison:
            continue
        for item in comparison.items:
            rows.append({
                "order_id": order.id,
                "order_no": order.order_no,
                "customer_code": order.customer_code,
                "salesperson": order.salesperson,
                "internal_code": item.internal_code,
                "product_cn": item.product_cn or "",
                "order_quantity": item.order.quantity if item.order else None,
                "order_unit_price": item.order.unit_price if item.order else None,
                "order_total": item.order.total_amount if item.order else None,
                "pi_quantity": item.pi.quantity if item.pi else None,
                "pi_unit_price": item.pi.unit_price if item.pi else None,
                "pi_total": item.pi.total_amount if item.pi else None,
                "association_status": order.association_status,
                "diff_status": item.diff.status,
            })

    return {
        "orders": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export")
async def export_dashboard_excel(
    search: Optional[str] = Query(None, description="模糊搜索"),
    status: Optional[str] = Query(None, description="关联状态筛选"),
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    导出数据看板 Excel 文件。

    - 不分页，按关联状态降序导出全部数据
    - 包含表头样式（加粗、背景色）和边框
    """
    export_service = ExportService()

    # 获取全部数据
    all_orders = merge_service.get_order_list(tab="all", search=search, page=1, page_size=10000)

    # 状态筛选
    if status:
        status_list = [s.strip() for s in status.split(",")]
        filtered_orders = [
            o for o in all_orders.orders
            if o.association_status in status_list
        ]
    else:
        filtered_orders = all_orders.orders

    # 按关联状态降序排列
    status_order = {"none": 0, "partial": 1, "full": 2}
    filtered_orders.sort(key=lambda x: status_order.get(x.association_status, 2))

    # 聚合 items
    rows = []
    for order in filtered_orders:
        comparison = merge_service.get_order_comparison(order.id)
        if not comparison:
            continue
        for item in comparison.items:
            rows.append({
                "order_no": order.order_no,
                "customer_code": order.customer_code or "",
                "salesperson": order.salesperson or "",
                "internal_code": item.internal_code,
                "product_cn": item.product_cn or "",
                "order_quantity": item.order.quantity if item.order else "",
                "pi_quantity": item.pi.quantity if item.pi else "",
                "diff_status": item.diff.status,
                "association_status": order.association_status,
            })

    # 生成 Excel
    excel_bytes = export_service.generate_excel_bytes(rows)
    filename = export_service.generate_filename()

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.post("/records", response_model=SaveRecordResponse, summary="落库 — 双轨合并数据写入")
async def save_order_pi_record(
    request: SaveRecordRequest,
    save_service: SaveService = Depends(get_save_service),
):
    """
    Phase 1 核心落库接口。

    接收订单数据 + PI数据 + 包装计算结果，合并后写入 order_pi_records 表。

    轨道A合并逻辑：以 internal_code 为锚点，PI数据覆盖订单中的同名字段
    轨道B挂载：直接将包装计算结果挂到同一条记录

    **请求体**：
    - order_data: 订单解析数据（来自外贸销售订单表粘贴/上传）
    - pi_data: PI合同数据（来自PI文件上传），可选
    - packaging_result: 包装计算结果（来自包装计算模块），可选

    **响应**：
    - record_id: 落库记录ID
    - status: "confirmed"
    - message: 成功/失败描述
    """
    try:
        record_id = save_service.save_record(request)
        return SaveRecordResponse(
            record_id=record_id,
            status="confirmed",
            message="数据已成功落库",
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records", response_model=RecordListResponse, summary="查询落库记录")
async def query_order_pi_records(
    status: Optional[str] = Query(None, description="状态筛选：pending / confirmed"),
    search: Optional[str] = Query(None, description="模糊搜索：订单号 / 客户编码 / PI号"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    save_service: SaveService = Depends(get_save_service),
):
    """
    查询已落库的订单PI记录。

    支持：
    - status 筛选（pending 待确认 / confirmed 已确认）
    - 模糊搜索（订单号、客户编码、PI号）
    - 分页
    """
    result = save_service.query_records(
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/records/{record_id}", response_model=OrderPiRecordResponse, summary="查询单条落库记录")
async def get_order_pi_record(
    record_id: int,
    save_service: SaveService = Depends(get_save_service),
):
    """根据 ID 查询单条落库记录。"""
    record = save_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record