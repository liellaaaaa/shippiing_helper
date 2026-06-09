# Phase 3 报关阶段设计方案

## 概述

Phase 3 在现有 Phase 2（文档编辑工作流）基础上，新增报关单证制作功能。结构和 Phase 2 完全一致——左侧参考数据面板 + 右侧 OnlyOffice 编辑器。区别在于文档类型是 multi-sheet Excel 工作簿（5个 sheet：报关单、发票、箱单、合同、委托书）。

**第一期目标**：打开模板 → 手动编辑 → 保存/下载，暂不做自动数据填充。

---

## 模板文件

文件路径：`references/出口报关资料 26.3.17.xlsx`

| Sheet | 名称 |用途 |
|-------|------|------|
| 1 | 报关单 | 中华人民共和国海关出口货物报关单 |
| 2 | 发票 | 商业发票 Commercial Invoice |
| 3 | 箱单 | 装箱单 Packing List |
| 4 | 合同 | 销售合同 Sales Contract |
| 5 | 委托书 | 报关委托书 Power of Attorney |

模板数据示例：宏昊化工 → TOA-DOVECHEM，2400kg 有机硅柔软剂，CIF 泰国。

---

## 交互设计

- **整本 workbook 一起编辑**：一次打开整个 Excel 文件（5个 sheet 均载入），用户在 OnlyOffice 中切换底部 sheet 标签页编辑，与本地打开 Excel 体验一致。
- **Tab 标签**：Phase 2 工具栏新增独立「报关」按钮，与订舱单/LOI/MSDS/空白模板平级，不影响现有 MSDS 流程。

---

## 后端设计

### 模板配置 (`backend/app/core/config.py`)

```python
TEMPLATES["customs"] = str(ROOT / "references" / "出口报关资料 26.3.17.xlsx")
```

### DocumentService (`backend/app/services/document_service.py`)

#### `generate_customs(order_id: int | None = None) -> dict`

- `order_id` 暂不使用，为后续自动数据填充留扩展口
- 流式读取模板文件，不将大 Excel 完整加载到内存
- 生成 UUID doc_key，写入 `shipment_docs` 表（version=1）
- 返回结构包含扩展字段，方便后续迭代

```python
def generate_customs(self, order_id: int | None = None) -> dict:
    template_path = TEMPLATES["customs"]
    doc_key = f"customs_{uuid.uuid4().hex}"
    safe_key = self._onlyoffice_svc.create_safe_key(doc_key)

    # 流式读取，不完整加载到内存
    file_stream = open(template_path, "rb")
    file_size = os.path.getsize(template_path)

    #写入 shipment_docs
    self._save_template_doc(
        doc_key=doc_key,
        doc_type="customs",
        file_stream=file_stream,
        file_size=file_size,
        safe_key=safe_key,
        order_id=order_id,
        file_name="出口报关资料.xlsx",
        version=1,
    )

    token, config = self._onlyoffice_svc.create_config(doc_key, "xlsx")

    return {
        "token": token,
        "doc_key": doc_key,
        "safe_key": safe_key,
        "file_type": "xlsx", # 明确指定 OnlyOffice 文件类型
        "template_id": "customs_declaration",  # 后续自动填充扩展口
        "sheet_names": ["报关单", "发票", "箱单", "合同", "委托书"],
        "download_url": f"/api/v1/onlyoffice/download/{safe_key}",
    }
```

### API路由 (`backend/app/api/v1/documents.py`)

```python
@router.get("/customs")
async def generate_customs(order_id: int | None = Query(None)):
    svc = DocumentService()
    result = svc.generate_customs(order_id=order_id)
    return result
```

### 流式读取实现要点

- 使用 `FileResponse` 或 `StreamingResponse` 从文件路径直出，不经过内存
- `shipment_docs.file_blob` 字段改为存储文件路径（字符串）而非 Base64，避免大文件撑爆数据库
  - **注意**：现有 `file_blob` 存储 Base64 的机制不变，只对 customs 类型做路径引用优化（待确认是否可行，或第一期仍存 Base64）

---

## 前端设计

### API (`frontend/src/api/phase2.ts`)

```typescript
generateCustoms(orderId: number | null) {
  return axios.get('/api/v1/documents/customs', {
    params: { order_id: orderId }
  })
}
```

### Phase2Workflow.vue 工具栏

在现有按钮组（订舱单 / LOI保函 / MSDS / 空白模板）右侧新增：

```vue
<el-button @click="openCustoms">报关</el-button>
```

### openCustoms 逻辑

```typescript
async function openCustoms() {
  const res = await phase2Api.generateCustoms(selectedOrderId.value)
  currentDocKey.value = res.data.doc_key
  currentConfig.value = buildConfig(res.data)  // 复用现有 buildConfig
  currentDocType.value = 'cell'  // xlsx → cell 模式
}
```

### DocumentEditor.vue 复用

- `fileType: "xlsx"` 已在 `buildConfig` 中正确传递
- 支持 cell 模式（Excel），直接复用

### ReferencePanel.vue

- 报关阶段复用现有参考数据面板（发货人、收货人、商品名、HS Code、毛净重等）
- 字段可复用 Phase 1 已有的 `order_pi_records` 数据

---

## 数据流

```
用户点击「报关」按钮
  → POST /api/v1/documents/customs?order_id=X
      └── DocumentService.generate_customs()
            ├── 流式读取 xlsx 模板
            ├── 生成 UUID doc_key + safe_key
            ├── 写入 shipment_docs 表
            └── 返回 { token, doc_key, safe_key, file_type:"xlsx", sheet_names }

  ← 返回 OnlyOffice 配置 JSON
      → currentConfig 传入 DocumentEditor
          → OnlyOffice 加载整本 workbook（5个 sheet）
              → 用户在 OnlyOffice 中切换 sheet 标签编辑
                  → 点击保存 → POST /api/v1/onlyoffice/callback
                      → 后端存储新版本（幂等 hash 去重）
```

---

## 扩展性预留（后续迭代）

Phase 3 后续叠加自动数据填充时，只需：

1. `DocumentService.generate_customs(order_id)` 接收 `order_id`，从 `order_pi_records` 查询数据
2. 使用 `openpyxl` 打开模板，替换标记单元格（如 `{{product_name}}` →实际品名）
3. 以流式写出修改后的 bytes，不改变整体接口结构

---

## 涉及文件清单

### 后端
| 文件 | 改动 |
|------|------|
| `backend/app/core/config.py` | 新增 `TEMPLATES["customs"]` |
| `backend/app/services/document_service.py` | 新增 `generate_customs()` 方法 |
| `backend/app/api/v1/documents.py` | 新增 `GET /documents/customs` 路由 |

### 前端
| 文件 | 改动 |
|------|------|
| `frontend/src/api/phase2.ts` | 新增 `generateCustoms()` |
| `frontend/src/views/phase2/Phase2Workflow.vue` | 工具栏新增「报关」按钮 + `openCustoms()` |

### 组件复用（无需改动）
- `DocumentEditor.vue` — 支持 xlsx/cell 模式
- `OnlyOfficeService` — JWT + UUID safe_key
- `ReferencePanel.vue` — 复用参考数据字段
- 回调存储机制 — 直接复用

---

## MSDS 状态说明

MSDS 当前无法正常启动，根因为 **标准模板文件 `MSDS标准模板.docx` 不存在**。代码有 fallback 机制但依赖产品名索引匹配和 .doc→.docx 转换，成功率不稳定。

Phase 3 开发不影响 MSDS 调试，两者独立并行推进。