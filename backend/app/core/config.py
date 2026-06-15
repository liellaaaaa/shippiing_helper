# backend/app/core/config.py
from pathlib import Path
import os

# ROOT = backend/app/core/ 向上4级 = 项目根目录
ROOT = Path(__file__).parent.parent.parent.parent.resolve()

TEMPLATES = {
    "booking": str(ROOT / "references" / "长晟出口海运BOOKING模板.xls"),
    "booking_xlsx": str(ROOT / "references" / "长晟出口海运BOOKING模板.xlsx"),
    "booking_marked": str(ROOT / "references" / "长晟出口海运BOOKING模板-已标记.xlsx"),
    "loi":     str(ROOT / "references" / "LOI-op-非危险品保函模板.docx"),
    "msds":    str(ROOT / "references" / "MSDS" / "MSDS标准模板.docx"),
    "customs": str(ROOT / "references" / "出口报关资料 26.3.17.xlsx"),
}

REFERENCES_DIR = str(ROOT / "references")
MSDS_DIR = str(ROOT / "references" / "MSDS")
# MSDS standard template — prefer the pre-built .docx if it exists, otherwise auto-generated
_MSDS_TEMPLATE_DEFAULT = str(ROOT / "references" / "MSDS" / "MSDS标准模板.docx")
TRANSPORT_REPORTS_DIR = str(ROOT / "references" / "海运鉴定报告")
EXPORT_CODES_FILE = str(ROOT / "references" / "2024.12.5 最新出口商品编码及报关成分.xlsx")
CUSTOMS_CODES_JSON = str(ROOT / "references" / "customs_codes.json")

DOCS_DIR = os.path.join(ROOT, "data", "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

DOCUMENT_SERVER_URL = os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080")
ONLYOFFICE_SECRET_KEY = os.getenv("ONLYOFFICE_SECRET_KEY", "shipping-helper-secret-key")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
