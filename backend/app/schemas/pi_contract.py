from pydantic import BaseModel
from typing import Optional


class PiContractItemRow(BaseModel):
    """PI合同明细行（上传响应用）"""
    row_index: int
    status: str  # "success" or "error"
    error_msg: Optional[str] = None
    internal_code: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    product_color: Optional[str] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_composition: Optional[str] = None
    order_customs_name: Optional[str] = None
    notes: Optional[str] = None
    _missing_fields: list[str] = []

    class Config:
        from_attributes = True


class ConfidenceInfo(BaseModel):
    """解析置信度信息"""
    recognized: int
    total: int
    percentage: str  # e.g. "83%"
    failed_rows: int


class PiContractUploadResponse(BaseModel):
    """PI合同上传响应"""
    pi_no: str
    customer_code: Optional[str] = None
    sales_person: Optional[str] = None
    pi_date: Optional[str] = None
    is_ordered: str = "0"
    # PI Header 信息
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    consignee_tel: Optional[str] = None
    destination: Optional[str] = None
    loading_port: Optional[str] = None # 装货地
    price_term: Optional[str] = None          # 价格条款 (FOB/C&F/CIF等)
    payment_terms: Optional[str] = None       # 付款方式
    invoice_to: Optional[str] = None          # 发票抬头
    items: list[PiContractItemRow] = []
    confidence: ConfidenceInfo

    class Config:
        from_attributes = True


class PiContractSaveItem(BaseModel):
    """PI合同保存明细项"""
    internal_code: Optional[str] = None  # Proforma格式可能为空
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    product_color: Optional[str] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_composition: Optional[str] = None
    order_customs_name: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PiContractSaveRequest(BaseModel):
    """PI合同保存请求"""
    pi_no: str
    customer_code: Optional[str] = None
    sales_person: Optional[str] = None
    pi_date: Optional[str] = None
    is_ordered: str = "0"
    order_id: Optional[int] = None
    # PI Header 信息
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    consignee_tel: Optional[str] = None
    destination: Optional[str] = None
    loading_port: Optional[str] = None # 装货地
    price_term: Optional[str] = None          # 价格条款 (FOB/C&F/CIF等)
    invoice_to: Optional[str] = None          # 发票抬头
    items: list[PiContractSaveItem] = []

    class Config:
        from_attributes = True


class PiContractSaveResponse(BaseModel):
    """PI合同保存响应"""
    contract_id: int
    items_count: int
    pi_data_updated: int
    message: str


class PiContractQueryResponse(BaseModel):
    """PI合同查询响应"""
    contracts: list[dict]