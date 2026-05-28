"""
知识库匹配服务。
自动补全 H.S.Code 和报关品名。
优先级：
  H.S.Code: PI > 知识库（internal_code）> 知识库（产品中文名）
  报关品名: 订单已有 > PI > 知识库 > 自动生成

匹配策略：去空格后精确匹配，不使用模糊匹配。
"""
from app.schemas.order import OrderItemSchema, ParsedOrderSchema
from app.database import SessionLocal
from app.models import ProductKnowledge


def auto_fill_knowledge(item: OrderItemSchema, pi_data: dict | None = None) -> None:
    """
    为单个产品明细填充 H.S.Code 和报关品名。
    在 item 对象上直接修改（in-place）。
    """
    db = SessionLocal()
    try:
        # --- H.S.Code 补全 ---
        if pi_data and pi_data.get("hs_code"):
            item.hs_code = pi_data["hs_code"]
        else:
            knowledge = None
            internal_code = item.internal_code.strip() if item.internal_code else ""

            # 2.1 优先用 internal_code 精确查（最准）
            if internal_code:
                knowledge = db.query(ProductKnowledge).filter(
                    ProductKnowledge.internal_code == internal_code
                ).first()

            # 2.2 如果查不到，用产品中文名去空格后精确匹配（仅当长度 > 4）
            if not knowledge and item.product_cn:
                clean_name = item.product_cn.strip()
                if len(clean_name) > 4:
                    knowledge = db.query(ProductKnowledge).filter(
                        ProductKnowledge.product_name_cn == clean_name
                    ).first()

            if knowledge:
                item.hs_code = knowledge.hs_code
            # 知识库查不到则保留原值（前端粘贴数据或已填充值），不覆盖为 None

        # --- H.S.Code 格式校验（10 位标准）---
        if item.hs_code and len(item.hs_code) < 10:
            item.hs_code_warning = f"H.S.Code 位数不足（当前 {len(item.hs_code)} 位），请核对或补足 10 位"

        # --- 报关品名补全 ---
        if item.customs_name:
            pass  # 已有，使用粘贴数据
        elif pi_data and pi_data.get("customs_name"):
            item.customs_name = pi_data["customs_name"]
        elif knowledge:
            item.customs_name = knowledge.customs_name
        else:
            # 知识库也没有，自动生成
            spec = f"{item.spec_kg}kg" if item.spec_kg else ""
            item.customs_name = f"{item.product_cn or ''} {spec}".strip()
            item.warning = "报关品名由系统自动生成，请务必核对！"

    finally:
        db.close()


def fill_knowledge_for_order(order: ParsedOrderSchema, pi_data: dict | None = None) -> None:
    """为订单下的所有产品明细填充知识库数据"""
    for item in order.items:
        auto_fill_knowledge(item, pi_data)