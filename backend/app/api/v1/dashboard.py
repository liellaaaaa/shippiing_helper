"""FR-5.x 数据看板 API — 合并数据查询与导出，以及 Phase 1 落库"""

import io
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from app.services.export_service import ExportService
from app.services.save_service import SaveService
from app.api.deps import get_save_service
from app.schemas.order_pi_record import (
    SaveRecordRequest,
    SaveRecordResponse,
    OrderPiRecordResponse,
    RecordListResponse,
)


router = APIRouter(prefix="/api/v1/dashboard", tags=["数据看板"])


@router.get("/orders")
async def get_dashboard_orders(
    search: Optional[str] = Query(None, description="模糊搜索：订单号 / 客户编码 / PI号"),
    status: Optional[str] = Query(None, description="状态筛选：pending / confirmed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    save_service: SaveService = Depends(get_save_service),
):
    """
    获取数据看板合并数据（支持分页和筛选）。

    直接查询 order_pi_records 表（落库合并数据），返回格式与旧接口兼容。
    diff_status 统一为 "一致"（落库数据已是合并结果，无差异），
    association_status 统一为 "full"（落库即已确认关联）。
    """
    result = save_service.query_records(
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )

    # 字段映射为旧 DashboardOrder 格式
    rows = []
    for r in result.records:
        rows.append({
            "order_id": r.id,
            "order_no": r.order_no or "",
            "customer_code": r.customer_code or "",
            "salesperson": r.sales_person or "",
            "internal_code": r.internal_code or "",
            "product_cn": r.product_cn or "",
            "order_quantity": r.quantity_kg,
            "order_unit_price": None,
            "order_total": None,
            "pi_quantity": None,
            "pi_unit_price": None,
            "pi_total": None,
            "association_status": "full",
            "diff_status": "一致",
        })

    return {
        "orders": rows,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.get("/export")
async def export_dashboard_excel(
    search: Optional[str] = Query(None, description="模糊搜索"),
    status: Optional[str] = Query(None, description="状态筛选：pending / confirmed"),
    save_service: SaveService = Depends(get_save_service),
):
    """
    导出数据看板 Excel 文件。

    - 直接从 order_pi_records 表导出全部数据
    - 包含表头样式（加粗、背景色）和边框
    """
    export_service = ExportService()

    # 获取全部数据（不分页，page_size=10000）
    result = save_service.query_records(
        status=status,
        search=search,
        page=1,
        page_size=10000,
    )

    # 字段映射
    rows = []
    for r in result.records:
        rows.append({
            "order_no": r.order_no or "",
            "customer_code": r.customer_code or "",
            "salesperson": r.sales_person or "",
            "internal_code": r.internal_code or "",
            "product_cn": r.product_cn or "",
            "order_quantity": r.quantity_kg or "",
            "pi_quantity": "",
            "diff_status": "一致",
            "association_status": "已关联",
        })

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