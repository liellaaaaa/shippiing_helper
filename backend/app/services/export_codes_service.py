# backend/app/services/export_codes_service.py
import openpyxl
from typing import Optional

_cache: dict | None = None


class ExportCodesService:
    @staticmethod
    def _load() -> dict:
        global _cache
        if _cache is not None:
            return _cache
        from app.core.config import EXPORT_CODES_FILE
        wb = openpyxl.load_workbook(EXPORT_CODES_FILE, data_only=True)
        ws = wb.active
        _cache = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            internal_code = str(row[1]).strip() if row[1] else ""
            if not internal_code or internal_code in ("商品编号", "None"):
                continue
            _cache[internal_code] = {
                "internal_code": internal_code,
                "product_name": str(row[3]).strip() if row[3] else "",
                "product_description": str(row[4]).strip() if row[4] else "",
                "export_hs_code": str(row[5]).strip() if row[5] else "",
                "customs_name": str(row[6]).strip() if row[6] else "",
                "components": str(row[7]).strip() if row[7] else "",
            }
        return _cache

    def find_by_internal_code(self, internal_code: str) -> Optional[dict]:
        return self._load().get(internal_code)

    def find_by_product_name(self, product_name: str) -> list[dict]:
        return [v for v in self._load().values() if product_name in v["product_name"]]