# 包装计算货柜类型选择器 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在包装计算界面增加货柜类型选择器（不装柜/20GP/40GP），替代当前固定 20GP 判断。

**Architecture:** 前端纯修改，后端 API 不变（后端正同时返回 `fits_20gp` 和 `fits_40gp`）。核心是修改 `PackagingCalculator.vue` 一个文件。

**Tech Stack:** Vue 3 + Element Plus + TypeScript

---

### Task 1: 新增 `containerType` 状态 + 工具栏选择器 + 辅助函数

**Files:**
- Modify: `frontend/src/components/phase1/PackagingCalculator.vue`

- [ ] **Step 1: 在 `script setup` 中新增响应式变量和辅助函数**

在 `script setup` 区域，`const showRemainderSection` 之后新增：

```ts
const containerType = ref<'none' | '20gp' | '40gp'>('20gp')

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

- [ ] **Step 2: 在工具栏添加 `el-radio-group`**

找到工具栏的 `<div class="calc-toolbar">` 区域，在「+ 添加产品」按钮右侧添加：

```html
<el-radio-group v-model="containerType" size="small">
  <el-radio-button value="none">不装柜</el-radio-button>
  <el-radio-button value="20gp">20GP</el-radio-button>
  <el-radio-button value="40gp">40GP</el-radio-button>
</el-radio-group>
```

预期结果：工具栏显示「[+ 添加产品] 货柜选择：○ 不装柜 ○ 20GP ○ 40GP」，默认选中 20GP。

---

### Task 2: 修改每行的货柜列

- [ ] **Step 1: 修改列标题为动态绑定**

将第 111 行的 `<el-table-column label="20GP" width="70" align="center">` 改为：

```html
<el-table-column :label="containerType === 'none' ? '货柜' : containerType.toUpperCase()" width="70" align="center">
```

- [ ] **Step 2: 修改列内容为动态显示**

将第 112-114 行的 template 内容改为：

```html
<template #default="{ row }">
  <el-tag v-if="containerType === 'none'" type="info" size="small">—</el-tag>
  <el-tag v-else-if="containerType === '20gp'" :type="row.fits_20gp ? 'success' : 'info'" size="small">
    {{ row.fits_20gp ? '✅' : '❌' }}
  </el-tag>
  <el-tag v-else :type="row.fits_40gp ? 'success' : 'warning'" size="small">
    {{ row.fits_40gp ? '✅' : '❌' }}
  </el-tag>
</template>
```

预期结果：选中 20GP 时列标题显示「20GP」，单元格 ✅/❌ 基于 `fits_20gp`。选中 40GP 时列标题显示「40GP」，基于 `fits_40gp`。选中不装柜时列标题显示「货柜」，单元格显示「—」。

---

### Task 3: 修改汇总行货柜判断

- [ ] **Step 1: 替换汇总行的货柜判断 el-tag**

在第 131-134 行，将：

```html
<el-tag :type="summary.fits_20gp ? 'success' : summary.fits_40gp ? 'warning' : 'danger'" size="small">
  {{ summary.fits_20gp ? '20GP ✅' : summary.fits_40gp ? '40GP ✅' : '超出' }}
</el-tag>
```

替换为：

```html
<el-tag :type="getContainerTagType()" size="small">{{ getContainerLabel() }}</el-tag>
```

预期结果：
| 选择 | fits | 显示 |
|------|------|------|
| 不装柜 | — | info 标签「不装柜 ✅」 |
| 20GP | ✅ | success 标签「20GP ✅」 |
| 20GP | ❌ | danger 标签「20GP ❌」 |
| 40GP | ✅ | success 标签「40GP ✅」 |
| 40GP | ❌ | warning 标签「40GP ❌」 |

---

### Task 4: getSummary() 增加 `container_type` 字段

- [ ] **Step 1: 在 `getSummary()` 方法的返回值中增加字段**

在 `return` 对象中增加：

```ts
container_type: containerType.value,
```

最终 `getSummary()` 的 `return`：

```ts
return {
  internal_code: ...,
  product_name: ...,
  ...
  fits_20gp: ...,
  container_type: containerType.value,
}
```

---

### Task 5: 验证

- [ ] **Step 1: 启动前端验证**

Run:
```bash
cd frontend && npm run dev
```

- [ ] **Step 2: 验证 3 种选择器行为**

1. 默认 20GP → 汇总行显示 20GP ✅/❌，每行列标题「20GP」
2. 切换到 40GP → 汇总行更新为 40GP ✅/❌，每行列标题「40GP」
3. 切换到 不装柜 → 汇总行显示「不装柜 ✅」，每行列标题「货柜」，单元格「—」

- [ ] **Step 3: 验证 TypeScript 编译无错误**

```bash
cd frontend && npx vue-tsc --noEmit
```

Expected: No type errors.
