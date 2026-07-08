"""
订单 API 路由。

错误码规范：
  200 - 成功
  400 - 请求参数错误（解析失败、验证失败）
  404 - 订单不存在（仅在明确需要查订单时返回）
  422 - Pydantic 验证错误
  500 - 服务器内部错误

接口列表：
  POST /api/v1/orders/paste              - 解析销售订单表粘贴文本
  POST /api/v1/orders/pi-contract-paste  - 解析PI合同表粘贴文本
  POST /api/v1/orders/merge-preview       - 三源合并预览
  POST /api/v1/orders/ledger             - 写入台账
  GET  /api/v1/orders/ledger/{id}       - 读取单条台账记录
  GET  /api/v1/orders/ledger             - 台账列表
  POST /api/v1/orders                    - 保存订单
  GET  /api/v1/orders/{id}               - 查询单个订单（供后续扩展）
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
from app.api.deps import get_order_service
from app.services.order_service import OrderService
from app.services.ledger_service import LedgerService
from app.schemas.order import (
    PasteParseRequest,
    PasteParseResponse,
    OrderSaveRequest,
    OrderSaveResponse,
)
from app.schemas.ledger import (
    PiContractTableParseRequest,
    MergePreviewRequest,
    MergePreviewResponse,
    LedgerWriteRequest,
    LedgerWriteResponse,
    LedgerRecordResponse,
    LedgerListResponse,
)
from app.schemas.pi_contract import PiContractUploadResponse

router = APIRouter(prefix="/api/v1/orders", tags=["订单管理"])



@router.post(
    "/paste",
    response_model=PasteParseResponse,
    summary="解析粘贴文本",
    description="""
解析用户从 Excel/Spreadsheet 复制的订单数据。

**功能**：
1. 识别分隔符（Tab 或 换行）
2. 按订单号聚合多行（一单多品）
3. 批次内去重（后行覆盖前行）
4. 知识库匹配（H.S.Code + 报关品名）

**请求示例**：
```json
{
  "raw_text": "订单号\\t客户编号\\t内部编号\\t产品中文名\\t规格kg\\t订单量kg\\nHT260304E01\\tTOA-DOVECHEM\\tSILI-001\\t有机硅柔软剂\\t25\\t2400"
}
```

**响应示例**：
```json
{
  "orders": [
    {
      "order_no": "HT260304E01",
      "customer_code": "TOA-DOVECHEM",
      "salesperson": null,
      "items": [
        {
          "internal_code": "SILI-001",
          "product_cn": "有机硅柔软剂",
          "spec_kg": 25.0,
          "quantity_kg": 2400.0,
          "hs_code": null,
          "customs_name": null
        }
      ],
      "header_conflict_warning": null
    }
  ],
  "skipped_rows": [],
  "warning": null
}
```

**错误码**：
- `400`: 无法识别分隔符格式
- `422`: 请求体验证失败
    """,
)
async def parse_paste(
    request: PasteParseRequest,
    service: OrderService = Depends(get_order_service),
):
    if not request.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="粘贴文本不能为空",
        )
    try:
        return service.parse_paste(request.raw_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析失败: {str(e)}",
        )


@router.post(
    "",
    response_model=OrderSaveResponse,
    summary="保存订单",
    description="""
将解析后的订单数据保存到数据库。

**功能**：
- 订单号已存在：覆盖旧数据（删除旧 order_items，插入新的）
- 订单号不存在：新建订单

**事务保证**：orders + order_items 要么全部成功，要么全部回滚。

**请求示例**：
```json
{
  "order": {
    "order_no": "HT260304E01",
    "customer_code": "TOA-DOVECHEM",
    "salesperson": "张三",
    "items": [
      {
        "internal_code": "SILI-001",
        "product_cn": "有机硅柔软剂",
        "spec_kg": 25.0,
        "quantity_kg": 2400.0,
        "unit_price": 29.5,
        "total_amount": 70800.0
      }
    ]
  }
}
```

**响应示例**：
```json
{
  "order_id": 1,
  "items_count": 1,
  "message": "订单 HT260304E01 保存成功，共 1 个产品"
}
```

**错误码**：
- `422`: Pydantic 验证错误（字段类型不匹配、必填字段缺失等）
- `500`: 数据库保存失败（事务回滚）
    """,
)
async def save_order(
    request: OrderSaveRequest,
    service: OrderService = Depends(get_order_service),
):
    try:
        return service.save_order(request.order)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存失败，事务已回滚: {str(e)}",
        )


# ── 台账模式 API（三源合并）─────────────────────────────────────────────

_ledger_svc: Optional[LedgerService] = None


def get_ledger_service() -> LedgerService:
    global _ledger_svc
    if _ledger_svc is None:
        _ledger_svc = LedgerService()
    return _ledger_svc


@router.post(
    "/pi-contract-paste",
    summary="解析 PI 合同表粘贴文本",
    description="解析企业微信在线表格格式的 PI 合同表粘贴数据（15列），返回订单结构",
)
async def parse_pi_contract_table(
    request: PiContractTableParseRequest,
    service: LedgerService = Depends(get_ledger_service),
):
    """解析 PI 合同表粘贴文本"""
    if not request.raw_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="粘贴文本不能为空")
    try:
        orders, skipped, warning = service.parse_pi_contract_table(request.raw_text)
        return PasteParseResponse(orders=orders, skipped_rows=skipped, warning=warning)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"解析失败: {str(e)}")


@router.post(
    "/sales-order-paste",
    summary="解析销售订单表粘贴文本",
    description="解析企业微信在线表格格式的销售订单表粘贴数据（23列），返回订单结构",
)
async def parse_sales_order_table(
    request: PiContractTableParseRequest,
    service: LedgerService = Depends(get_ledger_service),
):
    """解析销售订单表粘贴文本（与 /paste 相同逻辑）"""
    if not request.raw_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="粘贴文本不能为空")
    try:
        orders, skipped, warning = service.parse_sales_order_table(request.raw_text)
        return PasteParseResponse(orders=orders, skipped_rows=skipped, warning=warning)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"解析失败: {str(e)}")


@router.post(
    "/merge-preview",
    response_model=MergePreviewResponse,
    summary="三源合并预览",
    description="""
    接收 PI 合同表文本、销售订单表文本、PI 合同文件，执行三源关联和交叉校验，返回预览结果。

    前端分三次调用各自的解析 API 完成预览，再调用本 API 提交合并。
    """,
)
async def merge_preview(
    pi_contract_table_text: Optional[str] = Form(default=None),
    sales_order_table_text: Optional[str] = Form(default=None),
    pi_file: Optional[UploadFile] = File(default=None),
    service: LedgerService = Depends(get_ledger_service),
):
    """三源合并预览"""
    try:
        pi_file_content = None
        pi_filename = None
        if pi_file:
            pi_file_content = await pi_file.read()
            pi_filename = pi_file.filename

        req = MergePreviewRequest(
            pi_contract_table_text=pi_contract_table_text,
            sales_order_table_text=sales_order_table_text,
            pi_file_content=pi_file_content,
            pi_filename=pi_filename,
        )
        return service.merge_preview(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"合并预览失败: {str(e)}")


@router.post(
    "/ledger",
    response_model=LedgerWriteResponse,
    summary="写入台账",
    description="将三源合并后的完整数据写入台账，每产品一行",
)
async def write_ledger(
    request: LedgerWriteRequest,
    service: LedgerService = Depends(get_ledger_service),
):
    """写入台账"""
    try:
        return service.write_ledger(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"写入台账失败: {str(e)}")


@router.delete(
    "/ledger/{order_no}",
    summary="删除台账记录",
    description="按订单号删除整单台账记录（所有产品行）",
)
async def delete_ledger(
    order_no: str,
    service: LedgerService = Depends(get_ledger_service),
):
    """删除台账记录（按订单号整单删除）"""
    try:
        count = service.delete_ledger(order_no)
        if count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="台账记录不存在")
        return {"deleted": count, "message": f"已删除台账记录 {count} 条"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除失败: {str(e)}")


@router.get(
    "/ledger/{record_id}",
    response_model=LedgerRecordResponse,
    summary="读取台账记录",
    description="按 ID 读取单条台账记录（含所有字段和产品明细）",
)
async def get_ledger_record(
    record_id: int,
    service: LedgerService = Depends(get_ledger_service),
):
    """读取单条台账记录"""
    record = service.get_ledger_record(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="台账记录不存在")
    return record


@router.get(
    "/ledger/by-order/{order_no}",
    response_model=LedgerRecordResponse,
    summary="按订单号读取台账记录",
    description="按订单号读取台账记录（取第一条作为代表）",
)
async def get_ledger_record_by_order_no(
    order_no: str,
    service: LedgerService = Depends(get_ledger_service),
):
    """按订单号读取台账记录"""
    record = service.get_ledger_record_by_order_no(order_no)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="台账记录不存在")
    return record


@router.get(
    "/ledger",
    response_model=LedgerListResponse,
    summary="台账列表",
    description="按时间倒序返回台账记录列表（按订单号分组）",
)
async def list_ledger(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    service: LedgerService = Depends(get_ledger_service),
):
    """台账列表"""
    return service.list_ledger(search=search, page=page, page_size=page_size)