"""Declaration element service layer."""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.reference_data import DeclarationElement


class DeclarationElementService:

    def list_elements(self, db: Session, keyword: Optional[str] = None, page: int = 1, size: int = 50):
        query = db.query(DeclarationElement)
        if keyword:
            like_pattern = f"%{keyword}%"
            query = query.filter(
                (DeclarationElement.hs_code.like(like_pattern)) |
                (DeclarationElement.declaration_name.like(like_pattern))
            )
        total = query.count()
        items = query.order_by(DeclarationElement.hs_code, DeclarationElement.declaration_name) \
            .offset((page - 1) * size).limit(size).all()
        return items, total

    def get_element(self, db: Session, element_id: int) -> Optional[DeclarationElement]:
        return db.query(DeclarationElement).filter(DeclarationElement.id == element_id).first()

    def create_element(self, db: Session, data: dict) -> DeclarationElement:
        existing = db.query(DeclarationElement).filter(
            DeclarationElement.hs_code == data["hs_code"],
            DeclarationElement.declaration_name == data["declaration_name"],
        ).first()
        if existing:
            raise ValueError(f"已存在相同的记录 (HS Code: {data['hs_code']}, 申报名称: {data['declaration_name']})")
        element = DeclarationElement(
            hs_code=data["hs_code"],
            declaration_name=data["declaration_name"],
            elements_text=data.get("elements_text", ""),
        )
        db.add(element)
        db.commit()
        db.refresh(element)
        self._reset_cache()
        return element

    def update_element(self, db: Session, element_id: int, data: dict) -> Optional[DeclarationElement]:
        element = db.query(DeclarationElement).filter(DeclarationElement.id == element_id).first()
        if not element:
            return None
        if "hs_code" in data:
            element.hs_code = data["hs_code"]
        if "declaration_name" in data:
            element.declaration_name = data["declaration_name"]
        if "elements_text" in data:
            element.elements_text = data["elements_text"]
        db.commit()
        db.refresh(element)
        self._reset_cache()
        return element

    def delete_element(self, db: Session, element_id: int) -> bool:
        element = db.query(DeclarationElement).filter(DeclarationElement.id == element_id).first()
        if not element:
            return False
        db.delete(element)
        db.commit()
        self._reset_cache()
        return True

    @staticmethod
    def _reset_cache():
        from app.services.customs_declaration_service import CustomsDeclarationService
        CustomsDeclarationService.reset()


declaration_element_svc = DeclarationElementService()
