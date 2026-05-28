from pydantic import BaseModel
from typing import Optional


class OrderItemSchema(BaseModel):
    """产品明细 schema"""
    internal_code: str  # 产品级，必填
    product_cn: Optional[str] = None
    product_en: Optional[str] = None
    spec_kg: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_ingredients: Optional[str] = None
    quantity_kg: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    packaging_type_id: Optional[int] = None
    pallet_spec: Optional[str] = None
    drums_per_pallet: Optional[int] = None
    drum_count: Optional[int] = None
    pallet_count: Optional[int] = None
    net_weight_kg: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    hs_code_warning: Optional[str] = None   # H.S.Code 位数不足警告
    warning: Optional[str] = None            # 报关品名自动生成警告
    # 前端用：_selected 跟踪复选框状态（不出现在请求体中）
    _selected: Optional[bool] = None

    class Config:
        from_attributes = True


class ParsedOrderSchema(BaseModel):
    """解析后的订单 schema"""
    order_no: str
    customer_code: Optional[str] = None
    salesperson: Optional[str] = None
    items: list[OrderItemSchema] = []
    header_conflict_warning: Optional[str] = None  # 订单头字段冲突警告

    class Config:
        from_attributes = True


class PasteParseRequest(BaseModel):
    """粘贴解析请求"""
    raw_text: str  # 用户粘贴的原始文本


class SkippedRowSchema(BaseModel):
    """跳行（解析失败的行）"""
    line_index: int
    reason: str
    raw_data: list[str]


class PasteParseResponse(BaseModel):
    """粘贴解析响应"""
    orders: list[ParsedOrderSchema]
    skipped_rows: list[SkippedRowSchema]
    warning: Optional[str] = None  # 批次内重复等警告


class OrderSaveRequest(BaseModel):
    """保存订单请求"""
    order: ParsedOrderSchema


class OrderSaveResponse(BaseModel):
    """保存订单响应"""
    order_id: int
    items_count: int
    message: str