# 登录认证功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 ShippingHelper 添加 JWT 登录认证，用户通过 name + password 验证后才能访问系统。

**Architecture:** JWT Token 认证方案。用户登录后获取 token，后续请求携带 `Authorization: Bearer <token>` header。后端使用 FastAPI 依赖注入保护所有 API 端点（排除登录和健康检查）。前端使用 Pinia 存储 token，Axios 拦截器自动附加 token，路由守卫控制页面访问。

**Tech Stack:** Python-jose (JWT), python-dotenv, Vue 3, Pinia, Axios, Element Plus

---

## 文件结构

### Backend 新建
- `backend/data/users.json` — 用户数据（name + password 明文）
- `backend/app/models/user.py` — User Pydantic 模型
- `backend/app/services/auth_service.py` — JWT 生成 + 用户验证
- `backend/app/api/v1/auth.py` — 登录 API 路由

### Backend 修改
- `backend/app/api/deps.py` — 新增 `get_current_user` 依赖
- `backend/app/main.py` — 注册 auth 路由，全局依赖保护

### Frontend 新建
- `frontend/src/views/auth/Login.vue` — 登录页
- `frontend/src/stores/auth.ts` — Pinia store（token 状态管理）
- `frontend/src/api/axios.ts` — Axios 实例 + 请求拦截器

### Frontend 修改
- `frontend/src/router/index.ts` — 新增登录路由 + 导航守卫

---

## Task 1: 创建 users.json 用户数据文件

**Files:**
- Create: `backend/data/users.json`

- [ ] **Step 1: 创建 users.json**

```json
[
  {"name": "张三", "password": "zhangsan123"}
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/data/users.json && git commit -m "feat: add users.json with default user"
```

---

## Task 2: 创建后端 User 模型

**Files:**
- Create: `backend/app/models/user.py`

- [ ] **Step 1: 创建 user.py**

```python
"""User Pydantic models for authentication."""
from pydantic import BaseModel


class User(BaseModel):
    """User schema from users.json."""
    name: str
    password: str


class LoginRequest(BaseModel):
    name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/user.py && git commit -m "feat: add User Pydantic model"
```

---

## Task 3: 创建 Auth Service

**Files:**
- Create: `backend/app/services/auth_service.py`

**依赖安装：** `backend/app/services/__init__.py` 无需修改（Service 不注册到 FastAPI 路由）

- [ ] **Step 1: 创建 auth_service.py**

```python
"""Authentication service - JWT token generation and user validation."""
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from fastapi import HTTPException, status

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# users.json 路径
USERS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "users.json"
)


def load_users():
    """从 users.json 加载用户列表."""
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_user(name: str, password: str) -> Optional[dict]:
    """验证用户名和密码，返回用户信息或 None."""
    users = load_users()
    for user in users:
        if user.get("name") == name and user.get("password") == password:
            return user
    return None


def create_access_token(name: str) -> str:
    """为用户创建 JWT token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": name,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def authenticate(name: str, password: str) -> dict:
    """认证用户，成功返回 token，失败抛出 HTTPException."""
    user = verify_user(name, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    token = create_access_token(name)
    return {"access_token": token, "token_type": "bearer"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/auth_service.py && git commit -m "feat: add AuthService with JWT token generation"
```

---

## Task 4: 创建 Auth API 路由

**Files:**
- Create: `backend/app/api/v1/auth.py`

- [ ] **Step 1: 创建 auth.py**

```python
"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, status

from app.models.user import LoginRequest, TokenResponse
from app.services.auth_service import authenticate

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """用户登录，验证 name + password，返回 JWT token."""
    try:
        result = authenticate(body.name, body.password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/auth.py && git commit -m "feat: add POST /api/v1/auth/login endpoint"
```

---

## Task 5: 添加 get_current_user 依赖

**Files:**
- Modify: `backend/app/api/deps.py`

- [ ] **Step 1: 添加 get_current_user 到 deps.py**

在文件末尾添加：

```python
"""JWT authentication dependency."""
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
import os

JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


async def get_current_user(authorization: str = Header(...)) -> dict:
    """从 Authorization header 提取并验证 JWT token，返回用户信息."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization.startswith("Bearer "):
        raise credentials_exception
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        name: str = payload.get("sub")
        if name is None:
            raise credentials_exception
        return {"name": name}
    except JWTError:
        raise credentials_exception
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/deps.py && git commit -m "feat: add get_current_user JWT dependency"
```

---

## Task 6: 注册 Auth 路由并添加全局依赖保护

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 添加 auth 路由导入和注册**

在导入部分添加：
```python
from app.api.v1.auth import router as auth_router
```

在路由注册部分（其他 router.include_router 之后）添加：
```python
app.include_router(auth_router)
```

- [ ] **Step 2: 添加全局依赖保护（排除 login 和 health）**

在 `app.include_router(auth_router)` 之后添加：

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
import os

JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """全局认证中间件，排除登录和健康检查端点."""
    # 放行路径
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or \
       request.url.path.startswith("/api/v1/auth/"):
        return await call_next(request)
    
    # 检查 Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "未授权，请先登录"}
        )
    
    # 验证 token
    from jose import jwt, JWTError
    import os
    try:
        token = auth_header[7:]
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production"),
            algorithms=["HS256"]
        )
        request.state.user = {"name": payload.get("sub")}
    except JWTError:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "无效的认证凭证"}
        )
    
    return await call_next(request)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py && git commit -m "feat: add auth router and global auth middleware"
```

---

## Task 7: 创建前端 Axios 拦截器

**Files:**
- Create: `frontend/src/api/axios.ts`

- [ ] **Step 1: 创建 axios.ts**

```typescript
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const BASE_URL = '/api/v1'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// 请求拦截器：自动附加 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理 401 未授权
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/axios.ts && git commit -m "feat: add axios interceptor with JWT auth"
```

---

## Task 8: 创建 Pinia Auth Store

**Files:**
- Create: `frontend/src/stores/auth.ts`

- [ ] **Step 1: 创建 auth.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/api/axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const userName = ref<string | null>(localStorage.getItem('user_name'))

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(newToken: string, name: string) {
    token.value = newToken
    userName.value = name
    localStorage.setItem('access_token', newToken)
    localStorage.setItem('user_name', name)
  }

  function logout() {
    token.value = null
    userName.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_name')
  }

  async function login(name: string, password: string) {
    const response = await apiClient.post('/auth/login', { name, password })
    const { access_token } = response.data
    setAuth(access_token, name)
    return true
  }

  return {
    token,
    userName,
    isLoggedIn,
    setAuth,
    logout,
    login,
  }
})
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/auth.ts && git commit -m "feat: add Pinia auth store"
```

---

## Task 9: 创建登录页面

**Files:**
- Create: `frontend/src/views/auth/Login.vue`

**配色规范（与 global.css 一致）：**
- 主色：`#0077cc`
- 背景：`#f5f7fa`
- 卡片：`#ffffff`
- 文字主色：`#1a1a2e`

- [ ] **Step 1: 创建 Login.vue**

```vue
<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="brand-mark">
          <svg width="48" height="48" viewBox="0 0 28 28" fill="none">
            <path d="M14 2L25 8V20L14 26L3 20V8L14 2Z" stroke="currentColor" stroke-width="2" fill="none"/>
            <path d="M14 10L19 13V19L14 22L9 19V13L14 10Z" fill="currentColor"/>
          </svg>
        </div>
        <h1 class="login-title">ShippingHelper</h1>
        <p class="login-subtitle">船务效率工具</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  name: '',
  password: '',
})

const rules = {
  name: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form.name, form.password)
    ElMessage.success('登录成功')
    router.push('/workflow')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-primary);
}

.login-card {
  width: 400px;
  padding: 48px 40px;
  background: var(--bg-card);
  border-radius: 20px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-light);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  color: var(--color-primary);
  margin-bottom: 16px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.login-form {
  margin-top: 24px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/auth/Login.vue && git commit -m "feat: add login page"
```

---

## Task 10: 配置路由守卫

**Files:**
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: 修改 router/index.ts**

添加导入：
```typescript
import { useAuthStore } from '@/stores/auth'
```

在 `router.beforeEach` 中添加认证逻辑：
```typescript
router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string || 'ShippingHelper') + ' - ShippingHelper'
  
  const authStore = useAuthStore()
  
  // 允许访问登录页
  if (to.path === '/login') {
    if (authStore.isLoggedIn) {
      next('/workflow')
    } else {
      next()
    }
    return
  }
  
  // 其他页面需要登录
  if (!authStore.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})
```

在 routes 数组中添加登录路由：
```typescript
{
  path: '/login',
  name: 'Login',
  component: () => import('@/views/auth/Login.vue'),
  meta: { title: '登录', public: true }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/router/index.ts && git commit -m "feat: add login route and auth guard"
```

---

## Task 11: 安装后端 JWT 依赖

**Files:**
- Modify: `backend/requirements.txt`（如果存在）

- [ ] **Step 1: 检查并添加依赖**

检查 `backend/requirements.txt` 是否存在，如存在则添加：
```
python-jose[cryptography]
```

如果不存在，检查项目是否有其他依赖管理方式（pyproject.toml 等）。

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt 2>/dev/null || true
git commit -m "chore: add python-jose for JWT support"
```

---

## Task 12: 验证登录功能

- [ ] **Step 1: 启动后端**

```bash
cd backend && pip install python-jose[cryptography] && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 测试登录 API**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"name": "张三", "password": "zhangsan123"}'
```

预期返回：`{"access_token": "eyJ...", "token_type": "bearer"}`

- [ ] **Step 3: 测试受保护端点（不带 token）**

```bash
curl http://localhost:8000/api/v1/orders
```

预期返回：401 `{"detail": "未授权，请先登录"}`

- [ ] **Step 4: 测试受保护端点（带 token）**

```bash
TOKEN="<上面返回的token>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/orders
```

预期返回：正常数据或空数组

- [ ] **Step 5: 启动前端并测试 UI**

```bash
cd frontend && npm run dev
```

访问 http://localhost:5173/login，使用 张三/zhangsan123 登录，验证跳转到 /workflow。

---

## 自检清单

- [ ] users.json 创建，格式正确
- [ ] user.py Pydantic 模型定义正确
- [ ] auth_service.py JWT 生成和验证逻辑正确
- [ ] auth.py 路由注册到 /api/v1/auth/login
- [ ] deps.py 中 get_current_user 依赖正确
- [ ] main.py 中间件正确排除 /health 和 /api/v1/auth/*
- [ ] frontend axios.ts 拦截器正确附加 token
- [ ] frontend auth.ts store 正确管理 token 状态
- [ ] Login.vue 样式与 global.css 配色一致
- [ ] router 守卫正确跳转未登录用户到 /login
- [ ] python-jose 依赖已添加并安装
- [ ] 登录流程测试通过
