# ShippingHelper API 文档

> 本文档描述 Phase 1 订单粘贴解析模块的 API 接口规范。
> 版本：v1.0.0
> Base URL：`http://localhost:8000`
> 文档地址：`http://localhost:8000/docs`（Swagger UI）

---

## 认证

当前版本无需认证，后续 Phase 2 会添加 Token 认证。

---

## 错误码规范

| HTTP 状态码 | 含义 | 使用场景 |
|-------------|------|----------|
| 200 | 成功 | 正常返回数据 |
| 400 | 请求参数错误 | 解析失败、空文本，分隔符无法识别 |
| 422 | Pydantic 验证错误 | 字段类型不匹配，必填字段缺失 |
| 500 | 服务器内部错误 | 数据库保存失败（事务已回滚） |

**错误响应格式：**

```json
{
  "detail": "错误描述信息"
}
```

---

## 接口列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/orders/paste` | 解析粘贴文本 |
| POST | `/api/v1/orders` | 保存订单 |

---

## 1. 健康检查

### GET `/health`

**描述：** 验证服务是否正常运行。

**响应示例：**

```json
{
  "status": "ok"
}
```

---

## 2. 解析粘贴文本

### POST `/api/v1/orders/paste`

**描述：** 解析用户从 Excel/Spreadsheet 复制的订单数据。

**功能：**
1. 自动识别分隔符（Tab 分隔或换行分隔）
2. 按订单号聚合多行（一单多品）
3. 批次内去重（后出现的同名数据覆盖前面的）
4. 知识库匹配（H.S.Code + 报关品名自动补全）

**请求头：**

```
Content-Type: application/json
```

**请求体：**

```json
{
  "raw_text": "订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg\nHT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400"
}
```

**请求体字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| raw_text | string | ✅ | 粘贴的原始文本，支持 Tab 分隔（Excel）或换行分隔（网页表格） |

**粘贴数据列名映射（支持中英文别名）：**

| 内部字段 | 中文列名 | 英文列名 |
|----------|---------|---------|
| order_no | 订单号 | Order No / PO / PO Number |
| customer_code | 客户编号 | Customer Code / Client Code |
| internal_code | 内部编号 | Internal Code / Product Code / SKU |
| product_cn | 产品中文名 | Product Name (CN) / Description |
| spec_kg | 规格kg | Spec / Specification |
| quantity_kg | 订单量kg | Quantity / QTY (kg) |
| unit_price | 单价/kg | Unit Price / Price per kg |
| total_amount | 总金额 | Total Amount / Amount |
| salesperson | 业务员 | Salesperson / Sales Rep |
| merchandiser | 跟单员 | Merchandiser / Merch |
| customs_name | 报关名称 | Customs Name |
| hs_code | H.S.Code | HS Code / H.S. |

**成功响应（200）：**

```json
{
  "orders": [
    {
      "order_no": "HT260304E01",
      "customer_code": "TOA-DOVECHEM",
      "salesperson": null,
      "items": [
        {
          "internal_code": "SILI-001",
          "product_cn": "有机硅柔软剂",
          "spec_kg": 25.0,
          "quantity_kg": 2400.0,
          "hs_code": null,
          "customs_name": "有机硅柔软剂 25.0kg",
          "hs_code_warning": "H.S.Code 位数不足（当前 0 位），请核对或补足 10 位",
          "warning": "报关品名由系统自动生成，请务必核对！",
          "_selected": true
        }
      ],
      "header_conflict_warning": null
    }
  ],
  "skipped_rows": [],
  "warning": null
}
```

**响应字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| orders | array | 解析出的订单列表 |
| orders[].order_no | string | 订单号 |
| orders[].customer_code | string | 客户编号 |
| orders[].salesperson | string | 业务员 |
| orders[].items | array | 产品明细列表 |
| orders[].items[].internal_code | string | **必填** 内部编码 |
| orders[].items[].product_cn | string | 产品中文名 |
| orders[].items[].spec_kg | float | 规格kg |
| orders[].items[].quantity_kg | float | 订单量kg |
| orders[].items[].hs_code | string | H.S.Code（未匹配为 null） |
| orders[].items[].customs_name | string | 报关品名 |
| orders[].items[].hs_code_warning | string | H.S.Code 位数不足警告（当 hs_code 不足 10 位时） |
| orders[].items[].warning | string | 报关品名自动生成警告 |
| orders[].items[]._selected | boolean | 前端复选框状态 |
| orders[].header_conflict_warning | string | 订单头字段冲突警告（如同一订单号内客户编号不一致） |
| skipped_rows | array | 因缺少必要字段被跳过的行 |
| skipped_rows[].line_index | int | 行号（第几行） |
| skipped_rows[].reason | string | 跳过原因 |
| skipped_rows[].raw_data | array | 原始数据 |
| warning | string | 批次内重复等警告信息 |

**错误响应：**

- `400`：粘贴文本为空或解析失败

```json
{
  "detail": "粘贴文本不能为空"
}
```

- `422`：请求体验证失败

```json
{
  "detail": [
    {
      "loc": ["body", "raw_text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**H.S.Code 知识库匹配优先级：**
1. PI 数据中的 H.S.Code（最高）
2. 知识库按 `internal_code` 精确匹配
3. 知识库按产品中文名精确匹配（长度 > 4）
4. 均未命中 → `hs_code = null`，前端显示"待填写"

**报关品名知识库匹配优先级：**
1. 用户粘贴数据中已有
2. PI 数据中的报关品名
3. 知识库匹配结果
4. 均未命中 → 自动生成 `产品中文名 + 规格kg`，前端显示警告

---

## 3. 保存订单

### POST `/api/v1/orders`

**描述：** 将解析后的订单数据保存到数据库。

**功能：**
- 订单号已存在：**覆盖**旧数据（删除旧 order_items，插入新的）
- 订单号不存在：**新建**订单

**事务保证：** orders（订单头）+ order_items（产品明细）要么全部成功，要么全部回滚，绝不会出现在"订单头存进去了但明细没存进去"的脏数据。

**请求头：**

```
Content-Type: application/json
```

**请求体：**

```json
{
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
```

**请求体字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order.order_no | string | ✅ | 订单号（唯一索引） |
| order.customer_code | string | | 客户编号 |
| order.salesperson | string | | 业务员 |
| order.items | array | | 产品明细列表 |
| order.items[].internal_code | string | ✅ | 内部编码（产品级） |
| order.items[].product_cn | string | | 产品中文名 |
| order.items[].spec_kg | float | | 规格kg |
| order.items[].quantity_kg | float | | 订单量kg |
| order.items[].unit_price | float | | 单价/kg |
| order.items[].total_amount | float | | 总金额 |
| order.items[].hs_code | string | | H.S.Code |
| order.items[].customs_name | string | | 报关品名 |

**成功响应（200）：**

```json
{
  "order_id": 1,
  "items_count": 1,
  "message": "订单 HT260304E01 保存成功，共 1 个产品"
}
```

**响应字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | int | 订单在数据库中的主键 ID |
| items_count | int | 保存的产品明细数量 |
| message | string | 操作结果描述 |

**错误响应：**

- `500`：数据库保存失败

```json
{
  "detail": "保存失败，事务已回滚: <错误信息>"
}
```

- `422`：Pydantic 验证错误

```json
{
  "detail": [
    {
      "loc": ["body", "order", "items", 0, "internal_code"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 数据模型

### orders（订单头表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| order_no | TEXT | 订单号（唯一） |
| customer_code | TEXT | 客户编号 |
| salesperson | TEXT | 业务员 |
| ... | ... | 其他业务字段 |

### order_items（产品明细表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| order_id | INTEGER | 外键 → orders.id |
| internal_code | TEXT | 内部编码（产品级，**必填**） |
| product_cn | TEXT | 产品中文名 |
| spec_kg | REAL | 规格kg |
| quantity_kg | REAL | 订单量kg |
| ... | ... | 其他业务字段 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | `sqlite:///../data/shipping_helper.db` | 数据库连接地址 |

---

## OpenAPI 文档

完整的 OpenAPI（Swagger）文档访问：`http://localhost:8000/docs`

ReDoc 文档访问：`http://localhost:8000/redoc`
