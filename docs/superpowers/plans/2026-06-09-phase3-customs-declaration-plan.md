# Phase 3 报关阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase 2 工作流中新增「报关」按钮，点击后以整本 Excel workbook（5个 sheet）模式在 OnlyOffice 中打开出口报关资料模板，用户手动编辑后保存/下载。

**Architecture:** 复刻 Phase 2 的 Booking文档生成模式——后端 DocumentService 读取 xlsx 模板 bytes → OnlyOfficeService 创建 JWT 配置 → 前端 DocumentEditor 加载。零新增依赖，完全复用现有 OnlyOffice 回调存储机制。

**Tech Stack:** Python FastAPI + Vue 3 + OnlyOffice Document Server

---

## 文件变更概览

| 文件 | 改动类型 |
|------|---------|
| `backend/app/core/config.py` | 修改：新增 `TEMPLATES["customs"]` |
| `backend/app/services/document_service.py` | 修改：新增 `generate_customs()` 方法 |
| `backend/app/api/v1/documents.py` | 修改：新增 `GET /documents/customs` 路由 |
| `frontend/src/api/phase2.ts` | 修改：新增 `generateCustoms()` |
| `frontend/src/views/phase2/Phase2Workflow.vue` | 修改：工具栏新增「报关」按钮 + `openCustoms()` 函数 |

---

##任务拆分

### Task 1: 后端模板配置

**文件:** `backend/app/core/config.py`

- [ ] **Step 1: 添加 customs 模板路径**

在 `TEMPLATES`字典中添加 `"customs"` key，指向出口报关资料 xlsx：

```python
TEMPLATES = {
    "booking": str(ROOT / "references" / "长晟出口海运BOOKING模板.xls"),
    "booking_xlsx": str(ROOT / "references" / "长晟出口海运BOOKING模板.xlsx"),
    "loi":     str(ROOT / "references" / "LOI-op-非危险品保函模板.docx"),
    "msds":    str(ROOT / "references" / "MSDS" / "MSDS标准模板.docx"),
    "customs": str(ROOT / "references" / "出口报关资料 26.3.17.xlsx"),  # ← 新增
}
```

**验证:** 启动后端后 `python -c "from app.core.config import TEMPLATES; print(TEMPLATES['customs'])"` 应输出文件路径，且文件存在。

---

### Task 2: DocumentService 新增 generate_customs()

**文件:** `backend/app/services/document_service.py`

- [ ] **Step 1: 在 `generate_customs()` 方法末尾的 `generate_template_instance()`之前添加新方法**

```python
def generate_customs(self, order_id: int | None = None) -> Tuple[bytes, str, str]:
    """
    生成报关资料工作簿（整本 xlsx，5个 sheet）。
    第一期仅返回原始模板，不做数据填充（为后续自动填充留扩展口）。
    """
    template_path = TEMPLATES["customs"]
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Customs template not found: {template_path}")

    with open(template_path, "rb") as f:
        content = f.read()

    doc_key = f"customs_{uuid.uuid4().hex}"
    return content, doc_key, base64.b64encode(content).decode()
```

**注意:** 需要在文件顶部确保 `import uuid`（检查现有 import，若无则添加）。

**验证:** `python -c "from app.services.document_service import DocumentService; s=DocumentService(); c,d,b=s.generate_customs(); print(len(c), d[:20])"` 应输出文件字节数和以 `customs_` 开头的 doc_key。

---

### Task 3: 后端 API 路由

**文件:** `backend/app/api/v1/documents.py`

- [ ] **Step 1: 在 `/msds` 路由之后、`/history` 路由之前添加 `/customs` 路由**

```python
@router.get("/customs")
async def generate_customs(order_id: int | None = Query(None)):
    """
    生成出口报关资料工作簿（5个 sheet 的 xlsx）。
    order_id 暂不使用，为后续自动数据填充留扩展口。
    """
    svc = DocumentService()
    content, doc_key, _ = svc.generate_customs(order_id=order_id)
    token, config, safe_key = oo_svc.create_config(doc_key, "xlsx")
    _save_doc_to_db(doc_key, "customs", content, order_id=order_id, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }
```

**注意:** `_save_doc_to_db` 的 `file_name` 默认根据 `doc_type` 判断扩展名（booking→xlsx, 其他→docx），需确认 `customs` 对应 `xlsx`。若默认逻辑不满足，在调用处显式传入 `file_name`。

**验证:** 启动后端后 `curl -s "http://localhost:8000/api/v1/documents/customs" | python -m json.tool` 应返回包含 `token`, `documentKey`, `url`, `downloadUrl` 的 JSON。

---

### Task 4: 前端 API客户端

**文件:** `frontend/src/api/phase2.ts`

- [ ] **Step 1: 在 `generateMsds()`之后添加 `generateCustoms()`**

```typescript
generateCustoms(orderId: number | null) {
  return axios.get('/api/v1/documents/customs', {
    params: { order_id: orderId }
  })
},
```

**验证:** `npm run dev` 前端启动无报错。

---

### Task 5: Phase2Workflow 工具栏新增「报关」按钮

**文件:** `frontend/src/views/phase2/Phase2Workflow.vue`

- [ ] **Step 1: 在工具栏按钮组中（MSDS 按钮之后、空白模板之前）新增「报关」按钮**

在 `showMsdsDialog` ref 声明之后、`showBookingDialog` 之前添加：

```typescript
const showCustomsDialog = ref(false)
```

在 `confirmGenerateBooking` 函数之前添加 `openCustoms` 函数：

```typescript
async function openCustoms() {
  try {
    const res = await phase2Api.generateCustoms(selectedOrderId.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('报关资料生成失败: ' + (e.message || ''))
  }
}
```

在模板 toolbar-actions 中，MSDS 按钮之后、空白模板 dropdown 之前添加：

```vue
<el-button
  type="primary"
  size="small"
  :disabled="!selectedOrderId"
  @click="openCustoms"
>
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
    <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
  </svg>
  报关
</el-button>
```

**注意:** 报关按钮无需 dialog，直接点击即打开 OnlyOffice 编辑器。

**验证:** 加载 Phase2 页面，选择一个已确认订单，点击「报关」按钮，OnlyOffice 应在右侧面板加载出5个 sheet 的 Excel 工作簿。

---

## 测试验证要点

1. **后端 API**: `curl http://localhost:8000/api/v1/documents/customs` 返回有效 OnlyOffice 配置
2. **OnlyOffice 加载**: 点击「报关」后，右侧编辑器内正确显示 5个 sheet标签（报关单/发票/箱单/合同/委托书）
3. **Sheet 切换**: OnlyOffice 底部 sheet 标签可正常切换
4. **保存回调**: 在 OnlyOffice 中编辑后点击保存，`POST /api/v1/onlyoffice/callback` 成功，版本号递增
5. **我的模板**: 保存后的报关文档出现在「我的模板」列表中
6. **与 MSDS 无干扰**: MSDS 按钮流程不受影响

---

## 提交节点建议

| 提交 | 内容 |
|------|------|
| 1 | `config.py` + `DocumentService.generate_customs()` |
| 2 | `documents.py` 路由 |
| 3 | `phase2.ts` API + `Phase2Workflow.vue` 按钮 |
| 4 | 全流程联调验证 |

---

##依赖项

- Phase 2 的 OnlyOffice 回调存储机制（`/onlyoffice/callback`）已完备，直接复用
- `onlyoffice_service.py` 的 UUID safe_key 机制直接复用
- `DocumentEditor.vue` 支持 xlsx/cell 模式，直接复用