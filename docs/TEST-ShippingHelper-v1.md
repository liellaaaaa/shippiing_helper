# ShippingHelper 集成测试文档

> 本文档描述 Phase 1 订单粘贴解析模块的测试策略、用例和运行方法。
> 测试范围：后端单元测试 + API 集成测试

---

## 测试策略

### 分层测试

```
┌─────────────────────────────────────┐
│         API 集成测试                 │
│   (HTTP 请求 + 真实数据库)           │
│   测试 REST API 端到端流程           │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         Service 层测试               │
│   (Business Logic + Transaction)     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         Parser/Knowledge 测试        │
│   (单元测试，Mock 数据库)           │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         Model 测试                   │
│   (ORM 关系 + 数据库约束)            │
└─────────────────────────────────────┘
```

### 测试工具

| 类型 | 工具 | 说明 |
|------|------|------|
| 单元测试 | pytest | Python 测试框架 |
| Mock | `unittest.mock` | 模拟数据库查询 |
| HTTP 测试 | `requests` | 测试 FastAPI API 端点 |
| 数据库 | SQLite（真实文件） | 集成测试使用真实数据库 |

---

## 单元测试

### 运行方法

```bash
cd backend
python -m pytest tests/ -v
```

### 测试文件

#### `tests/test_order_parser.py`

测试 `core/order_parser.py` 的解析逻辑。

| 测试用例 | 描述 | 预期结果 |
|---------|------|----------|
| `test_parse_single_order_single_item` | 解析单订单单产品 | 1 个订单，1 个产品 |
| `test_parse_single_order_multiple_items` | 解析单订单多产品（一单多品） | 1 个订单，2 个产品 |
| `test_parse_batch_dedup` | 批次内去重（后行覆盖前行） | 警告信息，qty 以最后为准 |
| `test_parse_missing_internal_code_skipped` | 缺失 internal_code 被跳过 | skipped_rows 长度为 1 |
| `test_normalize_column_name` | 列名标准化映射 | "订单号" → order_no |

**测试数据示例：**

```python
# 单订单多产品
text = """订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂A\t25\t2400
HT260304E01\tTOA-DOVECHEM\tSILI-002\t有机硅柔软剂B\t50\t1600"""

# 结果：1 个订单，items 列表包含 2 个产品
```

```python
# 批次内去重
text = """订单号\t客户编号\t内部编号\t产品中文名\t订单量kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t1000
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t2000"""

# 结果：warning 包含"检测到 1 行重复数据"，quantity_kg = 2000
```

#### `tests/test_knowledge_filler.py`

测试 `core/knowledge_filler.py` 的知识库匹配逻辑。

| 测试用例 | 描述 | 预期结果 |
|---------|------|----------|
| `test_fill_from_internal_code` | internal_code 精确命中 | hs_code 和 customs_name 被填充 |
| `test_hs_code_length_warning` | H.S.Code 位数不足 | hs_code_warning 包含"位数不足" |
| `test_customs_name_auto_generate` | 知识库无匹配 | customs_name 自动生成，含"自动生成"警告 |
| `test_hs_code_from_pi_data_takes_priority` | PI 数据优先级最高 | pi_data 中的 hs_code 被采用 |

#### `tests/test_models.py`

测试 SQLAlchemy 模型和关系。

| 测试用例 | 描述 | 预期结果 |
|---------|------|----------|
| `test_order_item_relationship` | 订单-明细关系 | 创建 Order + 2 个 OrderItem，查询返回 2 个 items |

---

## API 集成测试

### 运行方法（手动）

**Step 1：启动后端服务**

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Step 2：验证服务运行**

```bash
curl http://localhost:8000/health
# 预期输出：{"status":"ok"}
```

**Step 3：测试 Paste 端点**

```python
import requests

url = "http://localhost:8000/api/v1/orders/paste"
payload = {
    "raw_text": "订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg\n"
                "HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400"
}
r = requests.post(url, json=payload)
print(f"Status: {r.status_code}")
print(f"Orders: {len(r.json()['orders'])}")
print(f"Items: {len(r.json()['orders'][0]['items'])}")
```

**预期结果：**
- Status: 200
- Orders: 1
- Items: 1
- `items[0].internal_code`: "SILI-001"

**Step 4：测试 Save 端点**

```python
import requests

url = "http://localhost:8000/api/v1/orders"
payload = {
    "order": {
        "order_no": "HT260304E01",
        "customer_code": "TOA-DOVECHEM",
        "salesperson": "张三",
        "items": [
            {
                "internal_code": "SILI-001",
                "product_cn": "有机硅柔软剂",
                "spec_kg": 25.0,
                "quantity_kg": 2400.0,
                "unit_price": 29.5,
                "total_amount": 70800.0
            }
        ]
    }
}
r = requests.post(url, json=payload)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")
```

**预期结果：**
- Status: 200
- `order_id`: 1
- `items_count`: 1
- `message`: "订单 HT260304E01 保存成功，共 1 个产品"

**Step 5：验证数据库写入**

```python
from backend.app.database import SessionLocal
from backend.app.models import Order, OrderItem

db = SessionLocal()
order = db.query(Order).filter_by(order_no="HT260304E01").first()
print(f"Order: {order.order_no}, Customer: {order.customer_code}")
items = db.query(OrderItem).filter_by(order_id=order.id).all()
print(f"Items count: {len(items)}")
for item in items:
    print(f"  - {item.internal_code}: {item.product_cn}, {item.quantity_kg}kg")
db.close()
```

**预期结果：**
- Order: HT260304E01, Customer: TOA-DOVECHEM
- Items count: 1
- Item: SILI-001, 有机硅柔软剂, 2400.0kg

---

## 测试用例库

### TC-001：一单多品解析

**目的：** 验证同一订单号的多行数据能正确聚合

**输入数据：**
```
订单号	客户编号	内部编号	产品中文名	规格kg	订单量kg
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂A	25	2400
HT260304E01	TOA-DOVECHEM	SILI-002	有机硅柔软剂B	50	1600
```

**预期输出：**
- orders 数量：1
- items 数量：2
- `orders[0].items[0].internal_code`: "SILI-001"
- `orders[0].items[1].internal_code`: "SILI-002"

---

### TC-002：批次内去重

**目的：** 验证重复行被后行者覆盖

**输入数据：**
```
订单号	客户编号	内部编号	产品中文名	订单量kg
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂	1000
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂	2000
```

**预期输出：**
- warning 包含："检测到 1 行重复数据"
- 最终 quantity_kg: 2000

---

### TC-003：缺失 internal_code 跳行

**目的：** 验证缺失 internal_code 的行不被丢弃，而是显示为跳行

**输入数据：**
```
订单号	客户编号	内部编号	产品中文名
HT260304E01	TOA-DOVECHEM	SILI-001	有机硅柔软剂
HT260304E01	TOA-DOVECHEM		改性硅油
```

**预期输出：**
- skipped_rows 数量：1
- `skipped_rows[0].reason`: "缺少必要字段: 内部编码"
- orders 数量：1（第一条正常解析）

---

### TC-004：保存订单（新建）

**目的：** 验证新订单能正确写入数据库

**操作：** 调用 `POST /api/v1/orders` 保存新订单

**预期结果：**
- order_id 为数据库自增 ID（> 0）
- order_items 数量正确

---

### TC-005：保存订单（覆盖）

**目的：** 验证已存在订单被正确覆盖

**操作：**
1. 保存订单 HT260304E01（1 个产品）
2. 再次保存同一订单号（2 个产品）

**预期结果：**
- order_id 相同（覆盖）
- order_items 数量：2（覆盖后为新的）

---

### TC-006：H.S.Code 10 位校验

**目的：** 验证 H.S.Code 不足 10 位时前端能显示警告

**输入：** internal_code 在知识库中，匹配的 H.S.Code 为 "3910"（4 位）

**预期输出：**
- `hs_code`: "3910"
- `hs_code_warning`: "H.S.Code 位数不足（当前 4 位），请核对或补足 10 位"

---

## 常见问题

### Q：测试报 `ModuleNotFoundError: No module named 'app'`

**原因：** 运行测试时当前目录不在 `backend/` 下。

**解决：**
```bash
cd backend
python -m pytest tests/ -v
```

### Q：端口 8000 被占用

**解决：**
```bash
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### Q：SQLite 数据库文件不存在

**解决：** 数据库文件会在首次调用 `SessionLocal()` 时自动创建。如需手动初始化：
```bash
cd backend
python -c "from app.database import init_db; init_db()"
```

---

## 覆盖率目标

| 模块 | 覆盖率目标 |
|------|-----------|
| core/order_parser.py | ≥ 90% |
| core/knowledge_filler.py | ≥ 90% |
| services/order_service.py | ≥ 80% |

---

## CI/CD（后续扩展）

后续接入 CI 时，建议：
1. 每次 PR 必须通过所有单元测试
2. API 集成测试在 staging 环境运行
3. 测试覆盖率低于目标时禁止合并
