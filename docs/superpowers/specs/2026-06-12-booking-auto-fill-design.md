# 订舱单自动填充设计文档

## 1. 背景与目标

Phase2 左侧有"订单信息"汇集栏（发货人、收货人、货名、毛重、体积等），右侧 OnlyOffice 编辑器目前打开的订舱单是空白模板，船务部同事需要手动一个个录入。

**目标**：点击"订舱单" → 弹出核对对话框 → 确认后自动填充到 Excel 模板 → OnlyOffice 渲染已填充好的文档。

---

## 2. 流程

```
用户选好订单（左侧数据已加载）
       ↓
点击"订舱单"按钮
       ↓
弹出核对对话框（BookingConfirmDialog）
  所有字段均可编辑：
  - 发货人、收货人、通知人
  - 截关日期
  - 收货地、装货港、卸货港、交货地
  - 件数/柜型、货名、毛重、尺码、唛头
       ↓
船务部同事核对修正
       ↓
点击"确认生成"
       ↓
后端 openpyxl 打开模板 → 填入数据 → 保存为 BytesIO
       ↓
OnlyOffice 打开已填充文档 → 浏览器渲染
```

---

## 3. 模板标记位置（已确认）

模板文件：`references/长晟出口海运BOOKING模板-已标记.xlsx`

| 标记 | 字段名 | 单元格位置 | 备注 |
|------|--------|-----------|------|
| `{{SHIPPER}}` | 发货人 | A3 | 合并格 A3:F7 左上角 |
| `{{CONSIGNEE}}` | 收货人 | A10 | 合并格 A10:F13 左上角 |
| `{{NOTIFY}}` | 通知人 | A15 | 合并格 A15:F18 左上角 |
| `{{CUT_OFF_DATE}}` | 截关日期 | D20 | |
| `{{PLACE_OF_RECEIPT}}` | 收货地 | D24 | |
| `{{POL}}` | 装货港 | D26 | |
| `{{POD}}` | 卸货港 | A29 | |
| `{{PLACE_OF_DELIVERY}}` | 交货地 | D29 | |
| `{{MARKS}}` | 唛头 | A33 | 表格数据行 |
| `{{NO_KIND_PKG}}` | 件数/柜型 | C33 | 表格数据行 |
| `{{DESC}}` | 货名 | F33 | 表格数据行 |
| `{{GROSS_WEIGHT}}` | 毛重 | H33 | 表格数据行 |
| `{{MEASUREMENT}}` | 尺码 | J33 | 表格数据行 |

**注意**：船名航次、柜型柜量由货代提供，模板中不设标记，留空。

---

## 4. 字段初始值

| 字段 | 初始值来源 |
|------|-----------|
| 发货人 | 弹窗编辑（暂无默认值） |
| 收货人 | 左侧汇集栏 `consignee` |
| 通知人 | 默认 `SAME AS CONSIGNEE`，可改 |
| 截关日期 | 空白（货代提供） |
| 收货地 | `GUANGZHOU,CHINA` |
| 装货港 | `GUANGZHOU,CHINA` |
| 卸货港 | 左侧汇集栏 `port` |
| 交货地 | 同卸货港 |
| 件数/柜型 | 空白（如需可从 pallet_count 换算） |
| 货名 | 左侧汇集栏 `product_cn` |
| 毛重 | 左侧汇集栏 `gross_weight_kg` + "KGS" |
| 尺码 | 左侧汇集栏 `volume_cbm` + "CBM" |
| 唛头 | 空白 |

---

## 5. 模板标记方案

使用 `{{FIELD_NAME}}` 单元格标记：
- openpyxl 打开模板，扫描所有单元格
- 找到 `{{FIELD_NAME}}` 格式的单元格，将整个格子内容替换为实际值
- 合并单元格的左上角是写入目标（openpyxl 行为一致）

---

## 6. 对话框 UI 设计

- el-dialog 居中，宽度 640px
- 使用 el-form + el-form-item 布局
- 字段分组展示：
  - **收发货**：发货人、收货人、通知人（3行，多行文本输入）
  - **港口**：收货地、装货港、卸货港、交货地、截关日期（5行）
  - **货物**：件数/柜型、货名、毛重、尺码、唛头（5行）
- 底部两个按钮：「取消」和「确认生成」

---

## 7. 关键文件改动

| 文件 | 改动 |
|------|------|
| `backend/app/services/document_service.py` | 新增 `fill_booking_template(fields)` 函数，扫描填充 `{{FIELD_NAME}}`；修改 `generate_booking()` 接收字段字典 |
| `backend/app/api/v1/documents.py` | `generate_booking` 接口改为接收 JSON body（所有字段） |
| `frontend/src/views/phase2/Phase2Workflow.vue` | 点击"订舱单"改为打开 BookingConfirmDialog，确认后调用 API |
| `frontend/src/views/phase2/components/BookingConfirmDialog.vue` | **新增**，核对对话框组件 |
| `frontend/src/api/phase2.ts` | `generateBooking()` 改为接收字段对象 |

---

## 8. 验证方法

1. 选一个有数据的订单
2. 点击"订舱单"按钮，弹出对话框
3. 检查初始值是否从左侧汇集栏正确带入（收货人、卸货港、货名、毛重、尺码）
4. 修改任意字段，点击"确认生成"
5. 在 OnlyOffice 中检查：
   - 标题栏显示正确文件名
   - 各 `{{FIELD_NAME}}` 单元格已被实际值替换，不再是标记文字
   - 导出文件时文件名正确