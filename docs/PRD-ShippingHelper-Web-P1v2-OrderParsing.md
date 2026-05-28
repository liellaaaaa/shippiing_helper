# Phase 1 订单粘贴解析模块设计方案

> 本文档为 Phase 1 第一个模块"订单粘贴解析"的详细设计方案，基于 PRD-ShippingHelper-Web-P1v2 的约束和 brainstorming 讨论结论生成。
> 存放路径：`C:\Users\windows\Desktop\shippiing_helper\docs\PRD-ShippingHelper-Web-P1v2-OrderParsing.md`
> 状态：**已锁定**（v3，2026/05/28）— 进入 writing-plans 阶段

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026/05/28 | 初始生成，基于 brainstorming 讨论结论 |
| 2026/05/28 | v2：明确 internal_code 归属 order_items；补充列名映射表；知识库改为严格匹配；增加全选/反选和 H.S.Code 格式校验 |

---

## 1. 概述

### 1.1 模块定位

订单粘贴解析模块（OrderPaste）是 Phase 1 的第一个功能模块，负责接收用户从 Excel/Spreadsheet 复制粘贴的多行订单数据，完成解析、智能聚合、知识库匹配后存储到数据库。

### 1.2 核心业务流程

```
用户全选 Excel 数据 → Ctrl+C 复制
        ↓
粘贴到系统文本框 → Ctrl+V
        ↓
后端解析（智能聚合）→ 按订单号合并多行
        ↓
知识库匹配（补全 H.S.Code / 报关品名）
        ↓
表单式预览编辑（用户确认）
        ↓
保存入库（orders 头表 + order_items 明细表）
```

### 1.3 关键设计决策

| 决策项 | 方案 | 依据 |
|--------|------|------|
| 前端粘贴交互 | 专用粘贴文本框 | 一次性操作，不需要污染数据看板 |
| 预览与编辑 | 表单式预览编辑 | 26字段逐个确认比表格编辑更高效 |
| 重复订单处理 | 覆盖（Reconcile） | 订单信息通常一次性完整更新 |
| 批次内重复 | 后行覆盖前行 + 前端提示 | 不打断工作流，符合 Excel 操作直觉 |
| 多行聚合 | 智能聚合（一单多品） | 一张订单包含多个产品，Excel 每行一个产品 |
| 知识库匹配 | internal_code 优先 → 中文名兜底 | internal_code 是产品主键，最准确 |

---

## 2. 数据模型

### 2.1 入库结构

用户粘贴的数据最终按以下结构存储：

```
orders（订单头表，1 条）
  └── order_items（产品明细表，N 条，外键 → orders.id）
```

### 2.2 解析中间对象

```python
class ParsedOrder:
    order_no: str          # 订单号（主键）
    customer_code: str
    salesperson: str
    # ... 其他订单级字段
    items: list[ParsedOrderItem]  # 该订单下的多个产品

class ParsedOrderItem:
    internal_code: str     # 内部编码（产品级，关联知识库）
    product_cn: str        # 产品中文名
    spec_kg: float        # 规格kg
    quantity_kg: float    # 订单量
    unit_price: float     # 单价
    # ... 其他产品级字段
    # 以下字段由知识库匹配填充
    hs_code: str | None
    customs_name: str | None
```

---

## 3. 交互设计

### 3.1 粘贴文本框

**位置**：OrderPaste 页面中央区域

```
┌─────────────────────────────────────────────────────────────┐
│  订单粘贴解析                                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                                                     │  │
│  │   将 Excel/Spreadsheet 订单数据粘贴到此处            │  │
│  │   （支持 Tab 分隔或换行分隔）                        │  │
│  │                                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│         [ 解析 ]    [ 清空 ]                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**行为**：
- 用户将光标聚焦在文本框内，按 `Ctrl+V` 粘贴
- 支持 Tab 分隔（从 Excel 复制）和换行分隔（从网页表格复制）两种格式
- 粘贴后文本框显示原始数据，不做解析（保持用户可追溯）

### 3.2 表单式预览编辑

点击"解析"后，文本框下方展示解析结果：

```
┌─────────────────────────────────────────────────────────────┐
│  解析结果                                                    │
│  共发现 1 个订单，5 个产品明细                               │
├─────────────────────────────────────────────────────────────┤
│  订单头信息                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 订单号: [HT260304E01          ] ✓                   │   │
│  │ 客户编号: [TOA-DOVECHEM     ] ✓                   │   │
│  │ 内部编码: [SILI-001          ] ✓                   │   │
│  │ 业务员: [张三                  ] ✓                   │   │
│  │ ...                                                  │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  产品明细（5 条）                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ #  │ 产品中文名          │ 规格kg │ 数量kg │ H.S.Code │   │
│  │ 1  │ 有机硅柔软剂 HT-MD41│  25kg  │  2400  │ 3910000000│   │
│  │ 2  │ 有机硅柔软剂 HT-MD42│  50kg  │  1600  │ 3910000000│   │
│  │ 3  │ 改性硅油            │  30kg  │  800   │ [待填写]  │ ⚠  │
│  │ 4  │ ...                 │        │        │           │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  [ 保存 ]    [ 重新粘贴 ]    [ 取消 ]                       │
└─────────────────────────────────────────────────────────────┘
```

**行为**：
- 订单头信息展示在同一区块（字段可能来自粘贴数据的任意一行，同订单号的多行这些字段应相同）
- 产品明细以子表格形式展示，每行对应 `order_items` 的一条记录
- H.S.Code 或报关品名未匹配的字段显示 `[待填写]` 并高亮，用户可直接在表格内修改
- **产品明细表格增加"全选/反选"复选框**，用户可一键取消勾选个别行，被取消的行不参与保存
- 底部操作按钮：保存（入库）、重新粘贴（清空重来）、取消

---

## 4. 后端解析逻辑

### 4.1 解析流程

```python
def parse_pasted_data(raw_text: str) -> tuple[list[ParsedOrder], str | None]:
    """
    解析用户粘贴的原始文本
    返回: (解析后的订单列表, 警告消息如果有的话)
    """
    # Step 1: 识别分隔符并切分行
    lines = split_by_delimiter(raw_text)  # Tab 或 换行

    # Step 2: 逐行解析为原始记录
    raw_items = [parse_line(line) for line in lines if is_valid_line(line)]

    # Step 3: 批次内智能去重
    # Key = (order_no, internal_code)
    # 后出现的同名 key 覆盖前面的
    # 注意：internal_code 是产品级，同订单的不同产品 internal_code 不同
    deduped_map = {}
    for item in raw_items:
        key = (item.order_no, item.internal_code)
        deduped_map[key] = item

    # Step 4: 按订单号聚合（一个订单号 → 一个 ParsedOrder）
    order_map = {}
    for item in deduped_map.values():
        if item.order_no not in order_map:
            order_map[item.order_no] = ParsedOrder(
                order_no=item.order_no,
                # 订单级字段从第一行提取（假设同订单号相同）
                # ⚠️ 防御性说明：若同一订单号的多行数据中订单头字段不一致
                # （如客户编号不同），以遇到的第一行数据为准，并记录 warning
                customer_code=item.customer_code,
                salesperson=item.salesperson,
                items=[]  # 初始化产品列表
            )
        order_map[item.order_no].items.append(item)

    # Step 5: 知识库匹配（补全 H.S.Code / 报关品名）
    for order in order_map.values():
        for item in order.items:
            auto_fill_knowledge(item)  # 见 §4.2

    # Step 6: 检测批次内去重（用于前端提示）
    warning = None
    if len(raw_items) > sum(len(o.items) for o in order_map.values()):
        dup_count = len(raw_items) - sum(len(o.items) for o in order_map.values())
        warning = f"检测到 {dup_count} 行重复数据，已自动合并，以最后出现的数据为准"

    return list(order_map.values()), warning
```

### 4.2 知识库匹配逻辑

```python
def auto_fill_knowledge(item: ParsedOrderItem, pi_data: dict | None = None):
    """
    自动补全 H.S.Code 和报关品名
    优先级：
      H.S.Code: PI > 知识库（internal_code）> 知识库（产品中文名）
      报关品名: 订单 > PI > 知识库 > 自动生成

    匹配策略：
      - 知识库匹配：去空格后精确匹配，不使用模糊/编辑距离匹配
        （报关字段误匹配风险太高，严格匹配确保准确性）
      - H.S.Code 格式：匹配后校验是否为 10 位，不足 10 位标黄提示
    """
    # --- H.S.Code 补全 ---
    if pi_data and pi_data.get('hs_code'):
        item.hs_code = pi_data['hs_code']
    else:
        # 优先用 internal_code 精确查（最准）
        knowledge = db.query(ProductKnowledge).filter_by(
            internal_code=item.internal_code.strip()
        ).first()

        # 如果查不到，用产品中文名去空格后精确匹配
        if not knowledge and item.product_cn:
            clean_name = item.product_cn.strip()
            # 仅当中文名长度 > 4 才查询（避免过短名称匹配错误）
            if len(clean_name) > 4:
                knowledge = db.query(ProductKnowledge).filter_by(
                    product_name_cn=clean_name
                ).first()

        if knowledge:
            item.hs_code = knowledge.hs_code
        else:
            item.hs_code = None  # 留空，前端标红提示人工填写

    # --- H.S.Code 格式校验（10 位标准）---
    if item.hs_code and len(item.hs_code) < 10:
        item.hs_code_warning = f"H.S.Code 位数不足（当前 {len(item.hs_code)} 位），请核对或补足 10 位"

    # --- 报关品名补全 ---
    if item.customs_name:
        pass  # 已有，使用粘贴数据
    elif pi_data and pi_data.get('customs_name'):
        item.customs_name = pi_data['customs_name']
    elif knowledge:
        item.customs_name = knowledge.customs_name
    else:
        # 知识库也没有，自动生成
        item.customs_name = f"{item.product_cn} {item.spec_kg}kg"
        item.warning = "报关品名由系统自动生成，请务必核对！"
```

### 4.3 保存入库

```python
def save_order(parsed_order: ParsedOrder) -> int:
    """
    将解析后的订单保存到数据库
    返回: orders.id
    """
    # Step 1: 检查是否已存在（按 order_no 查找）
    existing = db.query(orders).filter_by(order_no=parsed_order.order_no).first()

    if existing:
        # 覆盖：删除旧 order_items，插入新的
        db.query(order_items).filter_by(order_id=existing.id).delete()
        # 更新 orders 头表字段
        update_order_header(existing, parsed_order)
    else:
        # 新建
        existing = Order(**parsed_order.header_fields)
        db.add(existing)
        db.flush()  # 获取 id

    # Step 2: 批量插入 order_items
    for item in parsed_order.items:
        order_item = OrderItem(
            order_id=existing.id,
            **item.to_db_fields()
        )
        db.add(order_item)

    db.commit()
    return existing.id
```

---

## 5. 重复检测与处理

### 5.1 场景分类

| 场景 | 检测方式 | 处理策略 |
|------|----------|----------|
| 批次内同一订单号的多行 | 解析时 Map 去重 | 后行覆盖前行，前端提示 |
| 批次内同一 (订单号+产品) 的重复行 | Key=(order_no, internal_code) 去重 | 后行覆盖前行，前端提示 |
| 数据库已有该订单号 | 查询 orders 表 | 覆盖旧数据，保留变更记录（updated_at） |

### 5.2 前端提示设计

当检测到批次内重复时，在预览区域顶部显示非阻塞提示：

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ 检测到 2 行重复数据，已自动合并为 1 条记录，以最后一     │
│     行数据为准。请核对数量和金额是否正确。                    │
├─────────────────────────────────────────────────────────────┤
```

被覆盖的行在产品明细表格中背景色变为浅黄色，悬停显示：
`"订单 HT260304E01 + 产品 SILI-001 在粘贴内容中出现多次，已合并为 1 条记录"`

---

## 6. 字段映射

> **重要**：`internal_code`（内部编号）是产品级字段，仅存在于 `order_items` 表。`orders` 表不存 `internal_code`。

### 6.1 标准列名映射表

解析器需识别多种可能的列名变体，统一映射到内部字段：

| 内部字段 | 标准列名（中文） | 标准列名（英文） | 说明 |
|----------|-----------------|-----------------|------|
| order_no | 订单号 | Order No / PO / PO Number | **必填** |
| customer_code | 客户编号 | Customer Code / Client Code | |
| internal_code | 内部编号 | Internal Code / Product Code / SKU | **产品级，每行必填** |
| product_cn | 产品中文名 | Product Name (CN) / Description | |
| spec_kg | 规格kg | Spec / Specification | |
| quantity_kg | 订单量kg | Quantity / QTY (kg) / Order Qty | |
| unit_price | 单价/kg | Unit Price / Price per kg | |
| total_amount | 总金额 | Total Amount / Amount | |
| salesperson | 业务员 | Salesperson / Sales Rep | |
| merchandiser | 跟单员 | Merchandiser / Merch | |
| order_date | 下单日期 | Order Date | |
| delivery_date | 交货日期 | Delivery Date | |
| shipment_channel | 出货渠道 | Shipment Channel | |
| shipment_method | 出货方式 | Shipment Method / Transport | |
| customs_name | 报关名称 | Customs Name / 报关品名 | |
| hs_code | H.S.Code | HS Code / H.S. | |

**映射规则**：
1. 解析器按列名匹配字段，匹配时忽略大小写、空格、横杠（下划线）
2. `["订单号", "Order No", "PO", "PO Number"]` 均映射到 `order_no`
3. 未识别列名 → 忽略该列，不阻断解析
4. **必填字段**：`order_no`（订单号）、`internal_code`（内部编号），缺失则跳过该行

**跳行展示**：若某行因缺少 `order_no` 或 `internal_code` 被跳过，不静默丢弃——在预览表格中显示为**灰色行**，标注"缺少必要字段（订单号/内部编码）"，供用户补全后重新粘贴。

### 6.2 知识库匹配结果写入

| 匹配结果 | 写入字段 | 前端状态 |
|----------|----------|----------|
| internal_code 命中 | hs_code, customs_name | 正常（绿色勾） |
| 产品中文名命中 | hs_code | 正常，报关品名标黄提示核对 |
| 均未命中 | hs_code=None | 标红，需人工填写 |

---

## 7. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 必要字段（order_no / internal_code）为空 | 跳过该行，解析完成后警告"第 N 行因缺少必要字段被跳过" |
| 分隔符无法识别 | 返回错误"无法识别数据格式，请使用 Tab 分隔或换行分隔" |
| 数值字段格式错误 | 置为 None，前端标红提示 |
| 知识库连接失败 | 跳过匹配，H.S.Code 和报关品名均留空，前端提示"知识库暂不可用，请手动填写" |

---

## 8. 验收标准

- [ ] 用户在文本框按 Ctrl+V 粘贴 Excel 数据，系统正确解析为结构化数据
- [ ] 同一订单号的多行数据正确聚合为一个订单头 + N 个产品明细
- [ ] 批次内重复行（order_no + internal_code 相同）自动去重，以后出现为准
- [ ] H.S.Code 和报关品名正确按优先级匹配（PI > 知识库 > 自动生成）
- [ ] 预览界面显示订单头 + 产品明细子表格，缺失字段高亮提示
- [ ] 保存后数据正确写入 orders 表（1 条）和 order_items 表（N 条）
- [ ] 订单号已存在时正确覆盖旧数据（updated_at 更新）
- [ ] 解析失败时给出明确错误提示，不阻断用户修正重试

---

## 9. 涉及文件

| 文件 | 说明 |
|------|------|
| `backend/app/core/order_parser.py` | 解析器：分隔符识别、行解析、智能聚合 |
| `backend/app/core/knowledge_filler.py` | 知识库匹配逻辑（H.S.Code / 报关品名） |
| `backend/app/api/v1/orders.py` | API 端点：`POST /api/v1/orders/paste` |
| `backend/app/models/order.py` | SQLAlchemy models：orders, order_items |
| `backend/app/schemas/order.py` | Pydantic schemas |
| `frontend/src/views/phase1/OrderPaste.vue` | 粘贴解析页面 |
| `frontend/src/components/PasteTextarea.vue` | 粘贴文本框组件 |
| `frontend/src/components/OrderPreviewForm.vue` | 表单式预览编辑组件 |

---

## 10. Open Questions

| 问题 | 状态 | 说明 |
|------|------|------|
| 列名映射表 | **已解决** | 见 §6.1，去空格后忽略大小写、横杠精确匹配 |
| internal_code 归属 | **已解决** | 仅存于 order_items，orders 表不存此字段 |
| 知识库匹配策略 | **已解决** | 去空格后精确匹配（长度 > 4），不设模糊容错 |
| H.S.Code 位数不足 | **已解决** | 校验后标黄提示，由用户手动补足 10 位 |
| 历史数据迁移 | **Phase 1 暂不处理** | 旧数据（26字段平铺）后续写迁移脚本处理；**writing-plans 阶段需作为低优先级任务记录** |
