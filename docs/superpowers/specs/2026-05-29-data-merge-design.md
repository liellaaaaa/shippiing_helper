# FR-3.x 数据关联模块设计文档

> **版本**：v1.0.0
> **日期**：2026-05-29
> **模块**：Phase 1 FR-3.x（数据关联 / 核对诊断中心）
> **目标用户**：船务部同事
> **状态**：已锁定

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-05-29 | 初始生成，基于 Brainstorming 讨论结果 |

---

## 1. 概述

### 1.1 模块目标

将订单数据（orders + order_items）和 PI 数据（pi_contracts + pi_contract_items）通过 `internal_code` 进行智能关联与比对，以订单为中心展示合并结果，帮助船务人员快速发现"订单与 PI 数据不一致"的问题。

### 1.2 核心定位

**FR-3.x = 核对与诊断中心（只提示，不合并）**

- 职责：**发现问题**，通过智能高亮告诉用户哪些产品有差异
- 职责边界：**不写入**任何数据，不做自动覆盖或回填
- 后续流程：用户点击 🔗 跳转到 FR-1.x（订单）或 PI 模块去修正原始数据，刷新后标红自动消失

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| 单一事实来源 | 订单和 PI 是两个独立业务实体，各自维护各自的数据边界 |
| 零数据侵入 | 本模块仅读取和比对，不写入 orders 或 pi_contracts 表 |
| 裁决权归用户 | 系统仅展示差异，不判断哪边是"正确答案"，由用户选择跳转目标 |

---

## 2. 数据模型

### 2.1 关联逻辑

| 关联键 | 说明 |
|--------|------|
| `internal_code` | 订单产品明细（order_items）与 PI 产品明细（pi_contract_items）的关联字段 |
| `pi_no` | PI 合同头（pi_contracts）用于定位 PI 信息 |

### 2.2 比对字段

| 字段 | 类型 | 容差 | 检测规则 |
|------|------|------|----------|
| quantity（数量） | 数值 | ±0.01 | 绝对误差 ≤ 0.01 视为一致 |
| unit_price（单价） | 数值 | ±0.01 | 绝对误差 ≤ 0.01 视为一致 |
| total_amount（总金额） | 数值 | ±0.01 | 绝对误差 ≤ 0.01 视为一致 |
| hs_code（H.S.Code） | 文本 | 无 | 严格字符串比对 |
| customs_name（报关品名） | 文本 | 无 | 严格字符串比对 |

> **容差说明**：浮点数精度问题（如 29.500000 vs 29.5）不应触发误报，设置 ±0.01 容差。

---

## 3. 展示架构

### 3.1 订单中心视图

以订单为主线，选择一个订单后展开该订单的所有产品明细。

#### 第一层：订单列表（聚合视图）

| 字段 | 来源 | 说明 |
|------|------|------|
| 销售订单号 | orders.order_no | 主键 |
| 客户编码 | orders.customer_code | - |
| 业务员 | orders.salesperson | - |
| 订单总金额 | order_items 汇总 | Σ(quantity_kg × unit_price) |
| 关联状态 | 派生 | 已关联 / 部分关联 / 未关联 |

**关联状态判定**：
- `已关联`：该订单所有 order_items 的 `internal_code` 均能在 pi_contract_items 中找到匹配
- `部分关联`：部分 order_items 有匹配，部分无匹配
- `未关联`：没有任何 order_items 在 PI 中找到匹配

**交互**：点击订单行 → 展开嵌套明细表格

#### 第二层：合并明细行（比对视图）

展开后，每行代表一个 `internal_code`，左右两列数据进行硬对齐：

| 列名 | 说明 |
|------|------|
| 内部编码 | order_items.internal_code |
| 产品名称 | order_items.product_cn |
| 📦 订单数量/单价 | 来自 order_items（quantity_kg + unit_price） |
| 📄 PI 数量/单价 | 来自 pi_contract_items（quantity + unit_price） |
| ⚠️ 差异提示 | 状态图标 + 说明 |

**差异状态图标**：

| 图标 | 含义 | 触发条件 |
|------|------|----------|
| ✅ 一致 | 完全匹配 | 所有比对字段均在容差内或相等 |
| 🔴 数量不符 | 数量差异 | abs(order_qty - pi_qty) > 0.01 |
| 🔴 单价不符 | 单价差异 | abs(order_unit_price - pi_unit_price) > 0.01 |
| 🔴 金额不符 | 金额差异 | abs(order_total - pi_total) > 0.01 |
| 🔴 HS不符 | H.S.Code 差异 | order_hs ≠ pi_hs，且均非空 |
| 🟡 PI 未覆盖 | 订单有，PI 无 | order_items 有但 pi_contract_items 无匹配 |
| 🟡 订单无记录 | PI 有，订单无 | pi_contract_items 有但 order_items 无匹配 |

> **Tooltip 规则**：当字段标红时，鼠标悬停显示"订单值：XXX / PI值：YYY"，方便用户一眼看清具体差异。

---

## 4. 快速定位交互

### 4.1 Popover 二选一菜单

当用户点击差异行旁边的 🔗 图标时：

1. **触发**：鼠标点击 🔗 图标
2. **弹出示图**：在图标旁弹出 Popover 小卡片，不遮挡数据行
3. **卡片内容**：

```
┌─────────────────────────┐
│  选择检查目标            │
│                         │
│  📦 检查订单数据        │
│  📄 检查 PI 数据        │
└─────────────────────────┘
```

4. **跳转逻辑**：
   - "检查订单数据" → 携带 `internal_code` + `order_id` 跳转至 FR-1.x 订单编辑页，目标页面自动滚动 + 高亮对应行
   - "检查 PI 数据" → 携带 `internal_code` + `pi_contract_id` 跳转至 PI 预览页，目标页面自动滚动 + 高亮对应行

5. **返回闭环**：用户在目标页面修正数据并保存后，可点击"返回比对视图"或使用浏览器返回，重新刷新 FR-3.x 页面后，原标红行变为 ✅ 一致。

### 4.2 跳转参数设计

| 参数 | 说明 |
|------|------|
| internal_code | 定位到具体产品行 |
| order_id | 跳转至对应订单 |
| pi_contract_id | 跳转至对应 PI 合同 |

---

## 5. 数据范围与筛选

### 5.1 Tab 切换（默认：待处理）

| Tab | 内容 |
|-----|------|
| 🔴 待处理（默认） | 未关联 / 部分关联的订单，最新创建的排在最前 |
| 🟢 已完成 | 所有 order_items 均已关联 PI，无差异 |
| 📋 全部 | 所有订单，不区分关联状态 |

### 5.2 全局搜索（始终可用）

搜索框始终可见，不受当前 Tab 影响。支持模糊搜索：

| 搜索类型 | 示例 |
|----------|------|
| 销售订单号 | HT260529 |
| 内部编码 | SILI-001 |
| 客户名称 | TOA-DOVECHEM |

---

## 6. API 接口

### 6.1 数据合并查询

#### GET /api/v1/merge/orders

**描述**：查询订单列表及关联状态，支持 Tab 筛选和搜索

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| tab | string | `pending` / `completed` / `all`（默认 `pending`） |
| search | string | 模糊搜索（订单号 / 内部编码 / 客户名称） |
| page | int | 分页页码（默认 1） |
| page_size | int | 每页条数（默认 20） |

**响应**：
```json
{
  "orders": [
    {
      "id": 1,
      "order_no": "HT260529E01",
      "customer_code": "TOA-DOVECHEM",
      "salesperson": "张三",
      "total_amount": 115600.0,
      "association_status": "partial",  // "full" / "partial" / "none"
      "items_count": 3,
      "linked_count": 2,
      "created_at": "2026-05-29"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

#### GET /api/v1/merge/orders/{order_id}/comparison

**描述**：获取指定订单的合并明细比对数据

**路径参数**：
- `order_id`：订单主键

**响应**：
```json
{
  "order_id": 1,
  "order_no": "HT260529E01",
  "customer_code": "TOA-DOVECHEM",
  "items": [
    {
      "internal_code": "SILI-001",
      "product_cn": "有机硅柔软剂",
      "order": {
        "quantity": 2400.0,
        "unit_price": 29.5,
        "total_amount": 70800.0,
        "hs_code": null,
        "customs_name": "有机硅柔软剂"
      },
      "pi": {
        "quantity": 2400.0,
        "unit_price": 29.5,
        "total_amount": 70800.0,
        "hs_code": "39101000",
        "customs_name": "有机硅柔软剂"
      },
      "diff": {
        "status": "一致",
        "flags": []
      }
    },
    {
      "internal_code": "SILI-002",
      "product_cn": "改性硅油",
      "order": {
        "quantity": 1600.0,
        "unit_price": 28.0,
        "total_amount": 44800.0,
        "hs_code": null,
        "customs_name": "改性硅油"
      },
      "pi": {
        "quantity": 980.0,
        "unit_price": 28.0,
        "total_amount": 27440.0,
        "hs_code": "39101000",
        "customs_name": "改性硅油"
      },
      "diff": {
        "status": "数量不符",
        "flags": ["quantity"],
        "order_value": 1600.0,
        "pi_value": 980.0
      }
    }
  ]
}
```

---

## 7. 前端页面

### 7.1 DataMerge.vue（数据关联主页）

**布局**：
- 顶部：Tab 切换（待处理 / 已完成 / 全部）+ 全局搜索框
- 中部：订单列表（el-table，可展开）
- 底部：分页组件

**组件结构**：
```
DataMerge.vue
├── TabFilter（待处理/已完成/全部）
├── SearchBar（全局搜索，始终可见）
├── OrderList（el-table，可展开）
│   └── ExpandRow（嵌套明细行，含比对列）
│       └── DiffCell（标红单元格 + Tooltip）
├── QuickJumpPopover（🔗 图标触发）
└── Pagination（分页）
```

### 7.2 交互流程

1. 用户进入 `/data-merge` 页面，默认显示"待处理"Tab
2. 列表加载未关联 / 部分关联的订单，最新创建的排在最前
3. 用户点击订单行，展开嵌套明细行
4. 每行显示订单 vs PI 数据，差异处标红
5. 用户点击 🔗 图标，弹出 Popover 选择跳转目标
6. 用户跳转至 FR-1.x 或 PI 页面，修正数据后返回
7. 用户刷新 FR-3.x，标红消失（若已修正）

---

## 8. 字段优先级（数据展示用）

> **注意**：以下优先级仅用于**展示时字段填充**，不触发任何数据写入或合并。

| 字段 | 优先级（高→低） |
|------|----------------|
| 报关品名（customs_name） | 订单 > PI > 知识库（products_knowledge） |
| H.S.Code | PI > 知识库 |

---

## 9. 验收标准

| ID | 验收条件 |
|----|----------|
| AC-1 | Tab 切换正常：待处理 / 已完成 / 全部，各显示正确子集 |
| AC-2 | 全局搜索始终可用，支持订单号 / 内部编码 / 客户名称模糊匹配 |
| AC-3 | 展开订单后，每行显示订单 vs PI 比对数据，差异标红 |
| AC-4 | 数值字段允许 ±0.01 容差，避免浮点精度误报 |
| AC-5 | 标红单元格悬停显示 Tooltip：订单值 / PI 值 |
| AC-6 | 点击 🔗 图标弹出 Popover，提供"检查订单"和"检查PI"两个选项 |
| AC-7 | 跳转目标页面加载后自动定位到对应 internal_code 行 |
| AC-8 | 关联状态正确显示：已关联 / 部分关联 / 未关联 |

---

## 10. 非目标

- 本模块**不写入**任何数据到 orders 或 pi_contracts 表
- 不支持多选批量操作（每次只处理一个订单）
- 不支持"自动合并"或"自动回填"

---

## 11. Open Questions

| 问题 | 说明 |
|------|------|
| OQ-1 | 是否需要"部分关联"状态下的快捷操作（如一键为缺失项创建 PI 记录）？Phase 1 暂不考虑 |
| OQ-2 | 若同一个 internal_code 在多个 PI 中出现（重复 PI），如何处理？默认取最新的一条 |

---

*文档版本：v1.0.0（已锁定）*
*设计完成日期：2026-05-29*