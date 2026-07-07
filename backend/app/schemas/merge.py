"""合并查询的 Pydantic schemas — FR-3.x 数据关联模块"""

from pydantic import BaseModel
from typing import Optional


class OrderListItem(BaseModel):
    """订单列表项（聚合视图）"""
    id: int
    order_no: str
    customer_code: Optional[str] = None
    salesperson: Optional[str] = None
    total_amount: Optional[float] = None
    association_status: str  # "full" / "partial" / "none"
    items_count: int         # 订单产品总数
    linked_count: int         # 已关联 PI 的数量
    pi_no: Optional[str] = None  # 该订单关联的第一个 PI 号
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """订单列表响应（含分页）"""
    orders: list[OrderListItem]
    total: int
    page: int
    page_size: int


class OrderItemData(BaseModel):
    """订单产品数据"""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_ingredients: Optional[str] = None
    gross_weight: Optional[float] = None
    volume: Optional[float] = None
    product_en: Optional[str] = None
    appearance: Optional[str] = None


class PiItemData(BaseModel):
    """PI 产品数据"""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    consignee: Optional[str] = None
    port: Optional[str] = None


class DiffInfo(BaseModel):
    """差异信息"""
    status: str  # "一致" / "数量不符" / "单价不符" / "金额不符" / "HS不符" / "PI未覆盖" / "订单无记录"
    flags: list[str] = []  # 如 ["quantity", "unit_price"]
    order_value: Optional[float] = None  # 仅当数值差异时填充
    pi_value: Optional[float] = None     # 仅当数值差异时填充


class ComparisonItem(BaseModel):
    """比对明细行"""
    id: int
    internal_code: str
    product_cn: Optional[str] = None
    order: Optional[OrderItemData] = None
    pi: Optional[PiItemData] = None
    diff: DiffInfo

    class Config:
        from_attributes = True


class OrderComparisonResponse(BaseModel):
    """订单比对数据响应"""
    order_id: int
    order_no: str
    customer_code: Optional[str] = None
    pi_no: Optional[str] = None  # 该订单关联的 PI 号
    # 包装计算数据
    drum_count: Optional[int] = None
    pallet_count: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    fits_20gp: Optional[str] = None
    items: list[ComparisonItem]


class MergeQueryParams(BaseModel):
    """查询参数（用于 FastAPI Query）"""
    tab: str = "pending"  # "pending" / "completed" / "all"
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20