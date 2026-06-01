# backend/app/core/config.py
from pathlib import Path
import os

ROOT = Path(__file__).parent.parent.parent.resolve()

TEMPLATES = {
    "booking": str(ROOT / "references" / "长晟出口海运BOOKING模板.xls"),
    "loi":     str(ROOT / "references" / "LOI-op-非危险品保函模板.docx"),
    "msds":    str(ROOT / "references" / "MSDS"),
}

EXPORT_CODES_FILE = str(ROOT / "references" / "2024.12.5 最新出口商品编码及报关成分.xlsx")

DOCS_DIR = os.path.join(ROOT, "data", "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

DOCUMENT_SERVER_URL = os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080")
ONLYOFFICE_SECRET_KEY = os.getenv("ONLYOFFICE_SECRET_KEY", "shipping-helper-secret-key")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")