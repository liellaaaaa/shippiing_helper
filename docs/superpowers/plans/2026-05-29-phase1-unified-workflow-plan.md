# Phase 1 实施计划 — 统一工作流页面 + 数据落库

## 目标

实现一个**单页面工作流**：
1. 业务员粘贴/上传订单数据
2. 上传 PI 合同文件
3. 页面自动合并数据 + 计算包装
4. 点击「确认入库」→ 双轨数据（销售数据 + 包装结果）写入 SQLite

---

## 一、数据库设计

### 新建表：`order_pi_records`（订单PI宽表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| order_no | TEXT | 订单号 |
| customer_code | TEXT | 客户编码 |
| customer_name | TEXT | 客户名称 |
| pi_no | TEXT | PI号 |
| sales_person | TEXT | 业务员 |
| order_date | TEXT | 订单日期 |
| pi_date | TEXT | PI日期 |
| delivery_date | TEXT | 交货日期 |
| internal_code | TEXT | 内部编码 |
| product_cn | TEXT | 产品中文名 |
| product_en | TEXT | 产品英文名 |
| spec_kg | REAL | 规格kg |
| hs_code | TEXT | H.S.Code |
| customs_name | TEXT | 报关品名 |
| quantity_kg | REAL | 订单数量 |
| unit_price | REAL | 单价 |
| total_amount | REAL | 总金额 |
| order_requirement | TEXT | 订单要求（含包装指令文本） |
| notes | TEXT | 备注 |
| packaging_type_id | INTEGER | FK → packaging_types.id |
| pallet_spec | TEXT | 卡板规格（1.0m / 1.1m / 无） |
| drums_per_pallet | INTEGER | 每板桶数（人工可改） |
| drum_count | INTEGER | 总桶数（计算值） |
| pallet_count | INTEGER | 总卡板数（计算值） |
| net_weight_kg | REAL | 产品净重 |
| gross_weight_kg | REAL | 总毛重（含桶+卡板） |
| volume_cbm | REAL | 总体积 |
| fits_20gp | TEXT | 20GP判定（适合/超出） |
| packaging_result_json | TEXT | 完整包装方案JSON（用于后续单据生成） |
| status | TEXT | pending / confirmed（落库状态） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 包装计算结果 JSON 结构

```json
{
  "packaging_type": "125kg新款胶桶",
  "pallet_spec": "1.1m*1.1m",
  "drums": 20,
  "pallets": 4,
  "drums_per_pallet": 5,
  "net_weight_kg": 2500,
  "gross_weight_kg": 2680,
  "volume_cbm": 9.6,
  "fits_20gp": "适合",
  "load_rate": 34.3,
  "packing_scheme": "共需 4 个卡板，前 3 个满板（每板 5 个），最后一个板装 5 个。",
  "no_pallet": false
}
```

---

## 二、后端 API

### 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/order_pi_record.py` | 新建 | OrderPiRecord 模型 |
| `backend/app/schemas/order_pi_record.py` | 新建 | Pydantic schemas |
| `backend/app/api/v1/dashboard.py` | 新建 | 落库 API + 查询 API |
| `backend/migrations/003_add_order_pi_records.py` | 新建 | 数据库迁移 |
| `backend/app/services/requirement_parser.py` | 新建 | 订单要求解析器（轨道B引擎） |
| `backend/app/services/save_service.py` | 新建 | 双轨数据合并+落库服务 |

### API 接口

```
POST /api/v1/dashboard/records
  Body: { order_data, pi_data, packaging_result }
  Response: { record_id, status }

GET /api/v1/dashboard/records
  Query: ?status=pending&search=&page=1&page_size=20
  Response: { records[], total, page, page_size }

GET /api/v1/dashboard/records/{id}
  Response: OrderPiRecord 完整对象

DELETE /api/v1/dashboard/records/{id}
  Response: { deleted: true }
```

### 落库流程（POST /api/v1/dashboard/records）

```
1. 解析请求体：order_data + pi_data + packaging_result
2. 通过 internal_code 合并订单+PI（轨道A）
3. 合并包装计算结果（轨道B）
4. 写入 order_pi_records 表
5. 更新 status = "confirmed"
6. 返回 record_id
```

---

## 三、前端页面

### 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/views/phase1/Phase1Workflow.vue` | 新建 | 统一工作流页面 |
| `frontend/src/api/phase1.ts` | 新建 | 落库 API 封装 |
| `frontend/src/components/phase1/OrderInputPanel.vue` | 新建 | 订单输入区（粘贴+上传） |
| `frontend/src/components/phase1/PIUploadPanel.vue` | 新建 | PI上传区 |
| `frontend/src/components/phase1/MergedPreview.vue` | 新建 | 合并预览+包装计算结果 |
| `frontend/src/components/phase1/RequirementParser.vue` | 新建 | 订单要求解析显示 |
| `frontend/src/router/index.ts` | 修改 | 路由调整 |

### 页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1 — 外贸订单处理工作流                                    │
├───────────────────────────┬─────────────────────────────────────┤
│  左侧输入区（420px）       │  右侧预览区                          │
│  ┌─────────────────────┐  │  ┌─────────────────────────────────┐│
│  │ 订单粘贴/上传        │  │  │ 合并预览表（15字段）             ││
│  │ - 粘贴框            │  │  │ - 订单号/客户/PI号               ││
│  │ - 上传Excel按钮     │  │  │ - 产品/数量/单价/金额            ││
│  └─────────────────────┘  │  │ - 报关品名/H.S.Code              ││
│  ┌─────────────────────┐  │  └─────────────────────────────────┘│
│  │ PI文件上传          │  │  ┌─────────────────────────────────┐│
│  │ - 拖拽上传          │  │  │ 包装计算结果                    ││
│  │ - 支持.xls/.xlsx   │  │  │ - 桶数/卡板数/体积/毛重         ││
│  └─────────────────────┘  │  │ - 20GP判定/装配方案             ││
│                           │  └─────────────────────────────────┘│
├───────────────────────────┴─────────────────────────────────────┤
│  底部操作栏：[重置] [预览] ──────────────── [确认入库]             │
└─────────────────────────────────────────────────────────────────┘
```

### 交互流程

1. 用户粘贴订单数据 → 点击「解析」→ 显示预览（可编辑）
2. 用户上传 PI 文件 → 自动解析 → 数据合并到预览
3. 预览区实时显示合并后的 15 字段 + 包装计算结果
4. 用户点击「确认入库」→ 调用 POST API → 落库成功提示
5. 重置后可继续处理下一单

### 订单要求解析（轨道B）

订单要求文本示例：
> "125kg桶全新外贸专用桶，用1.1m*1.1m外贸消毒卡板，整柜出"

`RequirementParser` 组件使用规则匹配提取：
- 桶规格：匹配 "125kg桶", "200kg桶" 等
- 卡板规格：匹配 "1.1m*1.1m", "1.0m*1.0m"
- 出货方式：匹配 "整柜", "散货", "LCL"

提取后自动调用包装计算，预填充推荐值。

---

## 四、执行顺序

1. **DB Migration**：`order_pi_records` 表创建
2. **Backend Models**：`OrderPiRecord` 模型 + Schema
3. **Backend API**：`POST /api/v1/dashboard/records` 落库接口
4. **Frontend Page**：新建 `Phase1Workflow.vue` 串联全流程
5. **Order Excel Upload**：备选的 Excel 直读功能
6. **测试验证**：完整流程测试

---

## 五、非目标

- 不做订单与 PI 的"比对"页面（FR-3.x），Phase 1 直接合并落库
- 不做数据导出/打印功能（Phase 2）
- 不做编辑已落库记录（落库即确认）