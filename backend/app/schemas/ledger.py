"""台账（Ledger）相关 Pydantic Schemas — 三源合并后的完整记录结构"""

from pydantic import BaseModel
from typing import Optional


class LedgerItemSchema(BaseModel):
    """台账产品明细"""
    internal_code: str
    product_cn: Optional[str] = None
    product_en: Optional[str] = None
    spec_kg: Optional[float] = None
    quantity_kg: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_ingredients: Optional[str] = None
    product_appearance: Optional[str] = None
    # 包装
    packaging_name: Optional[str] = None
    packaging_type_id: Optional[int] = None
    pallet_spec: Optional[str] = None
    drums_per_pallet: Optional[int] = None
    drum_count: Optional[int] = None
    pallet_count: Optional[int] = None
    net_weight_kg: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    fits_20gp: Optional[str] = None

    class Config:
        from_attributes = True


class LedgerRecordSchema(BaseModel):
    """台账完整记录（三源合并后）"""
    # --- 来自 PI 合同表 ---
    pi_contract_table_order_no: str = ""   # PI号/订单号
    customer_code: Optional[str] = None
    sales_person: Optional[str] = None
    pi_date: Optional[str] = None
    # 产品级
    items: list[LedgerItemSchema] = []

    # --- 来自销售订单表 ---
    sales_order_no: Optional[str] = None  # 订单号（可能与PI号不同）
    merchandiser: Optional[str] = None   # 跟单员
    order_date: Optional[str] = None     # 下单日期
    delivery_date: Optional[str] = None   # 交货日期
    shipment_channel: Optional[str] = None  # 出货渠道
    shipment_method: Optional[str] = None  # 出货方式
    review_status: Optional[str] = None   # 审核状态
    spec_abnormal: Optional[str] = None   # 规格异常
    has_sample: Optional[str] = None       # 有无样品
    price_adjusted: Optional[str] = None  # 是否调价
    order_confirmed: Optional[str] = None  # 确认下单
    production_deadline: Optional[str] = None  # 生产交期
    shipment_title: Optional[str] = None  # 出货抬头
    document_type: Optional[str] = None   # 单据类型

    # --- 来自 PI 合同文件 ---
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    consignee_tel: Optional[str] = None
    destination: Optional[str] = None    # 目的港
    loading_port: Optional[str] = None  # 装货港
    price_term: Optional[str] = None    # 价格条款
    payment_terms: Optional[str] = None  # 付款方式
    bank_info: Optional[str] = None     # 银行信息
    currency: Optional[str] = None      # 币制：USD / CNY / RMB

    class Config:
        from_attributes = True


# ── 解析请求/响应 ────────────────────────────────────────────


class PiContractTableParseRequest(BaseModel):
    """PI合同表粘贴解析请求"""
    raw_text: str


class SalesOrderTableParseRequest(BaseModel):
    """销售订单表粘贴解析请求（与现有 paste 相同结构）"""
    raw_text: str


class MergePreviewRequest(BaseModel):
    """三源合并预览请求"""
    pi_contract_table_text: Optional[str] = None   # PI合同表粘贴文本
    sales_order_table_text: Optional[str] = None   # 销售订单表粘贴文本
    pi_file_content: Optional[bytes] = None        # PI合同文件(.xls/.xlsx)二进制
    pi_filename: Optional[str] = None             # 文件名（含扩展名）


class ValidationWarning(BaseModel):
    """单条校验警告"""
    internal_code: str
    field: str
    pi_contract_value: Optional[str | float] = None
    pi_file_value: Optional[str | float] = None
    sales_order_value: Optional[str | float] = None
    message: str


class MergePreviewItem(BaseModel):
    """合并预览中的单个产品"""
    internal_code: str
    # 来源标记
    source_pi_contract: bool = False
    source_sales_order: bool = False
    source_pi_file: bool = False
    source_note: Optional[str] = None  # 来源说明：如 "仅PI合同表"、"仅销售订单表"、"匹配"
    # 合并后的字段
    product_cn: Optional[str] = None
    spec_kg: Optional[float] = None
    quantity_kg: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_ingredients: Optional[str] = None
    product_appearance: Optional[str] = None
    # 校验状态
    validation_status: str = "ok"  # ok | warning | error
    warnings: list[ValidationWarning] = []


class MergePreviewResponse(BaseModel):
    """三源合并预览响应"""
    # 订单级别信息（来自各源）
    order_no: str                                 # PI合同表为主
    customer_code: Optional[str] = None
    sales_person: Optional[str] = None
    pi_date: Optional[str] = None
    # PI合同表提取的头部信息
    pi_contract_shipment_title: Optional[str] = None   # 出货抬头/公司抬头（来自PI合同表）
    pi_contract_shipment_method: Optional[str] = None  # 运输方式（来自PI合同表）
    # 销售订单表提取的头部信息
    sales_order_no: Optional[str] = None         # PI号（销售订单表中的订单号，用于交叉对照）
    shipment_title: Optional[str] = None         # 出货抬头（来自销售订单表）
    merchandiser: Optional[str] = None
    delivery_date: Optional[str] = None
    shipment_method: Optional[str] = None        # 运输方式（来自销售订单表）
    # PI合同文件提取的头部信息
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    consignee_tel: Optional[str] = None
    destination: Optional[str] = None
    loading_port: Optional[str] = None
    price_term: Optional[str] = None
    payment_terms: Optional[str] = None
    bank_info: Optional[str] = None
    currency: Optional[str] = None      # 币制：USD / CNY / RMB
    # 合并后的产品列表
    items: list[MergePreviewItem] = []
    # 产品匹配统计
    total_products: int = 0          # 总产品数（去重后）
    matched_count: int = 0           # 两源匹配的产品数
    pi_only_count: int = 0           # 仅PI合同表的产品数
    sales_only_count: int = 0        # 仅销售订单表的产品数
    # 整体校验状态
    validation_status: str = "ok"  # ok | warning | error
    validation_warnings: list[ValidationWarning] = []
    # 各源解析错误提示（供前端展示）
    pi_file_parse_error: Optional[str] = None   # PI合同文件解析失败原因
    pi_contract_table_parse_error: Optional[str] = None
    sales_order_table_parse_error: Optional[str] = None
    # 各源独立解析结果（用于前端显示）
    pi_contract_table_parsed: Optional[dict] = None
    sales_order_table_parsed: Optional[dict] = None
    pi_file_parsed: Optional[dict] = None


# ── 台账读写 ────────────────────────────────────────────────


class LedgerWriteRequest(BaseModel):
    """写入台账请求"""
    order_no: str
    customer_code: Optional[str] = None
    sales_person: Optional[str] = None
    pi_date: Optional[str] = None
    # 销售订单补充字段
    sales_order_no: Optional[str] = None
    merchandiser: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    shipment_channel: Optional[str] = None
    shipment_method: Optional[str] = None
    review_status: Optional[str] = None
    spec_abnormal: Optional[str] = None
    has_sample: Optional[str] = None
    price_adjusted: Optional[str] = None
    order_confirmed: Optional[str] = None
    production_deadline: Optional[str] = None
    shipment_title: Optional[str] = None
    document_type: Optional[str] = None
    # PI合同文件补充字段
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    consignee_tel: Optional[str] = None
    destination: Optional[str] = None
    loading_port: Optional[str] = None
    price_term: Optional[str] = None
    payment_terms: Optional[str] = None
    bank_info: Optional[str] = None
    currency: Optional[str] = None      # 币制：USD / CNY / RMB
    # 产品明细
    items: list[LedgerItemSchema] = []


class LedgerWriteResponse(BaseModel):
    """写入台账响应"""
    record_id: int
    items_count: int
    message: str


class LedgerRecordResponse(BaseModel):
    """读取单条台账记录"""
    id: int
    order_no: str
    customer_code: Optional[str] = None
    sales_person: Optional[str] = None
    pi_no: Optional[str] = None
    pi_date: Optional[str] = None
    sales_order_no: Optional[str] = None
    merchandiser: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    shipment_channel: Optional[str] = None
    shipment_method: Optional[str] = None
    review_status: Optional[str] = None
    spec_abnormal: Optional[str] = None
    has_sample: Optional[str] = None
    price_adjusted: Optional[str] = None
    order_confirmed: Optional[str] = None
    production_deadline: Optional[str] = None
    shipment_title: Optional[str] = None
    document_type: Optional[str] = None
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    consignee_tel: Optional[str] = None
    destination: Optional[str] = None
    loading_port: Optional[str] = None
    price_term: Optional[str] = None
    payment_terms: Optional[str] = None
    bank_info: Optional[str] = None
    currency: Optional[str] = None      # 币制：USD / CNY / RMB
    items: list[LedgerItemSchema] = []
    status: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class LedgerListResponse(BaseModel):
    """台账列表响应"""
    records: list[LedgerRecordResponse]
    total: int


# ── 判重 ────────────────────────────────────────────────


class DuplicateCheckRequest(BaseModel):
    """判重请求"""
    items: list[LedgerItemSchema]


class DuplicateItem(BaseModel):
    """单条重复产品"""
    internal_code: str
    customs_name: Optional[str] = None
    hs_code: Optional[str] = None
    components: Optional[str] = None
    product_appearance: Optional[str] = None
    existing_order_no: str
    existing_record_id: int


class DuplicateCheckResponse(BaseModel):
    """判重响应"""
    has_duplicates: bool
    duplicates: list[DuplicateItem] = []
    total_checked: int
    total_duplicates: int
