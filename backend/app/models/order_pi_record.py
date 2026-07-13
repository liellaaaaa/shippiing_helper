from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class OrderPiRecord(Base):
    __tablename__ = "order_pi_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), index=True)
    customer_code = Column(String(100))
    customer_name = Column(String(200))
    pi_no = Column(String(100))
    sales_person = Column(String(100))
    order_date = Column(String(20))
    pi_date = Column(String(20))
    delivery_date = Column(String(20))
    internal_code = Column(String(100), index=True)
    product_cn = Column(String(200))
    product_en = Column(String(200))
    spec_kg = Column(Float)
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    product_code = Column(String(20))
    components = Column(String(500))
    product_appearance = Column(String(200))
    customs_match_status = Column(String(20))
    quantity_kg = Column(Float)
    unit_price = Column(Float)
    total_amount = Column(Float)
    order_requirement = Column(Text)
    notes = Column(Text)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id"))
    pallet_spec = Column(String(20))
    drums_per_pallet = Column(Integer)
    drum_count = Column(Integer)
    pallet_count = Column(Integer)
    net_weight_kg = Column(Float)
    gross_weight_kg = Column(Float)
    volume_cbm = Column(Float)
    fits_20gp = Column(String(20))
    packaging_result_json = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- 来自 PI 合同文件 ---
    consignee_name = Column(String(200))
    consignee_address = Column(String(500))
    consignee_tel = Column(String(100))
    destination = Column(String(200))
    loading_port = Column(String(200))
    price_term = Column(String(50))
    payment_terms = Column(String(200))
    bank_info = Column(Text)
    currency = Column(String(10))  # 币制：USD / CNY / RMB 等

    # --- 来自销售订单表 ---
    sales_order_no = Column(String(100))   # 销售订单号（与 PI 号可能不同）
    merchandiser = Column(String(100))      # 跟单员
    shipment_channel = Column(String(50))   # 出货渠道
    shipment_method = Column(String(50))   # 出货方式
    review_status = Column(String(50))     # 审核状态
    spec_abnormal = Column(String(10))      # 规格异常 yes/no
    has_sample = Column(String(10))        # 有无样品 yes/no
    price_adjusted = Column(String(10))    # 是否调价 yes/no
    order_confirmed = Column(String(10))   # 确认下单 yes/no
    production_deadline = Column(String(20))  # 生产交期
    shipment_title = Column(String(200))   # 出货抬头
    document_type = Column(String(50))     # 单据类型

    packaging_type = relationship("PackagingType")
