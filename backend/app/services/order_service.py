"""
订单服务层。
封装所有订单相关业务逻辑，供 API 路由注入使用。
"""
from datetime import datetime
from app.core.order_parser import parse_pasted_data
from app.core.knowledge_filler import fill_knowledge_for_order
from app.schemas.order import (
    PasteParseResponse,
    ParsedOrderSchema,
    SkippedRowSchema,
)
from app.database import SessionLocal
from app.models import Order, OrderItem


class OrderService:
    """订单服务"""

    def parse_paste(self, raw_text: str) -> PasteParseResponse:
        """
        解析粘贴文本，返回预览数据（含知识库匹配结果）。
        """
        orders, skipped_rows, warning = parse_pasted_data(raw_text)

        # 知识库匹配（in-place 修改）
        for order in orders:
            fill_knowledge_for_order(order)

        return PasteParseResponse(
            orders=orders,
            skipped_rows=skipped_rows,
            warning=warning,
        )

    def save_order(self, order_data: ParsedOrderSchema) -> dict:
        """
        保存订单（覆盖或新建）。
        事务保证：orders + order_items 要么全部成功，要么全部回滚。

        Returns:
            dict with order_id, items_count, message
        """
        db = SessionLocal()
        try:
            # 检查是否已存在
            existing = db.query(Order).filter(Order.order_no == order_data.order_no).first()

            if existing:
                # 覆盖：删除旧 order_items（按 order_id）
                db.query(OrderItem).filter(OrderItem.order_id == existing.id).delete()
                # 更新 orders 头表
                existing.customer_code = order_data.customer_code
                existing.salesperson = order_data.salesperson
                existing.updated_at = datetime.utcnow()
                order_id = existing.id
            else:
                # 新建
                new_order = Order(
                    order_no=order_data.order_no,
                    customer_code=order_data.customer_code,
                    salesperson=order_data.salesperson,
                )
                db.add(new_order)
                db.flush()  # 获取 id
                order_id = new_order.id

            # 批量插入 order_items
            items_count = 0
            for item_data in order_data.items:
                item_dict = item_data.model_dump(exclude_none=False, exclude={"hs_code_warning", "warning", "_selected"})
                order_item = OrderItem(order_id=order_id, **item_dict)
                db.add(order_item)
                items_count += 1

            db.commit()  # ← 事务提交点

            return {
                "order_id": order_id,
                "items_count": items_count,
                "message": f"订单 {order_data.order_no} 保存成功，共 {items_count} 个产品",
            }

        except Exception as e:
            db.rollback()  # ← 显式回滚确保
            raise e
        finally:
            db.close()