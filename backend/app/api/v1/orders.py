"""
订单 API 路由。

错误码规范：
  200 - 成功
  400 - 请求参数错误（解析失败、验证失败）
  404 - 订单不存在（仅在明确需要查订单时返回）
  422 - Pydantic 验证错误
  500 - 服务器内部错误

接口列表：
  POST /api/v1/orders/paste  - 解析粘贴文本
  POST /api/v1/orders        - 保存订单
  GET  /api/v1/orders/{id}  - 查询单个订单（供后续扩展）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_order_service
from app.services.order_service import OrderService
from app.schemas.order import (
    PasteParseRequest,
    PasteParseResponse,
    OrderSaveRequest,
    OrderSaveResponse,
)

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