# PRD: ShippingHelper Web 重构 - Phase 1 需求确认稿 (P1v2)

> 本文档为 Phase 1 功能需求确认稿，描述第一阶段的产品逻辑、数据结构和技术细节。
> 存放路径：`C:\Users\windows\Desktop\shippiing_helper\docs\PRD-ShippingHelper-Web-P1v2.md`
> 技术栈：Vue 3 + FastAPI + SQLite + OnlyOffice（全栈统一）

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026/05/28 | 初始生成 |
| 2026/05/28 | 订单表字段更新（23→26字段，按实际表头） |
| 2026/05/28 | PI数据表拆分为 pi_data（汇总表）+ pi_contracts（单笔PI合同） |
| 2026/05/28 | 数据源说明更新（数据库存储，不再维护汇总Excel） |
| 2026/05/28 | 包装计算模块重构（13种包装、卡板容量映射、20GP判定逻辑明确） |
| 2026/05/28 | 全栈统一 OnlyOffice，移除 Luckysheet |
| 2026/05/28 | **orders 表拆分为 orders（订单头）+ order_items（产品明细），支持"一单多品" |

---

## 1. 概述

### 1.1 核心价值

解决外贸订单处理中的数据重复录入、包装计算繁琐、文档制作耗时等问题，通过数字化工作流提升船务部效率。

### 1.2 数据来源

历史数据清洗后预置入 SQLite 数据库，供查询选择。

**业务流程（Phase 1）**：
1. 业务员提供 PI 合同文件（.xls/.xlsx）→ 系统解析提取收发货人、品名、数量、H.S.Code 等
2. 业务员填写销售订单表（系统录入或批量导入）→ 包含内部编码、产品、订单量等
3. 系统通过 `internal_code` 自动关联两者数据，**不再手动汇总 Excel**

### 1.3 改造要点

原 PyQt 桌面版中由船务部手动维护的"外贸订单PI合同汇总.xlsx"，在 Web 版中改为数据库存储。

---

## 2. 技术架构

### 2.1 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + OnlyOffice + Pinia |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 文档服务 | OnlyOffice Document Server（Docker 部署） |

### 2.2 OnlyOffice 组件封装

```vue
<!-- OnlyOfficeEditor.vue -->
<template>
  <DocumentEditor
    :documentServerUrl="documentServerUrl"
    :config="config"
    :events_onDocumentReady="onDocumentReady"
    :events_onSave="onSave"
  />
</template>
```

**Props**：
- `documentServerUrl`：OnlyOffice 服务器地址
- `config`：含 `url`（文件下载地址）、`key`、`fileType` 等
- `editMode`：`edit` / `view`

**Events**：
- `events_onDocumentReady`：文档加载完成
- `events_onSave`：用户点击保存

---

## 3. 数据结构

> ⚠️ **重要变更**（2026/05/28）：一张订单可能包含多个产品（"一单多品"），Excel 中每个产品占一行。因此将原 orders 表拆分为 **orders（订单头）** 和 **order_items（产品明细）** 两张表，符合第三范式（3NF）。

### 3.1 orders（订单头表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| order_no | TEXT | 订单号 |
| customer_code | TEXT | 客户编号 |
| customer_name | TEXT | 客户名称 |
| internal_code | TEXT | 内部编号（关联键） |
| pi_no | TEXT | PI合同号 |
| salesperson | TEXT | 业务员 |
| merchandiser | TEXT | 跟单员 |
| order_date | TEXT | 下单日期 |
| production_deadline | TEXT | 生产交期 |
| delivery_date | TEXT | 交货日期 |
| shipment_date | TEXT | 出货日期 |
| shipment_channel | TEXT | 出货渠道 |
| shipment_method | TEXT | 出货方式 |
| order_confirmed | TEXT | 确认下单 |
| order_status | TEXT | 订单状态（pending/confirmed/locked/editing/saved） |
| locked_by | TEXT | 锁定人 |
| locked_at | TEXT | 锁定时间 |
| sales_area | TEXT | 销售区域 |
| shipment_title | TEXT | 出货抬头 |
| document_type | TEXT | 单据类型 |
| has_sample | TEXT | 有无样品 |
| price_adjusted | TEXT | 是否调价 |
| order_requirement | TEXT | 订单要求 |
| review_status | TEXT | 审核 |
| spec_abnormal | TEXT | 规格异常 |
| total_quantity_kg | REAL | 订单总重量kg（子表汇总） |
| total_gross_weight_kg | REAL | 总毛重kg（子表汇总） |
| total_volume_cbm | REAL | 总体积CBM（子表汇总） |
| fits_20gp | TEXT | 是否适合20GP（自动计算） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 3.1a order_items（产品明细表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| order_id | INTEGER FK | 关联订单ID（→ orders.id） |
| product_cn | TEXT | 产品中文名 |
| product_en | TEXT | 产品英文名 |
| spec_kg | REAL | 规格kg |
| hs_code | TEXT | 海关编码 |
| customs_name | TEXT | 报关名称 |
| customs_ingredients | TEXT | 报关成分 |
| quantity_kg | REAL | 订单量kg |
| unit_price | REAL | 单价/kg |
| total_amount | REAL | 总金额 |
| packaging_type_id | INTEGER FK | 包装类型（→ packaging_types.id） |
| pallet_spec | TEXT | 卡板规格（1.0m / 1.1m / 不打卡板） |
| drums_per_pallet | INTEGER | 每板桶数 |
| drum_count | INTEGER | 桶/包数量（计算得出） |
| pallet_count | INTEGER | 卡板数量（计算得出） |
| net_weight_kg | REAL | 产品净重kg（计算得出） |
| gross_weight_kg | REAL | 产品毛重kg（计算得出） |
| volume_cbm | REAL | 体积CBM（计算得出） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**关联说明**：一个订单（orders.id）对应多个产品明细（order_items.order_id）。

### 3.2 packaging_types（包装规格表）——13种包装

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 包装名称 |
| dims | TEXT | 外形尺寸 |
| cbm | REAL | 单桶体积（立方米） |
| tare_kg | REAL | 皮重（kg） |
| gross_kg | REAL | 产品+包装毛重（kg） |
| net_kg | REAL | 产品净重（kg） |
| barrel_type | TEXT | 桶类型 |
| pallet_qty_1x1 | INTEGER | 1.0*1.0m卡板容量 |
| pallet_qty_1_1x1_1 | INTEGER | 1.1*1.1m卡板容量 |
| no_pallet_qty | INTEGER | 无卡板20GP容量 |

### 3.3 pallets（卡板规格表）——2种卡板

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 卡板名称 |
| size_m | TEXT | 尺寸 |
| weight_kg | REAL | 皮重（约27kg） |
| cbm | REAL | 卡板体积 |

### 3.4 pi_data（PI汇总表）——来源：外贸订单PI合同.xlsx

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

### 3.5 pi_contracts（单笔PI合同表）——来源：Proforma Invoice *.xls

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| pi_no | TEXT | PI号 |
| consignee | TEXT | 收货人 |
| consignee_address | TEXT | 收货人地址 |
| pi_date | TEXT | PI日期 |
| product_name_en | TEXT | 品名英文 |
| quantity | REAL | 数量（kg） |
| unit_price | REAL | 单价 |
| amount | REAL | 金额 |
| hs_code | TEXT | H.S.Code |
| destination | TEXT | 目的港 |
| packing_note | TEXT | 包装说明 |
| shipment_method | TEXT | 运输方式 |
| payment_terms | TEXT | 付款方式 |
| beneficiary_name | TEXT | 受益人名称 |
| beneficiary_bank | TEXT | 受益人银行 |
| beneficiary_address | TEXT | 受益人地址 |
| bank_account | TEXT | 受益人账号 |
| swift_code | TEXT | SWIFT代码 |
| country_of_origin | TEXT | 原产国 |

### 3.6 products_knowledge / export_codes / shipment_history / templates

见主文档 `PRD-ShippingHelper-Web.md` 及 `P2v2`。

---

## 4. Phase 1 功能需求

### 4.1 订单粘贴解析（支持"一单多品"）

> **业务背景**：一张订单（同一订单号）可能包含多个产品，Excel 中每个产品占一行。粘贴解析时需要智能聚合：将同一订单号的多行数据合并为一个订单对象，包含一个订单头和多个产品明细。

**FR-1.1** 支持 Tab / 换行 分隔两种粘贴格式
**FR-1.2** 自动识别分隔符类型
**FR-1.3** 验证订单号和内部编号不能为空（其他字段允许部分为空）
**FR-1.4** 智能聚合：后端解析时按订单号分组，同一订单号的多行数据聚合为一个订单头（orders）+ 多个产品明细（order_items）
**FR-1.5** 自动匹配产品知识库补全 H.S.Code 和报关品名（报关品名：订单 > PI > 知识库；H.S.Code：PI > 知识库）
**FR-1.6** OnlyOffice 表格展示解析结果（只读模式，订单头 + 嵌套产品明细列表）

### 4.2 PI 文件提取

**FR-2.1** 支持 .xls / .xlsx
**FR-2.2** PI 汇总表（外贸订单PI合同.xlsx）按 internal_code 关联
**FR-2.3** 单笔 PI 合同（Proforma Invoice *.xls）按 PI号 关联

### 4.3 数据关联

**FR-3.1** 报关品名优先级：订单 > PI > 知识库
**FR-3.2** H.S.Code 优先级：PI > 知识库
**FR-3.3** 内部编码（internal_code）作为关联字段
**FR-3.4** 合并后的完整数据在 OnlyOffice 表格中展示（只读模式）

### 4.4 包装计算

**输入参数**：
- 订单量(kg)：数字输入
- 产品类型：下拉选择（13种）
- 卡板规格：下拉选择（1.0m / 1.1m）
- 每板数量：数字输入（系统根据映射表自动填充默认值，允许人工修改）
- 不打卡板：勾选框（默认不勾选）

**卡板容量映射表**：

| 包装类型 | 1.0*1.0m | 1.1*1.1m |
|----------|---------|---------|
| 30kg蓝桶 | - | 24 |
| 25kg/包 | - | 40 |
| 25kg 正方罐 | - | 20 |
| 25kg 纸桶 | - | 18 |
| 50kg蓝桶(细口) | - | 18 |
| 50kg蓝桶(大口) | - | 18 |
| 50kg纸桶 | - | 12 |
| 60kg蓝桶 | - | 16 |
| 125kg新款胶桶 | 4 | 5 |
| 150kg新款胶桶 | 3 | 4 |
| 200kg双环闭口桶 | 2 | 2 |
| 1吨桶 | 1 | 1 |

**计算公式**：

> ⚠️ **复用说明**：所有计算逻辑统一写在 `backend/app/services/calculation_service.py`，Phase 1 和 Phase 2 共用同一套代码，保证体积/重量计算一致。

```
桶/包数量 = 向上取整(订单量 / 单桶净重)

卡板数 =
  若勾选"不打卡板"：0
  若未勾选：向上取整(桶数 / 每板数量)

总体积 = (桶数 × 单桶CBM) + (卡板数 × 卡板CBM)
  ※ 若不打卡板，后半部分为0

总毛重 = (桶数 × 单桶毛重) + (卡板数 × 卡板皮重)
  ※ 若不打卡板，后半部分为0

20GP判定：
  若 总体积 ≤ 28CBM 且 总毛重 ≤ 21000kg → "适合20GP"
  否则 → "超出20GP限制"
```

**装配方案输出模板**：
- 整除：`共需 X 个卡板，每板 Y 个，满载。`
- 有余数：`共需 X 个卡板，前 X-1 个板每板 Y 个，最后一个板装 Z 个。`
- 不打卡板：`共需 Y 桶，不打卡板。`

**FR-4.1** 根据产品知识库自动推荐包装类型
**FR-4.2** 支持手动选择13种包装类型和2种卡板规格
**FR-4.3** 每板数量输入框显示默认值，允许人工修改
**FR-4.4** 勾选"不打卡板"时，卡板数和卡板相关重量/体积为0
**FR-4.5** 计算结果包含：桶数、卡板数、产品净重、产品毛重、卡板总重、总体积、20GP判定、装配方案

### 4.5 数据看板

**FR-5.1** OnlyOffice 表格只读展示合并数据（来自 Phase 1）
**FR-5.2** 按订单号、客户搜索过滤
**FR-5.3** 支持导出为 .xlsx 文件

---

## 5. 用户故事

- **US-001** 订单数据粘贴解析（26字段）
- **US-002** PI 文件关联（汇总表 + 单笔PI）
- **US-003** 包装计算（含不打卡板选项）
- **US-004** 数据看板展示

---

## 6. 非目标

- 多用户同时编辑同一订单（SQLite 单用户）
- 审批流程、邮件发送、移动端App、第三方物流API
- AI 功能（优先级低，Phase 1-2 后考虑）

---

## 7. Open Questions

1. 多人并发写入 SQLite 时文件锁是否足够？
2. 是否需要导出历史订单为 Excel？
3. 模板版本管理（历史留存 vs. 覆盖）？