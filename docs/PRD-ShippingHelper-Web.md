# PRD: ShippingHelper Web 重构 - 总需求文档

> 本文档为项目总需求文档，Phase 1 详细展开见 `P1v2.md`，Phase 2 详细展开见 `P2v2.md`。
> 存放路径：`C:\Users\windows\Desktop\shippiing_helper\docs\PRD-ShippingHelper-Web.md`
> 创建时间：2026/05/28

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026/05/28 | 初始生成 |
| 2026/05/28 | 订单表字段更新（23→26字段，按实际表头） |
| 2026/05/28 | PI数据表拆分为 pi_data + pi_contracts |
| 2026/05/28 | 数据源改为数据库存储，不再维护汇总Excel |
| 2026/05/28 | 包装计算逻辑明确（13种包装、卡板映射、20GP判定） |
| 2026/05/28 | 全栈统一 OnlyOffice，移除 Luckysheet |
| 2026/05/28 | orders 表拆分为 orders（订单头）+ order_items（产品明细），支持"一单多品" |

---

## 1. 概述

ShippingHelper 船务部效率工具 Web 版本，将原 PyQt5 桌面应用重构为现代化 Web 应用。采用 Vue.js + FastAPI + SQLite + OnlyOffice 技术栈，在浏览器内实现在线订单处理、包装计算、数据汇聚、模板编辑与文档生成的全流程数字化。

**核心价值**：解决外贸订单处理中的数据重复录入、包装计算繁琐、文档制作耗时等问题，通过数字化工作流提升船务部效率。

**技术栈**：
- 前端：Vue 3 + Vite + Element Plus + OnlyOffice + Pinia
- 后端：FastAPI + SQLAlchemy + SQLite
- 文档服务：OnlyOffice Document Server（Docker 部署）

**业务流程（Phase 1）**：
1. 业务员提供 PI 合同文件 → 系统解析提取收发货人、品名、数量、H.S.Code 等
2. 业务员填写销售订单表（系统录入或批量导入）
3. 系统通过 `internal_code` 自动关联两者数据，**不再手动汇总 Excel**

**改造要点**：原 PyQt 桌面版中由船务部手动维护的"外贸订单PI合同汇总.xlsx"，在 Web 版中改为数据库存储。

---

## 2. 目标

- 将原 PyQt5 桌面应用重构为 Vue + FastAPI 的 Web 应用
- 保留 Phase 1（订单解析 + 包装计算）和 Phase 2（订舱出货）业务流程
- **全栈统一使用 OnlyOffice**（Excel + Word），无 Luckysheet
- **计算逻辑统一复用**，Phase 1 和 Phase 2 调用同一服务，保证体积/重量计算一致
- AI 辅助数据校验与推荐（优先级：低，Phase 1-2 完成后考虑）
- 支持局域网多用户部署
- SQLite 作为本地数据存储，预置历史数据

---

## 3. 技术架构

### 3.1 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 现代化响应式前端框架 |
| UI 组件库 | Element Plus | 企业级 UI 组件 |
| 文档组件 | OnlyOffice | 全栈统一（Excel + Word） |
| 状态管理 | Pinia | Vue 3 官方推荐状态管理 |
| 后端框架 | FastAPI | 高性能 Python API 框架 |
| 数据库 | SQLite | Python 内置，支持局域网文件共享 |
| 文档服务 | OnlyOffice Document Server | Docker 部署，iframe 嵌入 |

### 3.2 计算服务（复用）

> **重要设计原则**：Phase 1（包装计算）和 Phase 2（订舱出货）共用同一套计算逻辑，代码不重复。

**服务位置**：`backend/app/services/calculation_service.py`

**计算方法（全局唯一）**：

| 方法 | 说明 |
|------|------|
| `calculate_drum_count(quantity_kg, net_kg_per_drum)` | 计算桶/包数量 = ⌈订单量 / 单桶净重⌉ |
| `calculate_pallet_count(drum_count, pallet_spec, capacity_map)` | 计算卡板数 = ⌈桶数 / 单板容量⌉ |
| `calculate_volume(drum_count, cbm_per_drum, pallet_count, cbm_per_pallet)` | 计算总体积 = 桶数×单桶CBM + 卡板数×卡板CBM |
| `calculate_gross_weight(drum_count, gross_kg_per_drum, pallet_count, pallet_weight)` | 计算总毛重 = 桶数×单桶毛重 + 卡板数×卡板皮重 |
| `judge_20gp(total_volume_cbm, total_weight_kg)` | 判定：总体积≤28CBM 且 总毛重≤21000kg → 适合/超出 |
| `build_packing_plan(drum_count, pallet_count, capacity_per_pallet)` | 生成装配方案文案 |

**调用关系**：
- Phase 1 包装计算 → 调用 `calculation_service`
- Phase 2 订舱出货 → 调用同一 `calculation_service`
- 两侧输入参数相同，输出结果一致

**不重复原则**：所有体积/重量/20GP 判定逻辑只写在 `calculation_service.py`，前端和文档生成均通过 API 调用，不在多处重复实现。

### 3.2 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      浏览器 (Browser)                        │
│  ┌─────────────┐  ┌─────────────────────────────────────┐ │
│  │   Vue.js   │  │      OnlyOffice Document Server      │ │
│  │   前端UI   │  │   (iframe 嵌入，Excel + Word 编辑)   │ │
│  └─────────────┘  └─────────────────────────────────────┘ │
│                            │                                │
│                     HTTP/REST API                           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端服务                          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      SQLite 数据库                           │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 项目目录结构

```
shipping_helper_web/
├── frontend/src/
│   ├── api/                # API 调用（Axios）
│   ├── components/         # 公共组件（含 OnlyOfficeEditor.vue）
│   ├── views/
│   │   ├── phase1/        # P1：OrderPaste, PIExtract, DataMerge, PackageCalc, DataDashboard
│   │   └── phase2/        # P2：Shipment, Booking, MSDS, LOI
│   ├── stores/            # Pinia 状态管理
│   └── router/           # Vue Router
├── backend/app/
│   ├── api/v1/           # orders, pi, packages, documents
│   ├── core/             # order_parser, pi_extractor, merger
│   ├── services/          # calculation_service（Phase 1 & 2 共用计算逻辑）
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   └── db/               # database, init_db
├── templates/            # booking, loi, msds（模板文件）
└── data/                  # shipping_helper.db
```

---

## 4. 数据结构

> 详细字段定义见 `P1v2.md` 第 3 章。

### 4.1 核心表

| 表名 | 说明 | 详见 |
|------|------|------|
| orders | 订单头表 | P1v2 §3.1 |
| order_items | 产品明细表（外键→orders） | P1v2 §3.1a |
| packaging_types | 包装规格表（13种） | P1v2 §3.2 |
| pallets | 卡板规格表（2种） | P1v2 §3.3 |
| pi_data | PI 汇总表 | P1v2 §3.4 |
| pi_contracts | 单笔 PI 合同表 | P1v2 §3.5 |
| products_knowledge | 产品知识库 | P1v2 §3.6 |
| export_codes | 出口商品编码表 | P1v2 §3.6 |
| shipment_history | 历史出货记录 | P1v2 §3.6 |
| templates | 模板配置表 | P2v2 §3.2 |

---

## 5. Phase 1 功能需求

> 详见 `P1v2.md` 第 4 章。

- **FR-1.1 ~ FR-1.6** 订单粘贴解析（支持"一单多品"智能聚合）
- **FR-2.1 ~ FR-2.3** PI 文件提取
- **FR-3.1 ~ FR-3.4** 数据关联
- **FR-4.1 ~ FR-4.5** 包装计算（含不打卡板选项、20GP判定、装配方案）
- **FR-5.1 ~ FR-5.3** 数据看板（OnlyOffice 表格只读展示）

---

## 6. Phase 2 功能需求

> 详见 `P2v2.md`。

- **FR-6.1 ~ FR-6.4.3** 订舱出货数据管理（含 ShipmentData 聚合模型）
- **FR-6.5 ~ FR-6.8.2** 模板管理（OnlyOffice 全栈统一）
- **FR-6.9 ~ FR-6.13.1** 文档生成（订舱单/MSDS/LOI）
- **FR-6.14 ~ FR-6.17** 数据展示（OnlyOffice 嵌入）

---

## 7. 用户故事

| 编号 | 描述 | 详见 |
|------|------|------|
| US-001 | 订单数据粘贴解析 | P1v2 §5 |
| US-002 | PI 文件关联 | P1v2 §5 |
| US-003 | 包装计算 | P1v2 §5 |
| US-004 | 数据看板展示 | P1v2 §5 |
| US-005 | 订舱单在线编辑 | P2v2 §7 |
| US-006 | 文档生成与下载 | P2v2 §7 |
| US-007 | MSDS/LOI 模板编辑 | P2v2 §7 |

---

## 8. 非目标

- 多用户同时编辑同一订单（SQLite 单用户）
- 审批流程、邮件发送、移动端 App、第三方物流 API
- AI 功能（优先级低，Phase 1-2 后考虑）

---

## 9. 架构约束（关键）

### 9.1 悲观锁（Pessimistic Locking）

> **背景**：一张销售订单只被一个船务部同事跟单，无需多人同时编辑同一订单。但人为覆盖（如两人同时改同一单）仍是业务不可容忍的。

**机制**：
1. 用户 A 打开订单 #123 开始编辑时，系统立即标记 `order_status = "editing"`，`locked_by = "张三"`
2. 用户 B 试图打开 #123 时，系统提示："该订单正在被【张三】处理，请稍后。"
3. 用户 A 保存或退出后，锁自动释放，`order_status` 恢复 `"editing"` → `"saved"`

**表结构扩展（orders 表新增字段）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| order_status | TEXT | 状态：`normal` / `editing` |
| locked_by | TEXT | 当前锁定人姓名 |
| locked_at | DATETIME | 锁定时间 |

**API 行为**：
- `POST /api/v1/documents/open/{order_id}` → 加锁，返回文档流
- `POST /api/v1/documents/save/{order_id}` → 保存并释放锁
- `DELETE /api/v1/documents/close/{order_id}` → 释放锁（用户取消）

### 9.2 文件存储策略

> **背景**：OnlyOffice 默认可能直接操作挂载的共享文件夹，在 Windows 局域网下易出现文件句柄未释放（"文件被占用"错误）。

**方案**：数据库存储（文件流），不依赖共享文件夹直写。

**读取流程**：
```
用户点击"编辑文档"
  → Python 读取 DB 中文件流（BLOB 或文件路径）
  → 传给 OnlyOffice Document Server
  → 用户在 OnlyOffice 中编辑
```

**保存流程**：
```
用户点击"保存"
  → OnlyOffice POST 文件流到 callbackUrl
  → Python 接收文件流，写入 DB
  → 释放锁
```

**表结构扩展（shipment_docs 表）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| order_id | INTEGER FK | 关联订单ID |
| doc_type | TEXT | 文档类型（booking/msds/loi） |
| file_name | TEXT | 文件名 |
| file_blob | BLOB | 文件内容（流） |
| version | INTEGER | 版本号 |
| created_by | TEXT | 创建人 |
| created_at | DATETIME | 创建时间 |

### 9.3 模板与实例物理分离

> **背景**：模板文件是资产，只能复制使用，不可直接修改。

**原则**：
- **模板文件**（`templates` 表）→ 原始模板，只读
- **实例文档**（`shipment_docs` 表）→ 用户每次"生成文档"时，从模板复制一份并填充数据，存入实例表

**生成流程**：
```
用户点击"生成 MSDS"
  → Python 读取 templates 表中对应模板文件
  → Phase 1 数据填充到模板（创建新文档对象，不修改原模板）
  → 生成的文件存入 shipment_docs 表（新版本 version+1）
  → 用户在 OnlyOffice 编辑的是实例文档，不是模板
```

**禁止操作**：任何情况下不直接修改 `templates` 表中的模板文件。

---

## 10. Open Questions

1. OnlyOffice 使用 Cloud 版还是自部署社区版？
2. 是否需要导出历史订单为 Excel？
3. 模板版本管理策略？（保留最近 N 个版本 or 全部保留）
4. 锁超时自动释放时间？（建议 30 分钟）
| order_date | TEXT | 下单日期 |
| order_confirmed | TEXT | 确认下单 |
| production_deadline | TEXT | 生产交期 |
| delivery_date | TEXT | 交货日期 |
| shipment_channel | TEXT | 出货渠道 |
| shipment_method | TEXT | 出货方式 |
| has_sample | TEXT | 有无样品 |
| price_adjusted | TEXT | 是否调价 |
| order_requirement | TEXT | 订单要求 |
| review_status | TEXT | 审核 |
| sales_area | TEXT | 销售区域 |
| shipment_title | TEXT | 出货抬头 |
| document_type | TEXT | 单据类型 |
| spec_abnormal | TEXT | 规格异常 |
| created_at | DATETIME | 创建时间 |

**packaging_types（包装规格表）**——来源：产品包装资料(2020-6-10).xls

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 包装名称（如：30kg蓝桶） |
| dims | TEXT | 外形尺寸（如：250*250*430mm） |
| cbm | REAL | 单桶体积（立方米） |
| tare_kg | REAL | 皮重（kg） |
| gross_kg | REAL | 产品+包装毛重（kg） |
| net_kg | REAL | 产品净重（kg） |
| barrel_type | TEXT | 桶类型（蓝桶/纸桶/胶桶/编织袋/铁桶） |
| pallet_qty_1x1 | INTEGER | 1.0*1.0m卡板容量 |
| pallet_qty_1_1x1_1 | INTEGER | 1.1*1.1m卡板容量 |
| no_pallet_qty | INTEGER | 无卡板20GP容量（仅125kg/200kg/1吨桶） |

**pallets（卡板规格表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 卡板名称（如：1.0*1.0m卡板） |
| size_m | TEXT | 尺寸（如：1.0*1.0） |
| weight_kg | REAL | 皮重（kg，约27kg） |
| cbm | REAL | 卡板体积（立方米） |

**products_knowledge（产品知识库）**——来源：products_knowledge.json + 2024.12.5 最新出口商品编码及报关成分.xlsx

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| internal_code | TEXT | 内部编号（唯一） |
| product_name_cn | TEXT | 产品中文名 |
| customs_name | TEXT | 报关名称 |
| hs_code | TEXT | H.S.Code |
| ingredients | TEXT | 报关成分 |
| appearance | TEXT | 产品外观 |
| barrel_type | TEXT | 推荐桶类型 |
| customer_code | TEXT | 客户编号 |
| customer_name | TEXT | 客户名称 |

**pi_data（PI数据表）**——来源：外贸订单PI合同.xlsx（汇总表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| order_id | INTEGER FK | 关联订单ID |
| pi_no | TEXT | PI号 |
| salesperson | TEXT | 业务员 |
| quantity | REAL | 数量 |
| unit_price | REAL | 单价 |
| amount | REAL | 金额 |
| internal_code | TEXT | 内部编码 |
| product_color | TEXT | 产品颜色 |
| hs_code | TEXT | 海关编码 |
| customs_name | TEXT | 报关品名 |
| customs_ingredients | TEXT | 报关成分 |
| pi_date | TEXT | 日期 |
| order_customs_name | TEXT | 填写订单报关品名 |
| is_ordered | TEXT | 是否下单 |

**pi_contracts（单笔PI合同表）**——来源：Proforma Invoice *.xls（业务员PI合同）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| pi_no | TEXT | PI号 |
| consignee | TEXT | 收货人 |
| consignee_address | TEXT | 收货人地址 |
| pi_date | TEXT | PI日期 |
| product_name_en | TEXT | 品名英文（Description of Goods） |
| quantity | REAL | 数量（kg） |
| unit_price | REAL | 单价 |
| amount | REAL | 金额 |
| hs_code | TEXT | H.S.Code |
| packing_note | TEXT | 包装说明 |
| destination | TEXT | 目的港 |
| shipment_method | TEXT | 运输方式 |
| payment_terms | TEXT | 付款方式 |
| beneficiary_name | TEXT | 受益人名称 |
| beneficiary_bank | TEXT | 受益人银行 |
| beneficiary_address | TEXT | 受益人地址 |
| bank_account | TEXT | 受益人账号 |
| swift_code | TEXT | SWIFT代码 |
| country_of_origin | TEXT | 原产国 |

**export_codes（出口商品编码表）**——来源：2024.12.5 最新出口商品编码及报关成分.xlsx

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| hs_code | TEXT | H.S.Code |
| product_name | TEXT | 产品名称 |
| component | TEXT | 报关成分 |
| category | TEXT | 类别 |

**shipment_history（历史出货记录）**——来源：参考目录 02.订舱出货/衍生文件/

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| order_id | INTEGER FK | 关联订单ID |
| shipment_date | TEXT | 出货日期 |
| booking_no | TEXT | 订舱单号 |
| container_no | TEXT | 柜号 |
| vessel_name | TEXT | 船名 |
| voyage | TEXT | 航次 |
| bl_no | TEXT | B/L单号 |
| remarks | TEXT | 备注 |

**templates（模板配置表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 模板名称 |
| type | TEXT | 类型（booking/loi/msds） |
| file_path | TEXT | 模板文件路径 |
| placeholders | TEXT | 占位符列表（JSON） |
| version | INTEGER | 版本号 |
| updated_at | DATETIME | 更新时间 |

### 4.2 初始数据预置

> Web 版中数据存储在数据库，不再维护汇总 Excel。初始化时将历史数据清洗入库，供查询选择。

**预置优先级**：
1. 包装规格表（13种包装类型）、卡板规格表（2种）、产品知识库（2种产品+客户信息）
2. 历史订单（约50-100条，来自外贸销售订单表.xlsx）
3. 历史 PI 合同（约50-100条，来自 PI 合同文件）
4. 出口商品编码（约100条，来自2024.12.5 最新出口商品编码及报关成分.xlsx）
5. 模板文件复制到 templates/ 目录

## 5. Phase 1 功能需求

### 5.1 订单粘贴解析

**功能**：用户从在线表格复制一行订单数据粘贴到系统，系统自动解析26个字段（序号除外）。

**FR-1.1**：系统应支持 Tab 分隔和换行分隔两种粘贴格式
**FR-1.2**：系统应自动识别分隔符类型
**FR-1.3**：系统应对解析结果进行验证，订单号和内部编号不能为空
**FR-1.4**：解析后数据应存储到 SQLite 数据库订单表
**FR-1.5**：解析完成后自动尝试匹配产品知识库，补全 H.S.Code 和报关名称
**FR-1.6**：解析结果应在 OnlyOffice 表格中展示（只读模式）

### 5.2 PI 文件提取

**功能**：读取 PI 合同 Excel 文件（.xls / .xlsx），提取字段信息。

> PI 文件分为两种类型：
> 1. **PI 汇总表**（外贸订单PI合同.xlsx）：订单级别的汇总表，含多个产品，按内部编码关联
> 2. **单笔 PI 合同**（Proforma Invoice *.xls）：业务员发给客户的正式 PI，含收发货人、商品明细、银行信息等

**FR-2.1**：系统应支持 .xls 格式文件读取（xlrd）
**FR-2.2**：系统应支持 .xlsx 格式文件读取（openpyxl）
**FR-2.3**：提取 PI 汇总表字段：客户编码、PI号、业务员、数量、单价、金额、内部编码、产品颜色、海关编码、报关品名、报关成分、日期、是否下单
**FR-2.4**：提取单笔 PI 合同字段：收货人、收货人地址、PI号、日期、品名英文、数量、单价、金额、H.S.Code、目的港、包装说明、运输方式、付款方式、受益人信息等
**FR-2.5**：PI 汇总表通过内部编码关联到对应订单，单笔 PI 合同通过 PI 号关联

### 5.3 数据关联

**功能**：订单数据与 PI 数据通过 `internal_code` 自动关联，无需手动汇总。

**FR-3.1**：报关品名优先级：订单数据 > PI合同（order_customs_name）> 产品知识库
**FR-3.2**：海关编码（H.S.Code）优先级：PI合同 > 产品知识库
**FR-3.3**：内部编码（internal_code）作为订单与 PI 数据的关联字段
**FR-3.4**：合并后的完整数据应在 OnlyOffice 表格中展示（只读模式）

### 5.4 包装计算

**功能**：根据订单量（kg）、选择的产品和包装类型，计算净重、毛重、卡板数、体积等，判断是否适合20GP集装箱，并给出装配方案。

**输入**：
- 订单量（kg）——来自订单数据
- 产品内部编码——匹配产品知识库获取推荐包装类型
- 包装类型（13种）——手动选择或知识库自动推荐
- 卡板规格（2种）——1.0*1.0m / 1.1*1.1m

**包装类型（13种）**——来源：产品包装资料(2020-6-10).xls

| 名称 | 外形尺寸 | CBM | 皮重kg | 毛重kg | 净重kg |
|------|----------|-----|--------|--------|--------|
| 30kg蓝桶 | 250*250*430mm | 0.026 | 2.0 | 32.0 | 30.0 |
| 25kg/包 | 200*500*800mm | 0.028 | 0.5 | 25.5 | 25.0 |
| 25kg 正方罐（蓝色） | 270*270*410mm | 0.03 | 2.0 | 27.0 | 25.0 |
| 25kg 纸桶 | 310*310*400mm | 0.039 | 2.0 | 27.0 | 25.0 |
| 50kg蓝桶(细口) | 395*395*585mm | 0.09 | 2.5 | 52.5 | 50.0 |
| 50kg蓝桶(大口) | 330*390*590mm | 0.08 | 2.5 | 52.5 | 50.0 |
| 50kg纸桶 | 410*410*高500mm | 0.085 | 2.5 | 52.5 | 50.0 |
| 60kg蓝桶 | 320*410*640mm | 0.09 | 3.5 | 63.5 | 60.0 |
| 125kg新款胶桶 | 510*510*810mm | 0.21 | 6.0 | 131.0 | 125.0 |
| 150kg新款胶桶 | 450*450*970mm | 0.196 | 9.0 | 159.0 | 150.0 |
| 200kg双环闭口桶 | 590*590*930mm | 0.31 | 10.0 | 210.0 | 200.0 |
| 1吨桶 | 1200*1000*1150mm | 1.38 | 58.0 | 1058.0 | 1000.0 |

**卡板规格（2种）**：

| 名称 | 尺寸 | 皮重kg | CBM |
|------|------|--------|-----|
| 1.0*1.0m卡板 | 1000*1000mm (H150mm) | 27.0 | 0.15 |
| 1.1*1.1m卡板 | 1100*1100mm (H150mm) | 27.0 | 0.2 |

**卡板容量映射**（每种包装类型在每种卡板上的最大装载数）：

| 包装类型 | 1.0*1.0m卡板 | 1.1*1.1m卡板 |
|----------|-------------|-------------|
| 30kg蓝桶 | - | 24桶 |
| 25kg/包 | - | 40包 |
| 25kg 正方罐 | - | 20罐 |
| 25kg 纸桶 | - | 18桶 |
| 50kg蓝桶(细口) | - | 18桶 |
| 50kg蓝桶(大口) | - | 18桶 |
| 50kg纸桶 | - | 12桶 |
| 60kg蓝桶 | - | 16桶 |
| 125kg新款胶桶 | 4桶 | 5桶 |
| 150kg新款胶桶 | 3桶 | 4桶 |
| 200kg双环闭口桶 | 2桶 | 2桶 |
| 1吨桶 | 1桶 | 1桶 |

**不打卡板时20GP集装箱容量**：
- 125kg新款胶桶：116桶 / 14.5吨
- 200kg双环闭口桶：80桶 / 16吨
- 1吨桶：20桶

**20GP集装箱内部尺寸**：内长5.898米、内宽2.352米、内高2.385米、门高2.28米、门宽2.343米

**计算输出**：
- 桶/包数量
- 所需卡板数
- 产品净重 = 桶数 × 单桶净重
- 产品毛重 = 桶数 × 单桶毛重
- 卡板总重量
- 总体积（CBM）= 桶数 × 单桶CBM + 卡板数 × 卡板CBM
- 是否适合20GP集装箱判定
- 装配方案（是否合板、如何堆叠）

**FR-4.1**：系统应根据产品知识库自动推荐包装类型（barrel_type匹配）
**FR-4.2**：系统应支持手动选择13种包装类型和2种卡板规格
**FR-4.3**：系统应计算桶数 = 向上取整(订单量 / 单桶净重)
**FR-4.4**：系统应计算卡板数 = 向上取整(桶数 / 单卡板容量)
**FR-4.5**：系统应计算总体积 = 桶数 × 单桶CBM + 卡板数 × 卡板CBM
**FR-4.6**：系统应计算总毛重 = 桶数 × 单桶毛重 + 卡板数 × 卡板皮重
**FR-4.7**：系统应判定20GP集装箱是否装得下（总体积≤28CBM 且 总重量≤21吨）
**FR-4.8**：系统应输出装配方案（是否合板、每板数量、余货处理）
**FR-4.9**：支持多产品混装同一卡板的计算（Phase 2需求）

### 5.5 数据看板

**功能**：在 OnlyOffice 表格中展示所有业务数据。

**FR-5.1**：左侧数据看板展示所有合并数据（只读）
**FR-5.2**：右侧模板编辑区支持 Tab 切换
**FR-5.3**：数据看板应支持按订单号、客户搜索过滤

## 6. Phase 2 功能需求

### 6.1 订舱出货数据管理

**功能**：整合 Phase 1 数据，处理订舱出货文档。

**FR-6.1**：系统应从 Phase 1 继承所有订单和包装数据
**FR-6.2**：系统应支持历史出货记录查询（下拉选择历史订单填充订舱数据）
**FR-6.3**：系统应支持导出商品编码表导入（Excel）
**FR-6.4**：数据合并为 ShipmentData 模型，统一供给文档生成

### 6.2 模板管理

**功能**：管理各类文档模板（订舱单、MSDS、LOI保函等）。

**FR-6.5**：系统在 OnlyOffice 表格旁展示模板列表
**FR-6.6**：订舱单/MSDS/LOI 统一使用 OnlyOffice 在线编辑
**FR-6.7**：MSDS、LOI保函提供模板下载→本地编辑→上传回系统的流程
**FR-6.8**：模板使用 {{placeholder}} 格式的占位符

### 6.3 文档生成

**功能**：基于模板和合并数据生成 Word 文档。

**FR-6.9**：系统应支持生成订舱单文档
**FR-6.10**：系统应支持生成中文 MSDS 文档
**FR-6.11**：系统应支持生成英文 MSDS 文档
**FR-6.12**：系统应支持生成 LOI 保函文档（非危险品/液体）
**FR-6.13**：生成的文档应支持下载

### 6.4 数据展示（Phase 2）

**FR-6.14**：左侧数据看板展示所有合并数据（来自 Phase 1，只读）
**FR-6.15**：右侧模板编辑区按文档类型（订舱单/MSDS/LOI）Tab 切换
**FR-6.16**：订舱单Tab内嵌在线编辑器，其他Tab提供下载/上传入口

## 7. AI 辅助功能（优先级：低，Phase 1-2 完成后实现）

### 7.1 数据校验

**FR-AI-1**：AI 校验订单数据完整性，检测字段缺失或格式异常
**FR-AI-2**：AI 对比历史订单，自动推荐包装方案和 H.S.Code
**FR-AI-3**：AI 检测规格异常（与同产品历史数据偏差过大时预警）

### 7.2 数据探查

**FR-AI-4**：AI 分析月度出货趋势
**FR-AI-5**：AI 按客户、产品统计订单分布

## 8. 用户故事

### US-001: 订单数据粘贴解析
**描述**：作为船务人员，我希望粘贴订单数据后系统自动解析，这样无需手动录入26个字段。

**验收标准**：
- [ ] 从在线表格复制一行数据，粘贴到系统
- [ ] 系统自动解析26个字段并显示预览
- [ ] 解析结果可编辑确认
- [ ] 数据保存到数据库
- [ ] 订单号或内部编号为空时给出明确错误提示
- [ ] 解析完成后自动匹配知识库补全 H.S.Code

### US-002: PI 文件关联
**描述**：作为船务人员，我希望上传 PI 汇总表或单笔 PI 合同文件，系统自动提取信息并关联到订单。

**验收标准**：
- [ ] 支持 .xls 和 .xlsx 格式文件上传
- [ ] PI汇总表：自动提取客户编码、PI号、业务员、海关编码、报关品名等字段，通过内部编码关联到订单
- [ ] 单笔PI合同：自动提取收货人、收货人地址、品名、数量、单价、H.S.Code、目的港等字段，通过PI号关联
- [ ] 关联结果在 OnlyOffice 表格中可见

### US-003: 包装计算
**描述**：作为船务人员，我希望系统自动计算包装需求，无需手动计算桶数和卡板。

**验收标准**：
- [ ] 输入订单量，自动计算所需桶数
- [ ] 选择卡板规格，自动计算卡板数
- [ ] 显示体积、毛重、20GP 判定结果
- [ ] 支持手动调整包装类型和卡板数量
- [ ] 知识库有记录时自动推荐包装类型

### US-004: 历史订单选择
**描述**：作为船务人员，我希望从历史订单列表中选择已有订单作为模板，快速发起新订舱。

**验收标准**：
- [ ] 历史订单列表按时间倒序展示
- [ ] 支持按订单号、客户名称搜索
- [ ] 选择历史订单后自动填充订舱表单
- [ ] 可修改任意字段后保存为新订单

### US-005: 订舱单在线编辑
**描述**：作为船务人员，我希望在浏览器内直接编辑订舱单模板，无需打开 WPS 或 Office。

**验收标准**：
- [ ] 在 OnlyOffice 中展示订舱单模板
- [ ] 支持直接编辑模板内容（内嵌编辑器）
- [ ] 保存后更新模板配置
- [ ] 生成订舱单时自动填充 {{placeholder}} 数据

### US-006: 文档生成与下载
**描述**：作为船务人员，我希望一键生成订舱单/MSDS/LOI保函文档。

**验收标准**：
- [ ] 选择模板类型（订舱单/MSDS/LOI）
- [ ] 选择关联的订单数据
- [ ] 点击生成按钮，文档自动填充数据
- [ ] 可下载 .docx 文件

### US-007: MSDS/LOI 模板下载编辑上传
**描述**：作为船务人员，我希望下载 MSDS 或 LOI 模板到本地编辑，完成后再上传回系统。

**验收标准**：
- [ ] 提供 MSDS（中文/英文）和 LOI（非危险品/液体）模板下载按钮
- [ ] 上传本地编辑完成的模板文件
- [ ] 系统验证占位符是否完整

## 9. 非目标（范围外）

- 不支持多人同时编辑同一订单（SQLite 单用户模式，局域网共享时以文件锁协调）
- 不支持审批流程
- 不支持邮件发送功能
- 不支持移动端原生 App
- 不支持对接第三方物流 API
- AI 功能不在 Phase 1-2 范围内（优先级低）

## 10. 技术约束

- SQLite 为单用户数据库，局域网多用户写入需依赖文件系统文件锁（建议最多 3-5 人并发）
- OnlyOffice Document Server 负责所有文档编辑
- MSDS、LOI 走下载-编辑-上传流程，不强求全内嵌
- 文档生成使用 python-docx，模板占位符格式为 {{key}}
- PI 文件解析支持 .xls（xlrd）和 .xlsx（openpyxl）

## 11. 部署架构

### 11.1 局域网部署

```bash
# 后端（服务器）
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端（服务器）
cd frontend
npm run build   # 构建产物
# Nginx 托管 dist 目录，反向代理 /api 到 localhost:8000
```

### 11.2 多用户并发说明

- SQLite 数据库文件存放在共享网络驱动器上
- FastAPI 开启文件锁支持（WAL 模式）
- 建议并发用户不超过 5 人
- 超过此规模建议迁移到 PostgreSQL

## 12. 开发计划

### 第一阶段：项目基础架构
1. 初始化 Vue.js 前端项目 + FastAPI 后端项目
2. 配置 SQLite 数据库 + 预置历史数据（包装规格表、产品知识库、历史订单、PI数据、出口商品编码）
3. 配置 OnlyOffice 组件
4. 基础 API CRUD 实现

### 第二阶段：Phase 1 核心功能
1. 订单粘贴解析功能（26字段）
2. PI 文件提取功能
3. 数据汇聚功能
4. 包装计算功能
5. OnlyOffice 数据看板展示（Phase 1）

### 第三阶段：Phase 2 核心功能
1. 订舱出货数据管理（历史订单选择）
2. 模板管理界面
3. 订舱单 OnlyOffice 内嵌编辑
4. MSDS/LOI 下载-上传流程
5. 文档生成服务（订舱单、MSDS、LOI）

### 第四阶段：AI 辅助（Phase 1-2 完成后）
1. AI 数据校验与推荐
2. AI 数据探查与统计

## 13. Open Questions

1. 多人并发写入 SQLite 时，文件锁机制是否足够？（建议评估后决定是否上 PostgreSQL）
2. OnlyOffice 自部署社区版 vs Cloud 版？
3. 是否需要支持导出历史订单数据为 Excel？
4. 模板版本管理如何实现？（历史版本留存 vs. 覆盖）