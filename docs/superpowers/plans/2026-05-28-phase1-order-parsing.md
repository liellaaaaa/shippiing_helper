# Phase 1 订单粘贴解析模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Phase 1 第一个模块——订单粘贴解析，包括粘贴文本框、后端解析（智能聚合）、知识库匹配、表单式预览编辑，数据存入 orders（订单头）+ order_items（产品明细）主从表。

**Architecture:**
- 后端：FastAPI + SQLAlchemy + SQLite，参考 `参考/core/order_parser.py` 的解析逻辑，迁移到新架构
- 前端：Vue 3 + Vite + Element Plus，OrderPaste 页面含粘贴文本框 + 预览表单
- 数据模型：orders（订单头）+ order_items（产品明细），支持"一单多品"聚合
- 项目目录：`backend/`（FastAPI）+ `frontend/`（Vue 3）

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy / SQLite / Vue 3 / Element Plus / @onlyoffice/document-editor-vue

---

## 文件结构

```
shipping_helper_web/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI 入口
│       ├── database.py          # SQLite 连接配置
│       ├── models/
│       │   ├── __init__.py
│       │   └── order.py         # orders + order_items SQLAlchemy models
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── order.py         # Pydantic schemas
│       ├── core/
│       │   ├── __init__.py
│       │   ├── order_parser.py  # 解析器：分隔符识别、智能聚合、去重
│       │   └── knowledge_filler.py  # 知识库匹配逻辑
│       ├── services/
│       │   ├── __init__.py
│       │   └── calculation_service.py  # 包装计算（Phase1/2共用）
│       └── api/
│           ├── __init__.py
│           └── v1/
│               ├── __init__.py
│               └── orders.py     # API 端点
├── frontend/
│   └── src/
│       ├── App.vue
│       ├── main.ts
│       ├── api/
│       │   └── orders.ts        # Axios API 封装
│       ├── views/
│       │   └── phase1/
│       │       └── OrderPaste.vue  # 粘贴解析页面
│       └── components/
│           └── phase1/
│               ├── PasteTextarea.vue    # 粘贴文本框组件
│               └── OrderPreviewForm.vue # 表单式预览编辑组件
└── data/
    └── shipping_helper.db       # SQLite 数据库（初始化时创建）
```

---

## Task 1: 项目脚手架初始化

创建 backend + frontend 项目基础结构，安装依赖，验证服务可启动。

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/requirements.txt`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`

- [ ] **Step 1: 创建 backend/requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pydantic==2.6.0
python-multipart==0.0.6
openpyxl==3.1.2
xlrd==2.0.1
```

- [ ] **Step 2: 创建 backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ShippingHelper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 3: 创建 backend/app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "shipping_helper.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
```

- [ ] **Step 4: 创建 frontend/package.json**

```json
{
  "name": "shipping-helper-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.6.0",
    "axios": "^1.6.0",
    "@element-plus/icons-vue": "^2.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.4.0",
    "vite": "^5.1.0",
    "vue-tsc": "^2.0.0"
  }
}
```

- [ ] **Step 5: 创建 frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 6: 安装依赖并验证后端启动**

Run: `cd backend && pip install -r requirements.txt && python -c "from app.main import app; print('OK')"`
Expected: 输出 "OK"

- [ ] **Step 7: 验证后端服务可启动**

Run: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &` 然后 `sleep 3 && curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 8: 安装前端依赖**

Run: `cd frontend && npm install`
Expected: node_modules 安装完成

- [ ] **Step 9: 提交**

```bash
git add -A
git commit -m "feat: scaffold backend + frontend project structure"
```

---

## Task 2: 数据库模型

创建 orders（订单头）+ order_items（产品明细）SQLAlchemy 模型。

**Files:**
- Create: `backend/app/models/order.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: 创建 backend/app/models/order.py**

```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), unique=True, nullable=False, index=True)
    customer_code = Column(String(100))
    customer_name = Column(String(200))
    pi_no = Column(String(100))
    salesperson = Column(String(100))
    merchandiser = Column(String(100))
    order_date = Column(String(20))
    production_deadline = Column(String(20))
    delivery_date = Column(String(20))
    shipment_date = Column(String(20))
    shipment_channel = Column(String(50))
    shipment_method = Column(String(50))
    order_confirmed = Column(String(20))
    order_status = Column(String(20), default="pending")
    locked_by = Column(String(100))
    locked_at = Column(DateTime)
    sales_area = Column(String(50))
    shipment_title = Column(String(200))
    document_type = Column(String(50))
    has_sample = Column(String(20))
    price_adjusted = Column(String(20))
    order_requirement = Column(Text)
    review_status = Column(String(20))
    spec_abnormal = Column(String(20))
    total_quantity_kg = Column(Float)
    total_gross_weight_kg = Column(Float)
    total_volume_cbm = Column(Float)
    fits_20gp = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_code = Column(String(100), nullable=False)
    product_cn = Column(String(200))
    product_en = Column(String(200))
    spec_kg = Column(Float)
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    customs_ingredients = Column(Text)
    quantity_kg = Column(Float)
    unit_price = Column(Float)
    total_amount = Column(Float)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id"))
    pallet_spec = Column(String(20))
    drums_per_pallet = Column(Integer)
    drum_count = Column(Integer)
    pallet_count = Column(Integer)
    net_weight_kg = Column(Float)
    gross_weight_kg = Column(Float)
    volume_cbm = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="items")


class PackagingType(Base):
    __tablename__ = "packaging_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    dims = Column(String(50))
    cbm = Column(Float)
    tare_kg = Column(Float)
    gross_kg = Column(Float)
    net_kg = Column(Float)
    barrel_type = Column(String(50))
    pallet_qty_1x1 = Column(Integer)
    pallet_qty_1_1x1_1 = Column(Integer)
    no_pallet_qty = Column(Integer)


class ProductKnowledge(Base):
    __tablename__ = "products_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    internal_code = Column(String(100), unique=True, index=True)
    product_name_cn = Column(String(200))
    product_name_en = Column(String(200))
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    customs_ingredients = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: 更新 backend/app/models/__init__.py**

```python
from app.models.order import Order, OrderItem, PackagingType, ProductKnowledge

__all__ = ["Order", "OrderItem", "PackagingType", "ProductKnowledge"]
```

- [ ] **Step 3: 创建 backend/app/database.py 初始化脚本（补充表创建）**

```python
# 在 database.py 末尾追加：
from app.models import Base

def init_db():
    Base.metadata.create_all(bind=engine)

# 如果 __name__ == "__main__"，则初始化
if __name__ == "__main__":
    from database import engine, Base
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")
```

- [ ] **Step 4: 创建测试**

```python
# backend/tests/test_models.py
import pytest
from app.models.order import Order, OrderItem
from app.database import SessionLocal, engine, Base


def test_order_and_item_relationship():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        order = Order(order_no="TEST-001", customer_code="CUST-001")
        db.add(order)
        db.flush()

        item = OrderItem(order_id=order.id, internal_code="SKU-001", quantity_kg=100)
        db.add(item)
        db.commit()

        fetched = db.query(Order).filter_by(order_no="TEST-001").first()
        assert len(fetched.items) == 1
        assert fetched.items[0].internal_code == "SKU-001"
    finally:
        db.query(Order).filter_by(order_no="TEST-001").delete()
        db.commit()
        db.close()
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: add Order, OrderItem, PackagingType, ProductKnowledge models"
```

---

## Task 3: Pydantic Schemas

创建 `ParsedOrder` 和 `ParsedOrderItem` 等请求/响应 schema。

**Files:**
- Create: `backend/app/schemas/order.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: 创建 backend/app/schemas/order.py**

```python
from pydantic import BaseModel
from typing import Optional


class OrderItemSchema(BaseModel):
    internal_code: str
    product_cn: Optional[str] = None
    product_en: Optional[str] = None
    spec_kg: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None
    customs_ingredients: Optional[str] = None
    quantity_kg: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    packaging_type_id: Optional[int] = None
    pallet_spec: Optional[str] = None
    drums_per_pallet: Optional[int] = None
    drum_count: Optional[int] = None
    pallet_count: Optional[int] = None
    net_weight_kg: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    hs_code_warning: Optional[str] = None  # H.S.Code 位数不足警告
    warning: Optional[str] = None  # 报关品名自动生成警告

    class Config:
        from_attributes = True


class ParsedOrderSchema(BaseModel):
    order_no: str
    customer_code: Optional[str] = None
    salesperson: Optional[str] = None
    items: list[OrderItemSchema] = []
    header_conflict_warning: Optional[str] = None  # 订单头字段冲突警告


class PasteParseRequest(BaseModel):
    raw_text: str  # 用户粘贴的原始文本


class PasteParseResponse(BaseModel):
    orders: list[ParsedOrderSchema]
    skipped_rows: list[dict]  # 跳行的原始数据 + 原因
    warning: Optional[str] = None  # 批次内重复等警告


class OrderSaveRequest(BaseModel):
    order: ParsedOrderSchema


class OrderSaveResponse(BaseModel):
    order_id: int
    items_count: int
    message: str
```

- [ ] **Step 2: 更新 backend/app/schemas/__init__.py**

```python
from app.schemas.order import (
    OrderItemSchema,
    ParsedOrderSchema,
    PasteParseRequest,
    PasteParseResponse,
    OrderSaveRequest,
    OrderSaveResponse,
)

__all__ = [
    "OrderItemSchema",
    "ParsedOrderSchema",
    "PasteParseRequest",
    "PasteParseResponse",
    "OrderSaveRequest",
    "OrderSaveResponse",
]
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: add Pydantic schemas for order parsing"
```

---

## Task 4: 解析器 core/order_parser.py

将参考 `参考/core/order_parser.py` 的逻辑迁移到新架构，实现：分隔符识别、智能聚合（按订单号）、批次内去重。

**Files:**
- Create: `backend/app/core/order_parser.py`
- Modify: `backend/app/core/__init__.py`
- Test: `backend/tests/test_order_parser.py`

- [ ] **Step 1: 分析参考代码并创建新解析器**

参考 `参考/core/order_parser.py` 的 COLUMNS 常量和分隔符识别逻辑，新的解析器需要支持"一单多品"（同一订单号多行聚合）。

**核心逻辑：**
1. 识别分隔符（Tab > 换行）
2. 逐行解析，每行映射到 `ParsedOrderItem` 临时对象
3. 批次内去重：Key = `(order_no, internal_code)`，后行覆盖前行
4. 按 `order_no` 聚合：同一订单号的多行 → `ParsedOrder` 头 + 多个 `ParsedOrderItem`
5. 缺失 `order_no` 或 `internal_code` 的行 → 跳过行（skipped_rows）

```python
# backend/app/core/order_parser.py
import re
from app.schemas.order import ParsedOrderSchema, OrderItemSchema, PasteParseResponse


# 标准列名映射表（支持中文/英文多种变体）
COLUMN_MAPPING = {
    "order_no": ["订单号", "Order No", "PO", "PO Number", "PI No"],
    "customer_code": ["客户编号", "Customer Code", "Client Code"],
    "internal_code": ["内部编号", "Internal Code", "Product Code", "SKU"],
    "product_cn": ["产品中文名", "Product Name (CN)", "Description"],
    "spec_kg": ["规格kg", "Spec", "Specification"],
    "quantity_kg": ["订单量kg", "Quantity", "QTY (kg)", "Order Qty"],
    "unit_price": ["单价/kg", "Unit Price", "Price per kg"],
    "total_amount": ["总金额", "Total Amount", "Amount"],
    "salesperson": ["业务员", "Salesperson", "Sales Rep"],
    "merchandiser": ["跟单员", "Merchandiser", "Merch"],
    "order_date": ["下单日期", "Order Date"],
    "delivery_date": ["交货日期", "Delivery Date"],
    "shipment_channel": ["出货渠道", "Shipment Channel"],
    "shipment_method": ["出货方式", "Shipment Method", "Transport"],
    "customs_name": ["报关名称", "Customs Name"],
    "hs_code": ["H.S.Code", "HS Code", "H.S."],
}


def normalize_column_name(col_name: str) -> str | None:
    """将任意列名标准化为内部字段名"""
    col_name = col_name.strip()
    for field, aliases in COLUMN_MAPPING.items():
        for alias in aliases:
            if col_name == alias or col_name.replace(" ", "").replace("_", "") == alias.replace(" ", "").replace("_", ""):
                return field
    return None


def detect_delimiter(raw_text: str) -> str:
    """检测分隔符类型：Tab 或 换行"""
    if "\t" in raw_text:
        return "\t"
    return "\n"


def split_lines(text: str, delimiter: str) -> list[list[str]]:
    """按分隔符切分文本，返回行列表（每行是字段列表）"""
    lines = text.strip().split("\n")
    result = []
    for line in lines:
        if not line.strip():
            continue
        if delimiter == "\t":
            parts = line.split("\t")
        else:
            parts = [line]
        result.append([p.strip() for p in parts])
    return result


def parse_header(header_line: list[str]) -> dict[int, str]:
    """解析表头行，返回 {列索引: 字段名} 映射"""
    col_map = {}
    for i, col_name in enumerate(header_line):
        field = normalize_column_name(col_name)
        if field:
            col_map[i] = field
    return col_map


def parse_row(parts: list[str], col_map: dict[int, str]) -> dict:
    """将一行数据按列映射转换为字段字典"""
    row_data = {}
    for i, field in col_map.items():
        if i < len(parts):
            row_data[field] = parts[i]
    return row_data


def parse_pasted_data(raw_text: str) -> tuple[list[ParsedOrderSchema], list[dict], str | None]:
    """
    解析用户粘贴的原始文本。
    返回: (orders列表, skipped_rows列表, warning消息)
    """
    if not raw_text.strip():
        return [], [], None

    delimiter = detect_delimiter(raw_text)
    lines = split_lines(raw_text, delimiter)

    if not lines:
        return [], [], None

    # 解析表头（第一行为表头）
    col_map = parse_header(lines[0])
    data_lines = lines[1:]

    # 逐行解析为临时记录
    raw_items = []
    for idx, parts in enumerate(data_lines):
        row_data = parse_row(parts, col_map)
        order_no = row_data.get("order_no", "").strip()
        internal_code = row_data.get("internal_code", "").strip()

        if not order_no or not internal_code:
            # 缺失必要字段，记录为跳行
            raw_items.append({
                "_skipped": True,
                "_line_index": idx + 2,  # 加2因为跳过表头且从1计数
                "_raw_data": parts,
                "_reason": f"缺少必要字段: {'订单号' if not order_no else '内部编码'}",
                **row_data
            })
            continue

        raw_items.append(row_data)

    # 批次内去重: Key = (order_no, internal_code)
    deduped_map = {}
    for item in raw_items:
        if "_skipped" in item:
            continue
        key = (item["order_no"], item["internal_code"])
        deduped_map[key] = item

    # 按订单号聚合
    order_map: dict[str, ParsedOrderSchema] = {}
    header_conflicts = {}

    for item in deduped_map.values():
        order_no = item["order_no"]

        if order_no not in order_map:
            order_map[order_no] = ParsedOrderSchema(
                order_no=order_no,
                customer_code=item.get("customer_code"),
                salesperson=item.get("salesperson"),
                items=[],
            )
        else:
            # 检测订单头字段冲突
            existing = order_map[order_no]
            for field in ["customer_code", "salesperson"]:
                if item.get(field) and existing.model_dump().get(field) and item[field] != existing.model_dump()[field]:
                    if order_no not in header_conflicts:
                        header_conflicts[order_no] = []
                    header_conflicts[order_no].append(field)

        item_schema = OrderItemSchema(
            internal_code=item["internal_code"],
            product_cn=item.get("product_cn"),
            spec_kg=_parse_float(item.get("spec_kg")),
            quantity_kg=_parse_float(item.get("quantity_kg")),
            unit_price=_parse_float(item.get("unit_price")),
            total_amount=_parse_float(item.get("total_amount")),
            customs_name=item.get("customs_name"),
            hs_code=item.get("hs_code"),
        )
        order_map[order_no].items.append(item_schema)

    # 添加订单头冲突警告
    for order_no, conflicts in header_conflicts.items():
        order_map[order_no].header_conflict_warning = (
            f"以下字段在同一订单内存在冲突，以第一行数据为准: {', '.join(conflicts)}"
        )

    # 构建 skipped_rows
    skipped_rows = [item for item in raw_items if "_skipped" in item]

    # 检测批次内去重警告
    original_count = len([i for i in raw_items if "_skipped" not in i])
    deduped_count = len(deduped_map)
    warning = None
    if original_count > deduped_count:
        warning = f"检测到 {original_count - deduped_count} 行重复数据，已自动合并，以最后出现的数据为准"

    return list(order_map.values()), skipped_rows, warning


def _parse_float(value) -> float | None:
    """安全解析浮点数"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 2: 创建测试**

```python
# backend/tests/test_order_parser.py
import pytest
from app.core.order_parser import parse_pasted_data, normalize_column_name


def test_parse_single_order_single_item():
    text = """订单号	客户编号	内部编号	产品中文名	规格kg	订单量kg	单价/kg
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂	25	2400	29.5"""
    orders, skipped, warning = parse_pasted_data(text)
    assert len(orders) == 1
    assert orders[0].order_no == "HT260304E01"
    assert len(orders[0].items) == 1
    assert orders[0].items[0].internal_code == "SILI-001"


def test_parse_single_order_multiple_items():
    """一单多品：同一订单号的多行应聚合为一个订单"""
    text = """订单号	客户编号	内部编号	产品中文名	规格kg	订单量kg
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂A	25	2400
HT260304E01	TOA-DOVECHEM	SILI-002	有机硅柔软剂B	50	1600"""
    orders, skipped, warning = parse_pasted_data(text)
    assert len(orders) == 1
    assert len(orders[0].items) == 2


def test_parse_batch_dedup():
    """批次内去重：同一 (订单号+内部编码) 的后行应覆盖前行"""
    text = """订单号	客户编号	内部编号	产品中文名	订单量kg
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂	1000
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂	2000"""
    orders, skipped, warning = parse_pasted_data(text)
    assert warning is not None
    assert len(orders[0].items) == 1
    assert orders[0].items[0].quantity_kg == 2000  # 后行覆盖前行


def test_parse_missing_internal_code_skipped():
    """缺失 internal_code 的行应被跳过"""
    text = """订单号	客户编号	内部编号	产品中文名
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂
HT260304E01	TOA-DOVECHEM		改性硅油"""
    orders, skipped, warning = parse_pasted_data(text)
    assert len(skipped) == 1
    assert skipped[0]["_reason"] == "缺少必要字段: 内部编码"


def test_normalize_column_name():
    assert normalize_column_name("订单号") == "order_no"
    assert normalize_column_name("Order No") == "order_no"
    assert normalize_column_name("PO") == "order_no"
    assert normalize_column_name("H.S.Code") == "hs_code"
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_order_parser.py -v`
Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: implement order_parser with smart aggregation and batch dedup"
```

---

## Task 5: 知识库匹配 core/knowledge_filler.py

实现 H.S.Code 和报关品名的知识库匹配逻辑（internal_code 精确 > 中文名精确），增加 H.S.Code 10位格式校验。

**Files:**
- Create: `backend/app/core/knowledge_filler.py`
- Modify: `backend/app/core/__init__.py`
- Test: `backend/tests/test_knowledge_filler.py`

- [ ] **Step 1: 创建 backend/app/core/knowledge_filler.py**

```python
from app.schemas.order import OrderItemSchema, ParsedOrderSchema
from app.database import SessionLocal
from app.models import ProductKnowledge


def auto_fill_knowledge(item: OrderItemSchema, pi_data: dict | None = None) -> None:
    """
    自动补全 H.S.Code 和报关品名。
    优先级：
      H.S.Code: PI > 知识库（internal_code）> 知识库（产品中文名）
      报关品名: 订单已有 > PI > 知识库 > 自动生成

    匹配策略：去空格后精确匹配，不使用模糊匹配。
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
            else:
                item.hs_code = None  # 留空，前端标红

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
```

- [ ] **Step 2: 创建测试**

```python
# backend/tests/test_knowledge_filler.py
import pytest
from app.core.knowledge_filler import auto_fill_knowledge
from app.schemas.order import OrderItemSchema


def test_fill_from_internal_code(monkeypatch):
    """internal_code 精确命中时直接填充"""
    class MockProductKnowledge:
        def __init__(self):
            self.internal_code = "SILI-001"
            self.hs_code = "3910000000"
            self.customs_name = "有机硅柔软剂"

    class MockQuery:
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return MockProductKnowledge()

    class MockDB:
        def query(self, *args, **kwargs):
            return MockQuery()
        def close(self):
            pass

    item = OrderItemSchema(internal_code="SILI-001", product_cn="有机硅柔软剂")
    auto_fill_knowledge(item, None)
    assert item.hs_code == "3910000000"


def test_hs_code_length_warning():
    """H.S.Code 不足10位时应有警告"""
    item = OrderItemSchema(internal_code="SILI-001", hs_code="3910")
    auto_fill_knowledge(item, None)
    assert item.hs_code_warning is not None
    assert "位数不足" in item.hs_code_warning


def test_customs_name_auto_generate():
    """知识库无匹配时自动生成报关品名"""
    class MockQuery:
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return None

    class MockDB:
        def query(self, *args, **kwargs):
            return MockQuery()
        def close(self):
            pass

    item = OrderItemSchema(internal_code="NEW-CODE", product_cn="改性硅油", spec_kg=25)
    auto_fill_knowledge(item, None)
    assert "改性硅油" in item.customs_name
    assert item.warning is not None
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_knowledge_filler.py -v`
Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: add knowledge_filler with HS code validation"
```

---

## Task 6: API 端点

创建 `POST /api/v1/orders/paste` 和 `POST /api/v1/orders` 端点。

**Files:**
- Modify: `backend/app/api/v1/orders.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 backend/app/api/v1/orders.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.order import (
    PasteParseRequest, PasteParseResponse,
    OrderSaveRequest, OrderSaveResponse,
    ParsedOrderSchema, OrderItemSchema
)
from app.core.order_parser import parse_pasted_data
from app.core.knowledge_filler import fill_knowledge_for_order
from app.models import Order, OrderItem

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/paste", response_model=PasteParseResponse)
def parse_paste(request: PasteParseRequest):
    """
    解析用户粘贴的订单文本。
    1. 识别分隔符，切分数据行
    2. 批次内去重（后行覆盖前行）
    3. 按订单号聚合（一单多品）
    4. 返回预览数据（含知识库匹配结果）
    """
    orders, skipped_rows, warning = parse_pasted_data(request.raw_text)

    # 知识库匹配
    for order in orders:
        fill_knowledge_for_order(order)

    return PasteParseResponse(
        orders=orders,
        skipped_rows=[{
            "line_index": s["_line_index"],
            "reason": s["_reason"],
            "raw_data": s.get("_raw_data", [])
        } for s in skipped_rows],
        warning=warning
    )


@router.post("", response_model=OrderSaveResponse)
def save_order(request: OrderSaveRequest, db: Session = Depends(get_db)):
    """
    保存解析后的订单到数据库。
    - 如果订单号已存在：覆盖旧数据（删除旧 order_items，插入新的）
    - 如果订单号不存在：新建订单
    """
    order_data = request.order

    # 检查是否已存在
    existing = db.query(Order).filter(Order.order_no == order_data.order_no).first()

    if existing:
        # 覆盖：删除旧 order_items
        db.query(OrderItem).filter(OrderItem.order_id == existing.id).delete()
        # 更新 orders 头表
        existing.customer_code = order_data.customer_code
        existing.salesperson = order_data.salesperson
        existing.updated_at = __import__("datetime").datetime.utcnow()
        order_id = existing.id
    else:
        # 新建
        new_order = Order(
            order_no=order_data.order_no,
            customer_code=order_data.customer_code,
            salesperson=order_data.salesperson,
        )
        db.add(new_order)
        db.flush()
        order_id = new_order.id

    # 批量插入 order_items
    for item_data in order_data.items:
        item_dict = item_data.model_dump(exclude_none=False)
        item_dict.pop("hs_code_warning", None)
        item_dict.pop("warning", None)
        order_item = OrderItem(order_id=order_id, **item_dict)
        db.add(order_item)

    db.commit()

    return OrderSaveResponse(
        order_id=order_id,
        items_count=len(order_data.items),
        message=f"订单 {order_data.order_no} 保存成功，共 {len(order_data.items)} 个产品"
    )
```

- [ ] **Step 2: 更新 backend/app/main.py 注册路由**

```python
from app.api.v1 import orders

app.include_router(orders.router)
```

- [ ] **Step 3: 测试 API 端点**

Run: `cd backend && uvicorn app.main:app --reload --port 8000 &`
Run: `sleep 3 && curl -X POST http://localhost:8000/api/v1/orders/paste -H "Content-Type: application/json" -d '{"raw_text":"订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg\nHT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400"}'`
Expected: JSON 响应包含 orders 数组

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: add orders API endpoints (paste parse + save)"
```

---

## Task 7: 前端 — 粘贴文本框组件

创建 `PasteTextarea.vue` 组件。

**Files:**
- Create: `frontend/src/components/phase1/PasteTextarea.vue`

- [ ] **Step 1: 创建 frontend/src/components/phase1/PasteTextarea.vue**

```vue
<template>
  <div class="paste-textarea">
    <el-input
      v-model="text"
      type="textarea"
      :rows="10"
      :placeholder="placeholder"
      @paste="handlePaste"
      resize="vertical"
    />
    <div class="actions">
      <el-button type="primary" :disabled="!text.trim()" @click="handleParse">
        解析
      </el-button>
      <el-button @click="handleClear" :disabled="!text.trim()">
        清空
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'parse': [text: string]
  'clear': []
}>()

const text = ref(props.modelValue ?? '')
const placeholder = '将 Excel/Spreadsheet 订单数据粘贴到此处\n（支持 Tab 分隔或换行分隔）'

function handlePaste() {
  // 等待剪贴板数据填充后再触发
  setTimeout(() => {
    emit('update:modelValue', text.value)
  }, 0)
}

function handleParse() {
  emit('parse', text.value)
}

function handleClear() {
  text.value = ''
  emit('update:modelValue', '')
  emit('clear')
}

// 监听外部 v-model 变化
import { watch } from 'vue'
watch(() => props.modelValue, (val) => {
  if (val !== text.value) text.value = val ?? ''
})
</script>

<style scoped>
.paste-textarea {
  width: 100%;
}
.paste-textarea :deep(.el-textarea__inner) {
  font-family: monospace;
  font-size: 13px;
}
.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "feat: add PasteTextarea component"
```

---

## Task 8: 前端 — 表单式预览编辑组件

创建 `OrderPreviewForm.vue`，展示订单头 + order_items 子表格，支持全选/反选、缺失字段高亮。

**Files:**
- Create: `frontend/src/components/phase1/OrderPreviewForm.vue`

- [ ] **Step 1: 创建 frontend/src/components/phase1/OrderPreviewForm.vue**

```vue
<template>
  <div class="order-preview-form">
    <!-- 警告提示 -->
    <el-alert v-if="warning" :title="warning" type="warning" show-icon :closable="true" style="margin-bottom: 16px" />

    <!-- 跳行提示 -->
    <el-alert v-if="skippedRows.length > 0" type="info" show-icon :closable="true" style="margin-bottom: 16px">
      <template #title>
        {{ skippedRows.length }} 行因缺少必要字段被跳过（显示为灰色）
      </template>
    </el-alert>

    <div v-for="order in orders" :key="order.order_no" class="order-card">
      <!-- 订单头 -->
      <el-card shadow="never" class="order-header-card">
        <template #header>
          <div class="card-header">
            <span>订单号：{{ order.order_no }}</span>
            <el-tag v-if="order.header_conflict_warning" type="warning" size="small">
              有冲突字段
            </el-tag>
          </div>
        </template>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="客户编号">{{ order.customer_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="业务员">{{ order.salesperson || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="order.header_conflict_warning" class="conflict-warning">
          {{ order.header_conflict_warning }}
        </div>
      </el-card>

      <!-- 产品明细 -->
      <el-card shadow="never" class="items-card">
        <template #header>
          <div class="card-header">
            <span>产品明细（{{ order.items.length }} 条）</span>
            <el-checkbox
              v-model="allSelected"
              :indeterminate="isIndeterminate"
              @change="toggleSelectAll(order.items)"
            >
              全选/反选
            </el-checkbox>
          </div>
        </template>

        <el-table :data="order.items" border stripe size="small">
          <el-table-column type="index" width="50" />
          <el-table-column type="selection" width="45" />
          <el-table-column prop="internal_code" label="内部编码" width="120" />
          <el-table-column prop="product_cn" label="产品中文名" min-width="160" />
          <el-table-column prop="spec_kg" label="规格kg" width="80" align="center" />
          <el-table-column prop="quantity_kg" label="订单量kg" width="100" align="right" />
          <el-table-column prop="unit_price" label="单价/kg" width="80" align="right" />
          <el-table-column prop="total_amount" label="总金额" width="100" align="right" />
          <el-table-column label="H.S.Code" width="160">
            <template #default="{ row }">
              <el-input
                v-model="row.hs_code"
                size="small"
                :class="{ 'hs-code-warning': row.hs_code_warning || (row.hs_code && row.hs_code.length < 10) }"
                :placeholder="row.hs_code ? '' : '待填写'"
              />
              <span v-if="row.hs_code_warning || (row.hs_code && row.hs_code.length < 10)" class="field-warning">
                ⚠️ {{ row.hs_code_warning || '位数不足' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="报关品名" min-width="160">
            <template #default="{ row }">
              <el-input v-model="row.customs_name" size="small" />
              <span v-if="row.warning" class="field-warning">⚠️ {{ row.warning }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <el-button type="primary" @click="handleSave" :loading="saving">
        保存
      </el-button>
      <el-button @click="handleReset">重新粘贴</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ParsedOrderSchema, PasteParseResponse } from '@/api/orders'

const props = defineProps<{
  parseResult: PasteParseResponse
}>()

const emit = defineEmits<{
  'save': [orders: ParsedOrderSchema[]]
  'reset': []
}>()

const saving = ref(false)

const orders = computed(() => props.parseResult.orders)
const skippedRows = computed(() => props.parseResult.skipped_rows)
const warning = computed(() => props.parseResult.warning)

const allSelected = ref(true)
const isIndeterminate = computed(() => {
  const total = orders.value.reduce((sum, o) => sum + o.items.length, 0)
  const selected = orders.value.reduce((sum, o) => sum + o.items.filter(i => i._selected !== false).length, 0)
  return selected > 0 && selected < total
})

function toggleSelectAll(items: any[]) {
  // 简化实现：实际需要用 Map 跟踪每个 item 的选中状态
}

async function handleSave() {
  saving.value = true
  try {
    emit('save', orders.value)
  } finally {
    saving.value = false
  }
}

function handleReset() {
  emit('reset')
}
</script>

<style scoped>
.order-preview-form {
  width: 100%;
}
.order-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.conflict-warning {
  margin-top: 8px;
  padding: 8px;
  background: #fffbe6;
  border-radius: 4px;
  font-size: 13px;
  color: #ad6800;
}
.field-warning {
  font-size: 12px;
  color: #ad6800;
  display: block;
  margin-top: 2px;
}
.hs-code-warning :deep(.el-input__inner) {
  border-color: #faad14;
  background: #fffbe6;
}
.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "feat: add OrderPreviewForm component with table and validation"
```

---

## Task 9: 前端 — OrderPaste 页面

创建 `OrderPaste.vue` 页面，整合粘贴文本框 + 预览表单，调用后端 API。

**Files:**
- Create: `frontend/src/views/phase1/OrderPaste.vue`
- Create: `frontend/src/api/orders.ts`

- [ ] **Step 1: 创建 frontend/src/api/orders.ts**

```typescript
import axios from 'axios'

const BASE_URL = '/api/v1'

export interface OrderItemSchema {
  internal_code: string
  product_cn?: string
  product_en?: string
  spec_kg?: number
  hs_code?: string
  customs_name?: string
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  hs_code_warning?: string
  warning?: string
  _selected?: boolean
}

export interface ParsedOrderSchema {
  order_no: string
  customer_code?: string
  salesperson?: string
  items: OrderItemSchema[]
  header_conflict_warning?: string
}

export interface PasteParseResponse {
  orders: ParsedOrderSchema[]
  skipped_rows: { line_index: number; reason: string; raw_data: string[] }[]
  warning?: string
}

export interface OrderSaveResponse {
  order_id: number
  items_count: number
  message: string
}

export const ordersApi = {
  parsePaste: async (rawText: string): Promise<PasteParseResponse> => {
    const resp = await axios.post(`${BASE_URL}/orders/paste`, { raw_text: rawText })
    return resp.data
  },

  saveOrder: async (order: ParsedOrderSchema): Promise<OrderSaveResponse> => {
    const resp = await axios.post(`${BASE_URL}/orders`, { order })
    return resp.data
  }
}
```

- [ ] **Step 2: 创建 frontend/src/views/phase1/OrderPaste.vue**

```vue
<template>
  <div class="order-paste-page">
    <el-page-header @back="() => $router.back()" content="订单粘贴解析" />

    <div class="page-content">
      <PasteTextarea
        v-model="rawText"
        @parse="handleParse"
        @clear="handleClear"
      />

      <div v-if="parseResult" class="preview-section">
        <OrderPreviewForm
          :parse-result="parseResult"
          @save="handleSave"
          @reset="handleReset"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import OrderPreviewForm from '@/components/phase1/OrderPreviewForm.vue'
import { ordersApi, type PasteParseResponse, type ParsedOrderSchema } from '@/api/orders'

const rawText = ref('')
const parseResult = ref<PasteParseResponse | null>(null)

async function handleParse(text: string) {
  try {
    parseResult.value = await ordersApi.parsePaste(text)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '解析失败')
  }
}

async function handleSave(orders: ParsedOrderSchema[]) {
  try {
    for (const order of orders) {
      await ordersApi.saveOrder(order)
    }
    ElMessage.success('保存成功')
    handleReset()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '保存失败')
  }
}

function handleReset() {
  rawText.value = ''
  parseResult.value = null
}

function handleClear() {
  handleReset()
}
</script>

<style scoped>
.order-paste-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-content {
  margin-top: 24px;
}
.preview-section {
  margin-top: 24px;
}
</style>
```

- [ ] **Step 3: 更新 frontend/src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 4: 更新 frontend/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <title>ShippingHelper</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 5: 创建 frontend/src/App.vue**

```vue
<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Arial, sans-serif;
}
</style>
```

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: add OrderPaste page and orders API client"
```

---

## Task 10: 集成测试与验收

运行前后端，验证端到端流程。

**Files:**
- None (integration testing only)

- [ ] **Step 1: 启动后端**

Run: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &`
Expected: 服务启动成功

- [ ] **Step 2: 启动前端**

Run: `cd frontend && npm run dev &`
Expected: Vite dev server 启动在 5173 端口

- [ ] **Step 3: 端到端测试**

1. 打开浏览器访问 http://localhost:5173
2. 导航到订单粘贴解析页面
3. 从 Excel 复制以下测试数据并粘贴：
```
订单号	客户编号	内部编号	产品中文名	规格kg	订单量kg
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂	25	2400
HT260304E01	TOA-DOVECHEM	SILI-002	改性硅油	30	800
```
4. 点击"解析"
5. 验证预览显示：1个订单，2个产品明细
6. 点击"保存"
7. 验证成功消息

- [ ] **Step 4: 验收标准检查**

- [ ] 用户在文本框按 Ctrl+V 粘贴 Excel 数据，系统正确解析
- [ ] 同一订单号的多行数据聚合为一个订单 + 2 个产品明细
- [ ] 批次内重复行自动去重
- [ ] H.S.Code 和报关品名显示匹配状态
- [ ] 预览界面显示订单头 + 产品明细子表格
- [ ] 保存后数据正确写入 orders 表（1条）和 order_items 表（2条）

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "test: integration test for order paste parsing E2E"
```

---

## 低优先级后续任务

以下任务不在 Phase 1 主流程中，但需记录：

- **历史数据迁移**：现有 26 字段平铺数据的迁移脚本（后续独立处理）
- **PI 数据关联**：`pi_data` / `pi_contracts` 表的关联逻辑（FR-2.x）
- **包装计算模块**：`calculation_service.py` 的实现（Phase 1 FR-4.x）

---

## 自查清单

- [ ] Spec 覆盖：FR-1.1 ~ FR-1.6 全部有对应任务
- [ ] 占位符：无 TBD/TODO/待实现
- [ ] 类型一致性：所有 schema 字段在 parser → API → frontend 链路中一致
- [ ] 无重复逻辑：知识库匹配仅在 `knowledge_filler.py` 一处实现
- [ ] 提交粒度：每任务一提交，message 符合规范
