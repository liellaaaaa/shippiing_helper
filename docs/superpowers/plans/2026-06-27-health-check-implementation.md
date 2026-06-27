# 系统连通性检测 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 导航栏添加系统检测按钮，后端扩展 `/api/v1/health` 检查 API、OnlyOffice、SQLite、Tesseract 四项组件状态。

**Architecture:** 后端在 `main.py` 的现有 `/health` 端点上扩展检查逻辑；前端在 `Layout.vue` 的 `.nav-actions` 区域添加检测按钮，用 `el-popover` 展示结果。

**Tech Stack:** FastAPI + httpx + SQLite + subprocess + Vue 3 + Element Plus

---

## 文件变更总览

| 文件 | 变更 |
|------|------|
| `backend/app/main.py` | 扩展 `/health` 端点，增加 4 项检查逻辑 |
| `frontend/src/views/Layout.vue` | 添加检测按钮 + popover 结果展示 |
| `frontend/src/api/health.ts` | 新建 health API 客户端（GET `/health`） |

---

## Task 1: 后端扩展 `/api/v1/health` 接口

**Files:**
- Modify: `backend/app/main.py:185-187`

---

- [ ] **Step 1: 在 main.py 顶部添加必要 import**

在 `main.py` 文件顶部（现有 import 区域）添加：

```python
import subprocess
import httpx
from sqlalchemy import text
```

---

- [ ] **Step 2: 重写 `/health` 端点**

替换 `backend/app/main.py` 第 185-187 行的现有函数：

```python
@app.get("/health")
def health():
    """
    系统连通性检测：
    - api:         直接返回 ok
    - onlyoffice:  httpx.get(DOCUMENT_SERVER_URL + "/health")
    - database:    SQLAlchemy SELECT 1
    - tesseract:   subprocess.run(["tesseract", "--version"])
    """
    DOCUMENT_SERVER_URL = os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")

    checks = {
        "api":        {"status": "ok", "message": "正常运行"},
        "onlyoffice": {"status": "error", "message": ""},
        "database":   {"status": "error", "message": ""},
        "tesseract":  {"status": "error", "message": ""},
    }

    # 1. API 本身（无需检查，直接 ok）
    # 已在 checks 初始化时设为 ok

    # 2. OnlyOffice
    try:
        resp = httpx.get(DOCUMENT_SERVER_URL + "/health", timeout=5.0)
        if resp.status_code == 200:
            checks["onlyoffice"] = {"status": "ok", "message": "Connected"}
        else:
            checks["onlyoffice"] = {"status": "error", "message": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        checks["onlyoffice"] = {"status": "error", "message": "连接失败"}
    except httpx.TimeoutException:
        checks["onlyoffice"] = {"status": "error", "message": "响应超时"}
    except Exception as e:
        checks["onlyoffice"] = {"status": "error", "message": str(e)}

    # 3. SQLite 数据库
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.commit()
        db.close()
        checks["database"] = {"status": "ok", "message": "正常"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}

    # 4. Tesseract OCR
    try:
        result = subprocess.run(
            [TESSERACT_CMD, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # 取第一行，如 "tesseract v5.3.1"
            first_line = result.stdout.strip().split("\n")[0]
            checks["tesseract"] = {"status": "ok", "message": first_line}
        else:
            checks["tesseract"] = {"status": "error", "message": "命令执行失败"}
    except FileNotFoundError:
        checks["tesseract"] = {"status": "error", "message": f"命令不存在: {TESSERACT_CMD}"}
    except subprocess.TimeoutExpired:
        checks["tesseract"] = {"status": "error", "message": "执行超时"}
    except Exception as e:
        checks["tesseract"] = {"status": "error", "message": str(e)}

    # 整体状态：任意一项 error 则 degraded
    overall_status = "ok" if all(c["status"] == "ok" for c in checks.values()) else "degraded"

    return {
        "status": overall_status,
        "checks": checks,
    }
```

---

- [ ] **Step 3: 验证后端接口**

启动后端后执行：

```bash
curl -s http://localhost:8000/health
```

预期返回 JSON 含 `"status": "ok"` 或 `"degraded"` 以及 `"checks"` 四项。

---

- [ ] **Step 4: 提交**

```bash
git add backend/app/main.py
git commit -m "feat: 扩展 /health 接口检查 onlyoffice/database/tesseract"
```

---

## Task 2: 前端 API 客户端

**Files:**
- Create: `frontend/src/api/health.ts`

---

- [ ] **Step 1: 创建 `frontend/src/api/health.ts`**

```typescript
import { apiClient } from './axios'

export interface HealthCheckItem {
  status: 'ok' | 'error'
  message: string
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  checks: {
    api: HealthCheckItem
    onlyoffice: HealthCheckItem
    database: HealthCheckItem
    tesseract: HealthCheckItem
  }
}

export const healthApi = {
  /** 调用 GET /api/v1/health */
  check(): Promise<HealthResponse> {
    return apiClient.get<HealthResponse>('/health').then(r => r.data)
  },
}
```

---

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/health.ts
git commit -m "feat: 添加 health API 客户端"
```

---

## Task 3: 前端检测按钮

**Files:**
- Modify: `frontend/src/views/Layout.vue:69-86`

---

- [ ] **Step 1: 在 script setup 中添加检测逻辑**

在 `Layout.vue` 的 `<script setup lang="ts">` 中添加：

```typescript
import { ref } from 'vue'
import { healthApi, type HealthResponse } from '@/api/health'

const healthPopoverVisible = ref(false)
const healthData = ref<HealthResponse | null>(null)
const healthLoading = ref(false)

async function checkHealth() {
  healthLoading.value = true
  healthPopoverVisible.value = true
  try {
    healthData.value = await healthApi.check()
  } catch {
    healthData.value = null
  } finally {
    healthLoading.value = false
  }
}

function getCheckIcon(s: 'ok' | 'error') {
  return s === 'ok' ? '✅' : '❌'
}
```

---

- [ ] **Step 2: 在 nav-actions 区域添加检测按钮**

在 `.nav-actions` 区域、el-dropdown 之前插入：

```html
<el-popover
  placement="bottom"
  :width="320"
  trigger="click"
  v-model:visible="healthPopoverVisible">
  <template #reference>
    <el-button class="health-btn" :loading="healthLoading" circle title="系统检测">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    </el-button>
  </template>
  <div v-if="healthLoading">检查中...</div>
  <div v-else-if="healthData">
    <div class="health-header" style="margin-bottom:12px">
      <span :class="['health-badge', healthData.status]">
        {{ healthData.status === 'ok' ? '✅ 全部正常' : '⚠️ 部分异常' }}
      </span>
    </div>
    <div class="health-row" v-for="(val, key) in healthData.checks" :key="key"
         style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <span>{{ getCheckIcon(val.status) }}</span>
      <span style="font-weight:500;width:80px">{{ key === 'api' ? 'API' :
        key === 'onlyoffice' ? 'OnlyOffice' :
        key === 'database' ? '数据库' : 'Tesseract' }}</span>
      <span style="color:var(--text-secondary);font-size:12px">{{ val.message }}</span>
    </div>
    <el-button size="small" style="margin-top:10px;width:100%" @click="checkHealth">
      重新检测
    </el-button>
  </div>
  <div v-else style="color:var(--text-secondary)">检测失败</div>
</el-popover>
```

---

- [ ] **Step 3: 添加按钮样式**

在 `<style>` 区域添加：

```css
.health-btn {
  border: none !important;
  background: transparent !important;
}
.health-btn:hover {
  background: var(--bg-hover) !important;
}
.health-badge.ok {
  color: #67c23a;
}
.health-badge.degraded {
  color: #e6a23c;
}
```

---

- [ ] **Step 4: 验证前端**

启动前端后访问任意页面，导航栏左侧应显示检测按钮（圆形图标），点击弹出检查结果。

---

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/Layout.vue frontend/src/api/health.ts
git commit -m "feat: 导航栏添加系统检测按钮"
```

---

## 自检清单

1. **Spec 覆盖**：所有 spec 中的 4 项检查（api/onlyoffice/database/tesseract）和 popover 展示均有对应 task。
2. **Placeholder 扫描**：无 "TBD"、"TODO"、未填写字段。
3. **类型一致性**：前端 `HealthResponse` interface 的字段名与后端返回 JSON 完全一致（`status`、`checks`）。
4. **环境变量**：OnlyOffice URL 和 Tesseract 路径均通过 `os.getenv` 读取，与现有代码模式一致。
5. **无权限**：health 接口已在 `auth_middleware` 的白名单中，无需登录。
