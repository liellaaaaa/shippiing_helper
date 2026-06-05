# Phase 2 空白模板功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase 2 工作流中新增"空白模板"入口，允许不关联订单直接打开/编辑 Booking/LOI/MSDS 内置模板，并支持"我的模板"查看已保存的独立模板实例。

**Architecture:** 后端新增 `GET /documents/template/{type}` 端点，调用 `DocumentService.generate_template_instance()` 加载模板文件（不填充 marker），返回 doc_key + JWT token。前端工具栏新增"空白模板"下拉菜单；ReferencePanel 在无订单时显示 marker 说明；新增"MyDocumentsDrawer"抽屉列出所有 `order_id=NULL` 的模板实例。

**Tech Stack:** FastAPI + SQLAlchemy + OnlyOffice + Vue 3 + Element Plus

---

## 文件结构

```
backend/
├── app/services/document_service.py   # 新增 generate_template_instance()
└── app/api/v1/documents.py           # 新增 GET /documents/template/{type}

frontend/src/
├── constants/
│   └── template_markers.ts           # marker_map 静态配置
├── api/phase2.ts                     # 新增 listMyTemplates() + openBlankTemplate()
├── views/phase2/
│   └── components/
│       └── MyDocumentsDrawer.vue     # "我的模板"抽屉组件
└── views/phase2/Phase2Workflow.vue  # 工具栏新增"空白模板"下拉 + "我的模板"按钮
```

---

## Task 1: 后端 — DocumentService 新增 generate_template_instance()

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 添加 generate_template_instance() 方法**

在 `DocumentService` 类中添加以下方法，加载模板文件后直接返回字节流，不做任何 marker 填充：

```python
def generate_template_instance(self, template_type: str) -> Tuple[bytes, str, str]:
    """加载空白模板（不填充 marker），返回 (content, doc_key, encoded_content)。"""
    type_map = {
        "booking": ("booking", "xlsx"),
        "loi":     ("loi",     "docx"),
        "msds":    ("msds",    "docx"),
    }
    if template_type not in type_map:
        raise ValueError(f"Unknown template type: {template_type}")
    key_prefix, file_ext = type_map[template_type]
    template_path = TEMPLATES[template_type]
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    if file_ext == "xlsx":
        wb = openpyxl.load_workbook(template_path)
        buf = BytesIO()
        wb.save(buf)
        content = buf.getvalue()
    else:
        doc = Document(template_path)
        buf = BytesIO()
        doc.save(buf)
        content = buf.getvalue()

    timestamp = int(time.time())
    doc_key = f"{key_prefix}_template_{timestamp}"
    return content, doc_key, base64.b64encode(content).decode()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/document_service.py
git commit -m "feat(phase2): add generate_template_instance() for blank template loading"
```

---

## Task 2: 后端 — 新增 GET /documents/template/{type} 端点

**Files:**
- Modify: `backend/app/api/v1/documents.py`

- [ ] **Step 1: 在 documents.py 末尾添加新端点**

```python
@router.get("/template/{template_type}")
async def open_blank_template(template_type: str):
    if template_type not in ("booking", "loi", "msds"):
        return {"error": "Invalid template type"}
    svc = DocumentService()
    try:
        _, doc_key, _ = svc.generate_template_instance(template_type)
        file_ext = "xlsx" if template_type == "booking" else "docx"
        jwt_token = oo_svc.generate_jwt_token(doc_key, file_ext)
        config = oo_svc.build_editor_config(jwt_token, doc_key, file_ext)
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        return {**config, "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{doc_key}"}
    except FileNotFoundError as e:
        return {"error": str(e)}
```

**注意:** OnlyOffice callback (`onlyoffice.py`) 的 `extract_order_id_from_key()` 从 `doc_key` 提取 order_id。对于 `{type}_template_{timestamp}` 格式的 key，`extract_order_id_from_key` 返回 `None`，而 `ShipmentDoc.order_id` 字段是 nullable（`nullable=True`），所以 `order_id=NULL` 的记录可以正常存储。

- [ ] **Step 2: 提交**

```bash
git add backend/app/api/v1/documents.py
git commit -m "feat(phase2): add GET /documents/template/{type} endpoint for blank template opening"
```

---

## Task 3: 前端 — template_markers.ts 常量配置

**Files:**
- Create: `frontend/src/constants/template_markers.ts`

- [ ] **Step 1: 创建 template_markers.ts**

根据现有模板文件中的 marker 名称，创建静态配置：

```typescript
// frontend/src/constants/template_markers.ts
export const TEMPLATE_MARKERS: Record<string, Array<{ marker: string; label: string; description: string }>> = {
  booking: [
    { marker: "{{MARK_SHIPPER}}", label: "发货人", description: "发货人公司名称" },
    { marker: "{{MARK_PORT}}", label: "卸货港", description: "目的港/卸货港" },
    { marker: "{{MARK_GOODS_TABLE}}", label: "货物明细表", description: "品名/规格/毛重/体积表格起始位" },
  ],
  loi: [
    { marker: "{{shipper}}", label: "发货人", description: "发货人公司名称" },
    { marker: "{{consignee}}", label: "收货人", description: "收货人名称" },
    { marker: "{{consignee_address}}", label: "收货人地址", description: "收货人完整地址" },
    { marker: "{{port_of_discharge}}", label: "卸货港", description: "目的港" },
    { marker: "{{product_name_cn}}", label: "品名中文", description: "产品中文名称" },
    { marker: "{{product_name_en}}", label: "品名英文", description: "产品英文名称" },
    { marker: "{{hs_code}}", label: "H.S.编码", description: "海关编码" },
    { marker: "{{gross_weight}}", label: "毛重", description: "总毛重(kg)" },
    { marker: "{{volume}}", label: "体积", description: "总体积(CBM)" },
    { marker: "{{date}}", label: "日期", description: "合同日期" },
  ],
  msds: [
    { marker: "{{product_name}}", label: "产品名称", description: "MSDS 产品名称" },
    { marker: "{{physical_form}}", label: "物理形态", description: "物理形态" },
    { marker: "{{ion_type}}", label: "离子类型", description: "离子/分子类型" },
    { marker: "{{ph}}", label: "pH值", description: "pH 值" },
  ],
}

export const TEMPLATE_TYPE_LABELS: Record<string, string> = {
  booking: "订舱单 (Booking)",
  loi: "LOI保函 (LOI)",
  msds: "MSDS物质安全表",
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/constants/template_markers.ts
git commit -m "feat(phase2): add TEMPLATE_MARKERS constant for marker reference display"
```

---

## Task 4: 前端 — Phase2Workflow 工具栏改造

**Files:**
- Modify: `frontend/src/views/phase2/Phase2Workflow.vue`

- [ ] **Step 1: 在 template 的工具栏 actions 区域新增空白模板下拉 + 我的模板按钮**

在 `toolbar-actions` 的三个按钮后面加入：

```html
<el-dropdown @command="(cmd: string) => openBlankTemplate(cmd)" trigger="click">
  <el-button size="small">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
      <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
    </svg>
    空白模板
    <el-icon class="el-icon--right"><arrow-down /></el-icon>
  </el-button>
  <template #dropdown>
    <el-dropdown-menu>
      <el-dropdown-item command="booking">📄 订舱单 Booking</el-dropdown-item>
      <el-dropdown-item command="loi">📝 LOI保函</el-dropdown-item>
      <el-dropdown-item command="msds">⚠️ MSDS物质安全表</el-dropdown-item>
    </el-dropdown-menu>
  </template>
</el-dropdown>

<el-button size="small" @click="showMyDocuments = true">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
  </svg>
  我的模板
</el-button>
```

- [ ] **Step 2: 在 script setup 中新增以下变量和函数**

```typescript
const showMyDocuments = ref(false)

async function openBlankTemplate(type: 'booking' | 'loi' | 'msds') {
  try {
    const res = await phase2Api.openBlankTemplate(type)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('模板打开失败: ' + (e.message || ''))
  }
}
```

- [ ] **Step 3: 在 template 的 `<DocumentEditor>` 后面新增 MyDocumentsDrawer**

```html
<MyDocumentsDrawer v-model="showMyDocuments" @open-doc="onOpenMyDoc" />
```

- [ ] **Step 4: 在 import 中新增组件引入**

```typescript
import MyDocumentsDrawer from './components/MyDocumentsDrawer.vue'
import { phase2Api } from '@/api/phase2'
import { ArrowDown } from '@element-plus/icons-vue'
```

- [ ] **Step 5: 新增 onOpenMyDoc 函数**

```typescript
function onOpenMyDoc(doc: any) {
  showMyDocuments.value = false
  currentDocKey.value = doc.doc_key
  currentConfig.value = {
    token: doc.token,
    documentServerUrl: currentConfig.value.documentServerUrl,
    documentKey: doc.doc_key,
    downloadUrl: `/api/v1/onlyoffice/download/${doc.doc_key}`,
  }
}
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/views/phase2/Phase2Workflow.vue
git commit -m "feat(phase2): add blank template dropdown and My Templates button to toolbar"
```

---

## Task 5: 前端 — phase2.ts 新增 API 方法

**Files:**
- Modify: `frontend/src/api/phase2.ts`

- [ ] **Step 1: 在 phase2Api 对象中添加两个新方法**

```typescript
openBlankTemplate(type: 'booking' | 'loi' | 'msds') {
  return axios.get(`/documents/template/${type}`)
},
listMyTemplates() {
  return axios.get('/documents/my-templates')
},
```

**注意:** `listMyTemplates()` 尚未在后端实现，将在 Task 6 中添加对应端点。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/phase2.ts
git commit -m "feat(phase2): add openBlankTemplate() and listMyTemplates() to phase2 API client"
```

---

## Task 6: 后端 — 新增 GET /documents/my-templates 端点

**Files:**
- Modify: `backend/app/api/v1/documents.py`

- [ ] **Step 1: 添加 my-templates 端点**

在 `documents.py` 末尾添加：

```python
@router.get("/my-templates")
async def list_my_templates():
    db = SessionLocal()
    try:
        docs = db.query(ShipmentDoc).filter(
            ShipmentDoc.order_id == None  # noqa: E711 — independent template instances
        ).order_by(desc(ShipmentDoc.created_at)).all()
        return [{
            "doc_key": d.doc_key,
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "version": d.version,
            "created_by": d.created_by,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        } for d in docs]
    finally:
        db.close()
```

**注意:** `order_id == None` 使用 SQLAlchemy `== None`（不是 Python 的 `is None`），SQLAlchemy 会正确翻译为 `IS NULL`。

- [ ] **Step 2: 提交**

```bash
git add backend/app/api/v1/documents.py
git commit -m "feat(phase2): add GET /documents/my-templates endpoint for listing saved template instances"
```

---

## Task 7: 前端 — MyDocumentsDrawer.vue 抽屉组件

**Files:**
- Create: `frontend/src/views/phase2/components/MyDocumentsDrawer.vue`

- [ ] **Step 1: 创建 MyDocumentsDrawer.vue**

```vue
<template>
  <el-drawer
    v-model="visible"
    title="我的模板"
    direction="rtl"
    size="400px"
    :append-to-body="true"
  >
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading"><loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else-if="!docs.length" class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
      <span>暂无已保存的模板</span>
      <span class="empty-hint">空白模板编辑后会保存在此</span>
    </div>

    <div v-else class="doc-list">
      <div
        v-for="doc in docs"
        :key="doc.doc_key"
        class="doc-item"
        @click="$emit('open-doc', doc)"
      >
        <div class="doc-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="doc.doc_type === 'booking'" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            <path v-else d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>
          </svg>
        </div>
        <div class="doc-info">
          <div class="doc-name">{{ doc.file_name }}</div>
          <div class="doc-meta">
            <el-tag size="small" type="info">{{ doc.doc_type }}</el-tag>
            <span class="doc-time">{{ formatDate(doc.created_at) }}</span>
          </div>
        </div>
        <div class="doc-open">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { phase2Api } from '@/api/phase2'
import { ElIcon } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'open-doc', doc: any): void }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const docs = ref<any[]>([])
const loading = ref(false)

watch(visible, async (open) => {
  if (!open) return
  loading.value = true
  docs.value = []
  try {
    const res = await phase2Api.listMyTemplates()
    docs.value = res.data || []
  } finally {
    loading.value = false
  }
})

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}
</script>

<style scoped>
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 200px;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}
.empty-hint { font-size: 11px; color: var(--el-text-color-placeholder); }
.doc-list { display: flex; flex-direction: column; }
.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  cursor: pointer;
  transition: background 0.15s;
}
.doc-item:hover { background: var(--el-fill-color-light); }
.doc-icon { color: var(--el-color-primary); flex-shrink: 0; }
.doc-info { flex: 1; min-width: 0; }
.doc-name { font-size: 13px; font-weight: 500; color: var(--el-text-color-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.doc-time { font-size: 11px; color: var(--el-text-color-placeholder); }
.doc-open { color: var(--el-text-color-placeholder); flex-shrink: 0; }
.doc-item:hover .doc-open { color: var(--el-color-primary); }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/phase2/components/MyDocumentsDrawer.vue
git commit -m "feat(phase2): add MyDocumentsDrawer component for listing saved template instances"
```

---

## Task 8: 前端 — ReferencePanel 无订单时显示 Marker 说明

**Files:**
- Modify: `frontend/src/views/phase2/components/ReferencePanel.vue`

- [ ] **Step 1: 在 import 中引入 TEMPLATE_MARKERS**

```typescript
import { TEMPLATE_MARKERS } from '@/constants/template_markers'
```

- [ ] **Step 2: 在 Phase1数据 tab 的 empty-state 后面新增 marker 说明区域**

当 `orderId` 为 `null` 时，在 Phase1数据 tab 的 `empty-state` 后显示 marker 说明：

```html
<div v-if="!orderId" class="marker-guide">
  <div class="marker-guide-header">
    <el-icon><tickets /></el-icon>
    <span>模板字段参考</span>
    <el-select v-model="selectedTemplateType" size="small" class="template-type-select">
      <el-option label="订舱单" value="booking" />
      <el-option label="LOI保函" value="loi" />
      <el-option label="MSDS" value="msds" />
    </el-select>
  </div>
  <div class="marker-table">
    <div class="marker-row marker-row--header">
      <span>字段名</span><span>含义</span>
    </div>
    <div
      v-for="m in currentMarkers"
      :key="m.marker"
      class="marker-row"
    >
      <code class="marker-code">{{ m.marker }}</code>
      <span>{{ m.label }} — {{ m.description }}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: 在 script 中新增相关变量**

```typescript
import { Tickets } from '@element-plus/icons-vue'

const selectedTemplateType = ref('booking')

const currentMarkers = computed(() => TEMPLATE_MARKERS[selectedTemplateType.value] || [])
```

- [ ] **Step 4: 新增 marker-guide 样式**

```css
/* ── Marker Guide ──────────────────────────────── */
.marker-guide {
  margin: 0 12px 12px;
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 8px;
  overflow: hidden;
}
.marker-guide-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.template-type-select { margin-left: auto; width: 100px; }
.marker-table { font-size: 11px; }
.marker-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  align-items: center;
}
.marker-row:last-child { border-bottom: none; }
.marker-row--header {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 11px;
  padding: 4px 12px;
}
.marker-code {
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-color-primary);
  font-size: 11px;
  background: var(--el-color-primary-light-9);
  padding: 1px 4px;
  border-radius: 3px;
}
```

**注意:** `!orderId` 的判断使用 `null` 和 `undefined` 的 falsy 特性，因为 `orderId` 的 TypeScript 类型是 `number | null`，当值为 `null` 时 `!orderId` 为 `true`。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/phase2/components/ReferencePanel.vue
git commit -m "feat(phase2): show marker reference guide in ReferencePanel when no order is selected"
```

---

## Task 9: 端到端联调测试

**Files:**
- No file changes — manual verification

- [ ] **Step 1: 启动后端**

```bash
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: Server starts without errors.

- [ ] **Step 2: 启动前端**

```bash
cd frontend && npm run dev
```

Expected: Vite dev server starts on port 5173.

- [ ] **Step 3: 测试空白模板打开**

Navigate to `/phase2` (document editor page). Click "空白模板" dropdown → select "订舱单 Booking".

Expected: OnlyOffice editor opens with a blank Booking template (unfilled markers visible). Document key contains `_template_` in the URL.

- [ ] **Step 4: 测试我的模板抽屉**

Click "我的模板" button.

Expected: Drawer opens on the right. If no templates saved yet, shows empty state message.

- [ ] **Step 5: 测试 Marker 说明显示**

In Phase2 page, with no order selected, expand "Phase1数据" tab.

Expected: Below the empty state, marker guide shows with template type selector and field list.

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "test: add end-to-end smoke tests for blank template feature"
```

---

## Self-Review Checklist

1. **Spec coverage:** All requirements from the confirmed design are implemented:
   - Blank template opening (Task 1, 2, 4, 5) ✅
   - My Templates drawer (Task 6, 7) ✅
   - Marker reference display (Task 3, 8) ✅
   - Tooltip naming (Task 4) ✅

2. **Placeholder scan:** No `TBD`, `TODO`, or placeholder steps found. All code is complete.

3. **Type consistency:** 
   - `generate_template_instance()` returns `Tuple[bytes, str, str]` matching other generate methods ✅
   - `doc_key` format `{type}_template_{timestamp}` ensures `extract_order_id_from_key` returns `None` ✅
   - `order_id == None` in SQLAlchemy query uses `==` (not `is`) for proper SQL translation ✅

4. **Callback compatibility:** `extract_order_id_from_key("booking_template_1749999999")` → `None` (parts[1] = "template" fails int conversion), `infer_doc_type("booking_template_xxx")` → `"booking"` ✅