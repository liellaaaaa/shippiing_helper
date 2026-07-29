# 报关资料字段优化设计

## 背景

报关资料（customs declaration）生成时，贸易国、运抵国、指运港、最终目的国的处理存在问题：
- `destination` 字段混合存储城市和国家（如 "Izmit,Turkiye"），未正确分离
- 所有字段需要写中文
- 申报要素只完整填充了编号1的产品，其他产品缺失

## 改动项

### 改动1：贸易国/运抵国/指运港 分离

**现状**：
- `destination` 存储混合信息如 "Izmit,Turkiye"
- `cn_port()` 函数试图翻译整个字符串，无法区分国家和城市
- `{{DEST_COUNTRY_CN}}`、`{{DEST_PORT}}` 都从同一字段推导

**改为**：
1. 新增 `parse_destination(dest: str) -> tuple[str, str]` 函数：
   - 按逗号/空格分割 "City, Country"
   - 分别通过城市翻译表和国名翻译表转为中文
   - 如 "Izmit,Turkiye" → ("伊兹米特", "土耳其")
   - 无法解析时返回 (原值, 原值)

2. 在 `generate_customs()` 中使用：
   ```
   dest_city_cn, dest_country_cn = parse_destination(dest_raw)
   replace_placeholder(ws, "{{DEST_COUNTRY_CN}}", dest_country_cn)     # 贸易国
   replace_placeholder(ws, "{{DEST_COUNTRY_CN_2}}", dest_country_cn)   # 运抵国
   replace_placeholder(ws, "{{DEST_PORT}}", dest_city_cn)               # 指运港
   ```

### 改动2：中文化翻译表

**现状**：`cn_port()` 内部 mapping 字典约30个条目，国家和港口混合

**改为**：
- 拆分为两个独立字典（代码内 dict，约 100 条目）
- `COUNTRY_CN_MAP: dict[str, str]` — 国家名英→中（~50条）
- `CITY_CN_MAP: dict[str, str]` — 城市名英→中（~50条）
- 覆盖常见贸易国和港口城市

### 改动3：所有产品完整填充申报要素行

**现状**（模板行结构）：

| 行偏移 | 列G | 列H | 列I |
|--------|-----|-----|-----|
| row (数据行) | 数量 | 千克 | 单价 |
| row+1 (申报要素) | - | - | 总价 |
| row+2 (币制行) | 数量引用 | 千克 | 币制 |

- 编号1（行20-22）：模板预置 `{{CURRENCY}}`，placeholder 替换填充
- 编号2+（行23-25+）：row+2 的币制、数量引用、单位未填充

**改为**：在每个产品的循环中填充 row+2：
```python
ws.cell(row + 2, 7, item.quantity_kg)   # G: 数量引用
ws.cell(row + 2, 8, "千克")              # H: 单位
ws.cell(row + 2, 9, currency)            # I: 币制
```

### 改动4：最终目的国使用中文国家名

**现状**：`ws.cell(row, 13, dest_cn)`，可能返回城市名或混合名

**改为**：`ws.cell(row, 13, dest_country_cn)`，始终用中文国家名

## 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/app/services/document_service.py` | 新增 parse_destination() 和翻译字典；修改 generate_customs() 填充逻辑 |

## 不需改动的文件

- `pi_parser.py` — PI 解析仍存储原始 `destination` 字段，不做拆分（数据源不变）
- `template.xlsx` — 模板占位符结构不变
- 数据库模型 — 不新增字段
- Schema — 不修改 API 结构
