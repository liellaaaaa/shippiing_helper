from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.models.declaration_ledger import HsCodeField, DeclarationProduct, DeclarationValue


class DeclarationLedgerService:
    """申报要素台账服务"""

    def __init__(self, db: Session):
        self.db = db

    def list_hs_codes(self, keyword: Optional[str] = None) -> List[dict]:
        """获取 HS Code 列表"""
        query = self.db.query(
            DeclarationProduct.hs_code,
            DeclarationProduct.website_name
        ).distinct()

        if keyword:
            query = query.filter(
                DeclarationProduct.hs_code.contains(keyword) |
                DeclarationProduct.website_name.contains(keyword) |
                DeclarationProduct.product_name.contains(keyword)
            )

        results = query.all()

        hs_codes = []
        for hs_code, website_name in results:
            product_count = self.db.query(DeclarationProduct).filter(
                DeclarationProduct.hs_code == hs_code
            ).count()
            hs_codes.append({
                "hs_code": hs_code,
                "website_name": website_name,
                "product_count": product_count
            })

        return sorted(hs_codes, key=lambda x: x["hs_code"])

    def get_hs_code_detail(self, hs_code: str) -> Optional[dict]:
        """获取 HS Code 详情（字段定义 + 产品列表 + 值）"""
        # 获取字段定义
        fields = self.db.query(HsCodeField).filter(
            HsCodeField.hs_code == hs_code
        ).order_by(HsCodeField.sort_order).all()

        # 获取产品列表
        products = self.db.query(DeclarationProduct).filter(
            DeclarationProduct.hs_code == hs_code
        ).all()

        # 构建产品数据（含要素值）
        product_list = []
        for product in products:
            values = self.db.query(DeclarationValue).filter(
                DeclarationValue.product_id == product.id
            ).all()

            values_dict = {v.field_name: v.field_value for v in values}
            product_list.append({
                "id": product.id,
                "hs_code": product.hs_code,
                "product_name": product.product_name,
                "website_name": product.website_name,
                "product_description": product.product_description,
                "values": values_dict
            })

        # 获取网站名称和描述（从第一个产品或字段定义中获取）
        website_name = None
        description = None
        if product_list:
            website_name = product_list[0].get("website_name")
            description = product_list[0].get("product_description")

        return {
            "hs_code": hs_code,
            "website_name": website_name,
            "description": description,
            "fields": [
                {
                    "field_name": f.field_name,
                    "field_type": f.field_type,
                    "sort_order": f.sort_order,
                    "is_required": bool(f.is_required)
                }
                for f in fields
            ],
            "products": product_list
        }

    def create_product(self, hs_code: str, product_name: str, 
                      website_name: Optional[str] = None,
                      product_description: Optional[str] = None) -> dict:
        """新增产品"""
        # 检查是否已存在
        existing = self.db.query(DeclarationProduct).filter(
            DeclarationProduct.hs_code == hs_code,
            DeclarationProduct.product_name == product_name
        ).first()

        if existing:
            raise ValueError(f"产品已存在: {hs_code} - {product_name}")

        product = DeclarationProduct(
            hs_code=hs_code,
            product_name=product_name,
            website_name=website_name,
            product_description=product_description
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)

        return {
            "id": product.id,
            "hs_code": product.hs_code,
            "product_name": product.product_name,
            "website_name": product.website_name,
            "product_description": product.product_description,
            "values": {}
        }

    def update_product(self, product_id: int, 
                      product_name: Optional[str] = None,
                      website_name: Optional[str] = None,
                      product_description: Optional[str] = None) -> dict:
        """更新产品信息"""
        product = self.db.query(DeclarationProduct).filter(
            DeclarationProduct.id == product_id
        ).first()

        if not product:
            raise ValueError(f"产品不存在: ID {product_id}")

        if product_name is not None:
            product.product_name = product_name
        if website_name is not None:
            product.website_name = website_name
        if product_description is not None:
            product.product_description = product_description

        self.db.commit()
        self.db.refresh(product)

        values = self.db.query(DeclarationValue).filter(
            DeclarationValue.product_id == product.id
        ).all()
        values_dict = {v.field_name: v.field_value for v in values}

        return {
            "id": product.id,
            "hs_code": product.hs_code,
            "product_name": product.product_name,
            "website_name": product.website_name,
            "product_description": product.product_description,
            "values": values_dict
        }

    def delete_product(self, product_id: int) -> bool:
        """删除产品"""
        product = self.db.query(DeclarationProduct).filter(
            DeclarationProduct.id == product_id
        ).first()

        if not product:
            return False

        self.db.delete(product)
        self.db.commit()
        return True

    def update_values(self, product_id: int, values: Dict[str, str]) -> dict:
        """批量更新产品要素值"""
        product = self.db.query(DeclarationProduct).filter(
            DeclarationProduct.id == product_id
        ).first()

        if not product:
            raise ValueError(f"产品不存在: ID {product_id}")

        for field_name, field_value in values.items():
            existing = self.db.query(DeclarationValue).filter(
                DeclarationValue.product_id == product_id,
                DeclarationValue.field_name == field_name
            ).first()

            if existing:
                existing.field_value = field_value
            else:
                new_value = DeclarationValue(
                    product_id=product_id,
                    field_name=field_name,
                    field_value=field_value
                )
                self.db.add(new_value)

        self.db.commit()

        # 返回更新后的值
        all_values = self.db.query(DeclarationValue).filter(
            DeclarationValue.product_id == product_id
        ).all()
        values_dict = {v.field_name: v.field_value for v in all_values}

        return {
            "id": product.id,
            "hs_code": product.hs_code,
            "product_name": product.product_name,
            "website_name": product.website_name,
            "product_description": product.product_description,
            "values": values_dict
        }

    def create_field(self, hs_code: str, field_name: str,
                    field_type: str = "text",
                    sort_order: int = 0,
                    is_required: bool = False) -> dict:
        """新增字段定义"""
        existing = self.db.query(HsCodeField).filter(
            HsCodeField.hs_code == hs_code,
            HsCodeField.field_name == field_name
        ).first()

        if existing:
            raise ValueError(f"字段已存在: {hs_code} - {field_name}")

        field = HsCodeField(
            hs_code=hs_code,
            field_name=field_name,
            field_type=field_type,
            sort_order=sort_order,
            is_required=int(is_required)
        )
        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)

        return {
            "field_name": field.field_name,
            "field_type": field.field_type,
            "sort_order": field.sort_order,
            "is_required": bool(field.is_required)
        }

    def update_field(self, field_id: int,
                    field_name: Optional[str] = None,
                    field_type: Optional[str] = None,
                    sort_order: Optional[int] = None,
                    is_required: Optional[bool] = None) -> dict:
        """更新字段定义"""
        field = self.db.query(HsCodeField).filter(
            HsCodeField.id == field_id
        ).first()

        if not field:
            raise ValueError(f"字段不存在: ID {field_id}")

        if field_name is not None:
            field.field_name = field_name
        if field_type is not None:
            field.field_type = field_type
        if sort_order is not None:
            field.sort_order = sort_order
        if is_required is not None:
            field.is_required = int(is_required)

        self.db.commit()
        self.db.refresh(field)

        return {
            "field_name": field.field_name,
            "field_type": field.field_type,
            "sort_order": field.sort_order,
            "is_required": bool(field.is_required)
        }

    def delete_field(self, field_id: int) -> bool:
        """删除字段定义"""
        field = self.db.query(HsCodeField).filter(
            HsCodeField.id == field_id
        ).first()

        if not field:
            return False

        self.db.delete(field)
        self.db.commit()
        return True
