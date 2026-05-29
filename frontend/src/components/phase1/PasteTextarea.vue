<template>
  <div class="paste-textarea">
    <el-input
      v-model="text"
      type="textarea"
      :rows="10"
      :placeholder="placeholder"
      resize="vertical"
      @paste="handlePaste"
    />
    <div class="actions">
      <el-button type="primary" :disabled="!text.trim()" @click="handleParse">
        解析
      </el-button>
      <el-button @click="handleClear" :disabled="!text.trim()">
        清空
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'parse': [text: string]
  'clear': []
}>()

const text = ref(props.modelValue ?? '')
const placeholder = `将 Excel/Spreadsheet 订单数据粘贴到此处
（支持 Tab 分隔或换行分隔）
示例：
订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400`

function handlePaste(_e: ClipboardEvent) {
  setTimeout(() => {
    const raw = text.value
    const cleaned = smartRepair(raw)
    text.value = cleaned
    emit('update:modelValue', cleaned)
  }, 0)
}

/**
 * 智能修复粘贴数据：合并被 Excel 单元格内换行符打断的行。
 *
 * 问题：Excel col10（订单要求）内嵌换行符，粘贴后变成多条行。
 *       一条产品记录被拆成"数据行"+"碎片行"+"碎片行"…"完整收尾行"+"新数据行"…
 *
 * 修复逻辑：
 * 1. 先还原引号碎片（" 开头/结尾的单列行并入上一行）
 * 2. 以表头列数（23）为基准
 * 3. 遍历每行，若列数 ≥ 15 且 col14 有值 → 判定为"新数据行"
 * 4. 若列数 ≥ 15 但 col14 为空 → 判定为"续接行"（col10 内容延续到 col22），
 *    将其前部拼接至上一行的 col10 末尾
 * 5. 若列数 < 15 → 判定为"纯碎片行"，拼入上一行的 col10 末尾
 */
function smartRepair(raw: string): string {
  let reconstructed = repairQuotedFields(raw)

  const lines = reconstructed.split('\n').filter(l => l.trim())
  if (lines.length < 2) return reconstructed

  const delimiter = reconstructed.includes('\t') ? '\t' : '\n'
  const headerCols = lines[0].split(delimiter).length
  if (headerCols < 3) return reconstructed

  const ORDER_NO_COL = 13   // col14 → index 13（从0开始）
  const REQ_COL = 9          // col10 → index 9

  const result: string[] = []
  let i = 0

  while (i < lines.length) {
    const parts = lines[i].split(delimiter)
    const colCount = parts.length

    if (colCount >= 15 && (parts[ORDER_NO_COL] || '').trim()) {
      // 情况 A：新数据行（有订单号），直接保留
      result.push(lines[i])
      i++
    } else if (result.length > 0) {
      // 情况 B：续接行或纯碎片行 → 并入上一行的 col10
      const prev = result[result.length - 1]
      const prevParts = prev.split(delimiter)

      if (prevParts.length > REQ_COL) {
        // 找到上一行的"订单要求"列，追加当前行内容
        const reqField = prevParts[REQ_COL] || ''
        prevParts[REQ_COL] = reqField ? `${reqField}\n${lines[i].trim()}` : lines[i].trim()
        result[result.length - 1] = prevParts.join(delimiter)
      }
      i++
    } else {
      // 碎片行但没有前一行，直接保留
      result.push(lines[i])
      i++
    }
  }

  return result.join('\n')
}

/**
 * 还原被 Excel 引号包围的单元格换行。
 *
 * Excel 引号单元格含换行时，复制出来格式为：
 *   "要求：\n1、xxx\n3、xxx\n4、xxx\n5、xxx："
 * 双引号 " 在跨行处被切断，变成孤立碎片行。
 *
 * 修复逻辑：
 * 1. 单列行（colCount == 1）且上一行存在 → 引号碎片
 * 2. 若上一行末字段以 " 结尾（无开始引号）→ 碎片并入上一行
 * 3. 若本行以 " 结尾（无开始引号）→ 碎片并入上一行
 */
function repairQuotedFields(raw: string): string {
  const lines = raw.split('\n')
  const delimiter = raw.includes('\t') ? '\t' : '\n'
  const result: string[] = []
  let i = 0

  while (i < lines.length) {
    const parts = lines[i].split(delimiter)
    const colCount = parts.length

    // 单列碎片行（可能是 " 引号打断的单元格内容）
    if (colCount === 1 && result.length > 0) {
      const fragment = lines[i].trim()
      const prevLine = result[result.length - 1]
      const prevParts = prevLine.split(delimiter)

      if (prevParts.length > 0) {
        const lastField = prevParts[prevParts.length - 1]

        // 上一行末字段以 " 结尾但非引号开头 → 结束引号碎片，拼入
        if (lastField.endsWith('"') && !lastField.startsWith('"')) {
          prevParts[prevParts.length - 1] = `${lastField}${fragment}`
          result[result.length - 1] = prevParts.join(delimiter)
          i++
          continue
        }
        // 本行以 " 结尾但非引号开头 → 结束引号碎片，拼入
        if (fragment.endsWith('"') && !fragment.startsWith('"')) {
          prevParts[prevParts.length - 1] = `${lastField}${fragment}`
          result[result.length - 1] = prevParts.join(delimiter)
          i++
          continue
        }
      }
    }

    result.push(lines[i])
    i++
  }

  return result.join('\n')
}

function handleParse() {
  if (!text.value.trim()) return
  emit('parse', text.value)
}

function handleClear() {
  text.value = ''
  emit('update:modelValue', '')
  emit('clear')
}

watch(() => props.modelValue, (val) => {
  if (val !== text.value) text.value = val ?? ''
})
</script>

<style scoped>
.paste-textarea {
  width: 100%;
}
.paste-textarea :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>