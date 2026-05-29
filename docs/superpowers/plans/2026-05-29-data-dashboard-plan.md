# FR-5.x 数据看板模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建数据看板页面，以只读 el-table 展示所有订单 + PI 合并数据，支持关联状态筛选、搜索、导出 Excel 和打印预览。

**Architecture:** 后端提供两个 API：合并数据查询（含分页/筛选）和 Excel 文件导出。前端使用 el-table + el-pagination + 工具栏按钮。

**Tech Stack:** FastAPI + openpyxl（后端生成 Excel），Vue 3 + Element Plus + TypeScript（前端）。

---

## 文件结构

```
backend/
├── app/
│   ├── api/v1/
│   │   └── dashboard.py      # NEW：数据看板 API 路由
│   └── services/
│       └── export_service.py  # NEW：Excel 导出服务
frontend/
├── src/
│   ├── api/
│   │   └── dashboard.ts      # NEW：数据看板 API 客户端
│   └── views/
│       └── phase1/
│           └── Dashboard.vue   # NEW：数据看板主页
```

---

## 任务索引

| ID | 轨道 | 描述 |
|----|------|------|
| BM-1 | Backend | export_service.py — Excel 生成服务（openpyxl） |
| BM-2 | Backend | API 路由 — GET /api/v1/dashboard/orders + GET /api/v1/dashboard/export |
| FE-1 | Frontend | dashboard.ts API 客户端 |
| FE-2 | Frontend | Dashboard.vue 主页面（工具栏 + el-table + 分页 + 打印样式） |

---

## Track 1: Backend（BM-1 → BM-2）

### Task BM-1: Excel 导出服务

**Files:**
- Create: `backend/app/services/export_service.py`
- Create: `backend/tests/test_export_service.py`

---

- [ ] **Step 1: 编写测试**

Create `backend/tests/test_export_service.py`:

```python
import pytest
from app.services.export_service import ExportService


def test_generate_excel_bytes():
    """测试 Excel 文件流生成"""
    service = ExportService()

    data = [
        {
            "order_no": "HT260529E01",
            "customer_code": "TOA-DOVECHEM",
            "salesperson": "张三",
            "internal_code": "SILI-001",
            "product_cn": "有机硅柔软剂",
            "order_quantity": 2400.0,
            "pi_quantity": 2400.0,
            "association_status": "full",
            "diff_status": "一致",
        }
    ]

    result = service.generate_excel_bytes(data)
    assert result is not None
    assert len(result) > 0
    # 验证是有效的 xlsx 文件（以 PK 开头，即 ZIP 文件）
    assert result[:2] == b'PK'
```

---

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_export_service.py -v`
Expected: FAIL with "No module named 'app.services.export_service'"

---

- [ ] **Step 3: 编写 export_service.py**

Create `backend/app/services/export_service.py`:

```python
"""Excel 导出服务 — FR-5.x 数据看板模块"""

import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment


class ExportService:
    """Excel 导出服务"""

    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    HEADER_FONT = Font(bold=True, color="FFFFFF")
    BORDER_SIDE = Side(style="thin", color="000000")
    BORDER = Border(
        left=BORDER_SIDE,
        right=BORDER_SIDE,
        top=BORDER_SIDE,
        bottom=BORDER_SIDE,
    )

    # 列定义
    COLUMNS = [
        ("订单号", "order_no"),
        ("客户编码", "customer_code"),
        ("业务员", "salesperson"),
        ("内部编码", "internal_code"),
        ("产品名称", "product_cn"),
        ("订单数量", "order_quantity"),
        ("PI 数量", "pi_quantity"),
        ("差异状态", "diff_status"),
        ("关联状态", "association_status"),
    ]

    def generate_excel_bytes(self, data: list[dict]) -> bytes:
        """
        将合并数据生成为 Excel 文件流。
        返回 bytes，可在 FastAPI 中直接作为 Response。
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "数据看板"

        # 写入表头
        headers = [col[0] for col in self.COLUMNS]
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.border = self.BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # 写入数据
        for row_idx, row_data in enumerate(data, start=2):
            for col_idx, (_, field_key) in enumerate(self.COLUMNS, start=1):
                value = row_data.get(field_key, "")
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = self.BORDER

        # 冻结第一行
        ws.freeze_panes = "A2"

        # 列宽自适应
        for col_idx, (header, _) in enumerate(self.COLUMNS, start=1):
            max_length = len(header)
            for row_idx in range(2, len(data) + 2):
                cell_value = ws.cell(row=row_idx, column=col_idx).value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))
            ws.column_dimensions[chr(64 + col_idx)].width = min(max_length + 2, 30)

        # 转换为 bytes
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_filename(self) -> str:
        """生成下载文件名"""
        today = datetime.now().strftime("%Y%m%d")
        return f"数据看板_{today}.xlsx"
```

---

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_export_service.py -v`
Expected: PASS

---

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/export_service.py backend/tests/test_export_service.py
git commit -m "feat(backend): add ExportService for FR-5.x dashboard Excel export"
```

---

### Task BM-2: API 路由 — 数据看板端点

**Files:**
- Create: `backend/app/api/v1/dashboard.py`
- Modify: `backend/app/main.py` — 注册 dashboard 路由

---

- [ ] **Step 1: 创建 API 路由**

Create `backend/app/api/v1/dashboard.py`:

```python
"""FR-5.x 数据看板 API — 合并数据查询与导出"""

import io
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from app.services.export_service import ExportService
from app.services.merge_service import MergeService
from app.database import SessionLocal
from app.api.deps import get_db


router = APIRouter(prefix="/api/v1/dashboard", tags=["数据看板"])


@router.get("/orders")
async def get_dashboard_orders(
    search: Optional[str] = Query(None, description="模糊搜索：订单号 / 客户编码"),
    status: Optional[str] = Query(None, description="关联状态筛选，逗号分隔：full,partial,none"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    """
    获取数据看板合并数据（支持分页和筛选）。

    - search：支持订单号、客户编码模糊匹配
    - status：关联状态筛选，支持多选（如 'partial,none'）
    - 默认按关联状态降序排列（问题数据置顶）
    """
    merge_service = MergeService(db)

    # 获取订单列表（不限状态，获取全部用于导出）
    all_orders = merge_service.get_order_list(tab="all", search=search, page=1, page_size=10000)

    # 状态筛选
    if status:
        status_list = [s.strip() for s in status.split(",")]
        filtered_orders = [
            o for o in all_orders.orders
            if o.association_status in status_list
        ]
    else:
        filtered_orders = all_orders.orders

    # 按关联状态降序排列（none > partial > full）
    status_order = {"none": 0, "partial": 1, "full": 2}
    filtered_orders.sort(key=lambda x: status_order.get(x.association_status, 2))

    # 分页
    total = len(filtered_orders)
    start = (page - 1) * page_size
    end = start + page_size
    page_orders = filtered_orders[start:end]

    # 聚合每个订单的 items
    rows = []
    for order in page_orders:
        comparison = merge_service.get_order_comparison(order.id)
        if not comparison:
            continue
        for item in comparison.items:
            rows.append({
                "order_id": order.id,
                "order_no": order.order_no,
                "customer_code": order.customer_code,
                "salesperson": order.salesperson,
                "internal_code": item.internal_code,
                "product_cn": item.product_cn or "",
                "order_quantity": item.order.quantity if item.order else None,
                "order_unit_price": item.order.unit_price if item.order else None,
                "order_total": item.order.total_amount if item.order else None,
                "pi_quantity": item.pi.quantity if item.pi else None,
                "pi_unit_price": item.pi.unit_price if item.pi else None,
                "pi_total": item.pi.total_amount if item.pi else None,
                "association_status": order.association_status,
                "diff_status": item.diff.status,
            })

    return {
        "orders": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export")
async def export_dashboard_excel(
    search: Optional[str] = Query(None, description="模糊搜索"),
    status: Optional[str] = Query(None, description="关联状态筛选"),
    db=Depends(get_db),
):
    """
    导出数据看板 Excel 文件。

    - 不分页，按关联状态降序导出全部数据
    - 包含表头样式（加粗、背景色）和边框
    """
    merge_service = MergeService(db)
    export_service = ExportService()

    # 获取全部数据
    all_orders = merge_service.get_order_list(tab="all", search=search, page=1, page_size=10000)

    # 状态筛选
    if status:
        status_list = [s.strip() for s in status.split(",")]
        filtered_orders = [
            o for o in all_orders.orders
            if o.association_status in status_list
        ]
    else:
        filtered_orders = all_orders.orders

    # 按关联状态降序排列
    status_order = {"none": 0, "partial": 1, "full": 2}
    filtered_orders.sort(key=lambda x: status_order.get(x.association_status, 2))

    # 聚合 items
    rows = []
    for order in filtered_orders:
        comparison = merge_service.get_order_comparison(order.id)
        if not comparison:
            continue
        for item in comparison.items:
            rows.append({
                "order_no": order.order_no,
                "customer_code": order.customer_code or "",
                "salesperson": order.salesperson or "",
                "internal_code": item.internal_code,
                "product_cn": item.product_cn or "",
                "order_quantity": item.order.quantity if item.order else "",
                "pi_quantity": item.pi.quantity if item.pi else "",
                "diff_status": item.diff.status,
                "association_status": order.association_status,
            })

    # 生成 Excel
    excel_bytes = export_service.generate_excel_bytes(rows)
    filename = export_service.generate_filename()

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
```

---

- [ ] **Step 2: 注册路由**

Modify `backend/app/main.py` — 添加：

```python
from app.api.v1.dashboard import router as dashboard_router

app.include_router(dashboard_router)
```

---

- [ ] **Step 3: 验证**

Run: `curl http://localhost:8000/api/v1/dashboard/orders?page=1&page_size=5`
Expected: 返回 JSON 数据

---

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/dashboard.py backend/app/main.py && git commit -m "feat(backend): add FR-5.x dashboard API endpoints"
```

---

## Track 2: Frontend（FE-1 → FE-2）

### Task FE-1: API 客户端 — dashboard.ts

**Files:**
- Create: `frontend/src/api/dashboard.ts`

---

- [ ] **Step 1: 创建 API 客户端**

Create `frontend/src/api/dashboard.ts`:

```typescript
import axios from 'axios'

const BASE_URL = '/api/v1/dashboard'

export interface DashboardOrder {
  order_id: number
  order_no: string
  customer_code?: string
  salesperson?: string
  internal_code: string
  product_cn?: string
  order_quantity?: number
  order_unit_price?: number
  order_total?: number
  pi_quantity?: number
  pi_unit_price?: number
  pi_total?: number
  association_status: 'full' | 'partial' | 'none'
  diff_status: string
}

export interface DashboardResponse {
  orders: DashboardOrder[]
  total: number
  page: number
  page_size: number
}

export const getDashboardOrders = async (params: {
  search?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<DashboardResponse> => {
  const response = await axios.get<DashboardResponse>(`${BASE_URL}/orders`, { params })
  return response.data
}

export const exportDashboardExcel = (params?: {
  search?: string
  status?: string
}) => {
  // 直接触发浏览器下载
  window.location.href = `${BASE_URL}/export?${new URLSearchParams(params as any).toString()}`
}
```

---

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/dashboard.ts && git commit -m "feat(frontend): add dashboard API client"
```

---

### Task FE-2: Dashboard.vue 主页面

**Files:**
- Create: `frontend/src/views/phase1/Dashboard.vue`
- Modify: `frontend/src/router/index.ts` — 添加 /dashboard 路由
- Modify: `frontend/src/views/Layout.vue` — 添加导航入口

---

- [ ] **Step 1: 创建 Dashboard.vue**

Create `frontend/src/views/phase1/Dashboard.vue`:

```vue
<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">数据看板</h1>
      <p class="page-subtitle">订单与 PI 合并数据汇总 — 确认数据无误后进入文档编辑</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchText"
          placeholder="搜索订单号 / 客户编码"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button icon="Search" @click="handleSearch" />
          </template>
        </el-input>

        <el-select
          v-model="selectedStatuses"
          multiple
          placeholder="关联状态筛选"
          collapse-tags
          collapse-tags-tooltip
          class="status-filter"
        >
          <el-option
            v-for="s in statusOptions"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
      </div>

      <div class="toolbar-right">
        <el-button type="primary" icon="Download" @click="handleExportExcel">
          导出 Excel
        </el-button>
        <el-button plain icon="Printer" @click="handlePrintPreview">
          打印预览
        </el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table
      :data="orderList"
      border
      stripe
      v-loading="loading"
      row-key="order_id"
      class="data-table"
    >
      <el-table-column prop="order_no" label="订单号" width="140" fixed />
      <el-table-column prop="customer_code" label="客户编码" width="120" />
      <el-table-column prop="salesperson" label="业务员" width="100" />
      <el-table-column prop="internal_code" label="内部编码" width="120" />
      <el-table-column prop="product_cn" label="产品名称" width="160" />
      <el-table-column prop="order_quantity" label="订单数量" width="100" align="right">
        <template #default="{ row }">
          {{ row.order_quantity ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="pi_quantity" label="PI 数量" width="100" align="right">
        <template #default="{ row }">
          {{ row.pi_quantity ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="diff_status" label="差异状态" width="120">
        <template #default="{ row }">
          <el-tag :type="diffStatusType(row.diff_status)" size="small">
            {{ row.diff_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="association_status" label="关联状态" width="100">
        <template #default="{ row }">
          <el-tooltip :content="getStatusTip(row.association_status)" placement="top">
            <el-tag :type="statusType(row.association_status)" size="small">
              {{ statusLabel(row.association_status) }}
            </el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getDashboardOrders, exportDashboardExcel, type DashboardOrder } from '@/api/dashboard'

const searchText = ref('')
const selectedStatuses = ref<string[]>([])
const orderList = ref<DashboardOrder[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

const statusOptions = [
  { label: '已关联', value: 'full' },
  { label: '部分关联', value: 'partial' },
  { label: '未关联', value: 'none' },
]

const statusType = (status: string) => {
  if (status === 'full') return 'success'
  if (status === 'partial') return 'warning'
  return 'danger'
}

const statusLabel = (status: string) => {
  if (status === 'full') return '已关联'
  if (status === 'partial') return '部分关联'
  return '未关联'
}

const getStatusTip = (status: string) => {
  if (status === 'none') return '此订单没有任何产品匹配 PI，需要补充 PI 数据'
  if (status === 'partial') return '此订单部分产品未匹配 PI 或存在数据差异'
  return '此订单所有产品均已匹配 PI，数据一致'
}

const diffStatusType = (status: string) => {
  if (status === '一致') return 'success'
  if (status === 'PI未覆盖') return 'warning'
  return 'danger'
}

const buildStatusParam = () => {
  if (selectedStatuses.value.length === 0) return undefined
  return selectedStatuses.value.join(",")
}

const loadData = async () => {
  loading.value = true
  try {
    const response = await getDashboardOrders({
      search: searchText.value || undefined,
      status: buildStatusParam(),
      page: currentPage.value,
      page_size: pageSize.value,
    })
    orderList.value = response.orders
    total.value = response.total
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

watch(selectedStatuses, () => {
  currentPage.value = 1
  loadData()
})

const handleExportExcel = () => {
  const params: any = {}
  if (searchText.value) params.search = searchText.value
  if (buildStatusParam()) params.status = buildStatusParam()
  exportDashboardExcel(params)
}

const handlePrintPreview = () => {
  window.print()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 12px 16px; background: #f5f7fa; border-radius: 8px; }
.toolbar-left { display: flex; gap: 12px; align-items: center; }
.toolbar-right { display: flex; gap: 8px; }
.search-input { width: 240px; }
.status-filter { width: 180px; }

.data-table { margin-bottom: 16px; }

.pagination-wrapper { display: flex; justify-content: flex-end; }

/* 打印样式 */
@media print {
  .toolbar { display: none !important; }
  .pagination-wrapper { display: none !important; }
  .page-header { margin-bottom: 12px; }
  .page-title { font-size: 20px; }
  .page-subtitle { display: none; }

  .data-table {
    width: 100%;
    page-break-inside: avoid;
  }

  :deep(.el-table__header-wrapper) {
    display: table-row-group;
  }

  :deep(.el-table__body-wrapper) {
    overflow: visible !important;
  }

  @page {
    size: landscape;
    margin: 1cm;
  }
}
</style>
```

---

- [ ] **Step 2: 添加路由**

Modify `frontend/src/router/index.ts` — 添加 `/dashboard` 路由，指向 `Dashboard.vue`。

---

- [ ] **Step 3: 添加导航入口**

Modify `frontend/src/views/Layout.vue` — 添加"数据看板"导航菜单项。

---

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/phase1/Dashboard.vue frontend/src/router/index.ts frontend/src/views/Layout.vue && git commit -m "feat(frontend): add Dashboard page with export and print preview"
```

---

## 验证清单

After all tasks are complete, verify each item:

- [ ] **Backend**: `curl http://localhost:8000/api/v1/dashboard/orders?page=1&page_size=5` 返回数据
- [ ] **Backend**: `curl http://localhost:8000/api/v1/dashboard/export` 返回 .xlsx 文件流
- [ ] **Frontend**: 访问 http://localhost:5173/dashboard 页面正常加载
- [ ] **Frontend**: 默认按关联状态降序排列（红色"未关联"在最前）
- [ ] **Frontend**: 关联状态下拉多选筛选正常
- [ ] **Frontend**: 全局搜索框搜索功能正常
- [ ] **Frontend**: 点击"导出 Excel"浏览器下载 .xlsx 文件
- [ ] **Frontend**: 点击"打印预览"唤起浏览器打印对话框
- [ ] **Frontend**: 打印样式正确（A4 横向、隐藏工具栏、表头重复）

---

## Self-Review Checklist

Before saving this plan, I checked:

1. **Spec coverage**: 所有 FR-5.x 验收标准（AC-1 ~ AC-9）均有对应任务实现
2. **Placeholder scan**: 无 "TBD"、"TODO"、未完成的步骤
3. **Type consistency**: 前端 TypeScript 接口与后端响应字段一致
4. **导出逻辑**: openpyxl 生成 xlsx，包含表头样式 + 边框 + 冻结窗格

---

*Plan version: v1.0.0 — for agentic execution*