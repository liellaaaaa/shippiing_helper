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
    order_requirement: Optional[str] = None   # 订单要求（含包装指令）
    order_date: Optional[str] = None          # 交货日期
    order_date_placed: Optional[str] = None  # 下单日期
    production_deadline: Optional[str] = None # 生产交期
    shipment_method: Optional[str] = None    # 出货方式
    shipment_channel: Optional[str] = None   # 出货渠道
    salesperson: Optional[str] = None        # 业务员（产品行级别）
    merchandiser: Optional[str] = None     # 跟单员
    price_adjusted: Optional[str] = None    # 是否调价
    has_sample: Optional[str] = None        # 有无样品
    order_confirmed: Optional[str] = None  # 确认下单
    spec_abnormal: Optional[str] = None    # 规格异常
    shipment_title: Optional[str] = None   # 出货抬头
    document_type: Optional[str] = None    # 单据类型
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
    # 报关品名匹配状态（解析时注入）
    product_code: Optional[str] = None
    product_appearance: Optional[str] = None
    customs_match_status: Optional[str] = None  # matched / conflict / filled / not_found
    conflict_customs_name: Optional[str] = None  # 仅 conflict 时有
    conflict_hs_code: Optional[str] = None  # 仅 hs_code 冲突时有
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