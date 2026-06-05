"""PI contract API endpoints — upload, save, query."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
from app.schemas.pi_contract import (
    PiContractUploadResponse,
    PiContractSaveRequest,
    PiContractSaveItem,
    PiContractSaveResponse,
    PiContractQueryResponse,
)
from app.core.pi_parser import parse_pi_bytes
from app.services.pi_service import PiService
from app.database import SessionLocal
import io
import os


router = APIRouter(prefix="/api/v1/pi", tags=["PI合同管理"])


@router.post(
    "/upload",
    response_model=PiContractUploadResponse,
    summary="上传并解析PI文件",
    description="""
解析 PI 文件（.xls/.xlsx），提取合同头信息和产品明细。

**功能**：
1. 支持 .xlsx 和 .xls 格式
2. 自动识别中英文表头
3. 提取 PI 号、客户编码、业务员、日期等公共字段
4. 解析每个产品的内部编码、数量、单价、金额等信息

**请求**：multipart/form-data，file 字段

**响应**：
- `pi_no`: PI合同号
- `customer_code`: 客户编码
- `items`: 产品明细列表（含解析状态）
- `confidence`: 字段识别置信度

**错误码**：
- `400`: 不支持的文件格式或文件过大
- `500`: 解析失败
    """,
)
async def upload_pi_file(
    file: UploadFile = File(...),
    customer_code: Optional[str] = None,
):
    """上传并解析 PI 文件 (.xls/.xlsx/.pdf)。"""
    # Validate file type
    allowed_extensions = {".xlsx", ".xls", ".pdf"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 .xls、.xlsx 或 .pdf 文件")

    # Validate file size (10MB max)
    await file.seek(0)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

    try:
        result = parse_pi_bytes(content, file.filename or "unknown.xlsx")
        print(f"[DEBUG] parse_pi_bytes result: pi_no={result.pi_no}, items={len(result.items)}, filename={file.filename}")

        # 自动持久化到 pi_contracts 表
        db = SessionLocal()
        try:
            svc = PiService(db)
            svc.save_contract(PiContractSaveRequest(
                pi_no=result.pi_no,
                customer_code=result.customer_code,
                sales_person=result.sales_person,
                pi_date=result.pi_date,
                consignee_name=result.consignee_name,
                consignee_address=result.consignee_address,
                destination=result.destination,
                items=[PiContractSaveItem(
                    internal_code=item.internal_code,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_amount=item.total_amount,
                    product_color=item.product_color,
                    hs_code=item.hs_code,
                    customs_name=item.customs_name,
                    customs_composition=item.customs_composition,
                    order_customs_name=item.order_customs_name,
                    notes=item.notes,
                ) for item in result.items],
            ))
        finally:
            db.close()

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.post(
    "/contracts",
    response_model=PiContractSaveResponse,
    summary="保存PI合同",
    description="""
将解析后的 PI 合同数据保存到数据库。

**功能**：
- 更新或插入 pi_data 表（PI摘要）
- 更新或插入 pi_contracts 表（合同明细）
- 关联现有订单（如 order_id 提供）

**请求示例**：
```json
{
  "pi_no": "PI20260315",
  "customer_code": "TOA-DOVECHEM",
  "sales_person": "张三",
  "pi_date": "2026-03-15",
  "order_id": 1,
  "items": [
    {
      "internal_code": "SILI-001",
      "quantity": 2400,
      "unit_price": 29.5,
      "total_amount": 70800
    }
  ]
}
```

**响应**：
- `contract_id`: 合同记录ID
- `items_count`: 产品明细条数
- `pi_data_updated`: pi_data 更新条数

**错误码**：
- `500`: 保存失败
    """,
)
async def save_pi_contract(
    request: PiContractSaveRequest,
):
    """保存 PI 合同到数据库。"""
    # BB-4: Full PiService implementation needed
    raise HTTPException(
        status_code=501,
        detail="PI合同保存功能等待 BB-4 服务层实现",
    )


@router.get(
    "/contracts",
    response_model=PiContractQueryResponse,
    summary="查询PI合同",
    description="""
查询历史 PI 合同记录，支持多条件筛选。

**筛选参数**（可选）：
- `pi_no`: PI合同号
- `customer_code`: 客户编码
- `internal_code`: 内部编码

**响应**：
```json
{
  "contracts": [
    {
      "id": 1,
      "pi_no": "PI20260315",
      "customer_code": "TOA-DOVECHEM",
      "sales_person": "张三",
      "pi_date": "2026-03-15",
      "items": [...]
    }
  ]
}
```
    """,
)
async def query_pi_contracts(
    pi_no: Optional[str] = None,
    customer_code: Optional[str] = None,
    internal_code: Optional[str] = None,
):
    """查询历史 PI 合同。"""
    # BB-4: Full PiService implementation needed
    raise HTTPException(
        status_code=501,
        detail="PI合同查询功能等待 BB-4 服务层实现",
    )