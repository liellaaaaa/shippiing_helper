# FR-5.x 数据看板模块设计文档

> **版本**：v1.0.0
> **日期**：2026-05-29
> **模块**：Phase 1 FR-5.x（数据看板）
> **目标用户**：船务部同事
> **状态**：已锁定

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-05-29 | 初始生成，基于 brainstorming 讨论结果 |

---

## 1. 概述

### 1.1 模块目标

以只读表格形式展示所有订单与 PI 的合并数据，帮助船务人员快速确认数据准确性。同时支持导出 Excel 归档和打印预览线下签字审批。

### 1.2 核心定位

**FR-5.x = 数据确认与归档（只读展示）**

- 职责：展示合并数据，支持确认和导出
- 职责边界：不写入任何数据，仅作为数据确认工具
- 后续流程：数据确认无误后，进入 Phase 2 文档编辑

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| 信任感与问题排查效率并重 | 展示完整数据的同时，让问题数据无处遁形 |
| 智能排序 | 默认将问题数据（未关联/部分关联）排在最前面 |
| 双导出路径 | Excel 用于正式归档，打印用于快速核对 |
| 零侵入 | 仅读取和展示，不修改任何数据 |

---

## 2. 数据模型

### 2.1 合并数据视图

基于 FR-3.x 的 `get_order_comparison` 结果，聚合所有订单的合并数据。

| 字段 | 来源 | 说明 |
|------|------|------|
| order_id | orders.id | 订单主键 |
| order_no | orders.order_no | 订单号 |
| customer_code | orders.customer_code | 客户编码 |
| salesperson | orders.salesperson | 业务员 |
| internal_code | order_items.internal_code | 内部编码 |
| product_cn | order_items.product_cn | 产品名称 |
| order_quantity | order_items.quantity_kg | 订单数量 |
| order_unit_price | order_items.unit_price | 订单单价 |
| order_total | order_items.total_amount | 订单金额 |
| pi_quantity | pi_contract_items.quantity | PI 数量 |
| pi_unit_price | pi_contract_items.unit_price | PI 单价 |
| pi_total | pi_contract_items.total_amount | PI 金额 |
| association_status | 派生 | full / partial / none |
| diff_status | 派生 | 一致 / 数量不符 / 单价不符 / 金额不符 / HS不符 / PI未覆盖 |

### 2.2 关联状态

| 状态 | 颜色 | 触发条件 |
|------|------|----------|
| 已关联 | el-tag success (绿色) | 该订单所有 order_items 均在 PI 中有匹配，且无差异 |
| 部分关联 | el-tag warning (橙色) | 部分 order_items 有匹配，部分无匹配或有差异 |
| 未关联 | el-tag danger (红色) | 没有任何 order_items 在 PI 中找到匹配 |

---

## 3. 功能需求

### FR-5.1：数据表格展示

**布局**：
- 顶部工具栏：搜索框 + 导出按钮（Excel + 打印预览）
- 主体：el-table 展示合并数据，支持展开行查看明细
- 底部：el-pagination 分页

**表格列**：

| 列名 | 说明 | 宽度 |
|------|------|------|
| 订单号 | order_no | 140px |
| 客户编码 | customer_code | 120px |
| 业务员 | salesperson | 100px |
| 内部编码 | internal_code | 120px |
| 产品名称 | product_cn | 160px |
| 订单数量 | order_quantity | 100px |
| PI 数量 | pi_quantity | 100px |
| 差异状态 | diff_status（标签） | 120px |
| 关联状态 | association_status（标签） | 100px |

**交互**：
- 点击行可展开，查看该产品更详细的订单 vs PI 对比
- 表头可筛选：关联状态下拉多选
- 默认排序：关联状态降序（未关联/部分关联置顶）

### FR-5.2：关联状态筛选

**筛选逻辑**：
- 工具栏提供关联状态下拉多选：`已关联` / `部分关联` / `未关联`
- 支持多选叠加（如只看"部分关联"和"未关联"）
- 筛选结果实时更新表格

### FR-5.3：全局搜索

**搜索框**：
- 支持订单号、客户编码模糊匹配
- 搜索时实时过滤表格数据
- 清空搜索恢复完整列表

### FR-5.4：导出 Excel

**触发**：点击工具栏"导出 Excel"按钮

**后端生成逻辑**：
1. 查询所有合并数据（不分页，按关联状态降序）
2. 使用 openpyxl 生成 .xlsx 文件
3. 表头：订单号 / 客户编码 / 业务员 / 内部编码 / 产品名称 / 订单数量 / PI数量 / 差异状态 / 关联状态
4. 添加表头样式（加粗、背景色）
5. 添加边框
6. 设置第一行为冻结窗格

**响应**：返回 `.xlsx` 文件流，浏览器自动下载，文件名为 `数据看板_YYYYMMDD.xlsx`

### FR-5.5：打印预览

**触发**：点击工具栏"打印预览"按钮

**打印样式**：
```css
@media print {
  /* 隐藏：侧边栏、顶部导航、工具栏按钮、分页 */
  .sidebar, .navbar, .toolbar-buttons, .pagination { display: none; }

  /* 仅显示表格内容 */
  .data-table { width: 100%; }

  /* A4 横向 */
  @page { size: landscape; margin: 1cm; }

  /* 表头在每页重复 */
  thead { display: table-row-group; }
}
```

---

## 4. API 接口

### GET /api/v1/dashboard/orders

**描述**：获取数据看板合并数据（支持分页和筛选）

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| search | string | 模糊搜索（订单号 / 客户编码） |
| status | string | 关联状态筛选，逗号分隔（如 `partial,none`） |
| page | int | 分页页码（默认 1） |
| page_size | int | 每页条数（默认 50） |

**响应**：
```json
{
  "orders": [
    {
      "order_id": 1,
      "order_no": "HT260529E01",
      "customer_code": "TOA-DOVECHEM",
      "salesperson": "张三",
      "internal_code": "SILI-001",
      "product_cn": "有机硅柔软剂",
      "order_quantity": 2400.0,
      "order_unit_price": 29.5,
      "order_total": 70800.0,
      "pi_quantity": 2400.0,
      "pi_unit_price": 29.5,
      "pi_total": 70800.0,
      "association_status": "full",
      "diff_status": "一致"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

### GET /api/v1/dashboard/export

**描述**：导出数据看板 Excel 文件

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| search | string | 模糊搜索（可选，不传则导出全部） |
| status | string | 关联状态筛选（可选） |

**响应**：
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename="数据看板_20260529.xlsx"`
- 文件体：.xlsx 二进制流

---

## 5. 前端页面

### 5.1 Dashboard.vue（数据看板主页）

**布局**：
- 顶部工具栏：搜索框 + 关联状态筛选 + 导出按钮
- 主体：el-table（可展开）
- 底部：el-pagination

**组件结构**：
```
Dashboard.vue
├── Toolbar（搜索 + 筛选 + 导出按钮）
├── DataTable（el-table，可展开行）
│   └── StatusTag（关联状态标签 + Tooltip）
├── Pagination（el-pagination）
```

---

## 6. 验收标准

| ID | 验收条件 |
|----|----------|
| AC-1 | 表格加载后，默认按关联状态降序排列（未关联/部分关联在最前） |
| AC-2 | 关联状态列使用 el-tag 颜色区分：绿色=已关联，橙色=部分关联，红色=未关联 |
| AC-3 | 支持关联状态下拉多选筛选，筛选结果实时更新 |
| AC-4 | 全局搜索框支持订单号/客户编码模糊匹配 |
| AC-5 | 点击"导出 Excel"按钮，浏览器下载 .xlsx 文件 |
| AC-6 | 导出的 Excel 包含表头样式（加粗、背景色）和边框 |
| AC-7 | 点击"打印预览"按钮，唤起浏览器打印对话框 |
| AC-8 | 打印样式正确：A4 横向、隐藏非表格元素、表头每页重复 |
| AC-9 | 表格支持展开行查看详细对比数据 |

---

## 7. 非目标

- 本模块不写入任何数据
- 不支持 OnlyOffice 集成（Phase 2 文档编辑时考虑）
- 不支持数据编辑或修改
- 不支持多语言导出

---

## 8. Open Questions

| 问题 | 说明 |
|------|------|
| OQ-1 | 是否需要在导出 Excel 时附带"汇总行"（如总件数、总金额）？Phase 1 暂不加 |
| OQ-2 | 打印预览是否需要支持 PDF 导出？Phase 1 仅用原生打印 |

---

*文档版本：v1.0.0（已锁定）*
*设计完成日期：2026-05-29*