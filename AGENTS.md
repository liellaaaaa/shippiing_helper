# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

---

## Project Overview

ShippingHelper is a shipping efficiency tool for the shipping department. It was originally a PyQt5 desktop application (`参考/` folder contains the legacy implementation) and is being重构为 a modern Web application.

**Current Architecture**: Web application using Vue 3 + FastAPI + SQLite + OnlyOffice (see `docs/` for PRD documents)

**Legacy Reference**: The `参考/` folder contains the mature PyQt5 implementation that should be referenced for business logic:
- `参考/core/` - Core business logic (order_parser, pi_extractor, package_calculator, etc.)
- `参考/knowledge/` - Product knowledge and packaging data (JSON)
- `参考/phase2/` - Phase 2 document generation (booking, MSDS)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3 + Vite + Element Plus + Pinia |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Document | OnlyOffice Document Server (Docker) |
| Editor | OnlyOffice (all document types, not Luckysheet) |

---

## Development Workflow (Mandatory)

Every task must follow this workflow:

```
用户请求 → brainstorming skill → 设计文档 → 用户批准 → writing-plans skill → 实现计划 → 用户批准
```

**HARD-GATE**: Never write code until user approves the design document.

Key skills to use:
- `brainstorming` - Before any implementation
- `writing-plans` - After design approval
- `frontend-design` - For UI components
- `verification-before-completion` - Before marking tasks done

---

## Critical Architecture Decisions

| Decision | Choice |
|----------|--------|
| Document Editor | **OnlyOffice only** (Excel + Word unified, no Luckysheet) |
| Calculation Logic | Single source: `backend/app/services/calculation_service.py` (Phase 1 & 2 shared) |
| Database | SQLite WAL mode, file-based storage |
| File Storage | Database BLOBs, not shared folder |
| Template Principle | Templates are read-only; instances are copied from templates |
| Pessimistic Locking | Order-level locking (`order_status`, `locked_by`, `locked_at`) |
| OnlyOffice Callback | Backend MUST expose `POST /api/v1/onlyoffice/callback` to receive file streams from Document Server. On save success: write to DB + release lock. |

---

## OnlyOffice Callback Interface

When the user clicks Save in OnlyOffice, the Document Server POSTs the file to the callback URL. The backend endpoint must:

```python
# POST /api/v1/onlyoffice/callback
# Request: multipart/form-data with file stream
# Response: JSON status

@app.post("/api/v1/onlyoffice/callback")
async def onlyoffice_callback(order_id: int, user: str):
    # 1. Receive file stream from OnlyOffice Document Server
    # 2. Write file blob to shipment_docs table
    # 3. Increment version number
    # 4. Release pessimistic lock (order_status = "saved", locked_by = null)
    # 5. Return success JSON
```

**Callback behavior**:
- Document Server sends file via HTTP POST with `document` field (file stream)
- Backend receives, stores in DB, releases lock
- Never write directly to shared folders (avoids file handle issues on Windows)

---

## Key Business Rules

### Packaging Calculation (复用)
All weight/volume calculations must use `calculation_service.py`:
- `calculate_drum_count(quantity_kg, net_kg_per_drum)` - drums = ⌈order_qty / net_per_drum⌉
- `calculate_pallet_count(drums, capacity_per_pallet)` - pallets = ⌈drums / capacity⌉
- `calculate_volume(drums, cbm_per_drum, pallets, cbm_per_pallet)`
- `calculate_gross_weight(drums, gross_per_drum, pallets, pallet_weight)`
- `judge_20gp(total_volume_cbm, total_weight_kg)` - fits if ≤28CBM AND ≤21000kg

### Data Priority (报关品名/H.S.Code)
- 报关品名: order > PI > knowledge base
- H.S.Code: PI > knowledge base
- 关联字段: `internal_code` (订单-PI), `pi_no` (PI contract)

---

## Project Structure

```
shipping_helper/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── v1/
│       │   │   ├── orders.py      # REST API: /api/v1/orders
│       │   │   ├── pi.py          # PI upload/save/query API
│       │   │   ├── packaging.py   # Packaging calculation API
│       │   │   ├── phase2.py      # Phase 2 document generation API
│       │   │   └── dashboard.py   # Dashboard data API
│       │   └── deps.py            # FastAPI dependency injection
│       ├── core/
│       │   ├── order_parser.py    # Delimiter detection, aggregation, dedup
│       │   ├── knowledge_filler.py # HS code + customs name auto-fill
│       │   └── pi_parser.py       # PI file parsing (.xlsx/.xls/.pdf)
│       ├── services/
│       │   ├── order_service.py   # Order service layer
│       │   ├── pi_service.py      # PI service layer
│       │   ├── packaging_service.py # Packaging calculation (drums, pallets, 20GP)
│       │   ├── save_service.py    # Transactional save for order+PI+packaging
│       │   └── document_service.py # Document template + BLOB storage
│       ├── models/
│       │   └── order.py          # SQLAlchemy models
│       ├── schemas/
│       │   └── order.py          # Pydantic schemas
│       ├── main.py               # FastAPI entry point
│       └── database.py           # SQLite connection
├── frontend/
│   └── src/
│       ├── api/
│       │   ├── orders.ts        # Axios API client
│       │   ├── pi.ts            # PI API client
│       │   ├── phase1.ts        # Phase 1 API client
│       │   ├── phase2.ts        # Phase 2 API client
│       │   └── packaging.ts     # Packaging API client
│       ├── components/
│       │   └── phase1/
│       │       ├── PasteTextarea.vue       # Order paste input
│       │       ├── OrderPreviewForm.vue   # Order preview + edit
│       │       ├── PiUploadDragger.vue     # PI file upload drag-and-drop
│       │       ├── PiPreviewTable.vue     # PI preview table
│       │       ├── PackagingCalculator.vue # Multi-row packaging calculator
│       │       └── ColumnMappingModal.vue  # PI column mapping modal
│       └── views/
│           ├── phase1/
│           │   ├── OrderPaste.vue         # Order paste page
│           │   └── Phase1Workflow.vue     # Phase 1 workflow page
│           └── phase2/
│               ├── Phase2Workflow.vue     # Phase 2 main workflow
│               └── components/
│                   ├── ReferencePanel.vue  # 4-tab reference panel
│                   ├── DocumentEditor.vue  # OnlyOffice editor wrapper
│                   ├── MyDocumentsDrawer.vue # Saved template instances
│                   └── DataCenterPanel.vue # Data center panel
├── docs/
│   ├── PRD-ShippingHelper-Web.md        # Main PRD
│   ├── PRD-ShippingHelper-Web-P1v2.md  # Phase 1 spec
│   ├── PRD-ShippingHelper-Web-P2v2.md  # Phase 2 spec
│   ├── PRD-ShippingHelper-Web-P1v2-OrderParsing.md  # Order parsing design
│   ├── API-ShippingHelper-v1.md        # API reference
│   ├── TEST-ShippingHelper-v1.md       # Integration test docs
│   └── superpower/plans/              # Implementation plans
│   └── superpower/specs/             # Design specs
├── 参考/                              # Legacy PyQt5 reference
└── data/
    └── shipping_helper.db            # SQLite database
```

---

## Data Models

Core tables (see `docs/` PRD for full schema):
- `orders` - Order header table (订单头)
- `order_items` - Product detail table (产品明细，外键→orders.id) — **一单多品**
- `packaging_types` - 13 packaging types
- `pallets` - 2 pallet types
- `pi_data` - PI summary table
- `pi_contracts` - Single PI contract
- `products_knowledge` - Product knowledge base
- `templates` - Document template config

> ⚠️ **重要**：orders 表和 order_items 表已拆分。`internal_code` 仅存在于 order_items（产品级），orders 表不存储此字段。

---

## Legacy Code Reference

The `参考/` folder contains the Python implementation that should inform implementation:

| File | Purpose |
|------|---------|
| `参考/core/order_parser.py` | Order parsing (Tab/newline delimited, 23 fields) |
| `参考/core/pi_extractor.py` | PI file extraction (.xls via xlrd) |
| `参考/core/package_calculator.py` | Packaging calculation logic |
| `参考/core/merger.py` | Data merging (order + PI + codes) |
| `参考/knowledge/packaging_data.json` | 13 packaging types, 2 pallets, capacity mapping |

---

## Phase Development Order

**Phase 1** (Order Processing):
1. ~~Project initialization (Vue + FastAPI)~~ ✅
2. ~~Order paste parsing~~ ✅
3. ~~PI file extraction (.xls/.xlsx/.pdf OCR)~~ ✅
4. ~~Data merging (internal_code association)~~ ✅
5. ~~Packaging calculation (13 types, 2 pallets, 20GP judgment, per-pallet capacity)~~ ✅
6. ~~Data dashboard (read-only order + PI merge preview)~~ ✅

**Phase 2** (Document Generation):
1. ~~Shipment data management~~ ✅
2. ~~Template management~~ ✅
3. ~~Document generation (Booking, MSDS via OnlyOffice)~~ ✅
4. ~~Data display (left dashboard, right editor)~~ ✅
5. ~~Blank template and My Templates support~~ ✅

---

## Important Notes

1. **OnlyOffice Integration**: All Excel and Word documents use OnlyOffice. Document Server URL configured via environment variable.

2. **Frontend Component Reuse**: A single shared `OnlyOfficeEditor.vue` component must be used for ALL document types (Booking, MSDS). Do NOT create separate editor components per page. The component accepts `config`, `documentServerUrl`, and `events` as props.

3. **Internal Code Location**: `internal_code` is stored ONLY in `order_items` (product-level). The `orders` table does NOT contain `internal_code`.

3. **Calculation Consistency**: Weight/volume/20GP logic exists ONLY in `calculation_service.py`. Phase 1 and Phase 2 call the same service.

4. **Locking Mechanism**: When user opens a document for editing, lock immediately (`order_status = "editing"`, `locked_by`, `locked_at`). Release on save/close.

5. **Template Files**: Never modify template files directly. Always copy to instance, then fill data.

6. **Mock Data**: Use simulated data for development. User will provide real samples later.

---

## Common Commands

```bash
# Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev

# Docker (OnlyOffice)
docker run -d -p 8080:80 onlyoffice/documentserver
```

---

## Phase 1 Progress

| Module | Status | Notes |
|--------|--------|-------|
| Project initialization | ✅ done | Vue 3 + FastAPI + SQLite scaffold |
| Order paste parsing | ✅ done | Tab/CRLF delimiter, smart aggregation, dedup, knowledge fill |
| PI file extraction | ✅ done | .xlsx/.xls/.pdf upload, column mapping, confidence, pi_data upsert, OCR |
| Data merging | ✅ done | internal_code association, order-PI merge |
| Packaging calculation | ✅ done | 13 drum types, 2 pallets, 20GP judgment, multi-row calculator, per-pallet capacity |
| Data dashboard | ✅ done | Read-only order + PI merge preview in Phase1Workflow |

**Completed Files:**
- `backend/app/models/order.py` — orders + order_items + packaging_types + products_knowledge
- `backend/app/models/pi_contract.py` — PiContract + PiContractItem + PiData models
- `backend/app/schemas/pi_contract.py` — Pydantic schemas for PI upload/save/query
- `backend/app/core/order_parser.py` — delimiter detection, batch dedup, aggregation
- `backend/app/core/knowledge_filler.py` — HS code + customs name auto-fill
- `backend/app/core/pi_parser.py` — column mapping, smart degradation, confidence
- `backend/app/services/order_service.py` — service layer with transactional save
- `backend/app/services/pi_service.py` — PI service with transactional save + pi_data upsert
- `backend/app/services/packaging_service.py` — packaging calculation (drums, pallets, volume, 20GP)
- `backend/app/api/v1/orders.py` — REST API endpoints
- `backend/app/api/v1/pi.py` — PI upload/save/query endpoints
- `backend/app/api/v1/phase2.py` — Phase 2 API routes (document generation, OnlyOffice callback)
- `backend/app/api/deps.py` — FastAPI dependency injection
- `backend/migrations/001_add_pi_contracts.py` — table migration
- `backend/migrations/002_add_indexes.py` — index migration
- `frontend/src/api/orders.ts` — Axios API client
- `frontend/src/api/pi.ts` — PI API client
- `frontend/src/api/phase2.ts` — Phase 2 API client
- `frontend/src/components/phase1/PasteTextarea.vue` — paste input component
- `frontend/src/components/phase1/OrderPreviewForm.vue` — preview + edit component
- `frontend/src/components/phase1/PIExtract.vue` — full page
- `frontend/src/components/phase1/PiUploadDragger.vue` — drag-and-drop upload (.xlsx/.xls/.pdf)
- `frontend/src/components/phase1/PiPreviewTable.vue` — editable preview table
- `frontend/src/components/phase1/ColumnMappingModal.vue` — column mapping modal
- `frontend/src/components/phase1/PackagingCalculator.vue` — packaging calculator component
- `frontend/src/views/phase1/OrderPaste.vue` — order paste page
- `frontend/src/views/phase2/Phase2Workflow.vue` — Phase 2 main workflow page
- `frontend/src/views/phase2/components/ReferencePanel.vue` — 4-tab reference panel
- `frontend/src/views/phase2/components/DocumentEditor.vue` — OnlyOffice editor wrapper

---

## Phase 2 Progress

| Module | Status | Notes |
|--------|--------|-------|
| Phase 2 API routes | ✅ done | All endpoints registered in main.py |
| OnlyOfficeService | ✅ done | Document generation (Booking/MSDS), marker-based filling |
| DocumentService | ✅ done | Template copying, BLOB storage, version management |
| ShipmentDoc model | ✅ done | Document version storage with content_hash idempotency |
| ExportCodesService | ✅ done | HS code lookup service |
| OnlyOffice callback | ✅ done | `POST /api/v1/onlyoffice/callback` with pessimistic lock release |
| Phase 2 frontend page | ✅ done | Phase2Workflow + ReferencePanel + DocumentEditor components |
| PI upload (.pdf) | ✅ done | PiUploadDragger supports .pdf via OCR |
| consignee/destination | ✅ done | PI Header fields extracted from PDF |

*Last updated: 2026/06/02*