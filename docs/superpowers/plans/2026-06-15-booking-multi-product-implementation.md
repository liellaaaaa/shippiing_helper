# 订舱单多产品 + 报关名称匹配 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一单多品订舱单（每个产品报关名称单独一行）+ 解析时自动匹配商品编码 JSON 补全报关名称

**Architecture:**
- 数据层：Excel → JSON 转换脚本 + CustomsNameService（内存缓存）
- 第一阶段：解析时触发匹配，补全 customs_name 等字段到 ParsedOrderSchema
- 第二阶段：订舱单表单改为多行表格，后端支持 customs_names 数组，模板支持 DESC1-DESC6

**Tech Stack:** Python (openpyxl) / Vue 3 + Element Plus / FastAPI

---

## 文件结构概览

```
backend/
├── scripts/
│   └── extract_customs_codes.py          # 新建：Excel → JSON
├── app/
│   ├── core/
│   │   └── config.py                     # 修改：添加 CUSTOMS_CODES_JSON 配置
│   ├── services/
│   │   └── customs_name_service.py       # 新建：报关名称查询服务
│   ├── core/
│   │   └── order_parser.py              # 修改：解析时触发匹配
│   ├── models/
│   │   └── order_pi_record.py          # 修改：新增 4 个字段
│   └── api/v1/
│       └── documents.py                 # 修改：BookingFields 添加 customs_names
└── services/
    └── document_service.py              # 修改：fill_booking_template 支持 DESC1-6

frontend/
├── src/api/
│   └── phase2.ts                       # 修改：generateBooking 添加 customs_names
└── views/phase2/
    ├── Phase2Workflow.vue              # 修改：传递 customs_names 到订舱表单
    └── components/
        └── BookingConfirmDialog.vue    # 修改：改为多行表格

references/
└── customs_codes.json                  # 新建：由脚本生成
```

---

## Task 1: Excel → JSON 转换脚本

**Files:**
- Create: `backend/scripts/extract_customs_codes.py`
- Output: `references/customs_codes.json`

```python
"""一次性脚本：从 Excel 提取商品编码数据生成 JSON"""
import json
import openpyxl

INPUT_FILE = "references/2024.12.5 最新出口商品编码及报关成分.xlsx"
OUTPUT_FILE = "references/customs_codes.json"

# 列索引（基于表头行）
COLS = {
    "internal_code": 1,
    "product_code": 5,
    "customs_name": 6,
    "components": 7,
    "product_appearance": 4,
}

def extract():
    wb = openpyxl.load_workbook(INPUT_FILE, data_only=True)
    ws = wb.active

    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
        if not row[COLS["internal_code"]]:
            continue
        record = {
            "internal_code": str(row[COLS["internal_code"]] or "").strip(),
            "product_code": str(row[COLS["product_code"]] or "").strip(),
            "customs_name": str(row[COLS["customs_name"]] or "").strip(),
            "components": str(row[COLS["components"]] or "").strip(),
            "product_appearance": str(row[COLS["product_appearance"]] or "").strip(),
        }
        records.append(record)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Extracted {len(records)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract()
```

- [ ] **Step 1: 创建脚本** — 创建 `backend/scripts/extract_customs_codes.py` 并写入以上代码

- [ ] **Step 2: 运行脚本生成 JSON**

```bash
cd c:/Users/windows/Desktop/shippiing_helper
python backend/scripts/extract_customs_codes.py
```

Expected: 生成 `references/customs_codes.json`

- [ ] **Step 3: 验证 JSON 内容** — 检查第一条记录的 `internal_code` / `customs_name` 是否正确

---

## Task 2: CustomsNameService

**Files:**
- Create: `backend/app/services/customs_name_service.py`
- Modify: `backend/app/core/config.py` (添加配置)
- Modify: `backend/app/main.py` (启动时加载)

```python
# backend/app/services/customs_name_service.py
import json
from pathlib import Path
from typing import Optional

class CustomsNameService:
    _instance: "CustomsNameService | None" = None

    def __init__(self, json_path: str):
        self._cache: dict[str, dict] = {}
        self._load(json_path)

    def _load(self, json_path: str):
        p = Path(json_path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            records = json.load(f)
        for r in records:
            key = r.get("internal_code", "").strip()
            if key:
                self._cache[key] = r

    def lookup(self, internal_code: str) -> Optional[dict]:
        return self._cache.get(internal_code.strip())

    @classmethod
    def get_instance(cls, json_path: str) -> "CustomsNameService":
        if cls._instance is None:
            cls._instance = cls(json_path)
        return cls._instance
```

**config.py 添加:**
```python
CUSTOMS_CODES_JSON = str(ROOT / "references" / "customs_codes.json")
```

**main.py 添加（在 startup 时实例化）:**
```python
from app.services.customs_name_service import CustomsNameService
from app.core.config import CUSTOMS_CODES_JSON

@app.on_event("startup")
async def startup():
    CustomsNameService.get_instance(CUSTOMS_CODES_JSON)
```

- [ ] **Step 1: 创建 CustomsNameService** — 创建 `backend/app/services/customs_name_service.py`

- [ ] **Step 2: 修改 config.py** — 添加 `CUSTOMS_CODES_JSON` 配置项

- [ ] **Step 3: 修改 main.py** — 在 startup 时实例化 CustomsNameService

- [ ] **Step 4: 验证启动加载** — 启动 Backend，检查日志是否无报错

---

## Task 3: OrderPiRecord 新增字段

**Files:**
- Modify: `backend/app/models/order_pi_record.py`

```python
# 新增字段（在 existing customs_name 之后添加）
product_code = Column(String(20))
components = Column(String(500))
product_appearance = Column(String(200))
customs_match_status = Column(String(20))  # matched / conflict / filled / not_found
```

- [ ] **Step 1: 修改 OrderPiRecord model** — 添加 4 个新字段（customs_name 已存在）

- [ ] **Step 2: 创建数据库迁移**

```bash
cd backend
python -m app.database  # 测试导入不报错
# 手动执行 ALTER TABLE（因 SQLite，迁移脚本为便利写法）
```

---

## Task 4: 解析时触发匹配逻辑

**Files:**
- Modify: `backend/app/core/order_parser.py`
- Modify: `backend/app/schemas/order.py` (OrderItemSchema 新增字段)

**OrderItemSchema 新增字段** (已在 line 12 存在 `customs_name`，需确认 `customs_ingredients` 对应 `components`):

```python
# customs_ingredients 已存在 (line 13)，确认是否改名为 components
# 或新增：
product_code: Optional[str] = None
product_appearance: Optional[str] = None
customs_match_status: Optional[str] = None
conflict_customs_name: Optional[str] = None  # 仅 conflict 时返回
```

**order_parser.py 匹配逻辑** — 在 `parse_pasted_data` 返回前，对每个 `order_item` 调用 `CustomsNameService.lookup(internal_code)`：

```python
from app.services.customs_name_service import CustomsNameService

# 在 parse_pasted_data 函数中，构建 OrderItemSchema 后：
customs_svc = CustomsNameService.get_instance(config.CUSTOMS_CODES_JSON)
for item in order.items:
    json_data = customs_svc.lookup(item.internal_code)
    if json_data is None:
        item.customs_match_status = "not_found"
    elif item.customs_name and item.customs_name != json_data["customs_name"]:
        item.customs_match_status = "conflict"
        item.conflict_customs_name = json_data["customs_name"]
        # 注意：保留用户已填的 customs_name，额外返回 json 中的值
    elif not item.customs_name:
        item.customs_name = json_data["customs_name"]
        item.customs_ingredients = json_data["components"]
        item.product_code = json_data["product_code"]
        item.product_appearance = json_data["product_appearance"]
        item.customs_match_status = "filled"
    else:
        item.customs_match_status = "matched"
```

- [ ] **Step 1: 修改 OrderItemSchema** — 确认/新增 `product_code`, `product_appearance`, `customs_match_status`, `conflict_customs_name` 字段

- [ ] **Step 2: 修改 order_parser.py** — 导入 CustomsNameService，在 `parse_pasted_data` 返回前注入匹配逻辑

- [ ] **Step 3: 测试解析** — POST 粘贴数据，观察返回 item 是否包含 customs_match_status

---

## Task 5: 后端 BookingFields 支持 customs_names 数组

**Files:**
- Modify: `backend/app/api/v1/documents.py`
- Modify: `backend/app/services/document_service.py`

**documents.py BookingFields:**
```python
class BookingFields(BaseModel):
    # ... existing fields ...
    customs_names: list[str] = []  # 新增：多产品报关名称
    gross_weight: str = ""
    measurement: str = ""
```

**模板映射:**
```python
for i, name in enumerate(fields.customs_names, 1):
    fields_dict[f"DESC{i}"] = name
# DESC1-DESC6，没有则留空
```

- [ ] **Step 1: 修改 BookingFields** — 添加 `customs_names: list[str]`

- [ ] **Step 2: 修改 document_service.py** — `fill_booking_template` 支持 DESC1-DESC6

- [ ] **Step 3: 测试后端 API** — 手动 POST `/api/v1/documents/booking` 带 customs_names，验证模板替换正确

---

## Task 6: 前端 generateBooking 支持 customs_names

**Files:**
- Modify: `frontend/src/api/phase2.ts`
- Modify: `frontend/src/views/phase2/Phase2Workflow.vue`
- Modify: `frontend/src/views/phase2/components/BookingConfirmDialog.vue`

**phase2.ts generateBooking:**
```typescript
generateBooking(fields: {
  // ... existing fields ...
  customs_names: string[]   // 新增
  gross_weight: string
  measurement: string
})
```

**BookingConfirmDialog.vue** — 改造为多行表格：
```vue
<!-- 货物 section -->
<div class="form-section-title">货物</div>
<el-table :data="goodsRows" border size="small">
  <el-table-column label="报关名称" prop="customsName" />
  <el-table-column label="毛重(KGS)">
    <template #default="{ row, $index }">
      <el-input v-model="row.grossWeight" :disabled="$index > 0" />
    </template>
  </el-table-column>
  <el-table-column label="尺码(CBM)">
    <template #default="{ row, $index }">
      <el-input v-model="row.measurement" :disabled="$index > 0" />
    </template>
  </el-table-column>
</el-table>
```

```typescript
interface GoodsRow {
  customsName: string
  grossWeight: string
  measurement: string
}

const goodsRows = ref<GoodsRow[]>([])

// 初始化：从 props.initialValues.customs_names 填充
watch(() => props.initialValues, (vals) => {
  const names = vals?.customs_names || []
  goodsRows.value = names.map((n: string) => ({ customsName: n, grossWeight: '', measurement: '' }))
  if (goodsRows.value.length) {
    goodsRows.value[0].grossWeight = vals?.gross_weight || ''
    goodsRows.value[0].measurement = vals?.measurement || ''
  }
}, { immediate: true })
```

**Phase2Workflow.vue** — `onBookingConfirm` 传递 customs_names：
```typescript
async function onBookingConfirm(fields: BookingForm) {
  const res = await phase2Api.generateBooking({
    ...fields,
    customs_names: goodsRows.value.map(r => r.customsName),  // 新增
    template_type: 'xlsx',
  })
  // ...
}
```

- [ ] **Step 1: 修改 phase2.ts** — `generateBooking` 添加 `customs_names` 参数

- [ ] **Step 2: 修改 BookingConfirmDialog.vue** — 改为多行表格，支持最多 6 行

- [ ] **Step 3: 修改 Phase2Workflow.vue** — 构造 `customs_names` 数组传递给 BookingConfirmDialog

- [ ] **Step 4: 端到端测试** — Phase 1 解析 → 汇数据 → Phase 2 订舱单，观察多行报关名称是否正确

---

## Task 7: 订舱单模板改造（DESC1-DESC6）

**Files:**
- Create: `references/长晟出口海运BOOKING模板-多产品.xlsx`（用户手动创建，占位符为 {{DESC1}} {{DESC2}} ... {{DESC6}}）

**模板占位符布局（建议）：**

| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| {{SHIPPER}} | ... | ... | ... | ... | ... | ... | ... |
| {{CONSIGNEE}} | ... | ... | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |
| **货名** | **毛重** | **尺码** | | | | | |
| {{DESC1}} | | | ← 毛重/尺码 | | | | |
| {{DESC2}} | | | | | | | |
| {{DESC3}} | | | | | | | |
| {{DESC4}} | | | | | | | |
| {{DESC5}} | | | | | | | |
| {{DESC6}} | | | | | | | |
| **{{GROSS_WEIGHT}}** | | | | | | | |
| **{{MEASUREMENT}}** | | | | | | | |

- [ ] **Step 1: 用户手动创建模板** — 基于原模板，添加 DESC2-DESC6 占位符到货名列

- [ ] **Step 2: 修改 config.py** — 添加 `booking_multi` 模板配置指向新模板

- [ ] **Step 3: 修改 document_service.py** — `fill_booking_template` 读取新模板文件

---

## Task 8: 汇数据保存时透传已补全数据

**Files:**
- Modify: `backend/app/api/v1/dashboard.py` 或 `save_service.py`

汇数据保存时，直接使用 ParsedOrderSchema 中已补全的 `customs_name` / `product_code` / `components` / `product_appearance` 写入 OrderPiRecord（无需重复查询 JSON）。

- [ ] **Step 1: 检查 save_service.py** — 确认 OrderPiRecord 保存逻辑透传了 customs_name 等字段

- [ ] **Step 2: 如需要修改** — 在保存时将 `item.customs_name` → `order_pi_record.customs_name`

---

## 验证清单

- [ ] 启动 Backend，无 `customs_codes.json` 加载报错
- [ ] Phase 1 粘贴数据，解析预览中每条 item 有 `customs_match_status`（matched/filled/conflict/not_found）
- [ ] 故意填错 internal_code，conflict 状态显示两方差异
- [ ] 汇数据后，数据看板中 customs_name / product_code / components 有值
- [ ] Phase 2 订舱单对话框显示多行报关名称（最多6行）
- [ ] OnlyOffice 渲染的 xlsx 中 DESC1-DESC6 正确填充

---

**Plan complete.**