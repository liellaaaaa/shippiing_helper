# 登录认证功能设计

## 概述

为 ShippingHelper 添加简单的 JWT 登录认证，用户通过 name + password 验证后才能使用系统。

## 配色规范

保持与现有系统一致：
- 主色：`#0077cc`（蓝）
- 浅蓝：`#00a8e8`
- 背景：`#f5f7fa`
- 卡片：`#ffffff`
- 文字主色：`#1a1a2e`
- 文字次级：`#5a6178`

## 架构设计

### 数据层

**文件：** `backend/data/users.json`

```json
[
  {"name": "张三", "password": "zhangsan123"}
]
```

### 后端

| 文件 | 职责 |
|------|------|
| `backend/app/models/user.py` | User 模型（不持久化，仅认证用） |
| `backend/app/services/auth_service.py` | 验证用户、生成 JWT |
| `backend/app/api/v1/auth.py` | 登录接口 `POST /api/v1/auth/login` |
| `backend/app/api/deps.py` | 新增 `get_current_user` 依赖 |

**API：**

```
POST /api/v1/auth/login
Body: {"name": "张三", "password": "zhangsan123"}
Response: {"access_token": "xxx", "token_type": "bearer"}
Error 401: {"detail": "用户名或密码错误"}
```

**受保护端点：** 除 `POST /auth/login`、`GET /health` 外全部需要 Authorization header。

**JWT 配置：**
- 算法：HS256
- 过期：24小时（可配置）
- 密钥：环境变量 `JWT_SECRET`

### 前端

| 文件 | 职责 |
|------|------|
| `frontend/src/views/auth/Login.vue` | 登录页 |
| `frontend/src/stores/auth.ts` | Pinia store（token 状态） |
| `frontend/src/api/axios.ts` | Axios 拦截器（自动附加 token） |
| `frontend/src/router/index.ts` | 路由守卫（未登录跳转登录页） |

**登录页 UI：**
- 居中卡片，主题蓝 logo
- 两个输入框：用户名、密码
- 登录按钮（primary 蓝色）
- 错误提示使用 Element Plus Message

**登录成功后：** 跳转至 `/workflow`

## 实现步骤

1. 创建 `backend/data/users.json`
2. 创建 `backend/app/models/user.py`
3. 创建 `backend/app/services/auth_service.py`
4. 创建 `backend/app/api/v1/auth.py`
5. 在 `backend/app/api/deps.py` 添加 `get_current_user`
6. 在 `backend/app/main.py` 全局依赖保护（排除 login 和 health）
7. 创建 `frontend/src/views/auth/Login.vue`
8. 创建 `frontend/src/stores/auth.ts`
9. 配置 Axios 拦截器
10. 添加路由守卫

## 错误处理

- 用户不存在：401
- 密码错误：401
- Token 过期/无效：401 → 跳转登录页
