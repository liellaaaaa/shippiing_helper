# 包装计算货柜类型选择器设计

## 概述

在包装计算界面增加货柜类型选择器，让用户手动选择「不装柜/20GP/40GP」，替代当前固定判断20GP的逻辑。

## 改动范围

改动集中在 **前端 `PackagingCalculator.vue`**，后端逻辑保持不变（已同时返回 `fits_20gp` 和 `fits_40gp` 数据）。

---

## 界面变更

### 1. 工具栏新增货柜选择器

表格上方工具栏，在「+ 添加产品」按钮右侧新增 `el-radio-group`：

```
[+ 添加产品]   货柜选择: ○ 不装柜  ○ 20GP  ○ 40GP
```

- 默认选中 **20GP**（兼容当前行为）
- 选中项变化时，汇总行和每行货柜列同步更新

### 2. 每行「20GP」列动态变化

| 选中货柜 | 列标题 | 单元格内容 |
|----------|--------|-----------|
| 不装柜 | 货柜 | 显示「—」 |
| 20GP | 20GP | ✅/❌（基于 `row.fits_20gp`） |
| 40GP | 40GP | ✅/❌（基于 `row.fits_40gp`） |

### 3. 汇总行货柜判断动态变化

| 选中货柜 | 标签类型 | 显示文本 |
|----------|---------|---------|
| 不装柜 | `info` | 不装柜 ✅ |
| 20GP（适配） | `success` | 20GP ✅ |
| 20GP（不适配） | `danger` | 20GP ❌ |
| 40GP（适配） | `success` | 40GP ✅ |
| 40GP（不适配） | `warning` | 40GP ❌ |

---

## 前端变更明细

### PackagingCalculator.vue

1. **新增响应式变量** `containerType: ref<'none' | '20gp' | '40gp'>('20gp')`

2. **工具栏添加选择器**（在「+ 添加产品」按钮右侧）：
   ```html
   <el-radio-group v-model="containerType" size="small">
     <el-radio-button value="none">不装柜</el-radio-button>
     <el-radio-button value="20gp">20GP</el-radio-button>
     <el-radio-button value="40gp">40GP</el-radio-button>
   </el-radio-group>
   ```

3. **修改每行货柜列标题**：
   ```diff
   - <el-table-column label="20GP" width="70" align="center">
   + <el-table-column :label="containerType === 'none' ? '货柜' : containerType.toUpperCase()" width="70" align="center">
   ```

4. **修改每行货柜列内容**：
   ```diff
   - <el-tag :type="row.fits_20gp ? 'success' : 'info'" size="small">{{ row.fits_20gp ? '✅' : '❌' }}</el-tag>
   + <template #default="{ row }">
   +   <el-tag v-if="containerType === 'none'" type="info" size="small">—</el-tag>
   +   <el-tag v-else-if="containerType === '20gp'" :type="row.fits_20gp ? 'success' : 'info'" size="small">{{ row.fits_20gp ? '✅' : '❌' }}</el-tag>
   +   <el-tag v-else :type="row.fits_40gp ? 'success' : 'warning'" size="small">{{ row.fits_40gp ? '✅' : '❌' }}</el-tag>
   + </template>
   ```

5. **修改汇总行货柜判断**：
   ```diff
   - <el-tag :type="summary.fits_20gp ? 'success' : summary.fits_40gp ? 'warning' : 'danger'" size="small">
   -   {{ summary.fits_20gp ? '20GP ✅' : summary.fits_40gp ? '40GP ✅' : '超出' }}
   - </el-tag>
   + <el-tag :type="getContainerTagType()" size="small">{{ getContainerLabel() }}</el-tag>
   ```

   新增计算函数：
   ```ts
   function getContainerTagType(): string {
     if (containerType.value === 'none') return 'info'
     if (containerType.value === '20gp') return summary.value.fits_20gp ? 'success' : 'danger'
     return summary.value.fits_40gp ? 'success' : 'warning'
   }

   function getContainerLabel(): string {
     if (containerType.value === 'none') return '不装柜 ✅'
     if (containerType.value === '20gp') return summary.value.fits_20gp ? '20GP ✅' : '20GP ❌'
     return summary.value.fits_40gp ? '40GP ✅' : '40GP ❌'
   }
   ```

6. **`getSummary()` 返回值增加 `container_type` 字段**

---

## 后端变更

**无**。后端 `packaging_service.py` / `calculation_service.py` / `packaging.py` 均已正确返回 `fits_20gp` 和 `fits_40gp`，前端直接使用已有数据即可。

---

## 边界情况

| 场景 | 行为 |
|------|------|
| 所有产品均未选包装 | 选择器可用，所有行货柜列显示「—」或 ❌ |
| 选择器切换 | 即时更新，无需重新请求后端 |
| 不装柜 + 有散货余数 | 散货区逻辑不变，货柜判断显示「不装柜 ✅」 |
| 打开已有保存的计算 | 默认 20GP，不破坏旧数据 |

---

## 不涉及

- 后端 API 不变
- 数据库 Schema 不变
- 不修改散货区/余数计算逻辑
- 不修改默认包装计算行为（20GP 为默认选中值）
