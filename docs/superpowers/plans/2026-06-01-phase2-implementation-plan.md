# Phase 2 文档生成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans

**Goal:** 实现 Phase 2 文档生成工作流 — 左侧参考面板 + 右侧 OnlyOffice 编辑器，支持 LOI 保函 / 订舱单 / MSDS 三种文档的生成、编辑、版本管理

**Architecture:** 后端 FastAPI + 前端 Vue 3 + OnlyOffice DocumentServer (Docker)。文档流：Phase 1 数据 → 后端渲染模板 → JWT 授权 → OnlyOffice iframe 编辑 → 回调保存（含 content_hash 幂等校验）→ 数据库版本归档

**Tech Stack:** FastAPI + SQLAlchemy + SQLite + openpyxl + python-docx + PyPDF2 + python-jose + OnlyOffice (Docker)

---

## Sprint 1: 基础设施与数据底座（Infrastructure & Data）

**目标：** 跑通后端依赖，确保文件读写和数据库操作正常。不涉及 OnlyOffice 连接。

### Task 1: 模板路径配置

**Files:**
- Create: `backend/app/core/config.py`

```python
# backend/app/core/config.py
from pathlib import Path
import os

ROOT = Path(__file__).parent.parent.parent.resolve()

TEMPLATES = {
    "booking": str(ROOT / "参考/02.订舱出货/长晟出口海运BOOKING模板.xlsx"),
    "loi":     str(ROOT / "参考/02.订舱出货/源文件/LOI-op-非危险品保函模板.docx"),
    "msds":    str(ROOT / "参考/02.订舱出货/MSDS标准模板.docx"),
}

MSDS_DIR = str(ROOT / "参考/02.订舱出货/源文件/MSDS")
EXPORT_CODES_FILE = str(ROOT / "参考/02.订舱出货/2024.12.5 最新出口商品编码及报关成分.xlsx")

DOCS_DIR = os.path.join(ROOT, "data", "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

DOCUMENT_SERVER_URL = os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080")
ONLYOFFICE_SECRET_KEY = os.getenv("ONLYOFFICE_SECRET_KEY", "shipping-helper-secret-key")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

**验收：** `python -c "from app.core.config import TEMPLATES; print(TEMPLATES['booking'])"` 不报错。

---

### Task 2: ShipmentDoc 模型（版本存储）

**Files:**
- Create: `backend/app/models/shipment_doc.py`

```python
# backend/app/models/shipment_doc.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ShipmentDoc(Base):
    __tablename__ = "shipment_docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_key = Column(String(100), nullable=False, index=True)
    doc_type = Column(String(20), nullable=False)
    order_id = Column(Integer, nullable=True)
    file_blob = Column(Text, nullable=False)
    content_hash = Column(String(32), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    file_name = Column(String(200), nullable=False)
    change_reason = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
```

**验收：** `python -c "from app.models.shipment_doc import ShipmentDoc; from app.database import engine, Base; Base.metadata.create_all(engine); print('OK')"`

---

### Task 3: ExportCodesService（出口商品编码查询）

**Files:**
- Create: `backend/app/services/export_codes_service.py`

```python
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
```

**验收：** `python -c "from app.services.export_codes_service import ExportCodesService; s=ExportCodesService(); r=s.find_by_internal_code('F-380-1'); print(r['export_hs_code'] if r else 'NOT FOUND')"`

---

### Task 4: find_marker_cell + clear_markers 工具函数

**Files:**
- Create: `backend/app/services/document_service.py`（工具函数部分）

```python
# backend/app/services/document_service.py
import openpyxl
from typing import Tuple


def find_marker_cell(ws, marker_text: str) -> Tuple[int, int]:
    """在 worksheet 中搜索 {{MARK_XXX}} 锚点，返回 (row, column)，1-based。"""
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and str(cell.value).strip() == marker_text:
                return cell.row, cell.column
    raise ValueError(f"Marker '{marker_text}' not found in template")


def clear_markers(ws):
    """渲染后清除所有 {{MARK_XXX}} 锚点。"""
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("{{MARK_"):
                cell.value = None
```

**验证：** `python -c "from app.services.document_service import find_marker_cell, clear_markers; import openpyxl; from app.core.config import TEMPLATES; wb = openpyxl.load_workbook(TEMPLATES['booking']); ws = wb.active; row, col = find_marker_cell(ws, '{{MARK_SHIPPER}}'); print(f'Found at row={row}, col={col}'); clear_markers(ws); print('Markers cleared')"`

---

## Sprint 2: 文档引擎与 API 接口（Engine & API）

### Task 5: DocumentService（完整实现）

追加完整 DocumentService 类到 `backend/app/services/document_service.py`：

```python
# 追加到 document_service.py

import os, time, base64
from io import BytesIO
import openpyxl
from docx import Document
from app.core.config import TEMPLATES, DOCS_DIR
from app.services.msds_service import MSDSService
from app.database import SessionLocal
from app.models.order_pi_record import OrderPiRecord
from app.models.pi_contract import PiContract


class DocumentService:
    def __init__(self):
        self.msds_service = MSDSService()

    def generate_booking(self, order_id: int) -> tuple[bytes, str, str]:
        template_path = TEMPLATES["booking"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Booking template not found: {template_path}")
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active
        db = SessionLocal()
        try:
            record = db.query(OrderPiRecord).filter(OrderPiRecord.id == order_id).first()
            pi = None
            if record and record.pi_no:
                pi = db.query(PiContract).filter(PiContract.pi_no == record.pi_no).first()
            shipper_row, shipper_col = find_marker_cell(ws, "{{MARK_SHIPPER}}")
            port_row, port_col = find_marker_cell(ws, "{{MARK_PORT}}")
            goods_row, goods_col = find_marker_cell(ws, "{{MARK_GOODS_TABLE}}")
            ws.cell(shipper_row, shipper_col + 1).value = "HONGHAO CHEMICAL CO., LTD."
            ws.cell(shipper_row, shipper_col + 2).value = "广东省清远市清新区太和镇百合花园综合楼"
            ws.cell(shipper_row, shipper_col + 3).value = "TEL: 0763-6866888"
            if pi:
                ws.cell(shipper_row + 1, shipper_col + 1).value = pi.consignee_name or ""
                ws.cell(shipper_row + 1, shipper_col + 2).value = pi.consignee_address or ""
                ws.cell(port_row, port_col + 1).value = pi.destination or ""
            if record:
                items = [(record.product_cn or "", record.product_en or "",
                          record.hs_code or "", record.gross_weight_kg or 0, record.volume_cbm or 0)]
            else:
                items = []
            for i, (cn, en, hs, gw, vol) in enumerate(items):
                r = goods_row + i
                ws.cell(r, goods_col).value = cn
                ws.cell(r, goods_col + 1).value = en
                ws.cell(r, goods_col + 2).value = hs
                ws.cell(r, goods_col + 3).value = gw
                ws.cell(r, goods_col + 4).value = vol
            clear_markers(ws)
            buf = BytesIO()
            wb.save(buf)
            content = buf.getvalue()
        finally:
            db.close()
        doc_key = f"booking_{order_id}_{int(time.time())}"
        doc_path = os.path.join(DOCS_DIR, doc_key + ".xlsx")
        os.makedirs(DOCS_DIR, exist_ok=True)
        with open(doc_path, "wb") as f:
            f.write(content)
        return content, doc_key, base64.b64encode(content).decode()

    def generate_loi(self, order_id: int, pi_no: str) -> tuple[bytes, str, str]:
        template_path = TEMPLATES["loi"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"LOI template not found: {template_path}")
        db = SessionLocal()
        try:
            record = db.query(OrderPiRecord).filter(OrderPiRecord.id == order_id).first()
            pi = db.query(PiContract).filter(PiContract.pi_no == pi_no).first() if pi_no else None
            doc = Document(template_path)
            replacements = {
                "{{shipper}}": "HONGHAO CHEMICAL CO., LTD.",
                "{{consignee}}": pi.consignee_name if pi else "",
                "{{consignee_address}}": pi.consignee_address if pi else "",
                "{{port_of_discharge}}": pi.destination if pi else "",
                "{{product_name_cn}}": record.product_cn if record else "",
                "{{product_name_en}}": record.product_en if record else "",
                "{{hs_code}}": record.hs_code if record else "",
                "{{gross_weight}}": str(record.gross_weight_kg) if record and record.gross_weight_kg else "",
                "{{volume}}": str(record.volume_cbm) if record and record.volume_cbm else "",
                "{{date}}": time.strftime("%Y 年 %m 月 %d 日"),
            }
            for para in doc.paragraphs:
                for key, val in replacements.items():
                    if key in para.text:
                        for run in para.runs:
                            if key in run.text:
                                run.text = run.text.replace(key, val)
            buf = BytesIO()
            doc.save(buf)
            content = buf.getvalue()
        finally:
            db.close()
        doc_key = f"loi_{order_id}_{int(time.time())}"
        doc_path = os.path.join(DOCS_DIR, doc_key + ".docx")
        with open(doc_path, "wb") as f:
            f.write(content)
        return content, doc_key, base64.b64encode(content).decode()

    def generate_msds(self, product_name: str) -> tuple[bytes, str, str]:
        template_path = TEMPLATES["msds"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"MSDS template not found: {template_path}")
        db = SessionLocal()
        try:
            msds_index = self.msds_service.get_msds_by_product(product_name, db)
            doc = Document(template_path)
            tables = doc.tables
            if msds_index and tables:
                text = self.msds_service.extract_text(msds_index.file_path)
                composition = self.msds_service.extract_composition_table(text)
                props = self.msds_service.extract_physical_props(text)
                if len(tables) >= 1:
                    t0 = tables[0]
                    t0.cell(0, 1).text = props.get("physical_form", "")
                    t0.cell(1, 1).text = props.get("ion_type", "")
                    t0.cell(2, 1).text = props.get("ph", "")
                if len(tables) >= 2:
                    comp_table = tables[1]
                    for i, item in enumerate(composition):
                        if i >= len(comp_table.rows):
                            break
                        row = comp_table.rows[i]
                        row.cells[0].text = str(i + 1)
                        row.cells[1].text = item.get("component", "")
                        row.cells[2].text = item.get("cas", "")
                        row.cells[3].text = item.get("percentage", "")
            buf = BytesIO()
            doc.save(buf)
            content = buf.getvalue()
        finally:
            db.close()
        doc_key = f"msds_{product_name}_{int(time.time())}"
        doc_path = os.path.join(DOCS_DIR, doc_key + ".docx")
        with open(doc_path, "wb") as f:
            f.write(content)
        return content, doc_key, base64.b64encode(content).decode()
```

---

### Task 6: OnlyOffice JWT + Callback（含幂等校验）

**Files:**
- Create: `backend/app/services/onlyoffice_service.py`
- Create: `backend/app/api/v1/onlyoffice.py`

```python
# backend/app/services/onlyoffice_service.py
import os
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import DOCUMENT_SERVER_URL, ONLYOFFICE_SECRET_KEY, API_BASE_URL


class OnlyOfficeService:
    def generate_jwt_token(self, document_key: str, file_type: str) -> str:
        now = datetime.utcnow()
        payload = {
            "document": {
                "key": document_key,
                "title": f"Document.{file_type}",
                "fileType": file_type,
                "callbackUrl": f"{API_BASE_URL}/api/v1/onlyoffice/callback?doc_key={document_key}",
            },
            "user": {"name": "admin", "id": "1"},
            "editorConfig": {
                "callbackUrl": f"{API_BASE_URL}/api/v1/onlyoffice/callback?doc_key={document_key}",
                "mode": "edit",
            },
            "iat": now,
            "exp": now + timedelta(hours=2),
        }
        return jwt.encode(payload, ONLYOFFICE_SECRET_KEY, algorithm="HS256")

    def build_editor_config(self, token: str, document_key: str, doc_type: str) -> dict:
        return {
            "token": token,
            "documentServerUrl": DOCUMENT_SERVER_URL,
            "documentKey": document_key,
            "docType": doc_type,
        }
```

```python
# backend/app/api/v1/onlyoffice.py
import os, hashlib, base64
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc
from app.database import SessionLocal
from app.models.shipment_doc import ShipmentDoc
from app.services.onlyoffice_service import OnlyOfficeService

router = APIRouter(prefix="/api/v1/onlyoffice", tags=["onlyoffice"])


def infer_doc_type(doc_key: str) -> str:
    if doc_key.startswith("booking"): return "booking"
    if doc_key.startswith("loi"): return "loi"
    return "msds"


def extract_order_id_from_key(doc_key: str):
    parts = doc_key.split("_")
    if len(parts) >= 2:
        try: return int(parts[1])
        except ValueError: pass
    return None


@router.post("/jwt")
async def create_jwt(documentKey: str = Query(...), fileType: str = Query(...)):
    svc = OnlyOfficeService()
    token = svc.generate_jwt_token(documentKey, fileType)
    config = svc.build_editor_config(token, documentKey, fileType)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{documentKey}"}


@router.post("/callback")
async def onlyoffice_callback(doc_key: str = Query(...), user: str = Query(default="admin"), file: UploadFile = File(...)):
    content = await file.read()
    content_hash = hashlib.md5(content).hexdigest()
    db = SessionLocal()
    try:
        last_doc = db.query(ShipmentDoc).filter(
            ShipmentDoc.doc_key == doc_key
        ).order_by(desc(ShipmentDoc.version)).first()
        if last_doc and last_doc.content_hash == content_hash:
            return {"error": 0}
        version = (last_doc.version + 1) if last_doc else 1
        new_doc = ShipmentDoc(
            doc_key=doc_key,
            doc_type=infer_doc_type(doc_key),
            order_id=extract_order_id_from_key(doc_key),
            file_blob=base64.b64encode(content).decode(),
            content_hash=content_hash,
            version=version,
            file_name=f"{doc_key}_v{version}",
            created_by=user,
        )
        db.add(new_doc)
        db.commit()
        return {"error": 0}
    finally:
        db.close()


@router.get("/download/{doc_key}")
async def download_doc(doc_key: str):
    db = SessionLocal()
    try:
        doc = db.query(ShipmentDoc).filter(
            ShipmentDoc.doc_key == doc_key
        ).order_by(desc(ShipmentDoc.version)).first()
        if not doc:
            return {"error": "Document not found"}
        content = base64.b64decode(doc.file_blob)
        suffix = doc_key.split(".")[-1] if "." in doc_key else "bin"
        return FileResponse(BytesIO(content), media_type="application/octet-stream", filename=f"{doc_key}.{suffix}")
    finally:
        db.close()
```

**幂等性验证：**
```bash
echo "test" | curl -X POST "http://localhost:8000/api/v1/onlyoffice/callback?doc_key=test123" --data-binary @-
echo "test" | curl -X POST "http://localhost:8000/api/v1/onlyoffice/callback?doc_key=test123" --data-binary @-
# 两次都返回 {"error":0}，第二次 version 不增加
```

---

### Task 7: 文档生成 API + MSDS/运输鉴定/出口编码路由

**Files:**
- Create: `backend/app/api/v1/documents.py`
- Create: `backend/app/api/v1/msds.py`
- Create: `backend/app/api/v1/transport.py`
- Create: `backend/app/api/v1/export_codes.py`
- Modify: `backend/app/main.py`（注册路由）

```python
# backend/app/api/v1/documents.py
import os
from fastapi import APIRouter, Query
from sqlalchemy import desc
from app.database import SessionLocal
from app.models.shipment_doc import ShipmentDoc
from app.services.document_service import DocumentService
from app.services.onlyoffice_service import OnlyOfficeService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
oo_svc = OnlyOfficeService()


@router.get("/booking")
async def generate_booking(order_id: int = Query(...)):
    svc = DocumentService()
    _, doc_key, _ = svc.generate_booking(order_id)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "xlsx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "xlsx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}


@router.get("/loi")
async def generate_loi(order_id: int = Query(...), pi_no: str = Query(...)):
    svc = DocumentService()
    _, doc_key, _ = svc.generate_loi(order_id, pi_no)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "docx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "docx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}


@router.get("/msds")
async def generate_msds(product: str = Query(...)):
    svc = DocumentService()
    _, doc_key, _ = svc.generate_msds(product)
    jwt_token = oo_svc.generate_jwt_token(doc_key, "docx")
    config = oo_svc.build_editor_config(jwt_token, doc_key, "docx")
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}


@router.get("/history/{order_id}")
async def get_doc_history(order_id: int):
    db = SessionLocal()
    try:
        docs = db.query(ShipmentDoc).filter(
            ShipmentDoc.order_id == order_id
        ).order_by(desc(ShipmentDoc.created_at)).all()
        return [{"doc_key": d.doc_key, "doc_type": d.doc_type, "version": d.version,
                  "file_name": d.file_name, "created_by": d.created_by,
                  "created_at": d.created_at.isoformat() if d.created_at else None} for d in docs]
    finally:
        db.close()
```

```python
# backend/app/api/v1/msds.py
from fastapi import APIRouter, Query
from app.database import SessionLocal
from app.models.msds_index import MSDSIndex
from app.services.msds_service import MSDSService
from app.core.config import MSDS_DIR

router = APIRouter(prefix="/api/v1/msds", tags=["msds"])


@router.get("/")
async def list_msds(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str = Query("")):
    db = SessionLocal()
    try:
        q = db.query(MSDSIndex)
        if search:
            q = q.filter(MSDSIndex.product_name_cn.ilike(f"%{search}%"))
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return {"items": [{"id": m.id, "filename": m.filename, "product_name_cn": m.product_name_cn,
                             "physical_form": m.physical_form, "ion_type": m.ion_type, "ph": m.ph} for m in items],
                "total": total}
    finally:
        db.close()


@router.get("/{msds_id}/content")
async def get_msds_content(msds_id: int):
    db = SessionLocal()
    try:
        m = db.query(MSDSIndex).filter(MSDSIndex.id == msds_id).first()
        if not m:
            return {"error": "not found"}
        svc = MSDSService()
        text = svc.extract_text(m.file_path)
        composition = svc.extract_composition_table(text)
        props = svc.extract_physical_props(text)
        return {"composition": composition, "physical_props": props}
    finally:
        db.close()


@router.post("/reindex")
async def reindex_msds():
    svc = MSDSService()
    db = SessionLocal()
    try:
        count = svc.index_msds_directory(MSDS_DIR, db)
        return {"indexed": count}
    finally:
        db.close()
```

```python
# backend/app/api/v1/transport.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.transport_service import TransportService
import tempfile, os

router = APIRouter(prefix="/api/v1/transport", tags=["transport"])


@router.post("/upload")
async def upload_transport_report(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF supported")
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(await file.read())
    tmp.close()
    try:
        text = TransportService.extract_text_from_pdf(tmp.name)
        fields = TransportService.extract_fields(text)
        return fields
    finally:
        os.unlink(tmp.name)
```

```python
# backend/app/api/v1/export_codes.py
from fastapi import APIRouter, Query
from app.services.export_codes_service import ExportCodesService

router = APIRouter(prefix="/api/v1/export-codes", tags=["export_codes"])
svc = ExportCodesService()


@router.get("/")
async def get_export_codes(internal_code: str = Query("")):
    if not internal_code:
        return {"error": "internal_code is required"}
    result = svc.find_by_internal_code(internal_code)
    return result or {"error": "not found"}
```

```python
# backend/app/main.py 添加：
from app.api.v1 import documents, msds, transport, export_codes, onlyoffice

app.include_router(documents.router)
app.include_router(msds.router)
app.include_router(transport.router)
app.include_router(export_codes.router)
app.include_router(onlyoffice.router)
```

---

## Sprint 3: 前端集成与交互（Frontend & UX）

### Task 8: 前端 API 客户端

**Files:**
- Create: `frontend/src/api/phase2.ts`

```typescript
// frontend/src/api/phase2.ts
import axios from '@/utils/request'

export const phase2Api = {
  generateBooking(orderId: number) {
    return axios.get('/documents/booking', { params: { order_id: orderId } })
  },
  generateLoi(orderId: number, piNo: string) {
    return axios.get('/documents/loi', { params: { order_id: orderId, pi_no: piNo } })
  },
  generateMsds(product: string) {
    return axios.get('/documents/msds', { params: { product } })
  },
  getDocHistory(orderId: number) {
    return axios.get(`/documents/history/${orderId}`)
  },
  listMsds(params: { page?: number; pageSize?: number; search?: string }) {
    return axios.get('/msds', { params })
  },
  getMsdsContent(id: number) {
    return axios.get(`/msds/${id}/content`)
  },
  reindexMsds() {
    return axios.post('/msds/reindex')
  },
  uploadTransportReport(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post('/transport/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getExportCodes(internalCode: string) {
    return axios.get('/export-codes', { params: { internal_code: internalCode } })
  },
  getJwt(documentKey: string, fileType: string) {
    return axios.post('/onlyoffice/jwt', null, { params: { documentKey, fileType } })
  },
}
```

---

### Task 9: OnlyOffice 编辑器封装（10秒超时检测）

**Files:**
- Create: `frontend/src/views/phase2/components/DocumentEditor.vue`

```vue
<template>
  <div class="document-editor">
    <div v-if="!editorReady" class="editor-loading">
      <el-skeleton :rows="10" animated />
      <div class="loading-hint">正在连接文档服务器...</div>
    </div>
    <iframe
      v-show="editorReady"
      ref="iframeRef"
      :src="editorUrl"
      class="editor-iframe"
      frameborder="0"
      allowfullscreen
      @load="onIframeLoad"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  documentServerUrl: string
  docKey: string
  token: string
  downloadUrl: string
}>()

const editorReady = ref(false)
let loadingTimer: ReturnType<typeof setTimeout>

const editorUrl = computed(() => {
  const base = props.documentServerUrl.replace(/\/$/, '')
  return `${base}/apps/documenteditor/main.html?docKey=${props.docKey}&token=${props.token}&downloadUrl=${encodeURIComponent(props.downloadUrl)}`
})

function onIframeLoad() {
  editorReady.value = true
  clearTimeout(loadingTimer)
}

onMounted(() => {
  loadingTimer = setTimeout(() => {
    if (!editorReady.value) {
      ElMessage.error('文档服务器连接超时，请刷新重试')
    }
  }, 10000)
})

onUnmounted(() => {
  clearTimeout(loadingTimer)
})
</script>

<style scoped>
.document-editor { width: 100%; height: 100%; position: relative; }
.editor-iframe { width: 100%; height: 100%; min-height: 600px; }
.editor-loading { padding: 24px; }
.loading-hint { text-align: center; color: #999; margin-top: 16px; font-size: 14px; }
</style>
```

---

### Task 10: 参考面板组件（4个Tab，运输鉴定可编辑）

**Files:**
- Create: `frontend/src/views/phase2/components/ReferencePanel.vue`

核心要求：
- 4 个 el-collapse-item：Phase1数据 / MSDS摘要 / 运输鉴定 / 出口编码
- 运输鉴定区域所有字段用 `el-input`（非 readonly），允许手动修正
- 每行字段有复制图标按钮，`ElMessage.success('已复制')`
- Phase1数据：挂载时调用 `/api/v1/merge/orders/{orderId}/comparison` 获取完整数据

---

### Task 11: Phase2Workflow 主页面

**Files:**
- Create: `frontend/src/views/phase2/Phase2Workflow.vue`

布局：顶部工具栏 + 左侧参考面板（35%）+ 右侧编辑器（65%）+ 底部操作栏

关键逻辑：
- 路由 query 读取 `orderId`
- 订单下拉变化 -> `/api/v1/merge/orders/{id}/comparison` 获取商品列表
- 点击"订舱单"/"LOI"/"MSDS" -> 更新 `currentDocKey` + `currentConfig` -> DocumentEditor 重新渲染

---

### Task 12: 路由更新 + Phase1Workflow 添加进入按钮

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/phase1/Phase1Workflow.vue`

```typescript
// router/index.ts 添加导入和路由：
import Phase2Workflow from '@/views/phase2/Phase2Workflow.vue'
// children 数组添加：
{ path: 'phase2', name: 'Phase2Workflow', component: Phase2Workflow, meta: { title: '文档编辑' } }
```

```html
<!-- Phase1Workflow.vue 底部操作栏添加： -->
<el-button type="primary" @click="$router.push({ path: '/phase2', query: { orderId: currentOrderId } })">
  进入文档编辑 →
</el-button>
```

---

## Sprint 验收标准

### Sprint 1 验收
- [ ] `python -c "from app.core.config import TEMPLATES; print(TEMPLATES['booking'])"` 不报错
- [ ] `data/shipping_helper.db` 中 `shipment_docs` 表存在
- [ ] `ExportCodesService.find_by_internal_code('F-380-1')` 返回正确 HS Code
- [ ] `find_marker_cell(ws, '{{MARK_SHIPPER}}')` 正确返回坐标

### Sprint 2 验收
- [ ] `http://localhost:8000/docs` 可打开 Swagger
- [ ] `GET /api/v1/documents/booking?order_id=1` 返回 `{token, documentKey, downloadUrl}`
- [ ] Callback 幂等：两次相同内容保存，第二次 version 不增加
- [ ] `data/docs/` 下生成了 `.xlsx` / `.docx` 文件

### Sprint 3 验收
- [ ] `npm run dev` 启动成功
- [ ] 访问 `/phase2?orderId=1`，左侧显示 Phase1 数据
- [ ] 点击"订舱单"，右侧加载 OnlyOffice 编辑器
- [ ] 10 秒超时弹出 ElMessage.error

---

## 环境变量（.env）

```
DOCUMENT_SERVER_URL=http://localhost:8080
ONLYOFFICE_SECRET_KEY=shipping-helper-secret-key
API_BASE_URL=http://localhost:8000
```

## DevOps 注意事项

1. **OnlyOffice Docker 网络**：Docker 容器需访问宿主机 8000 端口。`docker-compose.yml` 添加：
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

2. **MSDS 标准模板**：`参考/02.订舱出货/MSDS标准模板.docx` 需人工制作，预置 15 行空白成分表。否则后端启动不报错，但生成 MSDS 时 404。
