"""台账服务 — 三源合并预览 + 台账读写"""

from app.database import SessionLocal
from app.models.order_pi_record import OrderPiRecord
from app.schemas.ledger import (
    MergePreviewRequest,
    MergePreviewResponse,
    MergePreviewItem,
    ValidationWarning,
    LedgerWriteRequest,
    LedgerWriteResponse,
    LedgerRecordResponse,
    LedgerItemSchema,
    LedgerListResponse,
)
from app.schemas.order import ParsedOrderSchema, OrderItemSchema, SkippedRowSchema
from app.schemas.pi_contract import PiContractUploadResponse
from app.core.order_parser import parse_pasted_data, parse_pi_contract_table
from app.core.pi_parser import parse_pi_bytes
from app.services.customs_name_service import CustomsNameService
from app.core.config import CUSTOMS_CODES_JSON
from typing import Optional


FLOAT_TOLERANCE = 0.01


class LedgerService:
    """台账服务 — 三源合并预览和读写"""

    def parse_sales_order_table(self, raw_text: str) -> tuple[list[ParsedOrderSchema], list[SkippedRowSchema], str | None]:
        """解析销售订单表粘贴文本（复用现有逻辑）"""
        return parse_pasted_data(raw_text)

    def parse_pi_contract_table(self, raw_text: str) -> tuple[list[ParsedOrderSchema], list[SkippedRowSchema], str | None]:
        """解析 PI 合同表粘贴文本"""
        return parse_pi_contract_table(raw_text)

    def parse_pi_file(self, content: bytes, filename: str) -> PiContractUploadResponse:
        """解析 PI 合同文件"""
        return parse_pi_bytes(content, filename)

    def merge_preview(self, req: MergePreviewRequest) -> MergePreviewResponse:
        """
        三源合并预览：
        1. 解析 PI 合同表 → 获取订单号、产品列表、数量、金额、HS Code、报关品名、报关成分
        2. 解析销售订单表 → 获取产品名、规格、交货日期、包装要求、跟单员等
        3. 解析 PI 合同文件 → 获取收货人、目的港、装货港、价格条款、付款方式、银行信息
        4. 按内部编码匹配合并（两源产品全部保留，不匹配的标记来源）
        5. 交叉校验数量/金额
        """
        # 1. 解析 PI 合同表
        pi_contract_parsed = None
        pi_contract_orders: list[ParsedOrderSchema] = []
        pi_contract_table_error: Optional[str] = None
        if req.pi_contract_table_text:
            try:
                pi_contract_orders, _, _ = parse_pi_contract_table(req.pi_contract_table_text)
                pi_contract_parsed = self._orders_to_dict(pi_contract_orders)
            except Exception as e:
                pi_contract_table_error = f"PI合同表解析失败：{str(e)}"

        # 2. 解析销售订单表
        sales_order_parsed = None
        sales_orders: list[ParsedOrderSchema] = []
        sales_order_error: Optional[str] = None
        if req.sales_order_table_text:
            try:
                sales_orders, _, _ = parse_pasted_data(req.sales_order_table_text)
                sales_order_parsed = self._orders_to_dict(sales_orders)
            except Exception as e:
                sales_order_error = f"销售订单表解析失败：{str(e)}"

        # 3. 解析 PI 合同文件
        pi_file_parsed = None
        pi_file_data: Optional[PiContractUploadResponse] = None
        pi_file_parse_error: Optional[str] = None
        if req.pi_file_content and req.pi_filename:
            try:
                pi_file_data = parse_pi_bytes(req.pi_file_content, req.pi_filename)
                pi_file_parsed = self._pi_file_to_dict(pi_file_data)
            except Exception as e:
                pi_file_parse_error = f"PI合同文件解析失败：{str(e)}"

        # 4. 构建合并预览
        merged_items: list[MergePreviewItem] = []
        validation_warnings: list[ValidationWarning] = []
        validation_status = "ok"

        # 收集所有内部编码（两源合并）
        pi_order = pi_contract_orders[0] if pi_contract_orders else None
        so_order = sales_orders[0] if sales_orders else None
        order_no = pi_order.order_no if pi_order else (so_order.order_no if so_order else "UNKNOWN")

        # 构建 PI合同表 产品索引 {internal_code: item}
        pi_items_map: dict[str, OrderItemSchema] = {}
        if pi_order:
            for pi_item in pi_order.items:
                pi_items_map[pi_item.internal_code] = pi_item

        # 构建 销售订单表 产品索引 {internal_code: item}
        so_items_map: dict[str, OrderItemSchema] = {}
        if so_order:
            for so_item in so_order.items:
                so_items_map[so_item.internal_code] = so_item

        # 合并所有内部编码（保持PI合同表优先顺序，追加销售订单独有的）
        all_codes: list[str] = []
        seen_codes: set[str] = set()
        if pi_order:
            for pi_item in pi_order.items:
                if pi_item.internal_code not in seen_codes:
                    all_codes.append(pi_item.internal_code)
                    seen_codes.add(pi_item.internal_code)
        if so_order:
            for so_item in so_order.items:
                if so_item.internal_code not in seen_codes:
                    all_codes.append(so_item.internal_code)
                    seen_codes.add(so_item.internal_code)

        for code in all_codes:
            pi_item = pi_items_map.get(code)
            so_item = so_items_map.get(code)

            in_pi = pi_item is not None
            in_so = so_item is not None

            # 确定来源标记
            if in_pi and in_so:
                source_note = "匹配"
            elif in_pi:
                source_note = "仅PI合同表"
            else:
                source_note = "仅销售订单表"

            # 合并字段：PI合同表优先，销售订单表补充
            item = MergePreviewItem(
                internal_code=code,
                source_pi_contract=in_pi,
                source_sales_order=in_so,
                source_pi_file=False,
                source_note=source_note,
                # 产品名称：优先销售订单表的product_cn，降级用PI合同表的customs_name
                product_cn=(
                    (so_item.product_cn if so_item and so_item.product_cn else None)
                    or (pi_item.customs_name if pi_item else None)
                ),
                spec_kg=so_item.spec_kg if so_item else None,
                # 数量：PI合同表为准
                quantity_kg=pi_item.quantity_kg if pi_item else (so_item.quantity_kg if so_item else None),
                # 单价：PI合同表为准
                unit_price=pi_item.unit_price if pi_item and pi_item.unit_price is not None else (so_item.unit_price if so_item else None),
                # 金额：PI合同表为准
                total_amount=pi_item.total_amount if pi_item else (so_item.total_amount if so_item else None),
                # HS Code：PI合同表优先
                hs_code=(
                    (pi_item.hs_code if pi_item and pi_item.hs_code else None)
                    or (so_item.hs_code if so_item else None)
                ),
                # 报关品名：PI合同表优先
                customs_name=(
                    (pi_item.customs_name if pi_item and pi_item.customs_name else None)
                    or (so_item.customs_name if so_item else None)
                ),
                customs_ingredients=getattr(pi_item, "customs_ingredients", None) if pi_item else None,
                product_appearance=getattr(pi_item, "product_appearance", None) if pi_item else None,
            )

            # 从 PI 合同文件校验数量/金额
            if pi_file_data:
                item.source_pi_file = True
                for pf_item in pi_file_data.items:
                    if pf_item.internal_code == code:
                        # 数量校验
                        compare_qty = pi_item.quantity_kg if pi_item else (so_item.quantity_kg if so_item else None)
                        if compare_qty is not None and pf_item.quantity is not None:
                            if abs(compare_qty - pf_item.quantity) > FLOAT_TOLERANCE:
                                validation_status = "warning"
                                validation_warnings.append(ValidationWarning(
                                    internal_code=code,
                                    field="quantity_kg",
                                    pi_contract_value=compare_qty,
                                    pi_file_value=pf_item.quantity,
                                    message=f"数量不一致：合同表={compare_qty}，PI文件={pf_item.quantity}",
                                ))
                        # 金额校验
                        compare_amount = pi_item.total_amount if pi_item else (so_item.total_amount if so_item else None)
                        if compare_amount is not None and pf_item.total_amount is not None:
                            if abs(compare_amount - pf_item.total_amount) > FLOAT_TOLERANCE:
                                validation_status = "warning"
                                validation_warnings.append(ValidationWarning(
                                    internal_code=code,
                                    field="total_amount",
                                    pi_contract_value=compare_amount,
                                    pi_file_value=pf_item.total_amount,
                                    message=f"金额不一致：合同表={compare_amount}，PI文件={pf_item.total_amount}",
                                ))
                        break

            merged_items.append(item)

        # 补充知识库填充
        customs_svc = CustomsNameService.get_instance(CUSTOMS_CODES_JSON)
        for item in merged_items:
            if not item.hs_code or not item.customs_name:
                json_data = customs_svc.lookup(item.internal_code)
                if json_data:
                    if not item.hs_code:
                        item.hs_code = json_data.get("product_code")
                    if not item.customs_name:
                        item.customs_name = json_data.get("customs_name")
                    if not item.customs_ingredients:
                        item.customs_ingredients = json_data.get("components")

        # 统计匹配情况
        matched_count = sum(1 for i in merged_items if i.source_pi_contract and i.source_sales_order)
        pi_only_count = sum(1 for i in merged_items if i.source_pi_contract and not i.source_sales_order)
        sales_only_count = sum(1 for i in merged_items if not i.source_pi_contract and i.source_sales_order)

        # 从销售订单表提取订单级字段
        so_first_item = so_order.items[0] if so_order and so_order.items else None

        return MergePreviewResponse(
            order_no=order_no,
            customer_code=pi_order.customer_code if pi_order else None,
            sales_person=pi_order.salesperson if pi_order else None,
            pi_date=pi_order.pi_date if pi_order else None,
            # PI合同表头部字段
            pi_contract_shipment_title=pi_order.shipment_title if pi_order else None,
            pi_contract_shipment_method=pi_order.shipment_method if pi_order else None,
            # 销售订单表头部字段
            sales_order_no=so_order.order_no if so_order else None,
            shipment_title=getattr(so_first_item, "shipment_title", None) if so_first_item else None,
            merchandiser=getattr(so_first_item, "merchandiser", None) if so_first_item else None,
            delivery_date=getattr(so_first_item, "order_date", None) if so_first_item else None,
            shipment_method=getattr(so_first_item, "shipment_method", None) if so_first_item else None,
            # PI合同文件字段
            consignee_name=pi_file_data.consignee_name if pi_file_data else None,
            consignee_address=pi_file_data.consignee_address if pi_file_data else None,
            consignee_tel=getattr(pi_file_data, "consignee_tel", None) if pi_file_data else None,
            destination=pi_file_data.destination if pi_file_data else None,
            loading_port=pi_file_data.loading_port if pi_file_data else None,
            price_term=pi_file_data.price_term if pi_file_data else None,
            payment_terms=getattr(pi_file_data, "payment_terms", None) if pi_file_data else None,
            bank_info=getattr(pi_file_data, "beneficiary_bank", None) if pi_file_data else None,
            items=merged_items,
            total_products=len(merged_items),
            matched_count=matched_count,
            pi_only_count=pi_only_count,
            sales_only_count=sales_only_count,
            validation_status=validation_status,
            validation_warnings=validation_warnings,
            pi_file_parse_error=pi_file_parse_error,
            pi_contract_table_parse_error=pi_contract_table_error,
            sales_order_table_parse_error=sales_order_error,
            pi_contract_table_parsed=pi_contract_parsed,
            sales_order_table_parsed=sales_order_parsed,
            pi_file_parsed=pi_file_parsed,
        )

    def _orders_to_dict(self, orders: list[ParsedOrderSchema]) -> dict:
        """将 ParsedOrderSchema 列表转为可序列化字典"""
        return {
            "orders": [
                {
                    "order_no": o.order_no,
                    "customer_code": o.customer_code,
                    "salesperson": o.salesperson,
                    "pi_date": o.pi_date,
                    "shipment_method": o.shipment_method,
                    "shipment_title": o.shipment_title,
                    "items": [
                        {
                            "internal_code": i.internal_code,
                            "product_cn": i.product_cn,
                            "spec_kg": i.spec_kg,
                            "quantity_kg": i.quantity_kg,
                            "unit_price": i.unit_price,
                            "total_amount": i.total_amount,
                            "hs_code": i.hs_code,
                            "customs_name": i.customs_name,
                        }
                        for i in o.items
                    ],
                }
                for o in orders
            ]
        }

    def _pi_file_to_dict(self, data: PiContractUploadResponse) -> dict:
        """将 PI 文件解析结果转为可序列化字典"""
        return {
            "pi_no": data.pi_no,
            "customer_code": data.customer_code,
            "sales_person": data.sales_person,
            "pi_date": data.pi_date,
            "consignee_name": data.consignee_name,
            "consignee_address": data.consignee_address,
            "consignee_tel": getattr(data, "consignee_tel", None),
            "destination": data.destination,
            "loading_port": data.loading_port,
            "price_term": data.price_term,
            "items": [
                {
                    "internal_code": i.internal_code,
                    "quantity": i.quantity,
                    "unit_price": i.unit_price,
                    "total_amount": i.total_amount,
                }
                for i in data.items
            ],
        }

    # ── 台账读写 ────────────────────────────────────────────

    def write_ledger(self, req: LedgerWriteRequest) -> LedgerWriteResponse:
        """将合并后的完整数据写入台账（每产品一行）"""
        db = SessionLocal()
        first_record = None
        try:
            for item in req.items:
                record = OrderPiRecord(
                    order_no=req.order_no,
                    customer_code=req.customer_code,
                    sales_person=req.sales_person,
                    pi_no=req.order_no,
                    pi_date=req.pi_date,
                    # 销售订单补充
                    sales_order_no=req.sales_order_no,
                    merchandiser=req.merchandiser,
                    order_date=req.order_date,
                    delivery_date=req.delivery_date,
                    shipment_channel=req.shipment_channel,
                    shipment_method=req.shipment_method,
                    review_status=req.review_status,
                    spec_abnormal=req.spec_abnormal,
                    has_sample=req.has_sample,
                    price_adjusted=req.price_adjusted,
                    order_confirmed=req.order_confirmed,
                    production_deadline=req.production_deadline,
                    shipment_title=req.shipment_title,
                    document_type=req.document_type,
                    # PI 合同文件补充
                    consignee_name=req.consignee_name,
                    consignee_address=req.consignee_address,
                    consignee_tel=req.consignee_tel,
                    destination=req.destination,
                    loading_port=req.loading_port,
                    price_term=req.price_term,
                    payment_terms=req.payment_terms,
                    bank_info=req.bank_info,
                    # 产品明细
                    internal_code=item.internal_code,
                    product_cn=item.product_cn,
                    product_en=item.product_en,
                    spec_kg=item.spec_kg,
                    quantity_kg=item.quantity_kg,
                    unit_price=item.unit_price,
                    total_amount=item.total_amount,
                    hs_code=item.hs_code,
                    customs_name=item.customs_name,
                    components=item.customs_ingredients,
                    product_appearance=item.product_appearance,
                    # 包装（从计算服务填充）
                    packaging_type_id=item.packaging_type_id,
                    pallet_spec=item.pallet_spec,
                    drums_per_pallet=item.drums_per_pallet,
                    drum_count=item.drum_count,
                    pallet_count=item.pallet_count,
                    net_weight_kg=item.net_weight_kg,
                    gross_weight_kg=item.gross_weight_kg,
                    volume_cbm=item.volume_cbm,
                    fits_20gp="适合" if item.fits_20gp is True else ("超出" if item.fits_20gp is False else None),
                    status="pending",
                )
                db.add(record)
                if first_record is None:
                    first_record = record
            db.commit()
            # Refresh to get auto-generated IDs
            if first_record:
                db.refresh(first_record)
            return LedgerWriteResponse(
                record_id=first_record.id if first_record else 0,
                items_count=len(req.items),
                message=f"写入台账 {len(req.items)} 条产品记录",
            )
        finally:
            db.close()

    def get_ledger_record(self, record_id: int) -> Optional[LedgerRecordResponse]:
        """读取单条台账记录（含所有字段）"""
        db = SessionLocal()
        try:
            record = db.query(OrderPiRecord).filter_by(id=record_id).first()
            if not record:
                return None

            # 读取同 order_no 的所有产品行
            records = db.query(OrderPiRecord).filter_by(order_no=record.order_no).all()
            items = [
                LedgerItemSchema(
                    internal_code=r.internal_code,
                    product_cn=r.product_cn,
                    product_en=r.product_en,
                    spec_kg=r.spec_kg,
                    quantity_kg=r.quantity_kg,
                    unit_price=r.unit_price,
                    total_amount=r.total_amount,
                    hs_code=r.hs_code,
                    customs_name=r.customs_name,
                    customs_ingredients=r.components,
                    product_appearance=r.product_appearance,
                    packaging_type_id=r.packaging_type_id,
                    pallet_spec=r.pallet_spec,
                    drums_per_pallet=r.drums_per_pallet,
                    drum_count=r.drum_count,
                    pallet_count=r.pallet_count,
                    net_weight_kg=r.net_weight_kg,
                    gross_weight_kg=r.gross_weight_kg,
                    volume_cbm=r.volume_cbm,
                    fits_20gp=r.fits_20gp,
                )
                for r in records
            ]

            return LedgerRecordResponse(
                id=record.id,
                order_no=record.order_no,
                customer_code=record.customer_code,
                sales_person=record.sales_person,
                pi_no=record.pi_no,
                pi_date=record.pi_date,
                sales_order_no=record.sales_order_no,
                merchandiser=record.merchandiser,
                order_date=record.order_date,
                delivery_date=record.delivery_date,
                shipment_channel=record.shipment_channel,
                shipment_method=record.shipment_method,
                review_status=record.review_status,
                spec_abnormal=record.spec_abnormal,
                has_sample=record.has_sample,
                price_adjusted=record.price_adjusted,
                order_confirmed=record.order_confirmed,
                production_deadline=record.production_deadline,
                shipment_title=record.shipment_title,
                document_type=record.document_type,
                consignee_name=record.consignee_name,
                consignee_address=record.consignee_address,
                consignee_tel=record.consignee_tel,
                destination=record.destination,
                loading_port=record.loading_port,
                price_term=record.price_term,
                payment_terms=record.payment_terms,
                bank_info=record.bank_info,
                items=items,
                status=record.status or "pending",
                created_at=str(record.created_at) if record.created_at else None,
            )
        finally:
            db.close()

    def delete_ledger(self, order_no: str) -> int:
        """按订单号删除台账记录（整单删除），返回删除行数"""
        db = SessionLocal()
        try:
            count = db.query(OrderPiRecord).filter_by(order_no=order_no).delete()
            db.commit()
            return count
        finally:
            db.close()

    def list_ledger(self, search: Optional[str] = None, page: int = 1, page_size: int = 20) -> LedgerListResponse:
        """台账列表（按 order_no 分组，按时间倒序）"""
        from sqlalchemy import func, distinct

        db = SessionLocal()
        try:
            # 先查唯一 order_no 列表（用于分页和计数）
            base_query = db.query(OrderPiRecord)
            if search:
                pattern = f"%{search}%"
                base_query = base_query.filter(
                    (OrderPiRecord.order_no.like(pattern)) |
                    (OrderPiRecord.customer_code.like(pattern)) |
                    (OrderPiRecord.sales_person.like(pattern))
                )

            # 按 order_no 去重计数
            total = db.query(func.count(distinct(OrderPiRecord.order_no))).filter(
                base_query.where(True).subquery().c.order_no if search else True
            ).scalar()
            # 简化：用子查询方式统计唯一 order_no
            if search:
                total = db.query(func.count(distinct(OrderPiRecord.order_no))).filter(
                    (OrderPiRecord.order_no.like(pattern)) |
                    (OrderPiRecord.customer_code.like(pattern)) |
                    (OrderPiRecord.sales_person.like(pattern))
                ).scalar()
            else:
                total = db.query(func.count(distinct(OrderPiRecord.order_no))).scalar()

            # 获取当前页的唯一 order_no（按创建时间倒序）
            offset = (page - 1) * page_size
            order_nos = (
                db.query(OrderPiRecord.order_no)
                .filter(base_query.where(True).subquery().c.order_no if search else True)
                .order_by(OrderPiRecord.created_at.desc())
                .distinct()
                .offset(offset)
                .limit(page_size)
                .all()
            )
            # 简化查询
            if search:
                order_nos = (
                    db.query(OrderPiRecord.order_no)
                    .filter(
                        (OrderPiRecord.order_no.like(pattern)) |
                        (OrderPiRecord.customer_code.like(pattern)) |
                        (OrderPiRecord.sales_person.like(pattern))
                    )
                    .order_by(OrderPiRecord.created_at.desc())
                    .distinct()
                    .offset(offset)
                    .limit(page_size)
                    .all()
                )
            else:
                order_nos = (
                    db.query(OrderPiRecord.order_no)
                    .order_by(OrderPiRecord.created_at.desc())
                    .distinct()
                    .offset(offset)
                    .limit(page_size)
                    .all()
                )
            order_no_list = [row[0] for row in order_nos]

            if not order_no_list:
                return LedgerListResponse(records=[], total=total)

            # 批量加载所有产品的数据（避免 N+1 查询）
            all_records = (
                db.query(OrderPiRecord)
                .filter(OrderPiRecord.order_no.in_(order_no_list))
                .order_by(OrderPiRecord.order_no, OrderPiRecord.id)
                .all()
            )

            # 按 order_no 分组
            grouped: dict[str, list] = {}
            for r in all_records:
                grouped.setdefault(r.order_no, []).append(r)

            result_records: list[LedgerRecordResponse] = []
            for order_no in order_no_list:
                records = grouped.get(order_no, [])
                if not records:
                    continue
                first = records[0]
                items = [
                    LedgerItemSchema(
                        internal_code=ri.internal_code,
                        product_cn=ri.product_cn,
                        product_en=ri.product_en,
                        spec_kg=ri.spec_kg,
                        quantity_kg=ri.quantity_kg,
                        unit_price=ri.unit_price,
                        total_amount=ri.total_amount,
                        hs_code=ri.hs_code,
                        customs_name=ri.customs_name,
                        customs_ingredients=ri.components,
                        product_appearance=ri.product_appearance,
                    )
                    for ri in records
                ]
                result_records.append(LedgerRecordResponse(
                    id=first.id,
                    order_no=first.order_no,
                    customer_code=first.customer_code,
                    sales_person=first.sales_person,
                    pi_no=first.pi_no,
                    pi_date=first.pi_date,
                    sales_order_no=first.sales_order_no,
                    merchandiser=first.merchandiser,
                    order_date=first.order_date,
                    delivery_date=first.delivery_date,
                    shipment_channel=first.shipment_channel,
                    shipment_method=first.shipment_method,
                    review_status=first.review_status,
                    spec_abnormal=first.spec_abnormal,
                    has_sample=first.has_sample,
                    price_adjusted=first.price_adjusted,
                    order_confirmed=first.order_confirmed,
                    production_deadline=first.production_deadline,
                    shipment_title=first.shipment_title,
                    document_type=first.document_type,
                    consignee_name=first.consignee_name,
                    consignee_address=first.consignee_address,
                    consignee_tel=first.consignee_tel,
                    destination=first.destination,
                    loading_port=first.loading_port,
                    price_term=first.price_term,
                    payment_terms=first.payment_terms,
                    bank_info=first.bank_info,
                    items=items,
                    status=first.status or "pending",
                    created_at=str(first.created_at) if first.created_at else None,
                ))

            return LedgerListResponse(records=result_records, total=total)
        finally:
            db.close()
