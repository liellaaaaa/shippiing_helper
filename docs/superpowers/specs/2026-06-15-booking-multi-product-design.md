# 订舱单多产品 + 报关名称匹配设计方案

**日期**: 2026-06-15
**状态**: 已批准

---

## 一、需求背景

- 第一阶段：一单多品数据已支持，但第二阶段订舱单只引用单产品
- 订舱单货名需填写**报关名称**（非汇入品名），且每个产品单独一行
- 毛重/体积为汇总值（不分行）
- 报关名称来源于商品编码 JSON，需在解析阶段自动匹配补全（汇数据之前）

---

## 二、数据层

### 2.1 Excel → JSON 转换

**输入**：`references/2024.12.5 最新出口商品编码及报关成分.xlsx`
**输出**：`references/customs_codes.json`
**脚本**：`backend/scripts/extract_customs_codes.py`（一次性执行，生成后固化）

**JSON 字段（5个）**：

```json
{
  "internal_code": "F-380-1",        // 产品内编（匹配key）
  "product_code": "3402420000",      // 新商品编码
  "customs_name": "吸湿排汗整理剂",  // 报关名称
  "components": "柔软吸湿排汗整理剂9016-88-0：90％+水：10％",  // 成分
  "product_appearance": "黄色透明液体"  // 产品外观
}
```

**列对应关系（Excel → JSON）**：

| Excel列名 | JSON字段 |
|-----------|----------|
| 产品内编 | internal_code |
| 新商品编码 | product_code |
| 报关名称 | customs_name |
| 成分 | components |
| 产品外观 | product_appearance |

### 2.2 CustomsNameService

**职责**：Backend 启动时加载 `customs_codes.json`，提供按 `internal_code` 查询接口

```python
class CustomsNameService:
    def __init__(self):
        self._cache = {}  # internal_code → {customs_name, product_code, components, product_appearance}

    def lookup(self, internal_code: str) -> dict | None:
        return self._cache.get(internal_code)
```

**挂载点**：在 `backend/app/main.py` 启动时实例化，全局单例

---

## 三、第一阶段：解析时匹配补全（汇数据之前）

### 3.1 匹配时机

`POST /api/v1/orders/paste` 解析订单文本时，在返回预览数据之前触发匹配检查。

### 3.2 匹配逻辑

```
for each order item:
    json_data = customs_service.lookup(internal_code)

    if json_data is None:
        customs_match_status = "not_found"  # JSON中无此internal_code

    else if order_item.报关名称 exists and != json_data.customs_name:
        customs_match_status = "conflict"   # 汇入数据与JSON不一致，保留两方
        # 返回预览时同时返回：order_item.报关名称 和 json.customs_name

    else if order_item.报关名称 is empty:
        自动补全:
            报关名称 = json_data.customs_name
            商品编码 = json_data.product_code
            成分 = json_data.components
            产品外观 = json_data.product_appearance
        customs_match_status = "filled"

    else:
        customs_match_status = "matched"  # 完全匹配
```

### 3.3 冲突处理

- `conflict` 状态：在预览阶段显示两方差异（汇入的报关名称 vs JSON中的报关名称），让用户决定使用哪个
- `not_found` 状态：在预览中标注，提示用户检查 internal_code
- 用户可在汇数据之前修正冲突数据

### 3.4 返回预览数据扩展

解析接口返回时，每条 item 增加：
```json
{
  "customs_name": "报关名称",
  "product_code": "商品编码",
  "components": "成分",
  "product_appearance": "产品外观",
  "customs_match_status": "matched|conflict|filled|not_found",
  "conflict_original": "汇入的报关名称",  // 仅 conflict 时有
  "conflict_json": "JSON中的报关名称"     // 仅 conflict 时有
}
```

### 3.5 汇数据保存

`POST /api/v1/dashboard/records` 保存时：
- **不再重复触发匹配**（解析阶段已完成）
- 直接使用预览阶段已补全的数据

### 3.6 OrderPiRecord 新增字段

```python
class OrderPiRecord(Base):
    customs_name = Column(String(200))        # 报关名称
    product_code = Column(String(20))         # 商品编码
    components = Column(String(500))          # 成分
    product_appearance = Column(String(200))  # 产品外观
    customs_match_status = Column(String(20)) # matched / conflict / filled / not_found
```

---

## 四、第二阶段：订舱单改造

### 4.1 BookingConfirmDialog 表格结构

```
货名（报关名称）     毛重(KGS)    尺码(CBM)
------------------------------------------
报关名称1           总毛重       总尺码     ← 第一行可编辑
报关名称2           （只读）     （只读）   ← 其他行只读
报关名称3           （只读）     （只读）
报关名称4           （只读）     （只读）
报关名称5           （只读）     （只读）
报关名称6           （只读）     （只读）
```

**行为**：
- 报关名称列：只读，来自 `OrderPiRecord.customs_name`
- 毛重/尺码：只在第一行可编辑，其他行 disabled
- 最多支持 6 个产品

### 4.2 前端 API

```typescript
generateBooking(fields: {
  shipper, consignee, notify, cut_off_date,
  place_of_receipt, pol, pod, place_of_delivery,
  marks, no_kind_pkg, template_type,
  customs_names: string[],   // ["报关名称1", "报关名称2", ...]
  gross_weight: string,      // 总毛重
  measurement: string,        // 总体积
})
```

### 4.3 后端 API

```python
class BookingFields(BaseModel):
    customs_names: list[str] = []
    gross_weight: str = ""
    measurement: str = ""
```

模板映射：
```python
for i, name in enumerate(fields.customs_names, 1):
    fields_dict[f"DESC{i}"] = name
# DESC1, DESC2, DESC3, DESC4, DESC5, DESC6
```

---

## 五、订舱单模板改造

### 5.1 模板占位符

**改造后**（多产品）：

| 占位符 | 说明 |
|--------|------|
| `{{DESC1}}` | 产品1报关名称 |
| `{{DESC2}}` | 产品2报关名称 |
| `{{DESC3}}` | 产品3报关名称 |
| `{{DESC4}}` | 产品4报关名称 |
| `{{DESC5}}` | 产品5报关名称 |
| `{{DESC6}}` | 产品6报关名称 |
| `{{GROSS_WEIGHT}}` | 总毛重（单值） |
| `{{MEASUREMENT}}` | 总体积（单值） |

**模板文件**：`references/长晟出口海运BOOKING模板-多产品.xlsx`

### 5.2 fill_booking_template 适配

支持 DESC1-DESC6 逐个替换，没有则留空。

---

## 六、改动文件清单

| 文件 | 改动内容 |
|------|----------|
| `backend/scripts/extract_customs_codes.py` | 新建：Excel转JSON脚本 |
| `references/customs_codes.json` | 新建：商品编码JSON（自动生成） |
| `backend/app/core/config.py` | 添加 CUSTOMS_CODES_JSON 配置 |
| `backend/app/services/customs_name_service.py` | 新建：报关名称查询服务 |
| `backend/app/models/order_pi_record.py` | 新增5个字段 |
| `backend/app/core/order_parser.py` | 解析时触发匹配，返回带状态的预览数据 |
| `backend/app/api/v1/documents.py` | BookingFields添加customs_names |
| `backend/app/services/document_service.py` | fill_booking_template支持DESC1-6 |
| `references/长晟出口海运BOOKING模板-多产品.xlsx` | 新建：多产品模板 |
| `frontend/src/api/orders.ts` | 解析返回数据增加 customs_name 等字段 |
| `frontend/src/views/phase2/components/BookingConfirmDialog.vue` | 改为多行表格 |
| `frontend/src/views/phase2/Phase2Workflow.vue` | 传递customs_names到订舱表单 |

---

## 七、验证方式

1. 启动 Backend，检查日志确认 `customs_codes.json` 加载成功
2. Phase 1 粘贴一单多品数据，点击解析，观察预览中 `customs_name` 是否自动补全
3. 故意填错 `internal_code`，观察 `conflict` 标注和两方差异显示
4. 点击汇数据，观察数据看板中已补全的数据
5. Phase 2 选择该订单，点击订舱单，观察多行报关名称是否正确显示
6. 填写毛重/尺码，确认 OnlyOffice 渲染正确