# PRD: ShippingHelper Web 重构 - Phase 2 需求确认稿

> 本文档为 Phase 2 功能需求确认稿，承接 Phase 1 (P1v2)。
> 存放路径：`C:\Users\windows\Desktop\shippiing_helper\docs\PRD-ShippingHelper-Web-P2v2.md`
> 架构决策：**全栈 OnlyOffice**（Excel + Word），无 Luckysheet

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026/05/28 | Phase 2 初始需求 |
| 2026/05/28 | 确定 Luckysheet + OnlyOffice 混合架构 |
| 2026/05/28 | 数据整合逻辑、单位换算、占位符映射明确 |
| 2026/05/28 | **全栈统一 OnlyOffice**，移除所有 Luckysheet 描述 |
| 2026/05/28 | ShipmentData 模型更新：orders 表已拆分为 orders + order_items，支持"一单多品" |
| 2026/06/22 | JWT 登录认证已完成（2026-06-18 实现） |

---

## 1. Phase 2 整体架构

### 1.1 文档类型与组件分工

| 文档类型 | 核心组件 | 业务场景 |
|----------|----------|----------|
| Excel 类 | OnlyOffice | 订舱单（Booking） |
| Word 类 | OnlyOffice | MSDS / LOI 保函 / 其他文书 |

**架构决策**：全栈使用 OnlyOffice，架构统一。

### 1.2 技术栈

- 后端：Python (FastAPI)
- 前端：Vue 3 + @onlyoffice/document-editor-vue
- 文档服务：OnlyOffice Document Server（Docker 部署）

### 1.3 OnlyOffice 集成方式

**集成流程**：
1. 用户点击"编辑文档" → Vue 组件请求 Python 后端
2. Python 后端读取模板 + 填充 Phase 1 数据 → 生成临时文件
3. 后端返回配置对象 `{ downloadUrl, jwtToken, callbackUrl }`
4. Vue 拿到配置 → `<DocumentEditor />` 渲染 OnlyOffice 编辑器
5. 用户保存 → OnlyOffice 服务器 POST 文件流到 callbackUrl → 后端存档

---

## 2. 数据整合（FR-6.4 深化）

> ⚠️ **数据模型变更**（2026/05/28）：Phase 1 的 orders 表已拆分为 orders（订单头）+ order_items（产品明细）。ShipmentData 聚合模型需相应更新。

### 2.1 数据流向

```
Phase 1 数据
    │
    ├── orders 表（订单头）
    ├── order_items 表（产品明细，外键→orders）
    ├── pi_data / pi_contracts
    ├── packaging_types
    └── products_knowledge
            ↓
    ShipmentData 聚合模型
            ↓
    Phase 2 文档生成
```

### 2.2 ShipmentData 聚合模型

| 字段组 | 字段名 | 来源 | 说明 |
|--------|--------|------|------|
| 订单基础 | order_no | orders | 订单号 |
| | customer_code | orders | 客户编号 |
| | internal_code | orders | 内部编号 |
| | salesperson | orders | 业务员 |
| | merchandiser | orders | 跟单员 |
| PI 信息 | pi_no | orders / pi_data | PI号 |
| | consignee | pi_contracts | 收货人 |
| | consignee_address | pi_contracts | 收货人地址 |
| | discharge_port | pi_contracts | 卸货港 |
| 产品明细（来自 order_items） | product_cn | order_items | 产品中文名 |
| | customs_name | order_items | 报关名称 |
| | hs_code | order_items | 海关编码 |
| | quantity_kg | order_items | 订单量kg |
| | unit_price | order_items | 单价/kg |
| | total_amount | order_items | 总金额 |
| 汇总字段（来自 orders，由子表汇总） | total_quantity_kg | orders | 订单总重量kg |
| | total_gross_weight_kg | orders | 总毛重kg |
| | total_volume_cbm | orders | 总体积CBM |
| | fits_20gp | orders | 是否适合20GP |
| 包装信息 | packaging_type | packaging_types | 包装类型名称 |
| | drum_count | order_items | 桶/包数量 |
| | pallet_count | order_items | 卡板数量 |

**注意**：Phase 2 选择订单时，选择的是 orders 表中的一行（一个订单头），对应的产品明细（order_items）作为子表展示。一个订单可能包含多个产品。

### 2.3 数据输入方式（FR-6.4 细化）

用户有两种方式将数据填入 Phase 2：

**方式 A：从左侧数据区选取（推荐）**
- 界面左侧/上方为 Phase 1 数据看板（只读 OnlyOffice 表格）
- 用户在数据看板中选择一行或多行订单
- 系统自动将选中行对应的 ShipmentData 聚合模型填充到右侧表单区
- 表单区字段可供用户修改确认

**方式 B：历史订单导入**
- 从历史出货记录（shipment_history）中选择历史订单
- 自动填充订舱表单（如船名、航次、柜号等）

### 2.4 计算逻辑复用

> **重要**：Phase 1 和 Phase 2 共用同一套计算逻辑（`calculation_service.py`），不重复实现。

| 场景 | Phase 1 数据 | Phase 2 显示 | 说明 |
|------|-------------|-------------|------|
| 桶数 | Phase 1 计算得出 | 直接引用 Phase 1 存储结果 | 复用 Phase 1 结果 |
| 总体积 CBM | Phase 1 计算得出 | 直接引用 | 复用 Phase 1 结果 |
| 总毛重 kg | Phase 1 计算得出 | 直接引用 | 复用 Phase 1 结果 |
| 20GP 判定 | Phase 1 计算得出 | 直接引用 | 复用 Phase 1 结果 |

**复用原则**：
- 计算逻辑代码只写一遍：`backend/app/services/calculation_service.py`
- Phase 1 调用 → 结果存入 `packaging_calculations` 表
- Phase 2 调用 → 实时计算或读取 Phase 1 结果，保证数据一致

---

## 3. 模板管理

### 3.1 模板分类

| 类型 | 格式 | 编辑组件 | 生成方式 |
|------|------|----------|----------|
| 订舱单 | .xlsx | OnlyOffice | 后端填充 + OnlyOffice 编辑 |
| MSDS | .docx | OnlyOffice | 后端填充 + OnlyOffice 编辑 |
| LOI 保函 | .docx | OnlyOffice | 后端填充 + OnlyOffice 编辑 |
| 其他模板 | .docx / .xlsx | OnlyOffice | 后端填充 + OnlyOffice 编辑 |

**注意**：所有文档类型统一使用 OnlyOffice 编辑，架构统一，无需切换组件。

### 3.2 模板文件结构

**模板表（templates）** 新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| name | TEXT | 模板名称 |
| type | TEXT | 类型（booking/msds/loi） |
| file_path | TEXT | 模板文件路径 |
| editor_type | TEXT | 编辑器类型（`onlyoffice`） |
| placeholders | TEXT | 占位符列表（JSON，key 为字段名，label 为显示名） |
| version | INTEGER | 版本号 |
| updated_at | DATETIME | 更新时间 |

### 3.3 占位符映射（FR-6.8 细化）

**映射规则**：
1. **完全匹配**：`{{field_name}}` → 数据库对应字段，直接填充
2. **部分缺失**：`{{field_name}}` 对应数据库无此字段 → 文档中显示为空，允许部分缺失
3. **系统字段**：`{{date}}`、`{{company_name}}` 等 → 后端动态生成，非数据库字段

**验证规则**：
- 保存模板时，系统检测 `placeholders` 列表
- 生成文档时，对每个 placeholder 尝试填充，缺失值留空
- 生成后提示用户："文档已生成，其中 N 个字段为空，请确认是否下载"

### 3.4 模板在线编辑流程

**订舱单 / MSDS / LOI（统一 OnlyOffice）**：
1. 用户选择订单 → 点击"生成 [文档类型]"
2. 后端读取模板 Word/Excel → 将 Phase 1 数据填入对应位置
3. OnlyOffice 加载文档（iframe 嵌入）
4. 用户在 OnlyOffice 中编辑
5. 用户点击保存 → OnlyOffice 将文档传回后端存档
6. 文档存入 `shipment_docs` 表（新版本 version+1）

### 3.5 模板与实例物理分离

> **原则**：模板文件是资产，只能复制使用，不可直接修改。

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

## 4. 文档生成

### 4.1 订舱单（Booking）

**流程**：
1. 用户在数据看板选择订单
2. 点击"生成订舱单" → 后端加载 .xlsx 模板
3. Phase 1 数据（ShipmentData）填充到 Excel 对应格子
4. OnlyOffice 展示填充后文件，用户可微调
5. 点击"保存" → 文件流 POST 到后端 → 存入 `shipment_docs` 表
6. 点击"下载" → 导出 .xlsx 文件

**关键字段**（来自 ShipmentData）：
- 发货人（Shipper）、收货人（Consignee）、通知方（Notify Party）
- 船名/航次（Vessel/Voy No）、装港（Port of Loading）、卸港（Port of Discharge）
- 品名描述（Description of Goods）、件数重量体积（No. & Kind / Gross Weight / Measurement）

### 4.2 MSDS 文档

**流程**：
1. 用户选择订单 → 点击"生成 MSDS"
2. 后端加载 Word 模板 → 将 Phase 1 数据填入对应位置
3. OnlyOffice 加载文档，用户在线编辑
4. 保存后文档传回后端存档（shipment_docs 表）
5. 可下载 .docx 文件

### 4.3 LOI 保函

**两种模板**：
- **非危险品保函**：适用普通货物
- **液体保函**：适用液体货物

**流程**：同 MSDS

### 4.4 文档版本管理

- 每次编辑保存生成新版本（version +1）
- 历史版本保存在 `shipment_docs` 表
- 用户可查看历史版本并下载

---

## 5. 功能需求汇总

### 5.1 订舱出货数据管理

**FR-6.1** 系统从 Phase 1 继承所有订单和包装数据
**FR-6.2** 系统支持历史出货记录查询（下拉选择历史订单填充订舱数据）
**FR-6.3** 系统支持导出商品编码表导入（Excel）
**FR-6.4** ShipmentData 聚合模型统一供给文档生成
**FR-6.4.1** 左侧/上方数据看板展示 Phase 1 合并数据（只读 OnlyOffice 表格）
**FR-6.4.2** 用户选择数据行后，ShipmentData 填充到右侧表单区
**FR-6.4.3** 表单区字段允许用户修改确认

### 5.2 模板管理

**FR-6.5** 系统在数据看板旁展示模板列表
**FR-6.6** 订舱单/MSDS/LOI 统一使用 OnlyOffice 在线编辑
**FR-6.7** 系统使用数据库 `placeholders` 字段定义占位符映射
**FR-6.7.1** 允许部分占位符无对应数据（显示为空，不阻断生成）
**FR-6.7.2** 生成后提示用户哪些字段为空

### 5.3 文档生成

**FR-6.8** 系统支持生成订舱单（.xlsx via OnlyOffice）
**FR-6.9** 系统支持生成中文 MSDS（.docx via OnlyOffice）
**FR-6.10** 系统支持生成英文 MSDS（.docx via OnlyOffice）
**FR-6.11** 系统支持生成 LOI 保函（非危险品/液体两种）
**FR-6.12** 生成的文档支持下载
**FR-6.12.1** 支持历史版本查看和下载

### 5.4 数据展示（Phase 2）

**FR-6.13** 左侧数据看板展示所有合并数据（来自 Phase 1，只读 OnlyOffice 表格）
**FR-6.14** 右侧按文档类型（订舱单/MSDS/LOI）Tab 切换
**FR-6.15** 所有 Tab 统一内嵌 OnlyOffice 编辑器

---

## 6. 用户故事

### US-005: 订舱单在线编辑
**描述**：作为船务人员，我希望在浏览器内直接编辑订舱单模板，无需打开 WPS 或 Office。

**验收标准**：
- [ ] 选择订单后，系统自动将 Phase 1 数据填入订舱单模板
- [ ] OnlyOffice 展示填充后的订舱单表格
- [ ] 支持直接修改表格内容
- [ ] 保存后文件存入 shipment_docs 表（版本+1）
- [ ] 可下载 .xlsx 文件

### US-006: 文档生成与下载
**描述**：作为船务人员，我希望一键生成 MSDS/LOI 保函文档。

**验收标准**：
- [ ] 选择订单和文档类型（MSDS/LOI）
- [ ] 系统将 Phase 1 数据填入 Word 模板对应位置
- [ ] OnlyOffice 加载文档供用户在线编辑
- [ ] 保存后文档传回后端存档
- [ ] 可下载 .docx 文件

---

## 7. 非目标

- 不支持多用户同时编辑同一订单
- 不支持在线审稿/批注（OnlyOffice 协作功能暂不开通）
- 不支持对接第三方物流 API
- AI 功能不在 Phase 2 范围内

---

## 8. Open Questions

1. OnlyOffice 使用 Cloud 版还是自部署社区版？
2. 是否需要导出历史订单数据为 Excel？
3. 模板版本管理：历史版本留存策略？（保留最近 N 个版本 or 全部保留）
4. 锁超时自动释放时间？（建议 30 分钟）