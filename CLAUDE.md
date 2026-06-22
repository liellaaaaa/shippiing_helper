# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库工作时的指引文件。

---

## 项目概述

ShippingHelper 是一款外贸船务效率工具。

**当前架构**：Vue 3 + FastAPI + SQLite + OnlyOffice（详见 `docs/` 中的 PRD 文档）

**旧版参考**：`参考/` 文件夹包含旧版 PyQt5 实现，业务逻辑以此为准：
- `参考/core/` - 核心业务逻辑（order_parser, pi_extractor, package_calculator 等）
- `参考/knowledge/` - 产品知识和包装数据（JSON）
- `参考/phase2/` - Phase 2 单证生成（booking, LOI, MSDS）

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 认证 | JWT Token（python-jose） |
| 文档编辑 | OnlyOffice Document Server（Docker） |
| 编辑器 | OnlyOffice（Excel + Word 统一，不使用 Luckysheet） |

---

## 开发流程（强制）

所有任务必须遵循以下流程：

```
用户请求 → brainstorming skill → 设计文档 → 用户批准 → writing-plans skill → 实现计划 → 用户批准
```

**硬门槛**：用户批准设计文档前，禁止写代码。

使用的 skills：
- `brainstorming` - 任何实现工作前
- `writing-plans` - 设计批准后
- `frontend-design` - UI 组件
- `verification-before-completion` - 任务完成前验证

---

## 关键架构决策

| 决策 | 选择 |
|------|------|
| 文档编辑器 | **OnlyOffice 独占**（Excel + Word 统一，不用 Luckysheet） |
| 计算逻辑 | 单一来源：`backend/app/services/calculation_service.py`（Phase 1 & 2 共用） |
| 数据库 | SQLite WAL 模式，文件存储 |
| 文件存储 | 数据库 BLOB，不用共享文件夹 |
| 模板原则 | 模板只读，实例从模板复制 |
| 悲观锁 | 订单级锁（`order_status`, `locked_by`, `locked_at`） |
| OnlyOffice 回调 | 后端必须暴露 `POST /api/v1/onlyoffice/callback` 接收 Document Server 文件流，保存成功则写入 DB 并释放锁 |

---

## OnlyOffice 回调接口

用户点击 OnlyOffice 保存时，Document Server 会 POST 文件到回调 URL，后端必须：

```python
# POST /api/v1/onlyoffice/callback
# 请求：multipart/form-data 文件流
# 响应：JSON status

@app.post("/api/v1/onlyoffice/callback")
async def onlyoffice_callback(doc_key: str, user: str, file: UploadFile = File(default=None)):
    # 1. 接收 Document Server 发送的文件流
    # 2. 检查 content_hash 避免重复保存
    # 3. 写入 shipment_docs 表
    # 4. 版本号递增
    # 5. 返回 {"error": 0}
```

**回调行为**：
- Document Server 通过 HTTP POST 发送 `document` 字段（文件流）
- 后端接收后存 DB，释放锁
- 绝不直接写共享文件夹（避免 Windows 文件句柄问题）

---

## 核心业务规则

### 包装计算（复用）
所有重量/体积计算必须使用 `calculation_service.py`：
- `calculate_drums(quantity_kg, net_kg_per_drum)` - drums = ⌈order_qty / net_per_drum⌉
- `calculate_pallets(drums, capacity_per_pallet)` - pallets = ⌈drums / capacity⌉
- `calculate_volume(drums, cbm_per_drum, pallets, cbm_per_pallet)`
- `calculate_gross_weight(drums, gross_per_drum, pallets, pallet_weight)`
- `judge_container(total_volume_cbm, total_weight_kg)` - 20GP ≤28CBM 且 ≤21000kg

### 数据优先级（报关品名/H.S.Code）
- 报关品名：订单 > PI > 知识库
- H.S.Code：PI > 知识库
- 关联字段：`internal_code`（订单-PI）、`pi_no`（PI contract）

---

## 项目结构

```
shipping_helper/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── v1/
│       │   │   ├── auth.py        # POST /api/v1/auth/login（JWT 认证）
│       │   │   ├── orders.py      # POST /api/v1/orders/paste, POST /api/v1/orders
│       │   │   ├── pi.py         # POST /api/v1/pi/upload (.xlsx/.xls/.pdf)
│       │   │   ├── merge.py      # GET /api/v1/merge/orders, /comparison, /pi-contracts
│       │   │   ├── packages.py   # GET /api/v1/packages/calculate (sea/air/land)
│       │   │   ├── packaging.py  # POST /api/v1/packaging/calculate, /calculate-schemes
│       │   │   ├── dashboard.py  # GET /api/v1/dashboard/orders, POST /records
│       │   │   ├── documents.py  # POST /api/v1/documents/booking, /loi, /msds, /customs
│       │   │   ├── onlyoffice.py # POST /api/v1/onlyoffice/callback, GET /download
│       │   │   ├── msds.py       # GET /api/v1/msds/, /content, /reindex
│       │   │   ├── transport.py  # POST /api/v1/transport/upload (PDF)
│       │   │   ├── export_codes.py # GET /api/v1/export-codes/
│       │   │   ├── data_center.py # GET /api/v1/data-center/search, /tree, /file
│       │   │   ├── transport_reports.py # GET /search, POST /reindex
│       │   │   └── name_mapping.py # GET /api/v1/name-mapping, /lookup
│       │   └── deps.py            # FastAPI 依赖注入
│       ├── core/
│       │   ├── order_parser.py    # 分隔符检测、批量去重、聚合
│       │   ├── knowledge_filler.py # HS code + 报关品名自动补全
│       │   ├── pi_parser.py       # PI 文件解析 (.xlsx/.xls/.pdf OCR)
│       │   ├── config.py          # 目录路径和环境配置
│       │   └── name_mapping.py    # 产品名称中英文对照
│       ├── services/
│       │   ├── auth_service.py    # JWT 认证服务
│       │   ├── order_service.py   # 订单服务层
│       │   ├── pi_service.py      # PI 服务层
│       │   ├── packaging_service.py # 包装计算（桶数、托盘、20GP）
│       │   ├── calculation_service.py # 核心计算逻辑（Phase 1 & 2 共用）
│       │   ├── merge_service.py   # 订单-PI 合并 + 比对
│       │   ├── save_service.py    # 订单+PI+包装的事务性保存
│       │   ├── document_service.py # 文档模板 + BLOB 存储
│       │   ├── onlyoffice_service.py # OnlyOffice JWT + 配置生成
│       │   ├── export_service.py  # Excel 导出
│       │   ├── data_center_service.py # MSDS 搜索 + 索引
│       │   ├── msds_service.py    # MSDS 文本提取 + 物理特性
│       │   ├── transport_service.py # 运输鉴定报告解析 + 索引
│       │   ├── name_mapping_service.py # 品名对照查询
│       │   └── export_codes_service.py # HS code 查询
│       ├── models/
│       │   ├── user.py           # User Pydantic 模型
│       │   ├── order.py          # orders, order_items, packaging_types, pallets, products_knowledge
│       │   ├── pi_contract.py     # PiContract, PiContractItem, PiData
│       │   ├── order_pi_record.py # OrderPiRecord（合并记录）
│       │   ├── shipment_doc.py    # ShipmentDoc（文档版本）
│       │   ├── msds_index.py      # MSDSIndex
│       │   ├── msds_correction.py # MSDSCorrection
│       │   └── transport_report.py # TransportReport
│       ├── schemas/
│       │   ├── order.py          # Pydantic schemas（订单解析/保存）
│       │   ├── pi_contract.py    # Pydantic schemas（PI）
│       │   └── order_pi_record.py # Pydantic schemas（合并记录）
│       ├── main.py               # FastAPI 入口
│       └── database.py           # SQLite 连接
├── frontend/
│   └── src/
│       ├── api/
│       │   ├── axios.ts         # Axios 实例 + JWT 拦截器
│       │   ├── orders.ts        # POST /orders/paste, /orders
│       │   ├── pi.ts            # PI 上传 API
│       │   ├── merge.ts         # GET /merge/orders, /comparison, /pi-contracts
│       │   ├── packaging.ts     # POST /packaging/calculate, /calculate-order
│       │   ├── packages.ts      # GET /packages/calculate, /types, /recommend
│       │   ├── dashboard.ts     # GET /dashboard/orders, /records, export
│       │   ├── phase1.ts        # Phase 1 API 客户端
│       │   ├── phase2.ts        # Phase 2 API 客户端（documents, msds, data-center, onlyoffice）
│       │   └── name_mapping.ts  # GET /name-mapping, /lookup
│       ├── stores/
│       │   └── auth.ts         # Pinia 认证状态管理
│       ├── views/
│           ├── auth/
│           │   └── Login.vue    # 登录页面
│       ├── components/
│       │   └── phase1/
│       │       ├── PasteTextarea.vue       # 订单粘贴输入
│       │       ├── OrderPreviewForm.vue    # 订单预览 + 编辑
│       │       ├── PiUploadDragger.vue     # PI 文件拖拽上传
│       │       ├── PiPreviewTable.vue      # PI 预览表格
│       │       ├── ColumnMappingModal.vue  # PI 列映射弹窗
│       │       ├── PackagingCalculator.vue # 多行包装计算器
│       │       ├── PackagingTypeSelect.vue  # 包装类型下拉
│       │       ├── RemainderAllocationDialog.vue # 余数分配弹窗
│       │       ├── DiffCell.vue            # 比对差异单元格
│       │       ├── OrderExpandRow.vue     # 订单展开行
│       │       ├── QuickJumpPopover.vue   # 快速跳转弹窗
│       │       ├── AirFreightPanel.vue    # 空运计算面板
│       │       └── LandTransportPanel.vue # 陆运计算面板
│       └── views/
│           ├── Layout.vue                # 应用布局
│           ├── phase1/
│           │   ├── OrderPaste.vue        # 订单粘贴页面
│           │   ├── Phase1Workflow.vue    # Phase 1 工作流页面
│           │   └── Dashboard.vue        # Phase 1 看板
│           ├── phase2/
│           │   ├── Phase2Workflow.vue    # Phase 2 主工作流
│           │   └── components/
│           │       ├── ReferencePanel.vue    # 4标签页参考面板
│           │       ├── DocumentEditor.vue     # OnlyOffice 编辑器封装
│           │       ├── MyDocumentsDrawer.vue  # 我的模板抽屉
│           │       ├── DataCenterPanel.vue    # 数据中心面板
│           │       ├── BookingConfirmDialog.vue # 订舱确认弹窗
│           │       └── FieldReferenceCard.vue  # 字段参考卡片
│           ├── phase3/
│           │   └── Phase3Workflow.vue    # Phase 3（报关）
│           └── data-center/
│               └── DataCenter.vue        # 独立数据中心页面
├── docs/
│   ├── PRD-ShippingHelper-Web.md        # 主 PRD
│   ├── PRD-ShippingHelper-Web-P1v2.md  # Phase 1 规格
│   ├── PRD-ShippingHelper-Web-P2v2.md  # Phase 2 规格
│   ├── PRD-ShippingHelper-Web-P1v2-OrderParsing.md  # 订单解析设计
│   ├── API-ShippingHelper-v1.md        # API 参考（2026-06-15 更新）
│   ├── TEST-ShippingHelper-v1.md       # 集成测试文档
│   └── superpower/plans/              # 实现计划
│   └── superpower/specs/             # 设计规格
├── 参考/                              # 旧版 PyQt5 参考
└── data/
    └── shipping_helper.db            # SQLite 数据库
```

---

## 数据模型

核心表（详见 `docs/` PRD）：
- `orders` - 订单头表
- `order_items` - 产品明细表（外键→orders.id）— **一单多品**
- `order_pi_records` - 合并记录表（Phase 1 落库数据）
- `packaging_types` - 13 种包装类型
- `pallets` - 2 种托盘
- `pi_contracts` - PI 合同表（含 PiContractItem）
- `pi_data` - PI 摘要表
- `products_knowledge` - 产品知识库
- `shipment_docs` - 文档 BLOB 存储（含版本）
- `msds_index` - MSDS 文件索引
- `msds_correction` - MSDS 修正记录
- `transport_report` - 运输鉴定报告索引
- `templates` - 文档模板配置

> ⚠️ **重要**：`internal_code` 仅存在于 `order_items`（产品级），`orders` 表不存储此字段。

---

## API 端点总览

### 订单 & 粘贴
- `POST /api/v1/orders/paste` — 解析粘贴文本
- `POST /api/v1/orders` — 保存订单
- `GET /api/v1/orders/{id}` — 查询单个订单

### PI 合同
- `POST /api/v1/pi/upload` — 上传并解析 PI 文件（.xlsx/.xls/.pdf）
- `POST /api/v1/pi/contracts` — 保存 PI 合同（待实现）
- `GET /api/v1/pi/contracts` — 查询 PI 合同（待实现）

### 数据关联
- `GET /api/v1/merge/orders` — 订单列表（含关联状态）
- `GET /api/v1/merge/orders/{id}/comparison` — 订单比对数据
- `GET /api/v1/merge/orders/{id}/pi-contracts` — 订单关联的 PI 合同

### 包装计算
- `GET /api/v1/packaging/types` — 所有包装种类
- `GET /api/v1/packaging/pallets` — 所有托盘种类
- `POST /api/v1/packaging/calculate` — 计算包装方案
- `POST /api/v1/packaging/calculate-schemes` — 所有方案
- `POST /api/v1/packaging/calculate-order` — 订单级别汇总
- `GET /api/v1/packages/calculate` — 海运/空运/陆运统一入口
- `GET /api/v1/packages/recommend` — 推荐包装类型

### 数据看板
- `GET /api/v1/dashboard/orders` — 看板合并数据
- `POST /api/v1/dashboard/records` — 落库
- `GET /api/v1/dashboard/records` — 查询落库记录
- `DELETE /api/v1/dashboard/records/{id}` — 删除订单
- `GET /api/v1/dashboard/export` — 导出 Excel

### 文档生成
- `POST /api/v1/documents/booking` — 生成订舱单
- `GET /api/v1/documents/loi` — 生成 LOI
- `GET /api/v1/documents/msds` — 生成 MSDS
- `GET /api/v1/documents/customs` — 生成报关资料
- `GET /api/v1/documents/template/{type}` — 空白模板
- `GET /api/v1/documents/my-templates` — 我的模板
- `GET /api/v1/documents/history/{order_id}` — 文档历史

### OnlyOffice
- `POST /api/v1/onlyoffice/jwt` — 创建 JWT
- `POST /api/v1/onlyoffice/callback` — 文档保存回调
- `GET /api/v1/onlyoffice/download/{key}` — 下载文档

### 数据中心
- `GET /api/v1/data-center/search` — MSDS 搜索
- `GET /api/v1/data-center/tree` — 目录树
- `GET /api/v1/data-center/file` — 按路径读取文件
- `POST /api/v1/data-center/upload-corrected/{id}` — 上传修正版
- `POST /api/v1/data-center/reindex` — 重建索引

### 运输鉴定报告
- `GET /api/v1/transport-reports/search` — 搜索
- `GET /api/v1/transport-reports/files/{filename}` — 预览 PDF
- `POST /api/v1/transport-reports/reindex` — 重建索引

### 其他
- `GET /api/v1/msds/` — MSDS 列表
- `GET /api/v1/msds/{id}/content` — MSDS 内容
- `POST /api/v1/transport/upload` — 上传运输报告
- `GET /api/v1/export-codes/` — HS Code 查询
- `GET /api/v1/name-mapping` — 品名对照
- `GET /api/v1/name-mapping/lookup` — 品名查询

---

## 旧版代码参考

`参考/` 文件夹中的 Python 实现供参考：

| 文件 | 用途 |
|------|------|
| `参考/core/order_parser.py` | 订单解析（Tab/换行分隔，23字段） |
| `参考/core/pi_extractor.py` | PI 文件提取（.xls via xlrd） |
| `参考/core/package_calculator.py` | 包装计算逻辑 |
| `参考/core/merger.py` | 数据合并（订单 + PI + 编码） |
| `参考/knowledge/packaging_data.json` | 13 种包装类型、2 种托盘、容量映射 |

---

## 阶段开发进度

**Phase 1**（订单处理）：
1. ~~项目初始化（Vue + FastAPI）~~ ✅
2. ~~订单粘贴解析~~ ✅
3. ~~PI 文件提取（.xls/.xlsx/.pdf OCR）~~ ✅
4. ~~数据合并（internal_code 关联）~~ ✅
5. ~~包装计算（13类型、2托盘、20GP判断、每托盘容量）~~ ✅
6. ~~数据看板（只读订单 + PI 合并预览）~~ ✅

**Phase 2**（单证生成）：
1. ~~船务数据管理~~ ✅
2. ~~模板管理~~ ✅
3. ~~单证生成（Booking, MSDS, LOI via OnlyOffice）~~ ✅
4. ~~数据展示（左侧看板、右侧编辑器）~~ ✅
5. ~~空白模板和我的模板支持~~ ✅
6. ~~数据中心（MSDS 搜索、运输鉴定报告）~~ ✅
7. ~~OnlyOffice 回调（含版本管理）~~ ✅

**Phase 3**（报关）：
- 进行中 — `Phase3Workflow.vue` 已搭建

---

## 重要说明

1. **OnlyOffice 集成**：所有 Excel 和 Word 文档使用 OnlyOffice。Document Server URL 通过环境变量配置。

2. **前端组件复用**：所有文档类型（Booking, MSDS, LOI）共用一个 `OnlyOfficeEditor.vue` 组件，不应为每种页面创建单独的编辑器组件。组件接收 `config`、`documentServerUrl`、`events` 作为 props。

3. **Internal Code 位置**：`internal_code` 仅存储在 `order_items`（产品级），`orders` 表不包含此字段。

4. **计算一致性**：重量/体积/20GP 逻辑仅存在于 `calculation_service.py`，Phase 1 和 Phase 2 调用同一服务。

5. **锁机制**：用户打开文档编辑时立即加锁（`order_status = "editing"`, `locked_by`, `locked_at`），保存/关闭时释放。

6. **模板文件**：绝不直接修改模板文件，总是复制到实例后再填充数据。

7. **Phase 1 落库**：数据通过 `POST /api/v1/dashboard/records` 写入 `order_pi_records` 表，不是直接写入 orders/order_items 表。

---

## 常用命令

```bash
# 后端
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev

# Docker (OnlyOffice)
docker run -d -p 8080:80 onlyoffice/documentserver
```

---

## Phase 1 完成清单

| 模块 | 状态 | 备注 |
|------|------|------|
| 项目初始化 | ✅ 完成 | Vue 3 + FastAPI + SQLite 脚手架 |
| 订单粘贴解析 | ✅ 完成 | Tab/CRLF 分隔符、智能聚合、去重、知识库填充 |
| PI 文件提取 | ✅ 完成 | .xlsx/.xls/.pdf 上传、列映射、置信度、pi_data upsert、OCR |
| 数据合并 | ✅ 完成 | internal_code 关联、订单-PI 合并 |
| 包装计算 | ✅ 完成 | 13 桶类型、2 托盘、20GP 判断、多行计算器、每托盘容量 |
| 数据看板 | ✅ 完成 | Phase1Workflow 中的只读订单 + PI 合并预览 |
| 余数分配 | ✅ 完成 | 每行余数独立选择板规格 |

**已完成文件：**

后端：
- `backend/app/models/order.py` — orders + order_items + packaging_types + products_knowledge
- `backend/app/models/pi_contract.py` — PiContract + PiContractItem + PiData models
- `backend/app/models/order_pi_record.py` — OrderPiRecord 合并记录模型
- `backend/app/models/shipment_doc.py` — ShipmentDoc 文档版本
- `backend/app/models/msds_index.py` — MSDSIndex
- `backend/app/models/transport_report.py` — TransportReport
- `backend/app/schemas/pi_contract.py` — PI 上传/保存/查询的 Pydantic schemas
- `backend/app/core/order_parser.py` — 分隔符检测、批量去重、聚合
- `backend/app/core/knowledge_filler.py` — HS code + 报关品名自动补全
- `backend/app/core/pi_parser.py` — 列映射、智能降级、置信度
- `backend/app/services/order_service.py` — 服务层（事务性保存）
- `backend/app/services/pi_service.py` — PI 服务层 + pi_data upsert
- `backend/app/services/packaging_service.py` — 包装计算（桶数、托盘、体积、20GP）
- `backend/app/services/calculation_service.py` — 核心计算逻辑（Phase 1 & 2 共用）
- `backend/app/services/merge_service.py` — 订单-PI 合并 + 比对
- `backend/app/services/save_service.py` — 订单+PI+包装的事务性保存
- `backend/app/services/document_service.py` — 文档模板 + BLOB 存储
- `backend/app/services/onlyoffice_service.py` — OnlyOffice JWT + 配置
- `backend/app/services/export_service.py` — Excel 导出
- `backend/app/services/data_center_service.py` — MSDS 搜索 + 索引
- `backend/app/services/msds_service.py` — MSDS 文本提取
- `backend/app/services/transport_service.py` — 运输鉴定报告解析
- `backend/app/services/name_mapping_service.py` — 品名中英文对照
- `backend/app/services/export_codes_service.py` — HS code 查询
- `backend/app/api/v1/orders.py` — REST API 端点
- `backend/app/api/v1/pi.py` — PI 上传/保存/查询端点
- `backend/app/api/v1/merge.py` — 订单合并 + 比对端点
- `backend/app/api/v1/packaging.py` — 包装计算端点
- `backend/app/api/v1/packages.py` — 运输模式包装端点
- `backend/app/api/v1/dashboard.py` — 看板 + 记录端点
- `backend/app/api/v1/documents.py` — 文档生成端点
- `backend/app/api/v1/onlyoffice.py` — OnlyOffice 回调 + 下载
- `backend/app/api/v1/msds.py` — MSDS 列表端点
- `backend/app/api/v1/transport.py` — 运输报告上传
- `backend/app/api/v1/export_codes.py` — HS code 查询
- `backend/app/api/v1/data_center.py` — 数据中心搜索 + 目录树
- `backend/app/api/v1/transport_reports.py` — 运输鉴定报告搜索
- `backend/app/api/v1/name_mapping.py` — 品名对照
- `backend/app/api/deps.py` — FastAPI 依赖注入
- `backend/migrations/001_add_pi_contracts.py` — 表迁移
- `backend/migrations/002_add_indexes.py` — 索引迁移

前端：
- `frontend/src/api/orders.ts` — Axios API 客户端
- `frontend/src/api/pi.ts` — PI API 客户端
- `frontend/src/api/merge.ts` — 合并 API 客户端
- `frontend/src/api/packaging.ts` — 包装 API 客户端
- `frontend/src/api/packages.ts` — Packages API 客户端
- `frontend/src/api/dashboard.ts` — 看板 API 客户端
- `frontend/src/api/phase1.ts` — Phase 1 API 客户端
- `frontend/src/api/phase2.ts` — Phase 2 API 客户端（documents, msds, data-center）
- `frontend/src/api/name_mapping.ts` — 品名对照 API 客户端
- `frontend/src/components/phase1/PasteTextarea.vue` — 粘贴输入组件
- `frontend/src/components/phase1/OrderPreviewForm.vue` — 预览 + 编辑组件
- `frontend/src/components/phase1/PiUploadDragger.vue` — 拖拽上传（.xlsx/.xls/.pdf）
- `frontend/src/components/phase1/PiPreviewTable.vue` — 可编辑预览表格
- `frontend/src/components/phase1/ColumnMappingModal.vue` — 列映射弹窗
- `frontend/src/components/phase1/PackagingCalculator.vue` — 包装计算器组件
- `frontend/src/components/phase1/PackagingTypeSelect.vue` — 包装类型下拉
- `frontend/src/components/phase1/RemainderAllocationDialog.vue` — 余数分配弹窗
- `frontend/src/components/phase1/DiffCell.vue` — 比对差异单元格
- `frontend/src/components/phase1/OrderExpandRow.vue` — 订单展开行
- `frontend/src/components/phase1/QuickJumpPopover.vue` — 快速跳转弹窗
- `frontend/src/components/phase1/AirFreightPanel.vue` — 空运计算面板
- `frontend/src/components/phase1/LandTransportPanel.vue` — 陆运计算面板
- `frontend/src/views/phase1/OrderPaste.vue` — 订单粘贴页面
- `frontend/src/views/phase1/Phase1Workflow.vue` — Phase 1 工作流页面
- `frontend/src/views/phase1/Dashboard.vue` — Phase 1 看板
- `frontend/src/views/phase2/Phase2Workflow.vue` — Phase 2 主工作流页面
- `frontend/src/views/phase2/components/ReferencePanel.vue` — 4标签页参考面板
- `frontend/src/views/phase2/components/DocumentEditor.vue` — OnlyOffice 编辑器封装
- `frontend/src/views/phase2/components/MyDocumentsDrawer.vue` — 我的模板抽屉
- `frontend/src/views/phase2/components/DataCenterPanel.vue` — 数据中心面板
- `frontend/src/views/phase2/components/BookingConfirmDialog.vue` — 订舱确认弹窗
- `frontend/src/views/phase2/components/FieldReferenceCard.vue` — 字段参考卡片
- `frontend/src/views/phase3/Phase3Workflow.vue` — Phase 3 工作流（报关）
- `frontend/src/views/data-center/DataCenter.vue` — 独立数据中心页面

---

## Phase 2 完成清单

| 模块 | 状态 | 备注 |
|------|------|------|
| JWT 登录认证 | ✅ 完成 | AuthService、登录页面、路由守卫、Axios 拦截器 |
| Phase 2 API 路由 | ✅ 完成 | 所有端点已在 main.py 注册 |
| OnlyOfficeService | ✅ 完成 | 单证生成（Booking/LOI/MSDS）、基于标记填充 |
| DocumentService | ✅ 完成 | 模板复制、BLOB 存储、版本管理 |
| ShipmentDoc 模型 | ✅ 完成 | 文档版本存储（含 content_hash 去重） |
| ExportCodesService | ✅ 完成 | HS code 查询服务 |
| OnlyOffice 回调 | ✅ 完成 | `POST /api/v1/onlyoffice/callback` 含 content_hash 去重 |
| Phase 2 前端页面 | ✅ 完成 | Phase2Workflow + ReferencePanel + DocumentEditor 组件 |
| PI 上传（.pdf） | ✅ 完成 | PiUploadDragger 支持 .pdf OCR |
| 收货人/目的港 | ✅ 完成 | PI Header 字段从 PDF 提取 |
| 数据中心（MSDS） | ✅ 完成 | 搜索、预览、目录树、修正上传 |
| 运输鉴定报告 | ✅ 完成 | 在 references/ 中搜索 + 预览 |
| 空白模板 | ✅ 完成 | `GET /api/v1/documents/template/{type}` |
| 我的模板 | ✅ 完成 | `GET /api/v1/documents/my-templates` |
| 报关资料 | ✅ 完成 | `GET /api/v1/documents/customs`（5 sheet 工作簿） |

*最后更新：2026/06/22*