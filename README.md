# ShippingHelper 船务部效率工具

外贸船务部的数字化工作流工具，将原 PyQt5 桌面应用重构为现代化 Web 应用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + TypeScript |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 文档服务 | OnlyOffice Document Server（Docker） |

## 项目结构

```
shipping_helper/
├── backend/          # FastAPI 后端
├── frontend/          # Vue 3 前端
├── docs/             # 需求文档、API 文档、测试文档
├── 参考/              # PyQt5 旧版参考实现
└── data/             # SQLite 数据库
```

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### API 文档

启动后端后访问：`http://localhost:8000/docs`

## Phase 1 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 项目初始化 | ✅ | Vue 3 + FastAPI + SQLite |
| 订单粘贴解析 | ✅ | Tab/换行分隔、一单多品、知识库匹配 |
| PI 文件提取 | 🔲 | 待开发 |
| 数据关联 | 🔲 | 待开发 |
| 包装计算 | 🔲 | 待开发 |
| 数据看板 | 🔲 | 待开发 |

## Phase 2 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 出货数据管理 | 🔲 | 待开发 |
| 模板管理 | 🔲 | 待开发 |
| 文档生成 | 🔲 | 通过 OnlyOffice |

## 核心文档

| 文档 | 说明 |
|------|------|
| `docs/PRD-ShippingHelper-Web.md` | 主 PRD |
| `docs/PRD-ShippingHelper-Web-P1v2.md` | Phase 1 详细需求 |
| `docs/PRD-ShippingHelper-Web-P2v2.md` | Phase 2 详细需求 |
| `docs/PRD-ShippingHelper-Web-P1v2-OrderParsing.md` | 订单解析模块设计方案 |
| `docs/API-ShippingHelper-v1.md` | API 接口文档 |
| `docs/TEST-ShippingHelper-v1.md` | 集成测试文档 |

## 架构决策

| 决策 | 选择 |
|------|------|
| 文档编辑器 | OnlyOffice（全栈统一，不使用 Luckysheet） |
| 计算逻辑 | `backend/app/services/calculation_service.py`（Phase 1 & 2 共用） |
| 数据库 | SQLite WAL 模式 |
| 文件存储 | 数据库 BLOB，不使用共享文件夹 |
| 模板原则 | 模板只读，实例从模板复制 |
| 悲观锁 | 订单级锁（`order_status`, `locked_by`, `locked_at`） |

## 数据模型

一张订单（orders）包含多个产品明细（order_items），称为"一单多品"：

```
orders（订单头）
  └── order_items（产品明细，外键→orders.id）
```

**重要**：`internal_code`（内部编码）仅存在于 `order_items`，`orders` 表不存储此字段。

## 常见命令

```bash
# 后端启动
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端启动
cd frontend && npm run dev

# 运行测试
cd backend && python -m pytest tests/ -v
```

## License

Internal use only.