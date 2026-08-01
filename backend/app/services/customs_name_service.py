from typing import Optional

from app.database import SessionLocal
from app.models.order import ProductKnowledge


class CustomsNameService:
    _instance: "CustomsNameService | None" = None

    def __init__(self, json_path: str = ""):
        # json_path 参数保留以兼容旧调用点，数据源已改为数据库
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self):
        db = SessionLocal()
        try:
            rows = db.query(ProductKnowledge).all()
            for r in rows:
                key = (r.internal_code or "").strip()
                if not key:
                    continue
                self._cache[key] = {
                    "internal_code": r.internal_code,
                    "product_code": r.hs_code,
                    "customs_name": r.customs_name,
                    "components": r.customs_ingredients,
                    "product_appearance": r.product_appearance,
                }
        finally:
            db.close()

    def lookup(self, internal_code: str) -> Optional[dict]:
        return self._cache.get(internal_code.strip())

    @classmethod
    def get_instance(cls, json_path: str = "") -> "CustomsNameService":
        if cls._instance is None:
            cls._instance = cls(json_path)
        return cls._instance
