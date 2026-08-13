# 申报要素台账重构 — 详细实现方案

## 一、需求分析

### 当前痛点
1. `elements_text` 是 `|` 分隔的扁平字符串，无法按字段查询/筛选
2. 不同 HS Code 有不同的申报要素字段，但当前结构无法体现这种差异
3. 无法在表格中动态展示每个 HS Code 对应的字段列
4. `hs_codes.json` 已有结构化数据（字段定义 + 产品要素值），但未被系统使用

### 目标
1. 每个 HS Code 有独立的字段定义列表
2. 每个产品（商品名称）有独立的要素值记录
3. 前端根据选中的 HS Code 动态渲染表格列
4. 支持新增产品、在线编辑要素值
5. 保持与 `document_service.py` 的后向兼容

---

## 二、数据库表结构设计（SQLite）

### 2.1 新增表：`hs_code_fields` — HS Code 字段定义

```sql
CREATE TABLE hs_code_fields (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_code       TEXT    NOT NULL,              -- 海关编码，如 "3403910000"
    field_name    TEXT    NOT NULL,              -- 字段名，如 "用途"、"成分含量"
    sort_order    INTEGER NOT NULL DEFAULT 0,    -- 字段排序（同一 hs_code 内）
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(hs_code, field_name)
);
CREATE INDEX idx_hs_code_fields_hs_code ON hs_code_fields(hs_code);
```

**设计说明：**
- 每行代表某个 HS Code 下的一个申报要素字段
- `sort_order` 控制字段在前端表格列中的显示顺序
- 唯一约束 `(hs_code, field_name)` 防止重复

### 2.2 新增表：`declaration_products` — 产品台账

```sql
CREATE TABLE declaration_products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_code         TEXT    NOT NULL,            -- 海关编码
    product_name    TEXT    NOT NULL,            -- 商品名称（如 "纺织助剂整理剂"）
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(hs_code, product_name)
);
CREATE INDEX idx_declaration_products_hs_code ON declaration_products(hs_code);
```

**设计说明：**
- 每行代表某个 HS Code 下的一个产品
- `(hs_code, product_name)` 唯一约束，同一 HS Code 下产品名不能重复

### 2.3 新增表：`declaration_values` — 要素值

```sql
CREATE TABLE declaration_values (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES declaration_products(id) ON DELETE CASCADE,
    field_name      TEXT    NOT NULL,            -- 对应 hs_code_fields.field_name
    field_value     TEXT    NOT NULL DEFAULT '', -- 要素值
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(product_id, field_name)
);
CREATE INDEX idx_declaration_values_product_id ON declaration_values(product_id);
```

**设计说明：**
- 每行存储一个产品的一个字段值
- `(product_id, field_name)` 唯一约束，同一产品同一字段只有一个值
- 外键 `product_id → declaration_products.id`，级联删除

### 2.4 保留旧表

`declaration_elements` 表保留不删除，原因：
1. `CustomsDeclarationService` 和 `document_service.py` 依赖它
2. 迁移完成后，旧表作为只读备份
3. 后续可逐步将 `document_service.py` 切换到新表

---

## 三、数据迁移方案

### 3.1 迁移脚本：`backend/migrations/019_refactor_declaration_elements.py`

迁移分两步：

**Step 1：从 `hs_codes.json` 导入**
```
读取 hs_codes.json
  ↓ 遍历每个 HS Code
  ├─ 写入 hs_code_fields（从 "申报要素字段" 数组）
  │   └─ sort_order = 数组 index
  └─ 遍历 "数据库中商品名称及要素值" 数组
      ├─ 写入 declaration_products
      └─ 遍历每个字段，写入 declaration_values
```

**Step 2：从旧 `declaration_elements` 表迁移**
```
读取 declaration_elements 全部记录
  ↓ 遍历每条记录
  ├─ 解析 elements_text（按 | 分隔，再按 ：分隔 key/value）
  ├─ 查找或创建 declaration_products（按 hs_code + declaration_name）
  ├─ 提取字段名，补充到 hs_code_fields（如不存在）
  └─ 写入 declaration_values
```

**冲突处理：**
- `hs_code_fields`：INSERT OR IGNORE（已存在则跳过）
- `declaration_products`：INSERT OR IGNORE
- `declaration_values`：INSERT OR REPLACE（新值覆盖旧值）

### 3.2 迁移执行时机

作为 Alembic migration 019 自动执行，或手动运行：
```bash
cd backend && python -m migrations.019_refactor_declaration_elements
```

---

## 四、后端 API 设计

### 4.1 新增 Schema：`backend/app/schemas/declaration.py`

```python
from pydantic import BaseModel
from typing import Optional

# ── HS Code 字段定义 ──
class HsCodeFieldOut(BaseModel):
    id: int
    hs_code: str
    field_name: str
    sort_order: int

class HsCodeFieldCreate(BaseModel):
    hs_code: str
    field_name: str
    sort_order: int = 0

# ── 产品 ──
class DeclarationProductOut(BaseModel):
    id: int
    hs_code: str
    product_name: str

class DeclarationProductCreate(BaseModel):
    hs_code: str
    product_name: str

# ── 要素值 ──
class DeclarationValueOut(BaseModel):
    id: int
    product_id: int
    field_name: str
    field_value: str

class DeclarationValueUpdate(BaseModel):
    field_value: str

# ── 组合视图 ──
class ProductWithValues(BaseModel):
    """产品 + 所有字段值（用于表格行）"""
    product_id: int
    hs_code: str
    product_name: str
    values: dict[str, str]  # {field_name: field_value}

class HsCodeFieldListResponse(BaseModel):
    """某个 HS Code 的字段定义 + 产品列表"""
    hs_code: str
    web_name: str           # 网站商品名称
    description: str        # 商品描述
    fields: list[HsCodeFieldOut]
    products: list[ProductWithValues]
    total: int
```

### 4.2 API 端点：`backend/app/api/v1/declaration_ledger.py`

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/declaration-ledger/hs-codes` | 获取所有 HS Code 列表（含 web_name） |
| `GET` | `/declaration-ledger/hs-codes/{hs_code}` | 获取某 HS Code 的字段定义 + 产品列表 |
| `POST` | `/declaration-ledger/hs-codes/{hs_code}/fields` | 新增字段定义 |
| `PUT` | `/declaration-ledger/fields/{field_id}` | 修改字段定义（名称、排序） |
| `DELETE` | `/declaration-ledger/fields/{field_id}` | 删除字段定义 |
| `POST` | `/declaration-ledger/hs-codes/{hs_code}/products` | 新增产品 |
| `PUT` | `/declaration-ledger/products/{product_id}` | 修改产品名称 |
| `DELETE` | `/declaration-ledger/products/{product_id}` | 删除产品（级联删除 values） |
| `PUT` | `/declaration-ledger/products/{product_id}/values` | 批量更新产品的要素值 |
| `POST` | `/declaration-ledger/import` | 从 hs_codes.json 批量导入 |

### 4.3 新增 Service：`backend/app/services/declaration_ledger_service.py`

```python
class DeclarationLedgerService:

    def list_hs_codes(self, db, keyword=None):
        """返回所有 HS Code 列表（去重），含 web_name"""

    def get_hs_code_detail(self, db, hs_code, page=1, size=50):
        """返回字段定义 + 产品列表（含 values）"""

    def create_field(self, db, hs_code, field_name, sort_order):
        """新增字段定义"""

    def update_field(self, db, field_id, data):
        """修改字段定义"""

    def delete_field(self, db, field_id):
        """删除字段定义（同时删除所有产品的该字段值）"""

    def create_product(self, db, hs_code, product_name):
        """新增产品（自动从 hs_code_fields 初始化空值）"""

    def update_product(self, db, product_id, data):
        """修改产品名称"""

    def delete_product(self, db, product_id):
        """删除产品（级联删除 values）"""

    def update_values(self, db, product_id, values: dict):
        """批量更新产品的要素值（upsert 语义）"""

    def import_from_json(self, db, json_path):
        """从 hs_codes.json 批量导入"""
```

### 4.4 兼容性：保持 `CustomsDeclarationService` 不变

`CustomsDeclarationService` 继续从旧 `declaration_elements` 表读取数据。
`document_service.py` 的 `generate_customs()` 方法不需要修改。

**后续优化（可选）：** 将 `CustomsDeclarationService` 切换为从新表读取：
```python
def _load(self):
    # 从 declaration_products + declaration_values 重建 elements_text
    products = db.query(DeclarationProduct).all()
    for p in products:
        values = db.query(DeclarationValue).filter_by(product_id=p.id).all()
        elements_text = "|".join(f"{v.field_name}：{v.field_value}" for v in values)
        key = f"{p.hs_code}|{p.product_name}"
        self.data[key] = {"hs_code": p.hs_code, "申报名称": p.product_name, "申报要素": elements_text}
```

---

## 五、前端组件改造方案

### 5.1 新增 API Client：`frontend/src/api/declaration-ledger.ts`

```typescript
interface HsCodeField {
  id: number; hs_code: string; field_name: string; sort_order: number;
}

interface ProductWithValues {
  product_id: number; hs_code: string; product_name: string;
  values: Record<string, string>;
}

interface HsCodeDetail {
  hs_code: string; web_name: string; description: string;
  fields: HsCodeField[]; products: ProductWithValues[]; total: number;
}

export const declarationLedgerApi = {
  listHsCodes(keyword?: string): Promise<AxiosResponse<{items: any[], total: number}>>,
  getHsCodeDetail(hsCode: string, page?: number, size?: number): Promise<AxiosResponse<HsCodeDetail>>,
  createField(hsCode: string, data: {field_name: string, sort_order?: number}): Promise<any>,
  updateField(fieldId: number, data: Partial<HsCodeField>): Promise<any>,
  deleteField(fieldId: number): Promise<any>,
  createProduct(hsCode: string, data: {product_name: string}): Promise<any>,
  deleteProduct(productId: number): Promise<any>,
  updateValues(productId: number, values: Record<string, string>): Promise<any>,
}
```

### 5.2 重构 `DeclarationElementsTab.vue`

**核心变化：** 从固定列变为动态列

```
┌─────────────────────────────────────────────────────────────────┐
│  [HS Code 下拉筛选 ▼]  [搜索 🔍]                    [+ 新增产品] │
├─────────────────────────────────────────────────────────────────┤
│ HS Code  │ 网站名称     │ 商品名称       │ 用途 │ 成分含量 │ 外观 │ ... │ 操作  │
│ 34039100 │ 纺织制剂     │ 纺织助剂整理剂 │ xxx  │ xxx     │ xxx │ ... │ 编辑 删除│
│ 34039100 │ 纺织制剂     │ 还原清洗剂     │ xxx  │ xxx     │ xxx │ ... │ 编辑 删除│
│ 39100000 │ 聚硅氧烷     │ 有机硅柔软剂   │ xxx  │ xxx     │     │ ... │ 编辑 删除│
├─────────────────────────────────────────────────────────────────┤
│                                            共 15 条  < 1 >      │
└─────────────────────────────────────────────────────────────────┘
```

**实现要点：**

1. **左侧 HS Code 筛选器**
   - 页面加载时调用 `listHsCodes()` 获取所有 HS Code
   - 下拉选择 HS Code 后调用 `getHsCodeDetail()` 加载字段定义 + 产品数据
   - 支持 "全部" 模式（不选 HS Code，展示所有产品，列取所有字段的并集）

2. **动态列渲染**
   - 固定列：`hs_code`、`web_name`（网站商品名称）、`product_name`（商品名称）
   - 动态列：根据 `fields` 数组动态生成 `el-table-column`
   - 每个动态列的 `prop` 绑定到 `values[field_name]`

3. **单元格编辑**
   - 使用 `el-table` 的 `editable` 模式或双击编辑
   - 编辑后调用 `updateValues()` 保存

4. **新增产品弹窗**
   - 弹窗中显示当前 HS Code 的字段列表
   - 用户填写产品名称 + 各字段值
   - 提交后调用 `createProduct()` + `updateValues()`

### 5.3 重构 `ElementEditDialog.vue`

改造为 `ProductEditDialog.vue`：
- 左侧：产品基本信息（HS Code、商品名称）
- 右侧：根据 HS Code 动态渲染字段表单
- 每个字段一个 `el-form-item`，类型为 `el-input`（可扩展为下拉/日期等）
- 保存时调用 `updateValues()` 批量更新

### 5.4 DataCenter.vue 集成

Tab 保持不变（"申报要素"），内容替换为新的 `DeclarationElementsTab.vue`。

---

## 六、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `backend/app/schemas/declaration.py` | 新 Pydantic schemas |
| `backend/app/services/declaration_ledger_service.py` | 新 Service 层 |
| `backend/app/api/v1/declaration_ledger.py` | 新 API 路由 |
| `backend/migrations/019_refactor_declaration_elements.py` | 迁移脚本 |
| `frontend/src/api/declaration-ledger.ts` | 新 API Client |

### 修改文件

| 文件路径 | 变更内容 |
|----------|----------|
| `backend/app/models/reference_data.py` | 新增 3 个 ORM 模型：`HsCodeField`、`DeclarationProduct`、`DeclarationValue` |
| `backend/app/models/__init__.py` | 注册新模型 |
| `backend/app/database.py` | `init_db()` 中导入新模型 |
| `backend/app/main.py` | 注册新路由 `declaration_ledger_router` |
| `frontend/src/views/data-center/DeclarationElementsTab.vue` | 完全重构为动态列 + HS Code 筛选 |
| `frontend/src/views/data-center/ElementEditDialog.vue` | 重构为 `ProductEditDialog.vue`，动态字段表单 |

### 不变文件

| 文件路径 | 原因 |
|----------|------|
| `backend/app/services/customs_declaration_service.py` | 继续从旧表读取，保持兼容 |
| `backend/app/services/document_service.py` | 不需要修改 |
| `backend/app/services/declaration_element_service.py` | 保留旧 CRUD，旧表作为备份 |
| `backend/app/api/v1/declaration_elements.py` | 保留旧 API，旧表作为备份 |

---

## 七、实现步骤（推荐顺序）

### Phase 1：后端基础（约 2h）
1. 在 `reference_data.py` 新增 3 个 ORM 模型
2. 在 `__init__.py` 和 `database.py` 注册
3. 创建 `backend/app/schemas/declaration.py`
4. 创建 `backend/app/services/declaration_ledger_service.py`
5. 创建 `backend/app/api/v1/declaration_ledger.py`
6. 在 `main.py` 注册路由

### Phase 2：数据迁移（约 1h）
7. 创建 `backend/migrations/019_refactor_declaration_elements.py`
8. 运行迁移，验证数据

### Phase 3：前端改造（约 2h）
9. 创建 `frontend/src/api/declaration-ledger.ts`
10. 重构 `DeclarationElementsTab.vue`
11. 重构 `ElementEditDialog.vue` → `ProductEditDialog.vue`

### Phase 4：验证（约 1h）
12. 启动后端，测试 API
13. 启动前端，验证 UI
14. 验证 `document_service.py` 的报关单生成功能不受影响

---

## 八、风险与注意事项

1. **旧表兼容**：`declaration_elements` 表不删除，`CustomsDeclarationService` 不修改，确保报关单生成功能不受影响
2. **字段变更影响**：如果用户删除了某个字段定义（`hs_code_fields`），需要同时删除所有产品中该字段的值（`declaration_values`）
3. **HS Code 格式**：`hs_codes.json` 中的 key 是 10 位数字字符串，与现有系统一致
4. **排序**：`hs_code_fields.sort_order` 控制前端列的显示顺序，导入时按数组 index 设置
5. **空值处理**：`declaration_values.field_value` 允许为空字符串，前端显示为空单元格
