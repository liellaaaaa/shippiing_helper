# ShippingHelper 船务部效率工具

外贸船务部的数字化工作流工具，将原 PyQt5 桌面应用重构为现代化 Web 应用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + TypeScript |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 文档服务 | OnlyOffice Document Server（Docker） |
| 编辑器 | OnlyOffice（Excel + Word 统一，不使用 Luckysheet） |

## 项目结构

```
shipping_helper/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── v1/
│       │   │   ├── orders.py        # POST /orders/paste, /orders
│       │   │   ├── pi.py           # POST /pi/upload
│       │   │   ├── merge.py         # /merge/orders, /comparison, /pi-contracts
│       │   │   ├── packages.py      # /packages/calculate (sea/air/land)
│       │   │   ├── packaging.py     # /packaging/calculate, /calculate-schemes
│       │   │   ├── dashboard.py     # /dashboard/orders, /records
│       │   │   ├── documents.py     # /documents/booking, /loi, /msds, /customs
│       │   │   ├── onlyoffice.py    # /onlyoffice/callback, /download
│       │   │   ├── msds.py         # /msds/, /content, /reindex
│       │   │   ├── transport.py     # /transport/upload
│       │   │   ├── export_codes.py  # /export-codes/
│       │   │   ├── data_center.py  # /data-center/search, /tree, /file
│       │   │   ├── transport_reports.py # /transport-reports/search
│       │   │   └── name_mapping.py  # /name-mapping, /lookup
│       │   └── deps.py             # FastAPI 依赖注入
│       ├── core/
│       │   ├── order_parser.py     # 分隔符检测、批量去重、聚合
│       │   ├── knowledge_filler.py # HS code + 报关品名自动补全
│       │   ├── pi_parser.py        # PI 文件解析 (.xlsx/.xls/.pdf OCR)
│       │   ├── config.py           # 目录路径和环境配置
│       │   └── name_mapping.py     # 产品名称中英文对照
│       ├── services/
│       │   ├── order_service.py          # 订单服务层
│       │   ├── pi_service.py              # PI 服务层
│       │   ├── packaging_service.py      # 包装计算
│       │   ├── calculation_service.py     # 核心计算逻辑（Phase 1 & 2 共用）
│       │   ├── merge_service.py           # 订单-PI 合并 + 比对
│       │   ├── save_service.py           # 订单+PI+包装的事务性保存
│       │   ├── document_service.py       # 文档模板 + BLOB 存储
│       │   ├── onlyoffice_service.py     # OnlyOffice JWT + 配置生成
│       │   ├── export_service.py         # Excel 导出
│       │   ├── data_center_service.py    # MSDS 搜索 + 索引
│       │   ├── msds_service.py           # MSDS 文本提取
│       │   ├── transport_service.py      # 运输鉴定报告解析
│       │   ├── name_mapping_service.py   # 品名对照查询
│       │   └── export_codes_service.py   # HS code 查询
│       ├── models/
│       │   ├── order.py             # orders, order_items, packaging_types, pallets
│       │   ├── pi_contract.py       # PiContract, PiContractItem, PiData
│       │   ├── order_pi_record.py   # OrderPiRecord（合并记录）
│       │   ├── shipment_doc.py     # ShipmentDoc（文档版本）
│       │   ├── msds_index.py        # MSDSIndex
│       │   ├── msds_correction.py   # MSDSCorrection
│       │   └── transport_report.py  # TransportReport
│       ├── schemas/
│       │   ├── order.py             # Pydantic schemas（订单解析/保存）
│       │   ├── pi_contract.py       # Pydantic schemas（PI）
│       │   └── order_pi_record.py   # Pydantic schemas（合并记录）
│       ├── main.py                  # FastAPI 入口
│       └── database.py             # SQLite 连接
├── frontend/
│   └── src/
│       ├── api/
│       │   ├── orders.ts           # POST /orders/paste, /orders
│       │   ├── pi.ts               # PI 上传 API
│       │   ├── merge.ts            # /merge/orders, /comparison
│       │   ├── packaging.ts       # /packaging/calculate
│       │   ├── packages.ts        # /packages/calculate, /types
│       │   ├── dashboard.ts        # /dashboard/orders, /records
│       │   ├── phase1.ts           # Phase 1 API 客户端
│       │   ├── phase2.ts          # Phase 2 API 客户端
│       │   └── name_mapping.ts    # 品名对照 API
│       ├── components/
│       │   └── phase1/
│       │       ├── PasteTextarea.vue
│       │       ├── OrderPreviewForm.vue
│       │       ├── PiUploadDragger.vue
│       │       ├── PiPreviewTable.vue
│       │       ├── ColumnMappingModal.vue
│       │       ├── PackagingCalculator.vue
│       │       ├── PackagingTypeSelect.vue
│       │       ├── RemainderAllocationDialog.vue
│       │       ├── DiffCell.vue
│       │       ├── OrderExpandRow.vue
│       │       ├── QuickJumpPopover.vue
│       │       ├── AirFreightPanel.vue
│       │       └── LandTransportPanel.vue
│       └── views/
│           ├── Layout.vue
│           ├── phase1/
│           │   ├── OrderPaste.vue
│           │   ├── Phase1Workflow.vue
│           │   └── Dashboard.vue
│           ├── phase2/
│           │   ├── Phase2Workflow.vue
│           │   └── components/
│           │       ├── ReferencePanel.vue
│           │       ├── DocumentEditor.vue
│           │       ├── MyDocumentsDrawer.vue
│           │       ├── DataCenterPanel.vue
│           │       ├── BookingConfirmDialog.vue
│           │       └── FieldReferenceCard.vue
│           ├── phase3/
│           │   └── Phase3Workflow.vue
│           └── data-center/
│               └── DataCenter.vue
├── docs/                        # PRD、API、TEST 文档
├── 参考/                        # 旧版 PyQt5 参考
└── data/                        # SQLite 数据库
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

### OnlyOffice（可选）

```bash
docker run -d -p 8080:80 onlyoffice/documentserver
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
| 包装计算 | ✅ | 13种桶型、2种托盘、20GP判断、多行计算器 |
| 数据看板 | ✅ | Phase1Workflow 只读预览 |
| 余数分配 | ✅ | 每行余数独立选择板规格 |

## Phase 2 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| Phase 2 API 路由 | ✅ | 文档生成、OnlyOffice 回调 |
| OnlyOfficeService | ✅ | Booking/LOI/MSDS 生成、标记填充 |
| DocumentService | ✅ | 模板复制、BLOB 存储、版本管理 |
| ShipmentDoc 模型 | ✅ | 文档版本存储、content_hash 幂等 |
| ExportCodesService | ✅ | HS code 查询服务 |
| OnlyOffice 回调 | ✅ | content_hash 去重、悲观锁释放 |
| Phase 2 前端页面 | ✅ | Phase2Workflow + ReferencePanel + DocumentEditor |
| PI 上传 (.pdf) | ✅ | 支持 PDF via OCR |
| consignee/destination | ✅ | PI Header 字段从 PDF 提取 |
| 数据中心（MSDS） | ✅ | 搜索、预览、目录树、修正上传 |
| 运输鉴定报告 | ✅ | 在 references/ 中搜索 + 预览 |
| 空白模板 | ✅ | Booking/LOI/MSDS 空白模板 |
| 我的模板 | ✅ | 独立于订单的模板实例管理 |
| 报关资料 | ✅ | 5 sheet 工作簿生成 |

## Phase 3 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| Phase3Workflow 搭建 | ✅ | 页面骨架 |
| 报关功能 | 进行中 | — |

## 核心文档

| 文档 | 说明 |
|------|------|
| `docs/PRD-ShippingHelper-Web.md` | 主 PRD |
| `docs/PRD-ShippingHelper-Web-P1v2.md` | Phase 1 详细需求 |
| `docs/PRD-ShippingHelper-Web-P2v2.md` | Phase 2 详细需求 |
| `docs/PRD-ShippingHelper-Web-P1v2-OrderParsing.md` | 订单解析模块设计方案 |
| `docs/API-ShippingHelper-v1.md` | API 接口文档（2026-06-15 更新） |
| `docs/TEST-ShippingHelper-v1.md` | 集成测试文档 |
| `docs/superpowers/plans/` | 实施计划 |
| `docs/superpowers/specs/` | 设计规格 |
| `CLAUDE.md` | Claude Code 开发指南（中文） |

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

Phase 1 落库数据存储在 `order_pi_records` 表（合并记录），不直接写入 orders/order_items 表。

## API 端点概览

| 分组 | 端点 |
|------|------|
| 订单 | `POST /api/v1/orders/paste`, `POST /api/v1/orders` |
| PI | `POST /api/v1/pi/upload` |
| 数据关联 | `GET /api/v1/merge/orders`, `GET /api/v1/merge/orders/{id}/comparison` |
| 包装计算 | `GET /api/v1/packaging/types`, `POST /api/v1/packaging/calculate` |
| 数据看板 | `GET /api/v1/dashboard/orders`, `POST /api/v1/dashboard/records` |
| 文档生成 | `POST /api/v1/documents/booking`, `GET /api/v1/documents/loi` |
| OnlyOffice | `POST /api/v1/onlyoffice/callback`, `GET /api/v1/onlyoffice/download/{key}` |
| 数据中心 | `GET /api/v1/data-center/search`, `GET /api/v1/data-center/tree` |
| 运输报告 | `GET /api/v1/transport-reports/search` |
| 品名对照 | `GET /api/v1/name-mapping`, `GET /api/v1/name-mapping/lookup` |

详见 `docs/API-ShippingHelper-v1.md`。

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