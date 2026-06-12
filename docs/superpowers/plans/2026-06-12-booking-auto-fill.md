# 订舱单自动填充实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户点击"订舱单" → 弹出核对对话框 → 确认后自动填充 Excel 模板 → OnlyOffice 渲染

**Architecture:**
- 后端：`fill_booking_template(fields)` 扫描 `{{FIELD_NAME}}` 单元格并替换为实际值；`generate_booking(fields)` 接收字段字典
- 前端：`BookingConfirmDialog.vue` 核对对话框；`confirmGenerateBooking()` 改为 POST 字段对象到后端

**Tech Stack:** openpyxl, python-docx (templates), FastAPI POST body, Vue 3 + Element Plus

---

## 文件改动总览

| 文件 | 改动 |
|------|------|
| `backend/app/core/config.py` | 新增 `BOOKING_MARKED` 指向已标记模板 |
| `backend/app/services/document_service.py` | 新增 `fill_booking_template()` 和 `generate_booking(fields)` |
| `backend/app/api/v1/documents.py` | `generate_booking` 改为 POST，接收 JSON body |
| `frontend/src/api/phase2.ts` | `generateBooking()` 改为 POST，接收字段对象 |
| `frontend/src/views/phase2/Phase2Workflow.vue` | 替换现有 Booking Dialog 为 `BookingConfirmDialog` |
| `frontend/src/views/phase2/components/BookingConfirmDialog.vue` | 新增核对对话框组件 |

---

## Task 1: 后端 - config.py 添加已标记模板路径

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: 添加已标记模板路径**

```python
# 在 TEMPLATES 字典中添加 booking_marked 条目
TEMPLATES = {
    ...
    "booking_marked": str(ROOT / "references" / "长晟出口海运BOOKING模板-已标记.xlsx"),
}
```

---

## Task 2: 后端 - document_service.py 添加 fill_booking_template

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 添加 fill_booking_template 函数（在 generate_booking 方法之前）**

在 `DocumentService` 类中添加以下方法：

```python
def fill_booking_template(self, fields: dict, template_type: str = "xlsx") -> bytes:
    """
    打开已标记的 Booking 模板，扫描 {{FIELD_NAME}} 单元格，替换为实际值，返回填充后的 xlsx 字节。
    fields: dict，键为 {{FIELD_NAME}}（不带花括号），值为字符串
    """
    import openpyxl
    from io import BytesIO

    template_key = "booking_marked" if template_type == "xlsx" else "booking"
    template_path = TEMPLATES.get(template_key, TEMPLATES["booking"])

    if template_type != "xlsx":
        # .xls 转 .xlsx（复用现有逻辑）
        content_xlsx = convert_xls_to_xlsx(template_path)
        wb = openpyxl.load_workbook(BytesIO(content_xlsx))
    else:
        wb = openpyxl.load_workbook(template_path)

    ws = wb.active

    # 扫描所有单元格，替换 {{FIELD_NAME}} 标记
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                marker_match = re.match(r"^\{\{(\w+)\}\}$", cell.value.strip())
                if marker_match:
                    field_key = marker_match.group(1)
                    if field_key in fields:
                        cell.value = fields[field_key]
                    else:
                        cell.value = ""  # 未提供的字段清空标记

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out.read()
```

注意：需要在文件顶部确保 `import re` 已存在（检查是否已有，没有则添加）。

- [ ] **Step 2: 修改 generate_booking 方法**

将现有的 `generate_booking(self, order_id: int, template_type: str = "xls")` 改为：

```python
def generate_booking(self, fields: dict | None = None, template_type: str = "xlsx") -> Tuple[bytes, str, str]:
    """
    生成订舱单：支持自动填充字段。
    fields: 可选，键为字段名（无花括号），值未提供则返回空白模板。
    """
    if fields:
        content_xlsx = self.fill_booking_template(fields, template_type)
    else:
        # 兼容无参调用（空白模板）
        template_key = f"booking_{template_type}" if template_type == "xlsx" else "booking"
        template_path = TEMPLATES.get(template_key, TEMPLATES["booking"])
        if template_type == "xlsx" and os.path.exists(template_path):
            with open(template_path, "rb") as f:
                content_xlsx = f.read()
        else:
            content_xlsx = convert_xls_to_xlsx(template_path)

    doc_key = f"booking_{int(time.time())}"
    return content_xlsx, doc_key, base64.b64encode(content_xlsx).decode()
```

---

## Task 3: 后端 - documents.py 接口改为 POST

**Files:**
- Modify: `backend/app/api/v1/documents.py:15-33`

- [ ] **Step 1: 修改 generate_booking 接口**

将 `generate_booking` 从 GET 改为 POST，接收 JSON body：

```python
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

class BookingFields(BaseModel):
    shipper: str = ""
    consignee: str = ""
    notify: str = ""
    cut_off_date: str = ""
    place_of_receipt: str = ""
    pol: str = ""
    pod: str = ""
    place_of_delivery: str = ""
    marks: str = ""
    no_kind_pkg: str = ""
    desc: str = ""
    gross_weight: str = ""
    measurement: str = ""
    template_type: str = "xlsx"

@router.post("/booking")
async def generate_booking(fields: BookingFields = Body(...)):
    """
    生成订舱单，字段通过 JSON body 传入，自动填充到模板。
    """
    svc = DocumentService()
    # 将字段名转为 fill_booking_template 期望的格式（键无花括号）
    fields_dict = {
        "SHIPPER": fields.shipper,
        "CONSIGNEE": fields.consignee,
        "NOTIFY": fields.notify,
        "CUT_OFF_DATE": fields.cut_off_date,
        "PLACE_OF_RECEIPT": fields.place_of_receipt,
        "POL": fields.pol,
        "POD": fields.pod,
        "PLACE_OF_DELIVERY": fields.place_of_delivery,
        "MARKS": fields.marks,
        "NO_KIND_PKG": fields.no_kind_pkg,
        "DESC": fields.desc,
        "GROSS_WEIGHT": fields.gross_weight,
        "MEASUREMENT": fields.measurement,
    }
    content, doc_key, _ = svc.generate_booking(fields_dict, fields.template_type)
    token, config, safe_key = oo_svc.create_config(doc_key, "xlsx")
    _save_doc_to_db(doc_key, "booking", content, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }
```

注意：删除原来的 GET 路由。

---

## Task 4: 前端 - phase2.ts 改为 POST

**Files:**
- Modify: `frontend/src/api/phase2.ts`

- [ ] **Step 1: 修改 generateBooking 函数**

```typescript
generateBooking(fields: {
  shipper: string
  consignee: string
  notify: string
  cut_off_date: string
  place_of_receipt: string
  pol: string
  pod: string
  place_of_delivery: string
  marks: string
  no_kind_pkg: string
  desc: string
  gross_weight: string
  measurement: string
  template_type?: 'xls' | 'xlsx'
}) {
  return axios.post('/api/v1/documents/booking', fields)
},
```

---

## Task 5: 前端 - 新增 BookingConfirmDialog.vue

**Files:**
- Create: `frontend/src/views/phase2/components/BookingConfirmDialog.vue`

- [ ] **Step 1: 编写对话框组件**

```vue
<template>
  <el-dialog
    v-model="visible"
    title="生成订舱单"
    width="640px"
    :append-to-body="true"
    class="booking-confirm-dialog"
    @closed="onClosed"
  >
    <el-form label-width="120px" label-position="left">
      <!-- 收发货 -->
      <div class="form-section-title">收发货</div>
      <el-form-item label="发货人">
        <el-input v-model="form.shipper" type="textarea" :rows="2" placeholder="公司名称+地址+TEL" />
      </el-form-item>
      <el-form-item label="收货人">
        <el-input v-model="form.consignee" type="textarea" :rows="2" placeholder="公司名称+地址+TEL" />
      </el-form-item>
      <el-form-item label="通知人">
        <el-input v-model="form.notify" type="textarea" :rows="2" placeholder="默认 SAME AS CONSIGNEE" />
      </el-form-item>

      <!-- 港口 -->
      <div class="form-section-title">港口</div>
      <el-form-item label="收货地">
        <el-input v-model="form.place_of_receipt" placeholder="如 GUANGZHOU,CHINA" />
      </el-form-item>
      <el-form-item label="装货港">
        <el-input v-model="form.pol" placeholder="如 GUANGZHOU,CHINA" />
      </el-form-item>
      <el-form-item label="卸货港">
        <el-input v-model="form.pod" placeholder="如 LAT KRABANG,THAILAND" />
      </el-form-item>
      <el-form-item label="交货地">
        <el-input v-model="form.place_of_delivery" placeholder="如 LAT KRABANG,THAILAND" />
      </el-form-item>
      <el-form-item label="截关日期">
        <el-input v-model="form.cut_off_date" placeholder="货代提供" />
      </el-form-item>

      <!-- 货物 -->
      <div class="form-section-title">货物</div>
      <el-form-item label="件数/柜型">
        <el-input v-model="form.no_kind_pkg" placeholder="如 4 PALLETS" />
      </el-form-item>
      <el-form-item label="货名">
        <el-input v-model="form.desc" placeholder="产品中文名" />
      </el-form-item>
      <el-form-item label="毛重">
        <el-input v-model="form.gross_weight" placeholder="如 2600 KGS">
          <template #append>KGS</template>
        </el-input>
      </el-form-item>
      <el-form-item label="尺码">
        <el-input v-model="form.measurement" placeholder="如 4.64">
          <template #append>CBM</template>
        </el-input>
      </el-form-item>
      <el-form-item label="唛头">
        <el-input v-model="form.marks" placeholder="可留空" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onConfirm">确认生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue: boolean
  initialValues?: Partial<typeof defaultForm>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [fields: typeof defaultForm]
}>()

const defaultForm = () => ({
  shipper: '',
  consignee: '',
  notify: 'SAME AS CONSIGNEE',
  cut_off_date: '',
  place_of_receipt: 'GUANGZHOU,CHINA',
  pol: 'GUANGZHOU,CHINA',
  pod: '',
  place_of_delivery: '',
  marks: '',
  no_kind_pkg: '',
  desc: '',
  gross_weight: '',
  measurement: '',
})

const form = ref(defaultForm())
const loading = ref(false)
const visible = ref(props.modelValue)

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    form.value = {
      ...defaultForm(),
      ...(props.initialValues || {}),
      // 特殊默认值
      notify: props.initialValues?.notify || 'SAME AS CONSIGNEE',
      place_of_receipt: props.initialValues?.place_of_receipt || 'GUANGZHOU,CHINA',
      pol: props.initialValues?.pol || 'GUANGZHOU,CHINA',
    }
    // 卸货港默认值同装货港
    if (!props.initialValues?.pod && props.initialValues?.port) {
      form.value.pod = props.initialValues.port
      form.value.place_of_delivery = props.initialValues.port
    }
  }
})

watch(visible, (v) => emit('update:modelValue', v))

function onConfirm() {
  loading.value = true
  emit('confirm', { ...form.value })
  loading.value = false
  visible.value = false
}

function onClosed() {
  form.value = defaultForm()
}
</script>

<style scoped>
.form-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin: 12px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #dcdfe6;
}
</style>
```

---

## Task 6: 前端 - Phase2Workflow.vue 替换 Booking Dialog

**Files:**
- Modify: `frontend/src/views/phase2/Phase2Workflow.vue`

- [ ] **Step 1: 导入 BookingConfirmDialog**

在 `<script setup>` 的 import 部分添加：
```typescript
import BookingConfirmDialog from './components/BookingConfirmDialog.vue'
```

- [ ] **Step 2: 替换模板中的 Booking Dialog**

删除现有的 Booking Dialog（带模板格式选择的 el-dialog），替换为：
```vue
<BookingConfirmDialog
  v-model="showBookingDialog"
  :initial-values="bookingInitialValues"
  @confirm="onBookingConfirm"
/>
```

- [ ] **Step 3: 添加 bookingInitialValues 计算属性**

在 `<script setup>` 中添加：
```typescript
const bookingInitialValues = computed(() => ({
  consignee: currentOrderInfo.value.consignee,
  port: currentOrderInfo.value.port,
  desc: currentOrderInfo.value.product_cn,
  gross_weight: currentOrderInfo.value.gross_weight_kg,
  measurement: currentOrderInfo.value.volume_cbm,
}))

async function onBookingConfirm(fields: typeof defaultForm) {
  try {
    const res = await phase2Api.generateBooking({
      ...fields,
      template_type: 'xlsx',
    })
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('订舱单生成失败: ' + (e.message || ''))
  }
}
```

注意：`confirmGenerateBooking` 函数可以删除或保留（看是否还有其他地方调用）。`showBookingDialog` 行为改为由 `BookingConfirmDialog` 的 `v-model` 控制。

---

## Task 7: 验证测试

**Files:**
- Test: 直接在浏览器手动测试

- [ ] **Step 1: 启动后端和前端**

```bash
# 后端
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev
```

- [ ] **Step 2: 手动测试流程**

1. 选一个有数据的订单（左侧汇集栏有内容）
2. 点击"订舱单"按钮，弹出核对对话框
3. 检查初始值：收货人、卸货港、货名、毛重、尺码是否从左侧带入
4. 修改任意字段，点击"确认生成"
5. OnlyOffice 打开后检查各单元格是否被正确填充（不再是 `{{FIELD}}` 标记）
6. 导出文件，检查文件名是否正确

---

## 字段名映射表（API body → 模板标记）

| API body 字段 | 模板标记 | 含义 |
|--------------|---------|------|
| `shipper` | `{{SHIPPER}}` | 发货人 |
| `consignee` | `{{CONSIGNEE}}` | 收货人 |
| `notify` | `{{NOTIFY}}` | 通知人 |
| `cut_off_date` | `{{CUT_OFF_DATE}}` | 截关日期 |
| `place_of_receipt` | `{{PLACE_OF_RECEIPT}}` | 收货地 |
| `pol` | `{{POL}}` | 装货港 |
| `pod` | `{{POD}}` | 卸货港 |
| `place_of_delivery` | `{{PLACE_OF_DELIVERY}}` | 交货地 |
| `marks` | `{{MARKS}}` | 唛头 |
| `no_kind_pkg` | `{{NO_KIND_PKG}}` | 件数/柜型 |
| `desc` | `{{DESC}}` | 货名 |
| `gross_weight` | `{{GROSS_WEIGHT}}` | 毛重 |
| `measurement` | `{{MEASUREMENT}}` | 尺码 |