"""合并查询服务 — FR-3.x 数据关联模块（只读）"""

from typing import Optional, Union
from app.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.pi_contract import PiContract, PiContractItem
from app.models.order_pi_record import OrderPiRecord
from app.schemas.merge import (
    OrderListItem,
    OrderListResponse,
    OrderComparisonResponse,
    ComparisonItem,
    OrderItemData,
    PiItemData,
    DiffInfo,
)


FLOAT_TOLERANCE = 0.01  # 数值字段容差


class MergeService:
    """数据关联服务 — 只读查询，不写入任何数据"""

    def __init__(self, db_session):
        self.db = db_session

    def get_order_list(
        self,
        tab: str = "pending",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> OrderListResponse:
        """
        查询订单列表，计算关联状态，返回分页结果。

        关联状态判定：
        - full: 所有 order_items 的 internal_code 均在 pi_contract_items 中有匹配
        - partial: 部分有匹配
        - none: 没有任何匹配
        """
        query = self.db.query(Order)

        # 模糊搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Order.order_no.like(search_pattern)) |
                (Order.customer_code.like(search_pattern))
            )

        # 按创建时间倒序
        query = query.order_by(Order.created_at.desc())

        total = query.count()
        offset = (page - 1) * page_size
        orders = query.offset(offset).limit(page_size).all()

        result_items = []
        for order in orders:
            # 计算关联状态
            items = self.db.query(OrderItem).filter_by(order_id=order.id).all()
            linked_items = []
            if not items:
                association_status = "none"
                linked_count = 0
            else:
                internal_codes = [item.internal_code for item in items]
                # 查询有多少 items 在 PI 中有匹配
                linked_items = self.db.query(PiContractItem).filter(
                    PiContractItem.internal_code.in_(internal_codes)
                ).all()
                linked_codes = set(item.internal_code for item in linked_items)

                matched = sum(1 for item in items if item.internal_code in linked_codes)
                linked_count = matched

                if matched == len(items):
                    association_status = "full"
                elif matched > 0:
                    association_status = "partial"
                else:
                    association_status = "none"

            # 计算订单总金额
            total_amount = sum(
                (item.quantity_kg or 0) * (item.unit_price or 0)
                for item in items
            )

            # 取关联 PI 号（第一个匹配项的 PI 号）
            pi_no = None
            if linked_items:
                from app.models.pi_contract import PiContract
                first_pi_item = linked_items[0]
                pi_contract = self.db.query(PiContract).filter_by(id=first_pi_item.pi_contract_id).first()
                if pi_contract:
                    pi_no = pi_contract.pi_no

            result_items.append(OrderListItem(
                id=order.id,
                order_no=order.order_no,
                customer_code=order.customer_code,
                salesperson=order.salesperson,
                total_amount=total_amount if total_amount > 0 else None,
                association_status=association_status,
                items_count=len(items),
                linked_count=linked_count,
                pi_no=pi_no,
                created_at=order.created_at.strftime("%Y-%m-%d") if order.created_at else None,
            ))

        # Tab 过滤
        if tab == "pending":
            result_items = [i for i in result_items if i.association_status != "full"]
        elif tab == "completed":
            result_items = [i for i in result_items if i.association_status == "full"]

        return OrderListResponse(
            orders=result_items,
            total=len(result_items),
            page=page,
            page_size=page_size,
        )

    def get_order_comparison(self, order_id: int) -> Optional[OrderComparisonResponse]:
        """
        获取指定订单的合并比对数据。
        order_id 可以是 Order.id 或 OrderPiRecord.id（两者都是整数主键）。
        先按 OrderPiRecord.id 查找；如果找不到，再按 Order.id 查找。
        """
        # 优先按 OrderPiRecord.id 查找
        record = self.db.query(OrderPiRecord).filter(OrderPiRecord.id == order_id).first()

        if record:
            order_no = record.order_no
            all_records = self.db.query(OrderPiRecord).filter(
                OrderPiRecord.order_no == order_no
            ).order_by(
                OrderPiRecord.group_id.asc().nullslast(),
                OrderPiRecord.is_group_header.desc(),
                OrderPiRecord.id.asc(),
            ).all()

            first = all_records[0]
            pi_contract = self.db.query(PiContract).filter_by(pi_no=first.pi_no).first()

            comparison_items = []
            for r in all_records:
                # Direct field from order_pi_records
                appearance = getattr(r, 'product_appearance', '') or ''

                order_data = OrderItemData(
                    quantity=r.quantity_kg,
                    unit_price=r.unit_price,
                    total_amount=r.total_amount,
                    hs_code=r.hs_code,
                    customs_name=r.customs_name,
                    customs_ingredients=r.components,
                    gross_weight=r.gross_weight_kg,
                    volume=r.volume_cbm,
                    product_en=r.product_en,
                    appearance=appearance,
                )
                pi_item = self._find_pi_item(r, pi_contract)
                if pi_item is not None:
                    pi_data = PiItemData(
                        quantity=pi_item.quantity,
                        unit_price=pi_item.unit_price,
                        total_amount=pi_item.total_amount,
                        hs_code=pi_item.hs_code,
                        customs_name=pi_item.customs_name,
                        consignee=pi_contract.consignee_name if pi_contract else None,
                        port=pi_contract.destination if pi_contract else None,
                    )
                else:
                    pi_data = PiItemData(
                        consignee=pi_contract.consignee_name if pi_contract else None,
                        port=pi_contract.destination if pi_contract else None,
                    )
                comparison_items.append(ComparisonItem(
                    id=r.id,
                    internal_code=r.internal_code,
                    product_cn=r.product_cn,
                    order=order_data,
                    pi=pi_data,
                    diff=self._compute_record_diff(r, pi_contract, pi_item),
                ))

            # 汇总所有产品的重量、体积、桶数、托盘数
            total_gross_weight = round(sum(r.gross_weight_kg or 0 for r in all_records), 1)
            total_net_weight = round(sum(r.net_weight_kg or 0 for r in all_records), 1)
            total_volume = round(sum(r.volume_cbm or 0 for r in all_records), 3)
            total_drum_count = sum(r.drum_count or 0 for r in all_records)
            total_pallet_count = sum(r.pallet_count or 0 for r in all_records)

            return OrderComparisonResponse(
                order_id=first.id,
                order_no=first.order_no,
                customer_code=first.customer_code,
                pi_no=first.pi_no,
                net_weight_kg=total_net_weight,
                drum_count=total_drum_count,
                pallet_count=total_pallet_count,
                gross_weight_kg=total_gross_weight,
                volume_cbm=total_volume,
                fits_20gp=first.fits_20gp,
                items=comparison_items,
            )

        # 回退：直接按 Order.id 查找
        order = self.db.query(Order).filter_by(id=order_id).first()
        if not order:
            return None

        order_items = self.db.query(OrderItem).filter_by(order_id=order_id).order_by(OrderItem.id.asc()).all()
        comparison_items = []

        for item in order_items:
            pi_item = self.db.query(PiContractItem).filter_by(
                internal_code=item.internal_code
            ).first()
            order_data = OrderItemData(
                quantity=item.quantity_kg,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
                hs_code=item.hs_code,
                customs_name=item.customs_name,
                customs_ingredients=item.customs_ingredients,
                gross_weight=item.gross_weight_kg,
                volume=item.volume_cbm,
                product_en=item.product_en,
            )
            pi_data = None
            pi_contract_for_item = None
            if pi_item:
                pi_contract_for_item = self.db.query(PiContract).filter_by(
                    id=pi_item.pi_contract_id
                ).first()
                pi_data = PiItemData(
                    quantity=pi_item.quantity,
                    unit_price=pi_item.unit_price,
                    total_amount=pi_item.total_amount,
                    hs_code=pi_item.hs_code,
                    customs_name=pi_item.customs_name,
                    consignee=pi_contract_for_item.consignee_name if pi_contract_for_item else None,
                    port=pi_contract_for_item.destination if pi_contract_for_item else None,
                )
            diff = self._compute_diff(item, pi_item)
            comparison_items.append(ComparisonItem(
                id=item.id,
                internal_code=item.internal_code,
                product_cn=item.product_cn,
                order=order_data,
                pi=pi_data,
                diff=diff,
            ))

        return OrderComparisonResponse(
            order_id=order.id,
            order_no=order.order_no,
            customer_code=order.customer_code,
            pi_no=order.pi_no,
            net_weight_kg=sum(item.net_weight_kg or 0 for item in order_items),
            drum_count=order_items[0].drum_count if order_items else None,
            pallet_count=order_items[0].pallet_count if order_items else None,
            gross_weight_kg=order.total_gross_weight_kg,
            volume_cbm=order.total_volume_cbm,
            fits_20gp=order.fits_20gp,
            items=comparison_items,
        )

    def _find_pi_item(
        self,
        record: OrderPiRecord,
        pi_contract: Optional[PiContract],
    ) -> Optional[PiContractItem]:
        """按 internal_code 查 PI 行级明细；优先同一 PI 合同下的行。"""
        code = (record.internal_code or "").strip()
        if not code:
            return None
        query = self.db.query(PiContractItem).filter(PiContractItem.internal_code == code)
        if pi_contract is not None:
            same_pi = query.filter(PiContractItem.pi_contract_id == pi_contract.id).first()
            if same_pi is not None:
                return same_pi
        return query.first()

    def _compute_record_diff(
        self,
        record: OrderPiRecord,
        pi_contract: Optional[PiContract],
        pi_item: Optional[PiContractItem],
    ) -> DiffInfo:
        """OrderPiRecord 与 PI 的比对：行级复用 _compute_diff；头字段单独比对。

        比不了的字段记 flags（*_uncomparable / no_pi），不假装「一致」。
        """
        flags: list[str] = []
        order_value = None
        pi_value = None

        # ── 头字段：收货人 / 目的港 / 装货港 / 价格条款 / 付款条款 ──
        if pi_contract is None:
            flags.append("no_pi_contract")
        else:
            header_pairs = (
                ("consignee", record.consignee_name, pi_contract.consignee_name),
                ("port", record.destination, pi_contract.destination),
                ("loading_port", record.loading_port, pi_contract.loading_port),
                ("price_term", record.price_term, pi_contract.price_term),
                ("payment_terms", record.payment_terms, pi_contract.payment_terms),
            )
            for name, o_val, p_val in header_pairs:
                o_s = (str(o_val).strip() if o_val is not None else "")
                p_s = (str(p_val).strip() if p_val is not None else "")
                if bool(o_s) != bool(p_s):
                    flags.append(f"{name}_uncomparable")
                elif o_s and o_s != p_s:
                    flags.append(name)

        # ── 行级：有 PI 明细则复用 _compute_diff ──
        if pi_item is not None:
            line_diff = self._compute_diff(record, pi_item)
            for f in line_diff.flags:
                if f not in flags:
                    flags.append(f)
            if line_diff.order_value is not None:
                order_value = line_diff.order_value
                pi_value = line_diff.pi_value
            line_pairs = (
                ("quantity", record.quantity_kg, pi_item.quantity),
                ("unit_price", record.unit_price, pi_item.unit_price),
                ("total_amount", record.total_amount, pi_item.total_amount),
                ("hs_code", record.hs_code, pi_item.hs_code),
                ("customs_name", record.customs_name, pi_item.customs_name),
            )
            for name, o_val, p_val in line_pairs:
                o_missing = o_val is None or o_val == ""
                p_missing = p_val is None or p_val == ""
                if o_missing != p_missing:
                    flag = f"{name}_uncomparable"
                    if flag not in flags:
                        flags.append(flag)
        else:
            if "no_pi" not in flags:
                flags.append("no_pi")
            for name in ("quantity", "unit_price", "total_amount", "hs_code", "customs_name"):
                flag = f"{name}_uncomparable"
                if flag not in flags:
                    flags.append(flag)

        status_map = {
            "quantity": "数量不符",
            "unit_price": "单价不符",
            "total_amount": "金额不符",
            "hs_code": "HS不符",
            "customs_name": "品名不符",
            "consignee": "收货人不符",
            "port": "港口不符",
            "loading_port": "装货港不符",
            "price_term": "价格条款不符",
            "payment_terms": "付款条款不符",
        }
        mismatch_flags = [f for f in flags if f in status_map]
        if mismatch_flags:
            status = status_map[mismatch_flags[0]]
        elif pi_item is None:
            status = "PI未覆盖"
        elif any(f.endswith("_uncomparable") or f.startswith("no_pi") for f in flags):
            status = "无法比对"
        else:
            status = "一致"

        return DiffInfo(status=status, flags=flags, order_value=order_value, pi_value=pi_value)

    def _compute_diff(
        self,
        order_item: Union[OrderItem, OrderPiRecord],
        pi_item: Optional[PiContractItem],
    ) -> DiffInfo:
        """
        计算单个产品的差异状态。
        数值字段容差 ±0.01，文本字段严格比对。
        """
        flags = []
        order_value = None
        pi_value = None

        if pi_item is None:
            # PI 未覆盖
            return DiffInfo(
                status="PI未覆盖",
                flags=["no_pi"],
                order_value=order_item.quantity_kg,
                pi_value=None,
            )

        # 数量比对
        o_qty = order_item.quantity_kg
        p_qty = pi_item.quantity
        if o_qty is not None and p_qty is not None:
            if abs(o_qty - p_qty) > FLOAT_TOLERANCE:
                flags.append("quantity")
                order_value = o_qty
                pi_value = p_qty

        # 单价比对
        o_price = order_item.unit_price
        p_price = pi_item.unit_price
        if o_price is not None and p_price is not None:
            if abs(o_price - p_price) > FLOAT_TOLERANCE:
                flags.append("unit_price")

        # 金额比对
        o_total = order_item.total_amount
        p_total = pi_item.total_amount
        if o_total is not None and p_total is not None:
            if abs(o_total - p_total) > FLOAT_TOLERANCE:
                flags.append("total_amount")

        # HS Code 比对（严格）
        if order_item.hs_code and pi_item.hs_code:
            if order_item.hs_code != pi_item.hs_code:
                flags.append("hs_code")

        # 报关品名比对（严格）
        if order_item.customs_name and pi_item.customs_name:
            if order_item.customs_name != pi_item.customs_name:
                flags.append("customs_name")

        if flags:
            status_map = {
                "quantity": "数量不符",
                "unit_price": "单价不符",
                "total_amount": "金额不符",
                "hs_code": "HS不符",
                "customs_name": "品名不符",
            }
            status = status_map.get(flags[0], "不一致")
            return DiffInfo(status=status, flags=flags, order_value=order_value, pi_value=pi_value)
        else:
            return DiffInfo(status="一致", flags=[])