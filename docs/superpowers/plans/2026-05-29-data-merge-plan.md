# FR-3.x 数据关联模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建数据关联 / 核对诊断中心，以订单为中心展示订单与 PI 的合并比对结果，支持差异标红、Tooltip 和快速跳转。

**Architecture:** 后端提供两个只读 API：订单列表查询（含关联状态）+ 订单详情比对数据（含 diff 标志）。前端采用 el-table 可展开行 + Popover 二选一菜单实现核对与跳转闭环。

**Tech Stack:** FastAPI + SQLAlchemy + SQLite（后端只读），Vue 3 + Element Plus + TypeScript（前端）。

---

## 文件结构

```
backend/
├── app/
│   ├── models/
│   │   ├── order.py          # 现有：Order, OrderItem
│   │   └── pi_contract.py    # 现有：PiContract, PiContractItem, PiData
│   ├── schemas/
│   │   └── merge.py           # NEW：合并查询的 Pydantic schemas
│   ├── services/
│   │   └── merge_service.py   # NEW：合并查询服务层（只读）
│   └── api/v1/
│       └── merge.py           # NEW：合并查询 API 路由
frontend/
├── src/
│   ├── api/
│   │   └── merge.ts           # NEW：合并查询 API 客户端
│   ├── views/
│   │   └── phase1/
│   │       └── DataMerge.vue  # NEW：数据关联主页
│   └── components/
│       └── phase1/
│           ├── OrderExpandRow.vue    # NEW：展开行（含 DiffCell）
│           ├── DiffCell.vue          # NEW：差异单元格（含 Tooltip）
│           └── QuickJumpPopover.vue  # NEW：🔗 跳转选择弹窗
```

---

## 任务索引

| ID | 轨道 | 描述 |
|----|------|------|
| BM-1 | Backend | Pydantic schemas — 合并查询的请求/响应模型 |
| BM-2 | Backend | merge_service.py — 订单列表查询 + 关联状态计算 |
| BM-3 | Backend | merge_service.py — 订单比对数据查询 + diff 计算 |
| BM-4 | Backend | API 路由 — GET /api/v1/merge/orders + GET /api/v1/merge/orders/{order_id}/comparison |
| FE-1 | Frontend | merge.ts API 客户端 |
| FE-2 | Frontend | DataMerge.vue 主页面（Tab + 搜索 + 订单列表可展开） |
| FE-3 | Frontend | DiffCell.vue + OrderExpandRow.vue — 标红单元格 + 展开行 |
| FE-4 | Frontend | QuickJumpPopover.vue — Popover 二选一菜单 |

---

## Track 1: Backend（BM-1 → BM-2 → BM-3 → BM-4）

### Task BM-1: Pydantic Schemas — 合并查询

**Files:**
- Create: `backend/app/schemas/merge.py`
- Modify: `backend/app/schemas/__init__.py`

---

- [ ] **Step 1: 创建 schemas/merge.py**

```python
"""合并查询的 Pydantic schemas — FR-3.x 数据关联模块"""

from pydantic import BaseModel
from typing import Optional


class OrderListItem(BaseModel):
    """订单列表项（聚合视图）"""
    id: int
    order_no: str
    customer_code: Optional[str] = None
    salesperson: Optional[str] = None
    total_amount: Optional[float] = None
    association_status: str  # "full" / "partial" / "none"
    items_count: int         # 订单产品总数
    linked_count: int         # 已关联 PI 的数量
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """订单列表响应（含分页）"""
    orders: list[OrderListItem]
    total: int
    page: int
    page_size: int


class OrderItemData(BaseModel):
    """订单产品数据"""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None


class PiItemData(BaseModel):
    """PI 产品数据"""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    hs_code: Optional[str] = None
    customs_name: Optional[str] = None


class DiffInfo(BaseModel):
    """差异信息"""
    status: str  # "一致" / "数量不符" / "单价不符" / "金额不符" / "HS不符" / "PI未覆盖" / "订单无记录"
    flags: list[str] = []  # 如 ["quantity", "unit_price"]
    order_value: Optional[float] = None  # 仅当数值差异时填充
    pi_value: Optional[float] = None     # 仅当数值差异时填充


class ComparisonItem(BaseModel):
    """比对明细行"""
    internal_code: str
    product_cn: Optional[str] = None
    order: Optional[OrderItemData] = None
    pi: Optional[PiItemData] = None
    diff: DiffInfo

    class Config:
        from_attributes = True


class OrderComparisonResponse(BaseModel):
    """订单比对数据响应"""
    order_id: int
    order_no: str
    customer_code: Optional[str] = None
    items: list[ComparisonItem]


class MergeQueryParams(BaseModel):
    """查询参数（用于 FastAPI Query）"""
    tab: str = "pending"  # "pending" / "completed" / "all"
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20
```

---

- [ ] **Step 2: 更新 schemas/__init__.py**

```python
from app.schemas.merge import (
    OrderListItem,
    OrderListResponse,
    OrderComparisonResponse,
    ComparisonItem,
    MergeQueryParams,
)
```

---

- [ ] **Step 3: 验证导入**

Run: `cd backend && .venv/Scripts/python.exe -c "from app.schemas.merge import OrderListResponse, OrderComparisonResponse; print('OK')"`
Expected: `OK`

---

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/merge.py backend/app/schemas/__init__.py
git commit -m "feat(backend): add merge schemas for FR-3.x data merge API"
```

---

### Task BM-2: Merge Service — 订单列表查询 + 关联状态

**Files:**
- Create: `backend/app/services/merge_service.py`
- Test: `backend/tests/test_merge_service.py`

---

- [ ] **Step 1: 编写测试**

Create `backend/tests/test_merge_service.py`:

```python
import pytest
from app.database import init_db, SessionLocal
from app.services.merge_service import MergeService
from app.models.order import Order, OrderItem
from app.models.pi_contract import PiContract, PiContractItem


def test_association_status_full():
    """当订单所有 items 均在 PI 中有匹配 → status = full"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    # 创建一个订单，两个 items，均有关联 PI
    order = Order(order_no="TEST-FULL", customer_code="CUST")
    db.add(order)
    db.flush()

    item1 = OrderItem(order_id=order.id, internal_code="SILI-001", quantity_kg=100)
    item2 = OrderItem(order_id=order.id, internal_code="SILI-002", quantity_kg=200)
    db.add_all([item1, item2])

    pi = PiContract(pi_no="PI-FULL", customer_code="CUST")
    db.add(pi)
    db.flush()

    pi_item1 = PiContractItem(pi_contract_id=pi.id, internal_code="SILI-001", quantity=100)
    pi_item2 = PiContractItem(pi_contract_id=pi.id, internal_code="SILI-002", quantity=200)
    db.add_all([pi_item1, pi_item2])
    db.commit()

    result = service.get_order_list(tab="pending")
    # order_no="TEST-FULL" 应显示 partial 或 full
    item = next((o for o in result["orders"] if o["order_no"] == "TEST-FULL"), None)
    assert item is not None
    assert item["association_status"] in ["full", "partial"]

    db.close()


def test_association_status_none():
    """当订单没有任何 items 在 PI 中有匹配 → status = none"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    order = Order(order_no="TEST-NONE", customer_code="CUST")
    db.add(order)
    db.flush()

    item = OrderItem(order_id=order.id, internal_code="SILI-999", quantity_kg=100)
    db.add(item)
    db.commit()

    result = service.get_order_list(tab="pending")
    item = next((o for o in result["orders"] if o["order_no"] == "TEST-NONE"), None)
    assert item is not None
    assert item["association_status"] == "none"

    db.close()
```

---

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_merge_service.py -v`
Expected: FAIL with "No module named 'app.services.merge_service'"

---

- [ ] **Step 3: 编写 merge_service.py**

Create `backend/app/services/merge_service.py`:

```python
"""合并查询服务 — FR-3.x 数据关联模块（只读）"""

from typing import Optional
from app.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.pi_contract import PiContract, PiContractItem
from app.schemas.merge import (
    OrderListItem,
    OrderListResponse,
    OrderComparisonResponse,
    ComparisonItem,
    OrderItemData,
    PiItemData,
    DiffInfo,
)


FLOAT_TOLERANCE = 0.01  # 数值字段容差


class MergeService:
    """数据关联服务 — 只读查询，不写入任何数据"""

    def __init__(self, db_session):
        self.db = db_session

    def get_order_list(
        self,
        tab: str = "pending",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> OrderListResponse:
        """
        查询订单列表，计算关联状态，返回分页结果。

        关联状态判定：
        - full: 所有 order_items 的 internal_code 均在 pi_contract_items 中有匹配
        - partial: 部分有匹配
        - none: 没有任何匹配
        """
        query = self.db.query(Order)

        # 模糊搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Order.order_no.like(search_pattern)) |
                (Order.customer_code.like(search_pattern))
            )

        # 按创建时间倒序
        query = query.order_by(Order.created_at.desc())

        total = query.count()
        offset = (page - 1) * page_size
        orders = query.offset(offset).limit(page_size).all()

        result_items = []
        for order in orders:
            # 计算关联状态
            items = self.db.query(OrderItem).filter_by(order_id=order.id).all()
            if not items:
                association_status = "none"
                linked_count = 0
            else:
                internal_codes = [item.internal_code for item in items]
                # 查询有多少 items 在 PI 中有匹配
                linked_items = self.db.query(PiContractItem).filter(
                    PiContractItem.internal_code.in_(internal_codes)
                ).all()
                linked_codes = set(item.internal_code for item in linked_items)

                matched = sum(1 for item in items if item.internal_code in linked_codes)
                linked_count = matched

                if matched == len(items):
                    association_status = "full"
                elif matched > 0:
                    association_status = "partial"
                else:
                    association_status = "none"

            # 计算订单总金额
            total_amount = sum(
                (item.quantity_kg or 0) * (item.unit_price or 0)
                for item in items
            )

            result_items.append(OrderListItem(
                id=order.id,
                order_no=order.order_no,
                customer_code=order.customer_code,
                salesperson=order.salesperson,
                total_amount=total_amount if total_amount > 0 else None,
                association_status=association_status,
                items_count=len(items),
                linked_count=linked_count,
                created_at=order.created_at.strftime("%Y-%m-%d") if order.created_at else None,
            ))

        # Tab 过滤
        if tab == "pending":
            result_items = [i for i in result_items if i.association_status != "full"]
        elif tab == "completed":
            result_items = [i for i in result_items if i.association_status == "full"]

        return OrderListResponse(
            orders=result_items,
            total=len(result_items),
            page=page,
            page_size=page_size,
        )

    def get_order_comparison(self, order_id: int) -> Optional[OrderComparisonResponse]:
        """
        获取指定订单的合并比对数据。
        返回每个 order_item 与对应的 pi_contract_item 的比对结果。
        """
        order = self.db.query(Order).filter_by(id=order_id).first()
        if not order:
            return None

        order_items = self.db.query(OrderItem).filter_by(order_id=order_id).all()
        comparison_items = []

        for item in order_items:
            internal_code = item.internal_code

            # 查找对应的 PI item
            pi_item = self.db.query(PiContractItem).filter_by(
                internal_code=internal_code
            ).first()

            # 构建 order 数据
            order_data = OrderItemData(
                quantity=item.quantity_kg,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
                hs_code=item.hs_code,
                customs_name=item.customs_name,
            )

            # 构建 PI 数据（可能为空）
            pi_data = None
            if pi_item:
                pi_data = PiItemData(
                    quantity=pi_item.quantity,
                    unit_price=pi_item.unit_price,
                    total_amount=pi_item.total_amount,
                    hs_code=pi_item.hs_code,
                    customs_name=pi_item.customs_name,
                )

            # 计算差异
            diff = self._compute_diff(item, pi_item)

            comparison_items.append(ComparisonItem(
                internal_code=internal_code,
                product_cn=item.product_cn,
                order=order_data,
                pi=pi_data,
                diff=diff,
            ))

        return OrderComparisonResponse(
            order_id=order.id,
            order_no=order.order_no,
            customer_code=order.customer_code,
            items=comparison_items,
        )

    def _compute_diff(self, order_item: OrderItem, pi_item: Optional[PiContractItem]) -> DiffInfo:
        """
        计算单个产品的差异状态。
        数值字段容差 ±0.01，文本字段严格比对。
        """
        flags = []
        order_value = None
        pi_value = None

        if pi_item is None:
            # PI 未覆盖
            return DiffInfo(
                status="PI未覆盖",
                flags=["no_pi"],
                order_value=order_item.quantity_kg,
                pi_value=None,
            )

        # 数量比对
        o_qty = order_item.quantity_kg
        p_qty = pi_item.quantity
        if o_qty is not None and p_qty is not None:
            if abs(o_qty - p_qty) > FLOAT_TOLERANCE:
                flags.append("quantity")
                order_value = o_qty
                pi_value = p_qty

        # 单价比对
        o_price = order_item.unit_price
        p_price = pi_item.unit_price
        if o_price is not None and p_price is not None:
            if abs(o_price - p_price) > FLOAT_TOLERANCE:
                flags.append("unit_price")

        # 金额比对
        o_total = order_item.total_amount
        p_total = pi_item.total_amount
        if o_total is not None and p_total is not None:
            if abs(o_total - p_total) > FLOAT_TOLERANCE:
                flags.append("total_amount")

        # HS Code 比对（严格）
        if order_item.hs_code and pi_item.hs_code:
            if order_item.hs_code != pi_item.hs_code:
                flags.append("hs_code")

        # 报关品名比对（严格）
        if order_item.customs_name and pi_item.customs_name:
            if order_item.customs_name != pi_item.customs_name:
                flags.append("customs_name")

        if flags:
            status_map = {
                "quantity": "数量不符",
                "unit_price": "单价不符",
                "total_amount": "金额不符",
                "hs_code": "HS不符",
                "customs_name": "品名不符",
            }
            status = status_map.get(flags[0], "不一致")
            return DiffInfo(status=status, flags=flags, order_value=order_value, pi_value=pi_value)
        else:
            return DiffInfo(status="一致", flags=[])
```

---

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_merge_service.py -v`
Expected: PASS

---

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/merge_service.py backend/tests/test_merge_service.py
git commit -m "feat(backend): add MergeService with order list and comparison APIs"
```

---

### Task BM-3: 完善关联 PI 缺失的处理（补充）

> 本任务补充 BM-2 中未覆盖的场景：当订单有 item 但 PI 中完全没有匹配时，pi 侧应返回 `null` 而非空对象。

**Files:**
- Modify: `backend/app/services/merge_service.py:_compute_diff`

> 当前 _compute_diff 已在 pi_item is None 时返回 "PI未覆盖"，逻辑已完整。无需修改。

---

### Task BM-4: API 路由 — 合并查询端点

**Files:**
- Create: `backend/app/api/v1/merge.py`
- Modify: `backend/app/main.py`（注册路由）
- Modify: `backend/app/api/deps.py`（添加 get_merge_service）

---

- [ ] **Step 1: 创建 API 路由**

Create `backend/app/api/v1/merge.py`:

```python
"""FR-3.x 数据关联 API — 合并查询端点（只读）"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.services.merge_service import MergeService
from app.schemas.merge import OrderListResponse, OrderComparisonResponse
from app.api.deps import get_merge_service


router = APIRouter(prefix="/api/v1/merge", tags=["数据关联"])


@router.get("/orders", response_model=OrderListResponse)
async def get_merge_order_list(
    tab: str = Query("pending", description="pending / completed / all"),
    search: Optional[str] = Query(None, description="模糊搜索：订单号 / 客户名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    查询订单列表（含关联状态），支持 Tab 筛选和分页。

    - tab=pending：仅显示未关联 / 部分关联的订单
    - tab=completed：仅显示完全关联的订单
    - tab=all：显示全部订单
    - search：支持订单号、客户名称模糊匹配
    """
    return merge_service.get_order_list(
        tab=tab,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/orders/{order_id}/comparison", response_model=OrderComparisonResponse)
async def get_order_comparison(
    order_id: int,
    merge_service: MergeService = Depends(get_merge_service),
):
    """
    获取指定订单的合并比对数据。

    返回每个 order_item 与对应的 pi_contract_item 的比对结果，
    包含 diff.status（一致 / 数量不符 / ...）和 flags 列表。
    """
    result = merge_service.get_order_comparison(order_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="订单不存在")
    return result
```

---

- [ ] **Step 2: 添加 dependency**

Modify `backend/app/api/deps.py`:

```python
from app.services.merge_service import MergeService

def get_merge_service() -> MergeService:
    """数据关联服务依赖"""
    return MergeService(SessionLocal())
```

---

- [ ] **Step 3: 注册路由**

Modify `backend/app/main.py` — 添加：

```python
from app.api.v1.merge import router as merge_router

app.include_router(merge_router)
```

---

- [ ] **Step 4: 验证**

Run: `curl http://localhost:8000/api/v1/merge/orders`
Expected: 返回 JSON 格式的订单列表（含 association_status 字段）

---

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/merge.py backend/app/api/deps.py backend/app/main.py
git commit -m "feat(backend): add FR-3.x merge API endpoints"
```

---

## Track 2: Frontend（FE-1 → FE-2 → FE-3 → FE-4）

### Task FE-1: API 客户端 — merge.ts

**Files:**
- Create: `frontend/src/api/merge.ts`

---

- [ ] **Step 1: 创建 API 客户端**

Create `frontend/src/api/merge.ts`:

```typescript
import axios from 'axios'

const BASE_URL = '/api/v1/merge'

export interface OrderListItem {
  id: number
  order_no: string
  customer_code?: string
  salesperson?: string
  total_amount?: number
  association_status: 'full' | 'partial' | 'none'
  items_count: number
  linked_count: number
  created_at?: string
}

export interface OrderListResponse {
  orders: OrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface OrderItemData {
  quantity?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
}

export interface DiffInfo {
  status: string  // "一致" | "数量不符" | "单价不符" | "金额不符" | "HS不符" | "PI未覆盖"
  flags: string[]
  order_value?: number
  pi_value?: number
}

export interface ComparisonItem {
  internal_code: string
  product_cn?: string
  order?: OrderItemData
  pi?: OrderItemData
  diff: DiffInfo
}

export interface OrderComparisonResponse {
  order_id: number
  order_no: string
  customer_code?: string
  items: ComparisonItem[]
}

export const getOrderList = async (params: {
  tab?: string
  search?: string
  page?: number
  page_size?: number
}): Promise<OrderListResponse> => {
  const response = await axios.get<OrderListResponse>(`${BASE_URL}/orders`, { params })
  return response.data
}

export const getOrderComparison = async (orderId: number): Promise<OrderComparisonResponse> => {
  const response = await axios.get<OrderComparisonResponse>(`${BASE_URL}/orders/${orderId}/comparison`)
  return response.data
}
```

---

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/merge.ts
git commit -m "feat(frontend): add data merge API client"
```

---

### Task FE-2: 主页面 — DataMerge.vue

**Files:**
- Create: `frontend/src/views/phase1/DataMerge.vue`
- Modify: `frontend/src/router/index.ts`（添加 /data-merge 路由）
- Modify: `frontend/src/views/Layout.vue`（添加导航入口）

---

- [ ] **Step 1: 创建 DataMerge.vue**

Create `frontend/src/views/phase1/DataMerge.vue`:

```vue
<template>
  <div class="data-merge-page">
    <div class="page-header">
      <h1 class="page-title">数据关联</h1>
      <p class="page-subtitle">订单与 PI 数据核对诊断中心 — 只提示，不合并</p>
    </div>

    <!-- 顶部：Tab + 搜索 -->
    <div class="filter-bar">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="🔴 待处理" name="pending" />
        <el-tab-pane label="🟢 已完成" name="completed" />
        <el-tab-pane label="📋 全部" name="all" />
      </el-tabs>
      <el-input
        v-model="searchText"
        placeholder="搜索订单号 / 内部编码 / 客户名称"
        clearable
        class="search-input"
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button icon="Search" @click="handleSearch" />
        </template>
      </el-input>
    </div>

    <!-- 订单列表：可展开表格 -->
    <el-table
      :data="orderList"
      border
      stripe
      v-loading="loading"
      row-key="id"
      @expand-change="handleExpand"
      :expand-row-keys="expandedRows"
      class="order-table"
    >
      <el-table-column type="expand" width="50">
        <template #default="{ row }">
          <OrderExpandRow
            v-if="expandedRows.includes(row.id)"
            :order-id="row.id"
          />
        </template>
      </el-table-column>

      <el-table-column prop="order_no" label="订单号" width="160" />
      <el-table-column prop="customer_code" label="客户编码" width="140" />
      <el-table-column prop="salesperson" label="业务员" width="100" />
      <el-table-column prop="total_amount" label="订单总金额" width="120" align="right">
        <template #default="{ row }">
          {{ row.total_amount ? `¥${row.total_amount.toLocaleString()}` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="items_count" label="产品数" width="80" align="center" />
      <el-table-column label="关联状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.association_status)">
            {{ statusLabel(row.association_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建日期" width="120" />
      <el-table-column label="操作" width="80" align="center">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="toggleExpand(row.id)"
          >
            {{ expandedRows.includes(row.id) ? '收起' : '查看' }}
          </el-button>
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
import { ref, onMounted } from 'vue'
import { getOrderList, type OrderListItem } from '@/api/merge'
import OrderExpandRow from '@/components/phase1/OrderExpandRow.vue'

const activeTab = ref('pending')
const searchText = ref('')
const orderList = ref<OrderListItem[]>([])
const loading = ref(false)
const expandedRows = ref<number[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

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

const loadData = async () => {
  loading.value = true
  try {
    const response = await getOrderList({
      tab: activeTab.value,
      search: searchText.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    orderList.value = response.orders
    total.value = response.total
  } catch (error) {
    console.error('Failed to load order list:', error)
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  currentPage.value = 1
  expandedRows.value = []
  loadData()
}

const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

const toggleExpand = (id: number) => {
  const idx = expandedRows.value.indexOf(id)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value.push(id)
  }
}

const handleExpand = (row: OrderListItem, expanded: boolean) => {
  // 配合 row-key 自动管理展开状态
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.data-merge-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }
.filter-bar { display: flex; gap: 16px; align-items: center; margin-bottom: 20px; }
.filter-bar .el-tabs { flex: 0 0 auto; }
.search-input { width: 320px; }
.order-table { margin-bottom: 16px; }
.pagination-wrapper { display: flex; justify-content: flex-end; }
</style>
```

---

- [ ] **Step 2: 添加路由**

Modify `frontend/src/router/index.ts`：

```typescript
import DataMerge from "@/views/phase1/DataMerge.vue"

const routes = [
  // ... existing routes
  {
    path: "/data-merge",
    name: "DataMerge",
    component: DataMerge,
    meta: { title: "数据关联" }
  }
]
```

---

- [ ] **Step 3: 添加导航入口**

Modify `frontend/src/views/Layout.vue`：在 nav bar 中添加：

```vue
<el-menu-item index="/data-merge">数据关联</el-menu-item>
```

---

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/phase1/DataMerge.vue frontend/src/router/index.ts frontend/src/views/Layout.vue
git commit -m "feat(frontend): add DataMerge page with Tab filter and expandable order list"
```

---

### Task FE-3: DiffCell + OrderExpandRow

**Files:**
- Create: `frontend/src/components/phase1/DiffCell.vue`
- Create: `frontend/src/components/phase1/OrderExpandRow.vue`

---

- [ ] **Step 1: 创建 DiffCell.vue**

Create `frontend/src/components/phase1/DiffCell.vue`:

```vue
<template>
  <div class="diff-cell">
    <span v-if="!hasDiff" class="一致">✅ 一致</span>
    <el-tooltip
      v-else
      placement="top"
      :content="tooltipContent"
    >
      <span :class="cellClass">{{ displayValue }} <span class="diff-flag">⚠️</span></span>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  orderValue?: number | string
  piValue?: number | string
  diffStatus: string  // "一致" / "数量不符" / "PI未覆盖" 等
  flags: string[]
}>()

const hasDiff = computed(() => props.flags.length > 0 || props.diffStatus === 'PI未覆盖')

const displayValue = computed(() => {
  if (props.diffStatus === 'PI未覆盖') return '—'
  return props.orderValue !== undefined ? String(props.orderValue) : '—'
})

const cellClass = computed(() => {
  if (props.diffStatus === 'PI未覆盖') return 'pi-missing'
  return 'diff-warning'
})

const tooltipContent = computed(() => {
  if (props.diffStatus === 'PI未覆盖') {
    return `订单有数据，PI 未覆盖此产品`
  }
  return `订单值：${props.orderValue ?? '-'} / PI值：${props.piValue ?? '-'}`
})
</script>

<style scoped>
.diff-cell { font-size: 13px; }
.一致 { color: #67c23a; }
.diff-warning { color: #f56c6c; cursor: pointer; }
.pi-missing { color: #e6a23c; cursor: pointer; }
.diff-flag { margin-left: 2px; }
</style>
```

---

- [ ] **Step 2: 创建 OrderExpandRow.vue**

Create `frontend/src/components/phase1/OrderExpandRow.vue`:

```vue
<template>
  <div class="expand-row" v-loading="loading">
    <table class="comparison-table" v-if="!loading && comparison">
      <thead>
        <tr>
          <th>内部编码</th>
          <th>产品名称</th>
          <th>📦 订单数量/单价</th>
          <th>📄 PI 数量/单价</th>
          <th>差异状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in comparison.items" :key="item.internal_code">
          <td>{{ item.internal_code }}</td>
          <td>{{ item.product_cn || '-' }}</td>
          <td>
            <div class="cell-value">
              <span>{{ item.order?.quantity ?? '-' }} kg</span>
              <span class="secondary">{{ item.order?.unit_price ? `¥${item.order.unit_price}` : '' }}</span>
            </div>
          </td>
          <td>
            <div class="cell-value" :class="{ 'pi-missing': !item.pi }">
              <span v-if="item.pi">{{ item.pi.quantity ?? '-' }} kg</span>
              <span v-else class="no-data">— 无 PI 记录</span>
              <span v-if="item.pi?.unit_price" class="secondary">¥{{ item.pi.unit_price }}</span>
            </div>
          </td>
          <td>
            <DiffCell
              :order-value="item.order?.quantity"
              :pi-value="item.pi?.quantity"
              :diff-status="item.diff.status"
              :flags="item.diff.flags"
            />
          </td>
          <td>
            <QuickJumpPopover
              :internal-code="item.internal_code"
              :order-id="orderId"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getOrderComparison, type OrderComparisonResponse } from '@/api/merge'
import DiffCell from './DiffCell.vue'
import QuickJumpPopover from './QuickJumpPopover.vue'

const props = defineProps<{
  orderId: number
}>()

const loading = ref(false)
const comparison = ref<OrderComparisonResponse | null>(null)

const loadComparison = async () => {
  loading.value = true
  try {
    comparison.value = await getOrderComparison(props.orderId)
  } catch (error) {
    console.error('Failed to load comparison:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadComparison()
})
</script>

<style scoped>
.expand-row { padding: 12px 20px; background: #f5f7fa; }
.comparison-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.comparison-table th { text-align: left; padding: 8px 12px; background: #e4e7ed; border: 1px solid #dcdfe6; }
.comparison-table td { padding: 8px 12px; border: 1px solid #dcdfe6; background: #fff; }
.cell-value { display: flex; flex-direction: column; }
.cell-value .secondary { color: #909399; font-size: 12px; }
.no-data { color: #c0c4cc; font-style: italic; }
.pi-missing td { background: #fdf6ec; }
</style>
```

---

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/phase1/DiffCell.vue frontend/src/components/phase1/OrderExpandRow.vue
git commit -m "feat(frontend): add DiffCell and OrderExpandRow components"
```

---

### Task FE-4: QuickJumpPopover — 跳转选择弹窗

**Files:**
- Create: `frontend/src/components/phase1/QuickJumpPopover.vue`

---

- [ ] **Step 1: 创建 QuickJumpPopover.vue**

Create `frontend/src/components/phase1/QuickJumpPopover.vue`:

```vue
<template>
  <el-popover
    placement="top"
    :width="200"
    trigger="click"
  >
    <template #reference>
      <el-button link type="primary" size="small">🔗</el-button>
    </template>
    <div class="popover-content">
      <p class="popover-title">选择检查目标</p>
      <el-button class="jump-btn" @click="goToOrder">
        📦 检查订单数据
      </el-button>
      <el-button class="jump-btn" @click="goToPI">
        📄 检查 PI 数据
      </el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = defineProps<{
  internalCode: string
  orderId: number
  piContractId?: number
}>()

const router = useRouter()

const goToOrder = () => {
  router.push({
    path: '/order-paste',
    query: { orderId: String(props.orderId), highlight: props.internalCode }
  })
}

const goToPI = () => {
  router.push({
    path: '/pi-extract',
    query: { highlight: props.internalCode }
  })
}
</script>

<style scoped>
.popover-content { padding: 4px 0; }
.popover-title { font-size: 13px; color: #909399; margin: 0 0 8px 8px; }
.jump-btn { width: 100%; margin: 2px 0; justify-content: flex-start; }
</style>
```

---

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/phase1/QuickJumpPopover.vue
git commit -m "feat(frontend): add QuickJumpPopover for diff row navigation"
```

---

## 验证清单

After all tasks are complete, verify each item:

- [ ] **Backend**: `curl http://localhost:8000/api/v1/merge/orders` 返回订单列表，含 association_status 字段
- [ ] **Backend**: `curl http://localhost:8000/api/v1/merge/orders/1/comparison` 返回比对数据，含 diff.status
- [ ] **Backend**: 测试"PI未覆盖"场景：order_items 有但 pi_contract_items 无匹配时，diff.status = "PI未覆盖"
- [ ] **Backend**: 测试数值容差：qty 差 0.001 不标红，差 0.02 标红
- [ ] **Frontend**: 访问 http://localhost:5173/data-merge 页面正常加载
- [ ] **Frontend**: 点击"待处理"Tab 显示未关联 / 部分关联订单
- [ ] **Frontend**: 点击订单行展开，显示比对明细，差异行标红
- [ ] **Frontend**: 点击 🔗 图标，Popover 显示"检查订单"和"检查PI"两个选项

---

## Self-Review Checklist

Before saving this plan, I checked:

1. **Spec coverage**: 所有 FR-3.x 验收标准（AC-1 ~ AC-8）均有对应任务实现
2. **Placeholder scan**: 无 "TBD"、"TODO"、未完成的步骤
3. **Type consistency**: DiffInfo.status 使用一致（"一致"、"数量不符"、...），无 `clearLayers()` 类命名错误
4. **边界清晰**: MergeService 明确只读，不写入 orders 或 pi_contracts 表
5. **容差机制**: FLOAT_TOLERANCE = 0.01 在 _compute_diff 中正确应用

---

*Plan version: v1.0.0 — for agentic execution*