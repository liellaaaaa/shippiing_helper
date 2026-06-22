# ShippingHelper API 文档

> 外贸船务效率工具 — 完整 API 接口规范。
> 版本：v2.1.0（2026-06-22）
> Base URL：`http://localhost:8000`
> 文档地址：`http://localhost:8000/docs`（Swagger UI）

---

## 认证

**JWT Token 认证**（2026-06-18 实现）

所有 API 端点（除登录和健康检查外）均需要认证。

**登录流程：**
1. 调用 `POST /api/v1/auth/login` 获取 token
2. 后续请求携带 `Authorization: Bearer <token>` header

**错误响应（401）：**
```json
{ "detail": "未授权，请先登录" }
```

---

## 错误码规范

| HTTP 状态码 | 含义 | 使用场景 |
|-------------|------|----------|
| 200 | 成功 | 正常返回数据 |
| 400 | 请求参数错误 | 解析失败、空文本，分隔符无法识别 |
| 401 | 未授权 | 未登录或 token 无效 |
| 404 | 资源不存在 | 订单/记录/文件不存在 |
| 422 | Pydantic 验证错误 | 字段类型不匹配，必填字段缺失 |
| 500 | 服务器内部错误 | 数据库保存失败（事务已回滚） |

**错误响应格式：**

```json
{
  "detail": "错误描述信息"
}
```

---

## 接口总览

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| **认证** | | |
| POST | `/api/v1/auth/login` | 用户登录，获取 JWT token |
| **订单管理** | | |
| POST | `/api/v1/orders/paste` | 解析粘贴文本 |
| POST | `/api/v1/orders` | 保存订单 |
| GET | `/api/v1/orders/{id}` | 查询单个订单 |
| **PI 合同管理** | | |
| POST | `/api/v1/pi/upload` | 上传并解析 PI 文件 |
| POST | `/api/v1/pi/contracts` | 保存 PI 合同（待实现） |
| GET | `/api/v1/pi/contracts` | 查询 PI 合同（待实现） |
| **数据关联** | | |
| GET | `/api/v1/merge/orders` | 查询订单列表（含关联状态） |
| GET | `/api/v1/merge/orders/{order_id}/comparison` | 订单比对数据 |
| GET | `/api/v1/merge/orders/{order_id}/pi-contracts` | 订单关联的 PI 合同 |
| **包装计算** | | |
| GET | `/api/v1/packaging/types` | 获取所有包装种类 |
| GET | `/api/v1/packaging/pallets` | 获取所有托盘种类 |
| POST | `/api/v1/packaging/calculate` | 计算包装方案 |
| POST | `/api/v1/packaging/calculate-schemes` | 计算所有包装方案 |
| POST | `/api/v1/packaging/calculate-order` | 订单级别包装汇总计算 |
| GET | `/api/v1/packages/calculate` | 包装计算统一入口（海运/空运/陆运） |
| GET | `/api/v1/packages/types` | 获取所有包装类型（用于下拉） |
| GET | `/api/v1/packages/recommend` | 根据 internal_code 推荐包装类型 |
| **数据看板** | | |
| GET | `/api/v1/dashboard/orders` | 获取数据看板合并数据 |
| GET | `/api/v1/dashboard/export` | 导出数据看板 Excel |
| POST | `/api/v1/dashboard/records` | 落库 — 双轨合并数据写入 |
| GET | `/api/v1/dashboard/records` | 查询落库记录 |
| GET | `/api/v1/dashboard/records/{record_id}` | 查询单条落库记录 |
| DELETE | `/api/v1/dashboard/records/{record_id}` | 删除订单 |
| **文档生成** | | |
| POST | `/api/v1/documents/booking` | 生成订舱单 |
| GET | `/api/v1/documents/loi` | 生成 LOI |
| GET | `/api/v1/documents/msds` | 生成 MSDS |
| GET | `/api/v1/documents/msds/{msds_id}` | 加载指定 MSDS 文件 |
| GET | `/api/v1/documents/customs` | 生成出口报关资料 |
| GET | `/api/v1/documents/history/{order_id}` | 获取文档历史版本 |
| GET | `/api/v1/documents/template/{template_type}` | 打开空白模板 |
| GET | `/api/v1/documents/my-templates` | 我的模板列表 |
| **OnlyOffice** | | |
| POST | `/api/v1/onlyoffice/jwt` | 创建 JWT 配置 |
| POST | `/api/v1/onlyoffice/callback` | OnlyOffice 保存回调 |
| GET | `/api/v1/onlyoffice/download/{doc_key}` | 下载文档 |
| **MSDS** | | |
| GET | `/api/v1/msds/` | MSDS 列表（分页） |
| GET | `/api/v1/msds/{msds_id}/content` | 获取 MSDS 内容和物理特性 |
| POST | `/api/v1/msds/reindex` | 重建 MSDS 索引 |
| **运输** | | |
| POST | `/api/v1/transport/upload` | 上传运输鉴定报告（PDF） |
| **出口编码** | | |
| GET | `/api/v1/export-codes/` | 查询出口编码（HS Code） |
| **数据中心** | | |
| GET | `/api/v1/data-center/search` | 数据中心搜索（MSDS） |
| GET | `/api/v1/data-center/files/{file_id}` | 预览 MSDS 文件 |
| POST | `/api/v1/data-center/upload-corrected/{file_id}` | 上传修正版 MSDS |
| POST | `/api/v1/data-center/reindex` | 重建数据中心索引 |
| GET | `/api/v1/data-center/summary/{file_id}` | 获取 MSDS 摘要 |
| GET | `/api/v1/data-center/tree` | 获取 references/ 目录树 |
| GET | `/api/v1/data-center/file` | 按路径读取文件 |
| **运输鉴定报告** | | |
| GET | `/api/v1/transport-reports/search` | 搜索运输鉴定报告 |
| GET | `/api/v1/transport-reports/files/{filename}` | 预览运输鉴定报告 PDF |
| POST | `/api/v1/transport-reports/reindex` | 重建运输鉴定报告索引 |
| **品名对照** | | |
| GET | `/api/v1/name-mapping` | 获取所有品名对照数据 |
| GET | `/api/v1/name-mapping/lookup` | 查询对应语言名称 |

---

## 1. 健康检查

### GET `/health`

**响应：**

```json
{ "status": "ok" }
```

---

## 2. 用户登录

### POST `/api/v1/auth/login`

用户登录，验证用户名和密码，返回 JWT token。

**请求体：**

```json
{
  "name": "张三",
  "password": "zhangsan123"
}
```

**成功响应（200）：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误响应（401）：**

```json
{ "detail": "用户名或密码错误" }
```

**说明：**
- `access_token` 有效期 24 小时
- 后续请求需在 Header 中携带：`Authorization: Bearer <access_token>`
- 用户数据存储在 `backend/data/users.json`

---

## 3. 解析粘贴文本

### POST `/api/v1/orders/paste`

解析用户从 Excel/Spreadsheet 复制的订单数据。

**功能：**
1. 自动识别分隔符（Tab 分隔或换行分隔）
2. 按订单号聚合多行（一单多品）
3. 批次内去重（后出现的同名数据覆盖前面的）
4. 知识库匹配（H.S.Code + 报关品名自动补全）

**请求体：**

```json
{
  "raw_text": "订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg\nHT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400"
}
```

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
          "customs_name": null
        }
      ],
      "header_conflict_warning": null
    }
  ],
  "skipped_rows": [],
  "warning": null
}
```

---

## 4. 保存订单

### POST `/api/v1/orders`

将解析后的订单数据保存到数据库。

- 订单号已存在：**覆盖**旧数据
- 订单号不存在：**新建**订单

**事务保证：** orders + order_items 要么全部成功，要么全部回滚。

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

**响应：**

```json
{
  "order_id": 1,
  "items_count": 1,
  "message": "订单 HT260304E01 保存成功，共 1 个产品"
}
```

---

## 5. 上传并解析 PI 文件

### POST `/api/v1/pi/upload`

支持 `.xlsx`、`.xls`、`.pdf` 格式，自动解析 PI 合同。

**请求：** `multipart/form-data`，`file` 字段

**响应：**

```json
{
  "pi_no": "PI20260315",
  "customer_code": "TOA-DOVECHEM",
  "sales_person": "张三",
  "pi_date": "2026-03-15",
  "consignee_name": "...",
  "consignee_address": "...",
  "destination": "...",
  "items": [
    {
      "internal_code": "SILI-001",
      "quantity": 2400,
      "unit_price": 29.5,
      "total_amount": 70800,
      "product_color": "...",
      "hs_code": "...",
      "customs_name": "...",
      "customs_composition": "...",
      "order_customs_name": "...",
      "notes": "..."
    }
  ],
  "confidence": 0.95
}
```

---

## 6. 数据看板

### GET `/api/v1/dashboard/orders`

获取数据看板合并数据（按订单分组，支持分页和筛选）。

**参数：**
- `search`: 模糊搜索（订单号/客户编码/PI号）
- `status`: 状态筛选（`pending` / `confirmed`）
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20，最大 200）

### POST `/api/v1/dashboard/records`

Phase 1 核心落库接口。接收订单+PI+包装数据，写入 `order_pi_records` 表。

**请求体：**

```json
{
  "order_data": { ... },
  "pi_data": { ... },
  "packaging_result": { ... }
}
```

**响应：**

```json
{
  "record_id": 1,
  "status": "confirmed",
  "message": "数据已成功落库"
}
```

### GET `/api/v1/dashboard/export`

导出数据看板 Excel 文件。

---

## 7. 数据关联

### GET `/api/v1/merge/orders`

查询订单列表（含关联状态），支持 Tab 筛选和分页。

**参数：**
- `tab`: `pending` / `completed` / `all`
- `search`: 模糊搜索
- `page`: 页码
- `page_size`: 每页数量

### GET `/api/v1/merge/orders/{order_id}/comparison`

获取指定订单的合并比对数据，包含每个 item 的 `diff.status` 和 flags。

### GET `/api/v1/merge/orders/{order_id}/pi-contracts`

获取指定订单关联的所有 PI 合同列表。

---

## 8. 包装计算

### GET `/api/v1/packaging/types`

返回所有包装种类（含规格参数）。

### POST `/api/v1/packaging/calculate`

输入包装种类+数量+是否打卡板 → 返回计算结果。

**请求体：**

```json
{
  "packaging_name": "铁桶 200L",
  "order_qty_kg": 2400.0,
  "use_pallet": true
}
```

**响应：**

```json
{
  "drums": 12,
  "pallets": 1,
  "drums_per_pallet": 12,
  "pallet_type": "1.1*1.1m",
  "total_cbm": 2.16,
  "total_weight_kg": 534.0,
  "fits_20gp": true,
  "fits_40gp": true,
  "recommended": "20GP",
  "remainder": 0,
  "full_pallets": 1
}
```

### POST `/api/v1/packaging/calculate-order`

订单级别包装汇总计算，支持多产品。

### GET `/api/v1/packages/calculate`

包装计算统一入口，支持海运/空运/陆运三种模式。

**参数：**
- `mode`: `order` / `manual`
- `quantity_kg`: 订单量 kg
- `packaging_name`: 包装类型名称
- `pallet_spec`: `1.0x1.0` / `1.1x1.1`
- `pallet_qty`: 单板数量
- `no_pallet`: 是否不打卡板
- `transport_mode`: `sea` / `air` / `land`

---

## 9. 文档生成

### POST `/api/v1/documents/booking`

生成订舱单，字段通过 JSON body 传入。

**请求体：**

```json
{
  "shipper": "...",
  "consignee": "...",
  "notify": "...",
  "cut_off_date": "...",
  "place_of_receipt": "...",
  "pol": "...",
  "pod": "...",
  "place_of_delivery": "...",
  "marks": "...",
  "no_kind_pkg": "...",
  "desc": "...",
  "gross_weight": "...",
  "measurement": "...",
  "template_type": "xlsx"
}
```

### GET `/api/v1/documents/loi`

生成 LOI。参数：`order_no`, `pi_no`。

### GET `/api/v1/documents/msds`

生成 MSDS。参数：`product`。

### GET `/api/v1/documents/customs`

生成出口报关资料工作簿（5个 sheet 的 xlsx）。参数：`order_id`。

### GET `/api/v1/documents/template/{template_type}

打开空白模板。`template_type`: `booking` / `loi` / `msds`。

### GET `/api/v1/documents/my-templates`

我的模板列表（独立于订单的模板实例）。

---

## 10. OnlyOffice 回调

### POST `/api/v1/onlyoffice/callback`

OnlyOffice Document Server 保存文档时的回调接口。

**参数：**
- `doc_key`: 文档键
- `user`: 用户名

**请求：** `multipart/form-data`，`file` 字段（文件流）

**行为：**
1. 接收 Document Server 发送的文件流
2. 检查 content_hash 避免重复保存
3. 写入 `shipment_docs` 表
4. 版本号递增

### GET `/api/v1/onlyoffice/download/{doc_key}`

下载指定版本的文档。

---

## 11. 数据中心

### GET `/api/v1/data-center/search`

三级优先级搜索 MSDS 文件（文件名/产品名/物理特性）。

参数：`q` 查询字符串。

### GET `/api/v1/data-center/tree`

返回完整 `references/` 目录树。

### GET `/api/v1/data-center/file`

按文件路径直接读取 `references/` 下的文件。参数：`path`。

---

## 12. 运输鉴定报告

### GET `/api/v1/transport-reports/search`

在 `references/海运鉴定报告/` 目录中搜索 PDF。参数：`q`。

### POST `/api/v1/transport-reports/reindex`

手动重建运输鉴定报告索引。

---

## 13. 品名对照

### GET `/api/v1/name-mapping/lookup`

查询对应语言名称。

参数：`cn` 或 `en`（二选一）。

---

## 数据模型

### orders（订单头表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| order_no | TEXT | 订单号（唯一） |
| customer_code | TEXT | 客户编号 |
| salesperson | TEXT | 业务员 |
| order_status | TEXT | 订单状态 |
| locked_by | TEXT | 锁定人 |
| locked_at | DATETIME | 锁定时间 |

### order_items（产品明细表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| order_id | INTEGER | 外键 → orders.id |
| internal_code | TEXT | 内部编码（产品级，**必填**） |
| product_cn | TEXT | 产品中文名 |
| spec_kg | REAL | 规格kg |
| quantity_kg | REAL | 订单量kg |

### order_pi_records（合并记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| order_no | TEXT | 订单号 |
| customer_code | TEXT | 客户编号 |
| internal_code | TEXT | 内部编码 |
| product_cn | TEXT | 产品中文名 |
| quantity_kg | REAL | 订单量 |
| pi_no | TEXT | PI 号 |
| status | TEXT | pending / confirmed |

### pi_contracts（PI 合同表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| pi_no | TEXT | PI 合同号 |
| customer_code | TEXT | 客户编码 |
| sales_person | TEXT | 业务员 |
| pi_date | DATE | PI 日期 |
| consignee_name | TEXT | 收货人 |
| destination | TEXT | 目的地 |

### packaging_types（包装类型表）

13 种包装类型，含桶身体参数、容量、托盘配合等信息。

### pallets（托盘类型表）

2 种托盘：`1.0x1.0m` 和 `1.1x1.1m`。

### shipment_docs（文档版本表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| doc_key | TEXT | 文档键 |
| doc_type | TEXT | booking / loi / msds / customs |
| order_id | INTEGER | 关联订单 ID |
| file_blob | TEXT | Base64 编码的文件内容 |
| content_hash | TEXT | MD5 哈希（用于去重） |
| version | INTEGER | 版本号 |
| file_name | TEXT | 文件名 |

### msds_index（MSDS 索引表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| filename | TEXT | 文件名 |
| product_name_cn | TEXT | 产品中文名 |
| physical_form | TEXT | 物理形态 |
| ion_type | TEXT | 离子类型 |
| ph | TEXT | pH 值 |
| file_path | TEXT | 文件路径 |

### transport_report（运输鉴定报告索引表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| filename | TEXT | 文件名 |
| file_path | TEXT | 文件路径 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | `sqlite:///../data/shipping_helper.db` | 数据库连接地址 |
| DOCUMENT_SERVER_URL | `http://localhost:8080` | OnlyOffice Document Server 地址 |
| API_BASE_URL | `http://localhost:8000` | API 基础地址 |
| ONLYOFFICE_CALLBACK_BASE_URL | `http://host.docker.internal:8000` | OnlyOffice 回调地址 |
| MSDS_DIR | `references/MSDS/` | MSDS 文件目录 |
| TRANSPORT_REPORTS_DIR | `references/海运鉴定报告/` | 运输鉴定报告目录 |
| REFERENCES_DIR | `references/` | 参考文件根目录 |

---

## OpenAPI 文档

完整的 OpenAPI（Swagger）文档访问：`http://localhost:8000/docs`

ReDoc 文档访问：`http://localhost:8000/redoc`