"""MSDS ledger service layer."""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.msds_ledger import MsdsLedger


class MsdsLedgerService:

    def list_ledger(self, db: Session, keyword: Optional[str] = None, internal_code: Optional[str] = None) -> list:
        query = db.query(MsdsLedger)
        if internal_code:
            query = query.filter(MsdsLedger.internal_code == internal_code)
        elif keyword:
            like_pattern = f"%{keyword}%"
            query = query.filter(
                (MsdsLedger.customs_name.like(like_pattern)) |
                (MsdsLedger.internal_code.like(like_pattern)) |
                (MsdsLedger.product_name_en.like(like_pattern))
            )
        return query.order_by(MsdsLedger.customs_name).all()

    def get_ledger(self, db: Session, ledger_id: int) -> Optional[MsdsLedger]:
        return db.query(MsdsLedger).filter(MsdsLedger.id == ledger_id).first()

    def create_ledger(self, db: Session, data: dict) -> MsdsLedger:
        now = datetime.utcnow()
        ledger = MsdsLedger(
            internal_code=data.get("internal_code", ""),
            customs_name=data.get("customs_name", ""),
            appearance=data.get("appearance", ""),
            ion_type=data.get("ion_type", ""),
            ph=data.get("ph", ""),
            composition=data.get("composition", []),
            product_name_en=data.get("product_name_en", ""),
            appearance_en=data.get("appearance_en", ""),
            ion_type_en=data.get("ion_type_en", ""),
            version=1, created_at=now, updated_at=now,
        )
        db.add(ledger)
        db.commit()
        db.refresh(ledger)
        return ledger

    def update_ledger(self, db: Session, ledger_id: int, data: dict) -> Optional[MsdsLedger]:
        ledger = db.query(MsdsLedger).filter(MsdsLedger.id == ledger_id).first()
        if not ledger:
            return None
        for field in ["internal_code", "customs_name", "appearance", "ion_type", "ph", "composition", "product_name_en", "appearance_en", "ion_type_en"]:
            if field in data:
                setattr(ledger, field, data[field])
        ledger.version += 1
        ledger.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ledger)
        return ledger

    def delete_ledger(self, db: Session, ledger_id: int) -> bool:
        ledger = db.query(MsdsLedger).filter(MsdsLedger.id == ledger_id).first()
        if not ledger:
            return False
        db.delete(ledger)
        db.commit()
        return True


msds_ledger_svc = MsdsLedgerService()
