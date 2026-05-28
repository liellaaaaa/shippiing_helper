# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

ShippingHelper is a shipping efficiency tool for the shipping department. It was originally a PyQt5 desktop application (`参考/` folder contains the legacy implementation) and is being重构为 a modern Web application.

**Current Architecture**: Web application using Vue 3 + FastAPI + SQLite + OnlyOffice (see `docs/` for PRD documents)

**Legacy Reference**: The `参考/` folder contains the mature PyQt5 implementation that should be referenced for business logic:
- `参考/core/` - Core business logic (order_parser, pi_extractor, package_calculator, etc.)
- `参考/knowledge/` - Product knowledge and packaging data (JSON)
- `参考/phase2/` - Phase 2 document generation (booking, LOI, MSDS)

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
shipping_helper_web/
├── frontend/
│   └── src/
│       ├── api/                 # Axios API calls
│       ├── components/
│       │   └── OnlyOfficeEditor.vue   # SHARED - single component for all doc types
│       └── views/
│           ├── phase1/         # OrderPaste, PIExtract, DataMerge, PackageCalc, DataDashboard
│           └── phase2/         # Shipment, Booking, MSDS, LOI (all use OnlyOfficeEditor.vue)
├── backend/
│   └── app/
│       ├── api/v1/
│       │   ├── orders.py
│       │   ├── pi.py
│       │   ├── packages.py
│       │   ├── documents.py
│       │   └── onlyoffice.py   # Callback endpoint
│       ├── core/               # Business logic (order_parser, pi_extractor, merger)
│       ├── services/           # calculation_service.py (shared)
│       └── models/             # SQLAlchemy models
├── templates/                   # Document templates (booking, msds, loi)
└── data/                        # SQLite database
```

**Important**: All OnlyOffice editor instances MUST use `components/OnlyOfficeEditor.vue`. Never create document-specific editor components.

---

## Data Models

Core tables (see `docs/` PRD for full schema):
- `orders` - 26-field order table
- `packaging_types` - 13 packaging types
- `pallets` - 2 pallet types
- `pi_data` - PI summary table
- `pi_contracts` - Single PI contract
- `products_knowledge` - Product knowledge base
- `templates` - Document template config

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
1. Project initialization (Vue + FastAPI)
2. Order paste parsing (26 fields)
3. PI file extraction (.xls/.xlsx)
4. Data merging (internal_code association)
5. Packaging calculation (13 types, 2 pallets, 20GP judgment)
6. Data dashboard (OnlyOffice read-only)

**Phase 2** (Document Generation):
1. Shipment data management
2. Template management
3. Document generation (Booking, MSDS, LOI via OnlyOffice)
4. Data display (left dashboard, right editor)

---

## Important Notes

1. **OnlyOffice Integration**: All Excel and Word documents use OnlyOffice. Document Server URL configured via environment variable.

2. **Frontend Component Reuse**: A single shared `OnlyOfficeEditor.vue` component must be used for ALL document types (Booking, MSDS, LOI). Do NOT create separate editor components per page. The component accepts `config`, `documentServerUrl`, and `events` as props.

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

| Module | Status |
|--------|--------|
| Project initialization | pending |
| Order paste parsing | pending |
| PI file extraction | pending |
| Data merging | pending |
| Packaging calculation | pending |
| Data dashboard | pending |

---

## Phase 2 Progress

| Module | Status |
|--------|--------|
| Data management | pending |
| Template management | pending |
| Document generation | pending |
| Data display | pending |

---

*Last updated: 2026/05/28*