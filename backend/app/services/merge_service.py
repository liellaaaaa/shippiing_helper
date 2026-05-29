"""合并查询服务 — FR-3.x 数据关联模块（只读）"""

from typing import Optional
from app.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.pi_contract import PiContract, PiContractItem
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

            result_items.append(OrderListItem(
                id=order.id,
                order_no=order.order_no,
                customer_code=order.customer_code,
                salesperson=order.salesperson,
                total_amount=total_amount if total_amount > 0 else None,
                association_status=association_status,
                items_count=len(items),
                linked_count=linked_count,
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
        返回每个 order_item 与对应的 pi_contract_item 的比对结果。
        """
        order = self.db.query(Order).filter_by(id=order_id).first()
        if not order:
            return None

        order_items = self.db.query(OrderItem).filter_by(order_id=order_id).all()
        comparison_items = []

        for item in order_items:
            internal_code = item.internal_code

            # 查找对应的 PI item
            pi_item = self.db.query(PiContractItem).filter_by(
                internal_code=internal_code
            ).first()

            # 构建 order 数据
            order_data = OrderItemData(
                quantity=item.quantity_kg,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
                hs_code=item.hs_code,
                customs_name=item.customs_name,
            )

            # 构建 PI 数据（可能为空）
            pi_data = None
            if pi_item:
                pi_data = PiItemData(
                    quantity=pi_item.quantity,
                    unit_price=pi_item.unit_price,
                    total_amount=pi_item.total_amount,
                    hs_code=pi_item.hs_code,
                    customs_name=pi_item.customs_name,
                )

            # 计算差异
            diff = self._compute_diff(item, pi_item)

            comparison_items.append(ComparisonItem(
                internal_code=internal_code,
                product_cn=item.product_cn,
                order=order_data,
                pi=pi_data,
                diff=diff,
            ))

        return OrderComparisonResponse(
            order_id=order.id,
            order_no=order.order_no,
            customer_code=order.customer_code,
            items=comparison_items,
        )

    def _compute_diff(self, order_item: OrderItem, pi_item: Optional[PiContractItem]) -> DiffInfo:
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