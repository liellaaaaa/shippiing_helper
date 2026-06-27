# 系统连通性检测 - 设计文档

## 概述

在导航栏添加系统连通性检测按钮，后端新增 `/api/v1/health` 接口统一检查 API、OnlyOffice、SQLite、Tesseract 四项组件的存活状态，前端点击按钮后以 popover 展示结果。

## 后端

### 接口

`GET /api/v1/health`

已在 `main.py` 中存在（返回 `{"status": "ok"}`），将其扩展为：

```json
{
  "status": "ok|degraded",
  "checks": {
    "api":        { "status": "ok|error", "message": "正常运行" },
    "onlyoffice": { "status": "ok|error", "message": "Connected" },
    "database":   { "status": "ok|error", "message": "正常" },
    "tesseract":  { "status": "ok|error", "message": "tesseract 5.3.1" }
  }
}
```

HTTP 状态码始终为 200，由 `status` 字段区分整体状态。

### 检查项实现

| 检查项 | 实现方式 |
|--------|---------|
| API | 直接返回 `"ok"` |
| OnlyOffice | `httpx.get(DOCUMENT_SERVER_URL + "/health")`，成功返回 `"ok"` |
| SQLite | 通过 SQLAlchemy 执行 `SELECT 1`，验证读写正常 |
| Tesseract | `subprocess.run(["tesseract", "--version"])`，解析版本号返回 |

任意一项失败不影响其他项检查，全部完成后以最差结果决定整体 `status`（任意一项 `error` → `"degraded"`）。

### 异常处理

- OnlyOffice 连接超时 5s，失败返回 `error` + 错误信息
- SQLite 连接失败返回 `error` + 错误信息
- Tesseract 命令不存在返回 `error` + 错误信息

## 前端

### 位置

`frontend/src/views/Layout.vue`，在 `.nav-actions` 区域、用户下拉菜单左边插入检测按钮。

### 按钮样式

图标按钮（el-button circle），SVG 雷达/检测图标，tooltip 文案："系统检测"。

### 结果展示

点击后调用 `GET /api/v1/health`，结果以 `el-popover` 展示：

- 每项一行：`✅/❌ 名称  信息`
- 顶部显示整体状态 badge（ok → 绿色，degraded → 红色）
- 可手动再次检测

### 无权限要求

`/health` 接口已在 `auth_middleware` 中全局放行，无需登录即可访问。
