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
    items: list[PiContractItemRow] = []
    confidence: ConfidenceInfo

    class Config:
        from_attributes = True


class PiContractSaveItem(BaseModel):
    """PI合同保存明细项"""
    internal_code: str  # required
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