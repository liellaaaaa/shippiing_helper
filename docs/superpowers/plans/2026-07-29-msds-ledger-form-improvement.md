# MSDS 产品台账表单优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 MSDS 产品台账的「新配方导入」编辑卡和「新增/编辑配方」对话框：成分改为表格展示（组分/CAS NO./含量）、所有字段必填、删除内部编码字段。

**Architecture:** 后端模型删列 → 迁移文件 → API schema 调整 → service 清理 → 前端类型清理 → 前端 UI 改造。每步可独立验证。

**Tech Stack:** Python FastAPI + SQLAlchemy + SQLite, Vue 3 + Element Plus + TypeScript

---

### Task 1: 后端模型 — 删除 internal_code，字段改为 NOT NULL

**Files:**
- Modify: `backend/app/models/msds_ledger.py`
- Create: `backend/migrations/014_make_ledger_fields_required.py`

- [ ] **Step 1: 修改 ORM 模型**

在 `backend/app/models/msds_ledger.py` 中：
- 删除 `internal_code` 列定义
- `customs_name` 加 `nullable=False`
- `appearance` 加 `nullable=False`
- `ion_type` 加 `nullable=False`
- `ph` 加 `nullable=False`
- `composition` 加 `nullable=False`

```python
class MsdsLedger(Base):
    __tablename__ = "msds_product_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customs_name = Column(String(200), nullable=False, index=True)
    appearance = Column(String(500), nullable=False)
    ion_type = Column(String(50), nullable=False)
    ph = Column(String(50), nullable=False)
    composition = Column(JSON, nullable=False)
    product_name_en = Column(String(200))
    appearance_en = Column(String(500))
    ion_type_en = Column(String(50))
    version = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

- [ ] **Step 2: 创建迁移文件**

创建 `backend/migrations/014_make_ledger_fields_required.py`：

```python
"""Migration 014: make ledger fields NOT NULL, drop internal_code."""
from sqlalchemy import text
from app.database import engine


def migrate():
    with engine.connect() as conn:
        # SQLite doesn't support DROP COLUMN directly before 3.35.5,
        # but supports ALTER TABLE ... DROP COLUMN since 3.35.0.
        # We use the supported approach:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS msds_product_ledger_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customs_name VARCHAR(200) NOT NULL,
                appearance VARCHAR(500) NOT NULL,
                ion_type VARCHAR(50) NOT NULL,
                ph VARCHAR(50) NOT NULL,
                composition JSON NOT NULL DEFAULT '[]',
                product_name_en VARCHAR(200),
                appearance_en VARCHAR(500),
                ion_type_en VARCHAR(50),
                version INTEGER DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        conn.execute(text("""
            INSERT INTO msds_product_ledger_new (
                id, customs_name, appearance, ion_type, ph, composition,
                product_name_en, appearance_en, ion_type_en,
                version, created_at, updated_at
            )
            SELECT
                id, COALESCE(customs_name, ''), COALESCE(appearance, ''),
                COALESCE(ion_type, ''), COALESCE(ph, ''),
                COALESCE(composition, '[]'),
                product_name_en, appearance_en, ion_type_en,
                version, created_at, updated_at
            FROM msds_product_ledger
        """))
        conn.execute(text("DROP TABLE msds_product_ledger"))
        conn.execute(text("ALTER TABLE msds_product_ledger_new RENAME TO msds_product_ledger"))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_msds_ledger_customs_name
            ON msds_product_ledger(customs_name)
        """))
        conn.commit()
        print("[migration] 014: msds_product_ledger columns updated")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 3: 运行迁移**

```bash
cd backend && python -m migrations.014_make_ledger_fields_required
```

预期输出：`[migration] 014: msds_product_ledger columns updated`

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/msds_ledger.py backend/migrations/014_make_ledger_fields_required.py
git commit -m "feat: remove internal_code from msds_ledger, make fields NOT NULL"
```

---

### Task 2: 后端 API Schema + Service — 删除 internal_code，字段必填

**Files:**
- Modify: `backend/app/api/v1/msds_ledger.py`
- Modify: `backend/app/services/msds_ledger_service.py`

- [ ] **Step 1: 修改 API Schema**

在 `backend/app/api/v1/msds_ledger.py` 中：

```python
class LedgerCreate(BaseModel):
    customs_name: str  # 去掉默认值，必填
    appearance: str
    ion_type: str
    ph: str
    composition: list = []  # 保留默认空列表
    product_name_en: str = ""
    appearance_en: str = ""
    ion_type_en: str = ""


class LedgerUpdate(BaseModel):
    customs_name: Optional[str] = None
    appearance: Optional[str] = None
    ion_type: Optional[str] = None
    ph: Optional[str] = None
    composition: Optional[list] = None
    product_name_en: Optional[str] = None
    appearance_en: Optional[str] = None
    ion_type_en: Optional[str] = None
```

修改 `_to_dict()` 删除 `internal_code` 行：

```python
def _to_dict(item):
    return {
        "id": item.id,
        "customs_name": item.customs_name or "",
        "appearance": item.appearance or "",
        "ion_type": item.ion_type or "",
        "ph": item.ph or "",
        "composition": item.composition or [],
        "product_name_en": item.product_name_en or "",
        "appearance_en": item.appearance_en or "",
        "ion_type_en": item.ion_type_en or "",
        "version": item.version or 1,
    }
```

- [ ] **Step 2: 修改 Service 层**

在 `backend/app/services/msds_ledger_service.py` 中：

`create_ledger()` — 删除 `internal_code` 行：
```python
def create_ledger(self, db: Session, data: dict) -> MsdsLedger:
    now = datetime.utcnow()
    data = _auto_fill_english(data)
    ledger = MsdsLedger(
        customs_name=data.get("customs_name", ""),
        appearance=data.get("appearance", ""),
        ion_type=data.get("ion_type", ""),
        ph=data.get("ph", ""),
        composition=data.get("composition", []),
        product_name_en=data.get("product_name_en", ""),
        appearance_en=data.get("appearance_en", ""),
        ion_type_en=data.get("ion_type_en", ""),
        version=1, created_at=now, updated_at=now,
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return ledger
```

`update_ledger()` — 从字段列表删除 `"internal_code"`：
```python
for field in ["customs_name", "appearance", "ion_type", "ph", "composition", "product_name_en", "appearance_en", "ion_type_en"]:
    if field in data:
        setattr(ledger, field, data[field])
```

`list_ledger()` — 删除 `internal_code` 参数和过滤：
```python
def list_ledger(self, db: Session, keyword: Optional[str] = None) -> list:
    query = db.query(MsdsLedger)
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            (MsdsLedger.customs_name.like(like_pattern)) |
            (MsdsLedger.product_name_en.like(like_pattern))
        )
    return query.order_by(MsdsLedger.customs_name).all()
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/v1/msds_ledger.py backend/app/services/msds_ledger_service.py
git commit -m "feat: update msds ledger API schema and service"
```

---

### Task 3: 前端类型 — 删除 internal_code

**Files:**
- Modify: `frontend/src/api/msds-ledger.ts`

- [ ] **Step 1: 删除 `internal_code` 字段**

```typescript
export interface MsdsLedgerItem {
  id: number
  customs_name: string
  appearance: string
  ion_type: string
  ph: string
  composition: CompositionItem[]
  product_name_en: string
  appearance_en: string
  ion_type_en: string
  version: number
}
```

`list` 方法的参数也删除 `internal_code`：
```typescript
list(params?: { keyword?: string }) {
  return apiClient.get<{ items: MsdsLedgerItem[] }>('/msds-ledger', { params })
},
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/msds-ledger.ts
git commit -m "feat: remove internal_code from msds-ledger TypeScript types"
```

---

### Task 4: 前端组件 — 新配方编辑卡：成分改为表格

**Files:**
- Modify: `frontend/src/views/phase2/components/MSDSGeneratorDialog.vue`

- [ ] **Step 1: 改造新配方编辑卡（`newFormulas`）的成分显示**

**改动内容（lines 40-73）**：

当前成分 textarea：
```html
<div class="formula-edit-row">
  <div class="formula-field formula-field-wide">
    <label>成分</label>
    <el-input v-model="formula.customs_ingredients" size="small" type="textarea" :rows="2" />
  </div>
</div>
```

改为成分表（表格形式）：
```html
<div class="formula-edit-row">
  <div class="formula-field formula-field-wide">
    <label>成分表</label>
    <table class="composition-table">
      <thead>
        <tr>
          <th style="width:40%">组分</th>
          <th style="width:35%">CAS NO.</th>
          <th style="width:15%">含量</th>
          <th style="width:10%">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(comp, ci) in formula.composition" :key="ci">
          <td><el-input v-model="comp.component_cn" size="small" placeholder="必填" /></td>
          <td><el-input v-model="comp.cas" size="small" placeholder="如 123-45-6" /></td>
          <td><el-input v-model="comp.percentage" size="small" placeholder="如 30%" /></td>
          <td><el-button size="small" type="danger" link @click="removeFormulaComp(formula, ci)">删除</el-button></td>
        </tr>
      </tbody>
    </table>
    <el-button size="small" @click="addFormulaComp(formula)">+ 添加成分</el-button>
    <div v-if="formula.composition.length === 0" class="form-error">至少添加一行成分</div>
  </div>
</div>
```

- [ ] **Step 2: 添加成分表操作方法**

在 `<script>` 部分的 methods 区域添加：

```typescript
function addFormulaComp(formula: any) {
  if (!formula.composition) {
    formula.composition = []
  }
  formula.composition.push({ component_cn: '', component_en: '', cas: '', percentage: '' })
}

function removeFormulaComp(formula: any, idx: number) {
  formula.composition.splice(idx, 1)
}
```

- [ ] **Step 3: 修改 `loadLedger()` 中的新配方初始化逻辑**

在 `loadLedger()` 中（约 line 330），创建 `newFormulas` push 时，提前解析 composition：

```typescript
if (!exists) {
  const parsedComp = parseIngredients(orderItem.customs_ingredients || '')
  newFormulas.value.push({
    ...orderItem,
    ion_type: '',
    ph: generateRandomPh(),
    composition: parsedComp,
  })
}
```

同时从 push 对象中删除原来的 `customs_ingredients` 字段（不再需要，因为已解析到 composition）。

- [ ] **Step 4: 修改 `importAllFormulas()`**

当前 importAllFormulas 中：
```typescript
const ingredients = formula.customs_ingredients || ''
const composition = parseIngredients(ingredients)
```

改为直接从 formula.composition 取值：
```typescript
// composition already parsed on init; use directly
const composition = formula.composition || []
```

- [ ] **Step 5: 添加 CSS 样式**

在 `<style>` 末尾添加：

```css
.composition-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 8px;
}
.composition-table th {
  text-align: left;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color-light);
}
.composition-table td {
  padding: 4px 4px;
}
.form-error {
  font-size: 12px;
  color: var(--el-color-danger);
  margin-top: 4px;
}
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/views/phase2/components/MSDSGeneratorDialog.vue
git commit -m "feat: new formula composition table with component/cas/percentage columns"
```

---

### Task 5: 前端组件 — 新增/编辑表单：删除 internal_code + 加表格标题 + 必填校验

**Files:**
- Modify: `frontend/src/views/phase2/components/MSDSGeneratorDialog.vue`

- [ ] **Step 1: 删除「内部编码」输入项**

删除 lines 122-124：
```html
<!-- 删除以下整个 el-form-item -->
<el-form-item label="内部编码">
  <el-input v-model="formData.internal_code" placeholder="如 CF463" />
</el-form-item>
```

- [ ] **Step 2: 成分表加列标题 + 为各字段加 el-form-item 和 rules**

在 `el-dialog` 的新增/编辑表单区域内（lines 120-155）：
- 使用 `el-form` 的 `:rules` 和 `ref="formRef"` 来管理校验
- 报关名称、外观、离子性、pH值加 `el-form-item` 的 `required` 属性
- 成分表区域加列标题

```html
<el-dialog v-model="showForm" :title="editingItem ? '编辑配方' : '新增配方'" width="700px" append-to-body>
  <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
    <el-form-item label="报关名称" prop="customs_name">
      <el-input v-model="formData.customs_name" placeholder="中文报关名称" />
    </el-form-item>
    <el-form-item label="外观" prop="appearance">
      <el-input v-model="formData.appearance" />
    </el-form-item>
    <el-form-item label="离子性" prop="ion_type">
      <el-select v-model="formData.ion_type" placeholder="请选择">
        <el-option label="阳离子" value="阳离子" />
        <el-option label="阴离子" value="阴离子" />
        <el-option label="非离子" value="非离子" />
      </el-select>
    </el-form-item>
    <el-form-item label="pH值" prop="ph">
      <el-input v-model="formData.ph" placeholder="如 5.0-7.0" />
    </el-form-item>
    <el-form-item label="成分表" prop="composition">
      <table class="composition-table">
        <thead>
          <tr>
            <th style="width:40%">组分</th>
            <th style="width:35%">CAS NO.</th>
            <th style="width:15%">含量</th>
            <th style="width:10%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in formData.composition" :key="idx">
            <td><el-input v-model="item.component_cn" placeholder="必填" size="small" /></td>
            <td><el-input v-model="item.cas" placeholder="如 123-45-6" size="small" /></td>
            <td><el-input v-model="item.percentage" placeholder="如 30%" size="small" /></td>
            <td><el-button type="danger" link @click="removeComposition(idx)">删除</el-button></td>
          </tr>
        </tbody>
      </table>
      <el-button size="small" @click="addComposition()">+ 添加成分</el-button>
      <div v-if="formData.composition.length === 0" class="form-error">至少添加一行成分</div>
    </el-form-item>
  </el-form>
</el-dialog>
```

- [ ] **Step 3: 添加校验规则和 `formRef` 引用**

在 `<script setup>` 中：

```typescript
import { type FormInstance, type FormRules } from 'element-plus'

const formRef = ref<FormInstance>()

const formRules: FormRules = {
  customs_name: [{ required: true, message: '请输入报关名称', trigger: 'blur' }],
  appearance: [{ required: true, message: '请输入外观', trigger: 'blur' }],
  ion_type: [{ required: true, message: '请选择离子性', trigger: 'change' }],
  ph: [{ required: true, message: '请输入pH值', trigger: 'blur' }],
  composition: [{
    validator: (_rule: any, value: any[], callback: any) => {
      if (!value || value.length === 0) {
        callback(new Error('至少添加一行成分'))
      } else if (value.some(v => !v.component_cn?.trim())) {
        callback(new Error('每行成分的「组分」为必填'))
      } else {
        callback()
      }
    },
    trigger: 'change',
  }],
}
```

- [ ] **Step 4: 修改 `onSaveForm()` 加入校验**

```typescript
async function onSaveForm() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  try {
    if (editingItem.value) {
      await msdsLedgerApi.update(editingItem.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await msdsLedgerApi.create(formData.value)
      ElMessage.success('创建成功')
    }
    showForm.value = false
    loadLedger()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || ''))
  }
}
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/phase2/components/MSDSGeneratorDialog.vue
git commit -m "feat: remove internal_code, add form validation and composition table headers"
```

---

### Task 6: 前端组件 — 清理其他 internal_code 逻辑

**Files:**
- Modify: `frontend/src/views/phase2/components/MSDSGeneratorDialog.vue`

- [ ] **Step 1: 清理 `formData` 初始化（lines 228-238 和 386-396）**

从 `formData` 初始值删除 `internal_code`：
```typescript
const formData = ref({
  customs_name: '',
  appearance: '',
  ion_type: '',
  ph: '',
  product_name_en: '',
  appearance_en: '',
  ion_type_en: '',
  composition: [] as CompositionItem[],
})
```

同样的改动在 `showAddDialog()` 中。

- [ ] **Step 2: 清理 `showEditDialog()`**

从 `showEditDialog()` 删除：
```typescript
internal_code: selectedItem.value.internal_code,
```

- [ ] **Step 3: 清理 `loadLedger()` 中 orderItemsWithIngredients 的 `internal_code`**

从 lines 264-268 删除：
```typescript
internal_code: it.internal_code || '',
```

- [ ] **Step 4: 清理 `importAllFormulas()` 中的 `internal_code` 备用查找外观逻辑**

从 `importAllFormulas()` 删除以下代码块（lines 519-525）：
```typescript
if (!appearance && formula.internal_code) {
  const orderItem = orderItemsWithIngredients.value.find((item: any) =>
    item.internal_code === formula.internal_code
  )
  if (orderItem && orderItem.appearance) {
    appearance = orderItem.appearance
  }
}
```

以及 `create` 调用中删除 `internal_code: formula.internal_code || ''`：
```typescript
await msdsLedgerApi.create({
  customs_name: formula.customs_name,
  appearance: appearance,
  ion_type: formula.ion_type || '',
  ph: formula.ph || '',
  composition: composition,
})
```

- [ ] **Step 5: 清理 `autoSelectMatchingItems()` 中的 `internal_code` 匹配**

删除 Priority 1 的 internal_code 匹配块（lines 682-687）：
```typescript
// Priority 1: match by internal_code (most reliable)
if (orderItem.internal_code) {
  matched = candidates.find(
    (item: MsdsLedgerItem) => item.internal_code === orderItem.internal_code
  )
}
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/views/phase2/components/MSDSGeneratorDialog.vue
git commit -m "feat: cleanup internal_code references in MSDS dialog logic"
```

---

### Task 7: 验证 — 启动前后端并检查

- [ ] **Step 1: 启动后端和前端**

```bash
# 终端1 - backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2 - frontend
cd frontend && npm run dev
```

- [ ] **Step 2: 检查迁移是否成功**

访问 `http://localhost:8000/api/v1/msds-ledger`，确认返回数据中不再包含 `internal_code` 字段。

- [ ] **Step 3: 检查前端的三个入口**

1. 打开 Phase2 工作流 → 点击"MSDS生成器"
2. 确认台账主表格不再显示内部编码
3. 确认新配方编辑卡中成分以表格展示（组分/CAS NO./含量）
4. 点击"新增配方" → 确认无内部编码字段、成分表有列标题、字段有红色必填标记
5. 尝试保存空表单 → 确认校验拦截
6. 导入新配方 → 确认成分被正确解析为表格行
