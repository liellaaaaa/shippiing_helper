# ShippingHelper 船务部效率工具

外贸船务部的数字化工作流工具，将原 PyQt5 桌面应用重构为现代化 Web 应用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + TypeScript |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 文档服务 | OnlyOffice Document Server（Docker） |

## 项目结构

```
shipping_helper/
├── backend/
│   └── app/
│       ├── api/v1/
│       │   ├── orders.py        # REST API: /api/v1/orders
│       │   ├── pi.py            # PI upload/save/query
│       │   ├── phase2.py        # Document generation API
│       │   └── deps.py          # FastAPI dependency injection
│       ├── core/
│       │   ├── order_parser.py  # Delimiter detection, aggregation, dedup
│       │   ├── knowledge_filler.py # HS code + customs name auto-fill
│       │   └── pi_parser.py     # Column mapping, smart degradation
│       ├── services/
│       │   ├── order_service.py     # Service layer (transactional save)
│       │   ├── pi_service.py        # PI service + pi_data upsert
│       │   ├── packaging_service.py # Packaging calculation
│       │   └── calculation_service.py # Weight/volume/20GP logic
│       ├── models/
│       │   ├── order.py         # orders + order_items + packaging_types
│       │   └── pi_contract.py   # PiContract + PiContractItem + PiData
│       ├── schemas/
│       │   └── pi_contract.py   # Pydantic schemas
│       ├── main.py              # FastAPI entry point
│       └── database.py          # SQLite connection
├── frontend/
│   └── src/
│       ├── api/
│       │   ├── orders.ts        # Axios API client
│       │   ├── pi.ts            # PI API client
│       │   └── phase2.ts        # Phase 2 API client
│       ├── components/phase1/
│       │   ├── PasteTextarea.vue
│       │   ├── OrderPreviewForm.vue
│       │   ├── PIExtract.vue
│       │   ├── PiUploadDragger.vue
│       │   ├── PiPreviewTable.vue
│       │   ├── ColumnMappingModal.vue
│       │   └── PackagingCalculator.vue
│       └── views/
│           ├── phase1/OrderPaste.vue
│           └── phase2/
│               ├── Phase2Workflow.vue
│               └── components/
│                   ├── ReferencePanel.vue
│                   └── DocumentEditor.vue
├── docs/                        # PRD, API, TEST documentation
├── 参考/                        # Legacy PyQt5 reference
└── data/                        # SQLite database
```

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### API 文档

启动后端后访问：`http://localhost:8000/docs`

## Phase 1 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 项目初始化 | ✅ | Vue 3 + FastAPI + SQLite |
| 订单粘贴解析 | ✅ | Tab/换行分隔、一单多品、知识库匹配 |
| PI 文件提取 | ✅ | .xlsx/.xls/.pdf(OCR)、列映射、置信度 |
| 数据关联 | ✅ | internal_code 关联、订单-PI 合并 |
| 包装计算 | ✅ | 13种桶型、2种托盘、20GP判断 |
| 数据看板 | 🔲 | OnlyOffice 只读（待开发） |

## Phase 2 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| Phase 2 API 路由 | ✅ | 文档生成、OnlyOffice 回调 |
| OnlyOfficeService | ✅ | Booking/LOI/MSDS 生成、标记填充 |
| DocumentService | ✅ | 模板复制、BLOB 存储、版本管理 |
| ShipmentDoc 模型 | ✅ | 文档版本存储、content_hash 幂等 |
| ExportCodesService | ✅ | HS code 查询服务 |
| OnlyOffice 回调 | ✅ | 悲观锁释放 |
| Phase 2 前端页面 | ✅ | Phase2Workflow + ReferencePanel + DocumentEditor |
| PI 上传 (.pdf) | ✅ | 支持 PDF via OCR |
| consignee/destination | ✅ | PI Header 字段从 PDF 提取 |

## 核心文档

| 文档 | 说明 |
|------|------|
| `docs/PRD-ShippingHelper-Web.md` | 主 PRD |
| `docs/PRD-ShippingHelper-Web-P1v2.md` | Phase 1 详细需求 |
| `docs/PRD-ShippingHelper-Web-P2v2.md` | Phase 2 详细需求 |
| `docs/PRD-ShippingHelper-Web-P1v2-OrderParsing.md` | 订单解析模块设计方案 |
| `docs/API-ShippingHelper-v1.md` | API 接口文档 |
| `docs/TEST-ShippingHelper-v1.md` | 集成测试文档 |
| `docs/superpowers/plans/` | 实施计划 |
| `CLAUDE.md` | Claude Code 开发指南 |

## 架构决策

| 决策 | 选择 |
|------|------|
| 文档编辑器 | OnlyOffice（全栈统一，不使用 Luckysheet） |
| 计算逻辑 | `backend/app/services/calculation_service.py`（Phase 1 & 2 共用） |
| 数据库 | SQLite WAL 模式 |
| 文件存储 | 数据库 BLOB，不使用共享文件夹 |
| 模板原则 | 模板只读，实例从模板复制 |
| 悲观锁 | 订单级锁（`order_status`, `locked_by`, `locked_at`） |
| PDF 解析 | OCR（pymupdf）支持 PDF 格式 PI 文件 |

## 数据模型

一张订单（orders）包含多个产品明细（order_items），称为"一单多品"：

```
orders（订单头）
  └── order_items（产品明细，外键→orders.id）
```

**重要**：`internal_code`（内部编码）仅存在于 `order_items`，`orders` 表不存储此字段。

## 常见命令

```bash
# 后端启动
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端启动
cd frontend && npm run dev

# 运行测试
cd backend && python -m pytest tests/ -v
```

## License

Internal use only.