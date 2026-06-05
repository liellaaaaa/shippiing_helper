"""Phase 1 落库服务 — 双轨数据合并写入 order_pi_records 表"""

import json
from typing import Optional
from app.database import SessionLocal
from app.models.order_pi_record import OrderPiRecord
from app.schemas.order_pi_record import (
    SaveRecordRequest,
    OrderPiRecordResponse,
    RecordListResponse,
)


class SaveService:
    """落库服务 — 将订单+PI+包装计算结果写入数据库"""

    def __init__(self, db_session):
        self.db = db_session

    def save_record(self, request: SaveRecordRequest) -> int:
        """
        执行落库：支持多产品 — 每个产品单独一条 record。

        合并规则（报关品名/H.S.Code 优先级）：
        - 报关品名: order > pi > knowledge
        - H.S.Code: pi > order

        数据来源：
        - order_data: 外贸销售订单表（粘贴/上传），含多产品 items
        - pi_data: PI合同文件（上传解析）
        - packaging_result: 包装计算模块输出（订单级别汇总）
        """
        order_d = request.order_data
        pi_d = request.pi_data
        pkg = request.packaging_result

        # ── 公共字段（订单头） ──
        order_no = order_d.order_no
        customer_code = order_d.customer_code or (pi_d.customer_code if pi_d else None)
        customer_name = order_d.customer_name
        sales_person = order_d.sales_person
        order_date = order_d.order_date
        delivery_date = order_d.delivery_date
        order_requirement = order_d.order_requirement
        notes = order_d.notes

        # 包装计算结果（轨道B）- 订单级别汇总
        packaging_json = None
        if pkg:
            packaging_json = json.dumps({
                "packaging_type": pkg.packaging_type,
                "pallet_spec": pkg.pallet_spec,
                "drums": pkg.drums,
                "pallets": pkg.pallets,
                "drums_per_pallet": pkg.drums_per_pallet,
                "net_weight_kg": pkg.net_weight_kg,
                "gross_weight_kg": pkg.gross_weight_kg,
                "volume_cbm": pkg.volume_cbm,
                "fits_20gp": pkg.fits_20gp,
                "load_rate": pkg.load_rate,
                "packing_scheme": pkg.packing_scheme,
                "no_pallet": pkg.no_pallet,
            }, ensure_ascii=False)

        # ── 遍历每个产品，创建独立的 record ──
        first_record_id = None
        from app.models.order import PackagingType

        for i, item in enumerate(order_d.items):
            record = OrderPiRecord()

            # 订单头字段
            record.order_no = order_no
            record.customer_code = customer_code
            record.customer_name = customer_name
            record.sales_person = sales_person
            record.order_date = order_date
            record.delivery_date = delivery_date
            record.order_requirement = order_requirement
            record.notes = notes

            # ── 产品明细 ──
            record.internal_code = item.internal_code
            record.product_cn = item.product_cn
            record.product_en = item.product_en
            record.spec_kg = item.spec_kg

            # 数量/单价/金额 — 优先 PI（轨道A合并）
            if pi_d and pi_d.quantity is not None:
                record.quantity_kg = pi_d.quantity
            else:
                record.quantity_kg = item.quantity_kg

            if pi_d and pi_d.unit_price is not None:
                record.unit_price = pi_d.unit_price
            else:
                record.unit_price = item.unit_price

            if pi_d and pi_d.total_amount is not None:
                record.total_amount = pi_d.total_amount
            else:
                record.total_amount = item.total_amount

            # H.S.Code — 优先 PI
            if pi_d and pi_d.hs_code:
                record.hs_code = pi_d.hs_code
            else:
                record.hs_code = item.hs_code

            # 报关品名 — 优先订单
            if item.customs_name:
                record.customs_name = item.customs_name
            elif pi_d and pi_d.customs_name:
                record.customs_name = pi_d.customs_name
            else:
                record.customs_name = None

            # ── PI 专用字段 ──
            if pi_d:
                record.pi_no = pi_d.pi_no
                record.pi_date = pi_d.pi_date

            # ── 包装计算结果（轨道B） ──
            if pkg:
                record.drum_count = pkg.drums
                record.pallet_count = pkg.pallets
                record.drums_per_pallet = pkg.drums_per_pallet
                record.net_weight_kg = pkg.net_weight_kg
                record.gross_weight_kg = pkg.gross_weight_kg
                record.volume_cbm = pkg.volume_cbm
                record.fits_20gp = pkg.fits_20gp
                record.packaging_result_json = packaging_json
                record.pallet_spec = pkg.pallet_spec
                # 查找 packaging_type_id（按名称匹配）
                pkg_type = self.db.query(PackagingType).filter(
                    PackagingType.name == pkg.packaging_type
                ).first()
                if pkg_type:
                    record.packaging_type_id = pkg_type.id

            record.status = "confirmed"

            self.db.add(record)
            self.db.flush()  # 获取 id
            if first_record_id is None:
                first_record_id = record.id

        self.db.commit()
        return first_record_id or -1

    def query_records(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RecordListResponse:
        """查询落库记录，支持状态筛选 + 模糊搜索 + 分页"""
        query = self.db.query(OrderPiRecord)

        if status:
            query = query.filter(OrderPiRecord.status == status)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (OrderPiRecord.order_no.like(pattern)) |
                (OrderPiRecord.customer_code.like(pattern)) |
                (OrderPiRecord.pi_no.like(pattern))
            )

        total = query.count()
        offset = (page - 1) * page_size
        records = query.order_by(OrderPiRecord.created_at.desc()).offset(offset).limit(page_size).all()

        return RecordListResponse(
            records=[OrderPiRecordResponse.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_record(self, record_id: int) -> Optional[OrderPiRecordResponse]:
        """根据 ID 查询单条记录"""
        record = self.db.query(OrderPiRecord).filter(OrderPiRecord.id == record_id).first()
        if not record:
            return None
        return OrderPiRecordResponse.model_validate(record)

    def confirm_record(self, record_id: int) -> bool:
        """确认一条记录（status → confirmed）"""
        record = self.db.query(OrderPiRecord).filter(OrderPiRecord.id == record_id).first()
        if not record:
            return False
        record.status = "confirmed"
        self.db.commit()
        return True