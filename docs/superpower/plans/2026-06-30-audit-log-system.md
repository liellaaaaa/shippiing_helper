# 用户行为日志系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 ShippingHelper 添加用户行为日志系统，记录用户在各模块的操作轨迹，供运营团队分析工作量、用户活跃度和功能使用情况。

**Architecture:** 前端通过 Vue 指令 `v-track` 埋点 + router 钩子记录模块进入退出；后端记录登录登出；日志统一写入 SQLite `audit_logs` 表；提供查询和 Excel 导出 API。

**Tech Stack:** Vue 3 (Composition API, TypeScript), FastAPI + SQLAlchemy, SQLite

---

## ⚠️ 重要修正

| # | 问题 | 修正方案 |
|---|------|---------|
| 1 | sendBeacon 默认 `text/plain`，FastAPI Pydantic 解析不了 | 后端 `batch` 端点改用 `Request` 原始 body + `json.loads()` 手动解析 |
| 2 | batch 端点鉴权：禁止伪造用户日志 | 已在 Task 5 实现 |
| 3 | `get_current_user` 返回 `{"name": name}`，plan 中 `user["name"]` 正确 | 无需修改 |
| 4 | `getModuleFromPath` 的 `startsWith` 误匹配风险 | 改用 RegExp 精确匹配（Task 7） |
| 5 | beforeunload 同步 flush 不可靠 | 改用 `navigator.sendBeacon()`（Task 6） |
| 6 | logout 后端端点多余 | 移除，用 beforeunload sendBeacon 记录（Task 7） |
| 7 | `open_document_editor` 事件多余 | 移除，`enter_module` 已覆盖 Phase2 进入场景 |
| 8 | 模块值命名不一致：`datacenter` vs `data-center` | 统一为 `data-center`（有连字符），与路由 path 一致 |
| 9 | `audit_middleware.py` 不需要 | 移除，当前方案纯前端埋点 + 后端登录记录 |

---

## 文件结构

```
backend/
├── app/
│   ├── models/
│   │   └── audit_log.py          # [NEW] AuditLog 模型
│   ├── services/
│   │   └── audit_service.py     # [NEW] AuditService
│   ├── api/v1/
│   │   ├── audit.py             # [NEW] /logs, /export, /stats, /batch 端点
│   │   └── auth.py             # [MODIFY] 登录写入 user_login 日志
│   └── api/deps.py             # [MODIFY] 添加 get_audit_service
├── migrations/
│   └── 011_create_audit_logs.py  # [NEW] 建表迁移

frontend/src/
├── plugins/
│   └── track.ts                 # [NEW] v-track 指令 + sendBeacon 队列
├── api/
│   └── audit.ts                 # [NEW] audit API 客户端
├── router/
│   └── index.ts                # [MODIFY] beforeEach 记录 enter/exit_module
├── main.ts                      # [MODIFY] 注册 v-track
└── views/
    ├── audit/
    │   └── AuditLogs.vue       # [NEW] 日志查看页面
    ├── phase1/
    │   └── Phase1Workflow.vue  # [MODIFY] 确认入库按钮埋点
    ├── phase2/
    │   └── Phase2Workflow.vue  # [MODIFY] 文档生成按钮埋点
    └── Layout.vue              # [MODIFY] 导航栏 + 系统检测埋点
```

---

## Task 1: 后端 — AuditLog 模型

**Files:** Create `backend/app/models/audit_log.py`

- [ ] **Step 1: 创建模型**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """用户行为日志模型"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_name = Column(String(100), nullable=False, index=True)
    module = Column(String(50), nullable=True)
    action_time = Column(DateTime, nullable=False, index=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/models/audit_log.py
git commit -m "feat: add AuditLog SQLAlchemy model"
```

---

## Task 2: 后端 — 建表迁移

**Files:** Create `backend/migrations/011_create_audit_logs.py`

- [ ] **Step 1: 创建迁移**

```python
"""Create audit_logs table for user behavior tracking."""
import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "shipping_helper.db"
)

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type VARCHAR(50) NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            module VARCHAR(50),
            action_time DATETIME NOT NULL,
            detail TEXT,
            ip_address VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action_time ON audit_logs(action_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_name ON audit_logs(user_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)")

    conn.commit()
    print("Migration 011 complete: created audit_logs table")
    conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS audit_logs")
    conn.commit()
    print("Migration 011 rolled back")
    conn.close()

if __name__ == "__main__":
    upgrade()
```

- [ ] **Step 2: 执行并提交**

```bash
cd backend && python migrations/011_create_audit_logs.py
git add backend/migrations/011_create_audit_logs.py
git commit -m "feat: add audit_logs table migration 011"
```

---

## Task 3: 后端 — AuditService

**Files:** Create `backend/app/services/audit_service.py`, Modify `backend/app/api/deps.py`

- [ ] **Step 1: 创建 `backend/app/services/audit_service.py`**

```python
"""用户行为日志服务"""
import json
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db=None):
        self.db = db or SessionLocal()

    def log(self, event_type: str, user_name: str, module: Optional[str] = None,
            detail: Optional[dict] = None, ip_address: Optional[str] = None,
            action_time: Optional[datetime] = None) -> AuditLog:
        log_entry = AuditLog(
            event_type=event_type,
            user_name=user_name,
            module=module,
            action_time=action_time or datetime.now(),
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip_address=ip_address,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def query_logs(self, user_name: Optional[str] = None, event_type: Optional[str] = None,
                   module: Optional[str] = None, start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None, page: int = 1, page_size: int = 50):
        query = self.db.query(AuditLog)
        if user_name:
            query = query.filter(AuditLog.user_name == user_name)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if module:
            query = query.filter(AuditLog.module == module)
        if start_time:
            query = query.filter(AuditLog.action_time >= start_time)
        if end_time:
            query = query.filter(AuditLog.action_time <= end_time)

        total = query.count()
        logs = query.order_by(AuditLog.action_time.desc()) \
                    .offset((page - 1) * page_size).limit(page_size).all()
        return {"logs": logs, "total": total, "page": page, "page_size": page_size}

    def get_stats(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        from sqlalchemy import func

        q = self.db.query(AuditLog)
        if start_time:
            q = q.filter(AuditLog.action_time >= start_time)
        if end_time:
            q = q.filter(AuditLog.action_time <= end_time)

        by_user = q.group_by(AuditLog.user_name).all()
        by_event = q.group_by(AuditLog.event_type).all()
        by_module = q.filter(AuditLog.module.isnot(None)).group_by(AuditLog.module).all()

        return {
            "by_user": [{"user_name": r.user_name, "count": r.count} for r in by_user],
            "by_event": [{"event_type": r.event_type, "count": r.count} for r in by_event],
            "by_module": [{"module": r.module, "count": r.count} for r in by_module],
        }

    def export_logs(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        query = self.db.query(AuditLog)
        if start_time:
            query = query.filter(AuditLog.action_time >= start_time)
        if end_time:
            query = query.filter(AuditLog.action_time <= end_time)
        return query.order_by(AuditLog.action_time.desc()).all()
```

- [ ] **Step 2: 在 `backend/app/api/deps.py` 末尾添加**

```python
def get_audit_service():
    """审计日志服务依赖注入"""
    from app.services.audit_service import AuditService
    return AuditService(SessionLocal())
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/audit_service.py backend/app/api/deps.py
git commit -m "feat: add AuditService with query/export/stats methods"
```

---

## Task 4: 后端 — 登录日志（auth.py）

**Files:** Modify `backend/app/api/v1/auth.py`

- [ ] **Step 1: 修改登录接口，写入 `user_login` 日志**

```python
"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, status, Request
from app.models.user import LoginRequest, TokenResponse
from app.services.auth_service import authenticate
from app.services.audit_service import AuditService
from app.database import SessionLocal
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """用户登录，写入 user_login 日志"""
    try:
        result = authenticate(body.name, body.password)

        audit = AuditService(SessionLocal())
        audit.log(
            event_type="user_login",
            user_name=body.name,
            action_time=datetime.now(),
            ip_address=get_client_ip(request),
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/api/v1/auth.py
git commit -m "feat: record user_login audit log on successful authentication"
```

---

## Task 5: 后端 — Audit API（含 batch 鉴权 + sendBeacon 兼容）

**Files:** Create `backend/app/api/v1/audit.py`, Modify `backend/app/main.py`

- [ ] **Step 1: 创建 `backend/app/api/v1/audit.py`**

关键：`batch` 端点必须用 `Request` 原始 body 手动解析 JSON（sendBeacon 发 text/plain，FastAPI Pydantic 解析不了）。

```python
"""审计日志查询与导出 API"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from fastapi.responses import StreamingResponse
import io

from app.api.deps import get_audit_service, get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["审计日志"])


@router.get("/logs")
async def get_logs(
    user_name: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    result = service.query_logs(user_name, event_type, module, start_time, end_time, page, page_size)
    logs = [{
        "id": log.id,
        "event_type": log.event_type,
        "user_name": log.user_name,
        "module": log.module,
        "action_time": log.action_time.isoformat() if log.action_time else None,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in result["logs"]]
    return {"logs": logs, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.get("/stats")
async def get_stats(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: AuditService = Depends(get_audit_service),
):
    return service.get_stats(start_time=start_time, end_time=end_time)


@router.get("/export")
async def export_logs(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: AuditService = Depends(get_audit_service),
):
    from openpyxl import Workbook

    logs = service.export_logs(start_time=start_time, end_time=end_time)
    wb = Workbook()
    ws = wb.active
    ws.title = "行为日志"

    headers = ["ID", "事件类型", "用户名", "模块", "发生时间", "详情", "IP地址", "记录时间"]
    ws.append(headers)

    for log in logs:
        ws.append([
            log.id, log.event_type, log.user_name, log.module or "",
            log.action_time.isoformat() if log.action_time else "",
            log.detail or "", log.ip_address or "",
            log.created_at.isoformat() if log.created_at else "",
        ])

    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 22
    ws.column_dimensions['F'].width = 40
    ws.column_dimensions ['G'].width = 15
    ws.column_dimensions ['H'].width = 22

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/batch")
async def batch_log(
    request: Request,
    user: dict = Depends(get_current_user),  # JWT 鉴权
    service: AuditService = Depends(get_audit_service),
):
    """
    批量接收前端埋点日志。

    注意：sendBeacon 发送 Content-Type: text/plain，
    所以这里用 Request.body() 手动解析，不依赖 FastAPI Pydantic。
    """
    body = await request.body()
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    events = data.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="events must be a list")

    for item in events:
        # 安全校验：禁止伪造其他用户的日志
        if item.get("user_name") != user["name"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"禁止伪造用户日志: expected '{user['name']}', got '{item.get('user_name')}'"
            )

        try:
            action_time = datetime.fromisoformat(item.get("action_time", "").replace("Z", "+00:00"))
        except Exception:
            action_time = datetime.now()

        service.log(
            event_type=item.get("event_type"),
            user_name=item.get("user_name"),
            module=item.get("module"),
            action_time=action_time,
            detail=item.get("detail"),
            ip_address=item.get("ip_address"),
        )

    return {"success": True, "count": len(events)}
```

- [ ] **Step 2: 在 `backend/app/main.py` 中注册 audit 路由**

```python
from app.api.v1.audit import router as audit_router
app.include_router(audit_router)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/v1/audit.py backend/app/main.py
git commit -m "feat: add audit API (logs, stats, export, batch with JWT auth and sendBeacon compatibility)"
```

---

## Task 6: 前端 — v-track 指令 + sendBeacon 队列

**Files:** Create `frontend/src/plugins/track.ts`

- [ ] **Step 1: 创建 `frontend/src/plugins/track.ts`**

```typescript
import { App, Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

interface TrackOptions {
  event: string
  module?: string
  detail?: Record<string, unknown>
}

interface QueuedEvent {
  event_type: string
  user_name: string
  module?: string
  action_time: string
  detail?: string
  ip_address?: string
}

const eventQueue: QueuedEvent[] = []

function flush() {
  if (eventQueue.length === 0) return
  const events = eventQueue.splice(0)
  const payload = JSON.stringify({ events })

  // sendBeacon：异步发送，页面卸载时也能保证送达
  // sendBeacon 自动使用 text/plain;charset=UTF-8
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/v1/audit/batch', payload)
  } else {
    // 降级：同步 fetch（页面卸载时可能不完成）
    fetch('/api/v1/audit/batch', {
      method: 'POST',
      body: payload,
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
    }).catch(() => {})
  }
}

function enqueueEvent(options: TrackOptions) {
  const authStore = useAuthStore()
  if (!authStore.isLoggedIn || !authStore.userName) return

  eventQueue.push({
    event_type: options.event,
    user_name: authStore.userName,
    module: options.module,
    action_time: new Date().toISOString(),
    detail: options.detail ? JSON.stringify(options.detail) : undefined,
    ip_address: '',
  })

  if (eventQueue.length >= 10) {
    flush()
  }
}

export const trackDirective: Directive = {
  mounted(el: HTMLElement & { _trackHandler?: (e: Event) => void }, binding: { value?: TrackOptions }) {
    const options = binding.value || {}
    const handler = () => enqueueEvent(options)
    el._trackHandler = handler
    el.addEventListener('click', handler)
  },
  unmounted(el: HTMLElement & { _trackHandler?: (e: Event) => void }) {
    if (el._trackHandler) {
      el.removeEventListener('click', el._trackHandler)
    }
  },
}

export function trackEvent(options: TrackOptions) {
  enqueueEvent(options)
}

export { flush }

export function setupTrack(app: App) {
  app.directive('track', trackDirective)

  // 页面卸载时 flush（sendBeacon 保证送达）
  window.addEventListener('beforeunload', () => flush())
  // 标签页隐藏时也 flush
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush()
  })
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/plugins/track.ts
git commit -m "feat: add v-track directive with sendBeacon flush for reliable audit logging"
```

---

## Task 7: 前端 — 路由埋点（RegExp 精确匹配）

**Files:** Modify `frontend/src/router/index.ts`

- [ ] **Step 1: 修改 beforeEach，使用 RegExp 精确匹配**

```typescript
import { trackEvent, flush } from '@/plugins/track'

let currentModule: string | null = null

// 使用 RegExp 精确匹配，避免 /phase10 误匹配 /phase1
const moduleMap: Record<string, RegExp[]> = {
  'phase1': [/^\/workflow$/, /^\/$/],
  'phase2': [/^\/phase2/],
  'phase3': [/^\/phase3/],
  'dashboard': [/^\/dashboard/],
  'data-center': [/^\/data-center/],
}

function getModuleFromPath(path: string): string | null {
  for (const [module, patterns] of Object.entries(moduleMap)) {
    if (patterns.some(re => re.test(path))) return module
  }
  return null
}

router.beforeEach(async (to, from, next) => {
  document.title = (to.meta.title as string || 'ShippingHelper') + ' - ShippingHelper'
  const authStore = useAuthStore()

  if (to.path === '/login') {
    if (authStore.isLoggedIn) {
      next('/workflow')
    } else {
      if (currentModule) {
        trackEvent({ event: 'exit_module', module: currentModule })
        currentModule = null
      }
      await flush()
      next()
    }
    return
  }

  if (!authStore.isLoggedIn) {
    next('/login')
    return
  }

  const toModule = getModuleFromPath(to.path)
  if (toModule && toModule !== currentModule) {
    if (currentModule) trackEvent({ event: 'exit_module', module: currentModule })
    trackEvent({ event: 'enter_module', module: toModule })
    currentModule = toModule
  }

  next()
})
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: add module enter/exit tracking with precise RegExp path matching"
```

---

## Task 8: 前端 — main.ts 注册 v-track

**Files:** Modify `frontend/src/main.ts`

- [ ] **Step 1: 修改 `main.ts`**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@/styles/global.css'
import App from './App.vue'
import router from './router'
import { setupTrack } from '@/plugins/track'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus)
app.use(router)
setupTrack(app)
app.mount('#app')
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/main.ts
git commit -m "feat: register v-track directive via setupTrack in main.ts"
```

---

## Task 9: 前端 — 关键按钮埋点

**Files:** Modify `Phase1Workflow.vue`, `Phase2Workflow.vue`, `Layout.vue`

- [ ] **Step 1: Phase1Workflow.vue — 确认入库按钮添加 `v-track`**

```html
<el-button
  type="success"
  v-track="{ event: 'save_to_database', module: 'phase1' }"
  @click="handleSave"
>
  确认入库
</el-button>
```

- [ ] **Step 2: Phase2Workflow.vue — 文档生成按钮添加埋点**

```html
<el-button
  v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'booking' } }"
  @click="generateBooking"
>
  订舱单
</el-button>

<el-button
  v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'loi' } }"
  @click="generateLoi"
>
  LOI保函
</el-button>

<el-button
  v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'msds' } }"
  @click="generateMsds"
>
  MSDS
</el-button>
```

- [ ] **Step 3: Layout.vue — 系统检测按钮添加埋点**

在 `Layout.vue` 的 `setup()` 中添加：

```typescript
function getCurrentModule(): string {
  const path = router.currentRoute.value.path
  if (path.startsWith('/phase2')) return 'phase2'
  if (path.startsWith('/phase3')) return 'phase3'
  if (path.startsWith('/dashboard')) return 'dashboard'
  if (path.startsWith('/data-center')) return 'data-center'
  return 'phase1'
}
```

在系统检测按钮添加：

```html
<el-button
  v-track="{ event: 'system_health_check', module: getCurrentModule() }"
  @click="handleHealthCheck"
>
  系统检测
</el-button>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/phase1/Phase1Workflow.vue frontend/src/views/phase2/Phase2Workflow.vue frontend/src/views/Layout.vue
git commit -m "feat: add v-track directives to key action buttons"
```

---

## Task 10: 前端 — Audit API 客户端

**Files:** Create `frontend/src/api/audit.ts`

- [ ] **Step 1: 创建 API 客户端**

```typescript
import { apiClient } from '@/api/axios'

export interface AuditLog {
  id: number
  event_type: string
  user_name: string
  module: string | null
  action_time: string
  detail: string | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogsResponse {
  logs: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface AuditStats {
  by_user: { user_name: string; count: number }[]
  by_event: { event_type: string; count: number }[]
  by_module: { module: string; count: number }[]
}

export const auditApi = {
  getLogs: async (params?: {
    user_name?: string
    event_type?: string
    module?: string
    start_time?: string
    end_time?: string
    page?: number
    page_size?: number
  }): Promise<AuditLogsResponse> => {
    const response = await apiClient.get<AuditLogsResponse>('/audit/logs', { params })
    return response.data
  },

  getStats: async (params?: {
    start_time?: string
    end_time?: string
  }): Promise<AuditStats> => {
    const response = await apiClient.get<AuditStats>('/audit/stats', { params })
    return response.data
  },

  exportExcel: (params?: {
    start_time?: string
    end_time?: string
  }) => {
    const queryString = params
      ? '?' + new URLSearchParams(params as any).toString()
      : ''
    window.location.href = `/api/v1/audit/export${queryString}`
  },
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/audit.ts
git commit -m "feat: add audit API client for logs query and export"
```

---

## Task 11: 前端 — 日志查看页面 + 导航入口

**Files:** Create `frontend/src/views/audit/AuditLogs.vue`, Modify `router/index.ts`, Modify `Layout.vue`

- [ ] **Step 1: 创建 `frontend/src/views/audit/AuditLogs.vue`**

```vue
<template>
  <div class="audit-logs-page">
    <el-card>
      <template #header>
        <span>行为日志</span>
        <el-button type="primary" @click="handleExport">导出 Excel</el-button>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="用户名">
          <el-input v-model="filters.user_name" placeholder="用户名" clearable />
        </el-form-item>
        <el-form-item label="事件类型">
          <el-select v-model="filters.event_type" placeholder="全部" clearable>
            <el-option label="user_login" value="user_login" />
            <el-option label="enter_module" value="enter_module" />
            <el-option label="exit_module" value="exit_module" />
            <el-option label="save_to_database" value="save_to_database" />
            <el-option label="generate_document" value="generate_document" />
            <el-option label="system_health_check" value="system_health_check" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="filters.module" placeholder="全部" clearable>
            <el-option label="Phase1" value="phase1" />
            <el-option label="Phase2" value="phase2" />
            <el-option label="Phase3" value="phase3" />
            <el-option label="Dashboard" value="dashboard" />
            <el-option label="DataCenter" value="data-center" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="event_type" label="事件类型" width="180" />
        <el-table-column prop="user_name" label="用户名" width="120" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="action_time" label="发生时间" width="180" />
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="130" />
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadLogs"
        @size-change="loadLogs"
        style="margin-top: 16px"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { auditApi, type AuditLog } from '@/api/audit'
import { ElMessage } from 'element-plus'

const logs = ref<AuditLog[]>([])
const loading = ref(false)

const filters = reactive({
  user_name: '',
  event_type: '',
  module: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0,
})

async function loadLogs() {
  loading.value = true
  try {
    const result = await auditApi.getLogs({
      user_name: filters.user_name || undefined,
      event_type: filters.event_type || undefined,
      module: filters.module || undefined,
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    logs.value = result.logs
    pagination.total = result.total
  } catch {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

function handleExport() {
  auditApi.exportExcel()
}

onMounted(loadLogs)
</script>

<style scoped>
.audit-logs-page {
  padding: 20px;
}
.filter-form {
  margin-bottom: 16px;
}
</style>
```

- [ ] **Step 2: 在 `frontend/src/router/index.ts` 中添加 /audit 路由**

在 routes 中添加：

```typescript
{
  path: '/audit',
  name: 'AuditLogs',
  component: () => import('@/views/audit/AuditLogs.vue'),
  meta: { title: '日志查看' }
},
```

- [ ] **Step 3: 在 `frontend/src/views/Layout.vue` 侧边栏添加"日志"入口**

```html
<router-link to="/audit">
  <el-menu-item index="/audit">
    <el-icon><List /></el-icon>
    <span>日志查看</span>
  </el-menu-item>
</router-link>
```

导入 `List` 图标：`import { List } from '@element-plus/icons-vue'`

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/audit/AuditLogs.vue frontend/src/router/index.ts frontend/src/views/Layout.vue
git commit -m "feat: add audit log viewer page with navigation entry"
```

---

## Task 12: 集成验证

- [ ] **Step 1: 执行迁移，创建表**

```bash
cd backend && python migrations/011_create_audit_logs.py
# Expected: Migration 011 complete: created audit_logs table
```

- [ ] **Step 2: 启动后端和前端**

```bash
# 后端
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev
```

- [ ] **Step 3: 登录后验证 `user_login` 日志写入**

```bash
sqlite3 backend/data/shipping_helper.db "SELECT * FROM audit_logs WHERE event_type='user_login';"
```

- [ ] **Step 4: 验证 enter_module 日志（进入 Phase1）**

```bash
sqlite3 backend/data/shipping_helper.db "SELECT * FROM audit_logs WHERE event_type='enter_module';"
```

- [ ] **Step 5: 测试 API**

```bash
# 查询日志分页
curl -s "http://localhost:8000/api/v1/audit/logs?page=1&page_size=5"

# 导出 Excel
curl -sI "http://localhost:8000/api/v1/audit/export" | grep Content-Disposition
```

- [ ] **Step 6: 测试 batch 鉴权（伪造用户应返回 403）**

```bash
curl -s -X POST "http://localhost:8000/api/v1/audit/batch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <valid_token>" \
  -d '{"events":[{"event_type":"fake","user_name":"hacker","action_time":"2026-06-30T10:00:00Z"}]}'
# Expected: 403 {"detail":"禁止伪造用户日志: expected '张三', got 'hacker'"}
```

- [ ] **Step 7: 提交最终代码**

```bash
git add -A
git commit -m "feat: complete audit log system - all tasks integrated and verified"
```

---

## 实施顺序

**后端**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5
**前端**: Task 6 → Task 7 → Task 8 → Task 9 → Task 10 → Task 11
**验证**: Task 12

每个 Task 完成后独立提交。