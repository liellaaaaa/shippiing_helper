from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PackagingResult(BaseModel):
    packaging_type: str
    pallet_spec: Optional[str] = None
    drums: int
    pallets: int
    drums_per_pallet: int
    net_weight_kg: float
    gross_weight_kg: float
    volume_cbm: float
    fits_20gp: str
    load_rate: Optional[float] = None
    packing_scheme: Optional[str] = None
    no_pallet: bool = False


class OrderDataItem(BaseModel):
    """单个产品的订单数据"""
    internal_code: str
    product_cn: Optional[str] = None
    product_en: Optional[str] = None
    spec_kg: Optional[float] = None
    quantity_kg: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    order_requirement: Optional[str] = None
    notes: Optional[str] = None


class OrderData(BaseModel):
    """订单头数据 + 多产品明细"""
    order_no: str
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    sales_person: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    items: list[OrderDataItem] = []  # 多产品支持


class PiData(BaseModel):
    pi_no: str
    customer_code: Optional[str] = None
    pi_date: Optional[str] = None
    internal_code: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None


class SaveRecordRequest(BaseModel):
    order_data: OrderData
    pi_data: Optional[PiData] = None
    packaging_result: Optional[PackagingResult] = None


class SaveRecordResponse(BaseModel):
    record_id: int
    status: str
    message: str


class OrderPiRecordResponse(BaseModel):
    id: int
    order_no: Optional[str]
    customer_code: Optional[str]
    customer_name: Optional[str]
    pi_no: Optional[str]
    sales_person: Optional[str]
    order_date: Optional[str]
    pi_date: Optional[str]
    delivery_date: Optional[str]
    internal_code: Optional[str]
    product_cn: Optional[str]
    product_en: Optional[str]
    spec_kg: Optional[float]
    hs_code: Optional[str]
    customs_name: Optional[str]
    quantity_kg: Optional[float]
    unit_price: Optional[float]
    total_amount: Optional[float]
    order_requirement: Optional[str]
    notes: Optional[str]
    packaging_type_id: Optional[int]
    pallet_spec: Optional[str]
    drums_per_pallet: Optional[int]
    drum_count: Optional[int]
    pallet_count: Optional[int]
    net_weight_kg: Optional[float]
    gross_weight_kg: Optional[float]
    volume_cbm: Optional[float]
    fits_20gp: Optional[str]
    packaging_result_json: Optional[str]
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecordListResponse(BaseModel):
    records: list[OrderPiRecordResponse]
    total: int
    page: int
    page_size: int


class ProductPackagingItem(BaseModel):
    """单个产品的包装计算结果（用于多产品汇总）"""
    product_name: str
    packaging_name: str
    specification_kg: float
    drums: int
    drums_per_pallet: int
    pallets: int
    pallet_spec: str
    net_weight_kg: float
    gross_weight_kg: float
    volume_cbm: float


class PalletDetailItem(BaseModel):
    """按卡板尺寸分组的详情"""
    pallet_spec: str
    pallet_count: int
    drums_on_pallets: int
    volume_cbm: float
    weight_kg: float


class OrderPackagingResultSchema(BaseModel):
    """订单级别包装汇总结果"""
    total_drums: int
    total_pallets: int
    total_volume_cbm: float
    total_weight_kg: float
    total_net_weight_kg: float
    pallet_details: list[PalletDetailItem]
    product_details: list[ProductPackagingItem]
    container_20gp_fit: bool
    container_40hq_fit: bool
    recommended: str
    load_rate_20gp: float
    load_rate_40hq: float