# MSDS 产品台账表单优化设计

**日期**: 2026-07-29
**状态**: Approved

## 1. 概述

对 MSDS 产品台账（`msds_product_ledger`）的「新配方导入」编辑卡和「新增/编辑配方」对话框进行 UI 和数据结构的优化，并将字段从可选改为必填。

## 2. 改动范围

### 2.1 数据库

**表 `msds_product_ledger`**:

| 字段 | 当前 | 目标 |
|------|------|------|
| `internal_code` | VARCHAR(100) NOT NULL, INDEX | **删除列** |
| `customs_name` | VARCHAR(200) nullable | **NOT NULL** |
| `appearance` | VARCHAR(500) nullable | **NOT NULL** |
| `ion_type` | VARCHAR(50) nullable | **NOT NULL** |
| `ph` | VARCHAR(50) nullable | **NOT NULL** |
| `composition` | JSON nullable | **NOT NULL** |

新建迁移文件 `backend/migrations/014_make_ledger_fields_required.py`：
- 删除 `internal_code` 列
- 其他字段改为 NOT NULL

### 2.2 后端模型

`backend/app/models/msds_ledger.py`：
- 删除 `internal_code = Column(...)` 行
- `customs_name`, `appearance`, `ion_type`, `ph`, `composition` 设置 `nullable=False`

### 2.3 后端 API Schema

`backend/app/api/v1/msds_ledger.py`：
- **LedgerCreate**: 删除 `internal_code`，其余字段去除默认值（即必填）
- **LedgerUpdate**: 删除 `internal_code`
- **`_to_dict()`**: 删除 `internal_code` 输出

### 2.4 后端 Service

`backend/app/services/msds_ledger_service.py`：
- `create_ledger()`: 删除 `internal_code` 参数
- `update_ledger()`: 从迭代字段列表删除 `internal_code`
- `list_ledger()`: 删除 `internal_code` 查询参数

### 2.5 前端 TypeScript 类型

`frontend/src/api/msds-ledger.ts`：
- `MsdsLedgerItem` 接口删除 `internal_code`

### 2.6 前端组件 — MSDSGeneratorDialog.vue

#### A. 新配方编辑卡（`newFormulas`）

**当前**：成分以 textarea 显示原始文本字符串。
**改为**：内嵌成分表，每行三列（组分 / CAS NO. / 含量），支持增删行。

- `loadLedger()` 中初始化 `newFormulas` 时，提前调用 `parseIngredients()` 将 `customs_ingredients` 文本解析为 `composition` 数组
- 移除成分 textarea，替换为动态表格
- `importAllFormulas()` 中直接从 composition 数组取值，不再 parse

#### B. 新增/编辑表单

- 删除「内部编码」输入项
- 成分表增加列标题（组分 / CAS NO. / 含量）
- 新增 Element Plus `el-form` 校验规则：报关名称、外观、离子性、pH值、成分表（至少一行）均为必填

#### C. 台账主表格

- 成分列保持简洁文本（`getCompositionFull()`），不做改动
- 删除所有 `internal_code` 引用

#### D. 其他逻辑

- `autoSelectMatchingItems()`: 删除 `internal_code` 优先匹配逻辑，仅保留 CAS 匹配
- `importAllFormulas()`: 删除 `internal_code` 传参
- `formData` 初始化: 删除 `internal_code`
- `loadLedger()` 中的 `internal_code` 回退查找逻辑删除

## 3. 字段必填规则

| 字段 | 验证规则 |
|------|----------|
| 报关名称 (`customs_name`) | 非空 |
| 外观 (`appearance`) | 非空 |
| 离子性 (`ion_type`) | 非空 |
| pH值 (`ph`) | 非空 |
| 成分表 (`composition`) | 至少有一行，每行组分非空 |

## 4. 不涉及变更

- OnlyOffice 回调逻辑不变
- MSDS 模板（cnMSDS.docx / enMSDS.docx）不变
- MSDS 生成服务（`msds_generator_service.py`）不变
- 数据中心面板（DataCenterPanel）不变
- 其他不相关的 API 端点不变
