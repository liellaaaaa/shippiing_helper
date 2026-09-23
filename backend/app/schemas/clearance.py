"""清关文件生成入参"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ClearanceOverrides(BaseModel):
    """人工/订舱/货代覆盖值；None 表示不覆盖"""
    container_no: Optional[str] = None
    seal_no: Optional[str] = None
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    bl_no: Optional[str] = None
    carrier_code: Optional[str] = None
    dest_agent_name: Optional[str] = None
    dest_agent_addr: Optional[str] = None
    dest_agent_tax: Optional[str] = None
    dest_agent_tel: Optional[str] = None
    measure_cbm: Optional[float] = None
    gross_kg: Optional[float] = None
    net_kg: Optional[float] = None
    packages: Optional[int] = None
    pallets: Optional[int] = None
    batch_no: Optional[str] = None
    prod_date: Optional[str] = None
    exp_date: Optional[str] = None
    coa_pi_no: Optional[str] = None
    invoice_date: Optional[str] = None
    expiry_rule: Optional[str] = None
    show_bank_block: Optional[bool] = None
    show_po: Optional[bool] = None
    po_no: Optional[str] = None
    dest_style: Optional[Literal["port", "country", "custom"]] = None
    ph_label: Optional[str] = None
    solid_label: Optional[str] = None
    appearance_spec: Optional[str] = None
    appearance_result: Optional[str] = None
    ph_spec: Optional[str] = None
    ph_result: Optional[str] = None
    solid_spec: Optional[str] = None
    solid_result: Optional[str] = None

    class Config:
        extra = "ignore"


class ClearanceGenerateRequest(BaseModel):
    ledger_record_id: int
    order_id: Optional[int] = None
    customer_code: Optional[str] = None
    company_code: Optional[str] = "honghao"
    transport_mode: Optional[Literal["FCL", "LCL"]] = "FCL"
    overrides: ClearanceOverrides = Field(default_factory=ClearanceOverrides)

    class Config:
        extra = "ignore"
