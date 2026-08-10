<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:model-value', $event)"
    :title="isEdit ? '编辑申报要素' : '新增申报要素'"
    width="780px"
    :close-on-click-modal="false"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="商品编码" prop="hs_code">
        <el-input v-model="form.hs_code" placeholder="如 3910000000" />
      </el-form-item>
      <el-form-item label="申报名称" prop="declaration_name">
        <el-input v-model="form.declaration_name" placeholder="如 有机硅柔软剂" />
      </el-form-item>
      <el-form-item label="申报要素">
        <div class="kv-editor">
          <div v-if="kvPairs.length === 0" class="kv-empty">暂无字段，点击下方添加</div>
          <div v-for="(pair, index) in kvPairs" :key="index" class="kv-row">
            <div class="kv-row-main">
              <el-input
                v-model="pair.key"
                placeholder="字段名"
                class="kv-key"
              />
              <template v-if="pair.hasValue">
                <span class="kv-separator">：</span>
                <el-input
                  v-model="pair.value"
                  type="textarea"
                  :autosize="{ minRows: 1, maxRows: 8 }"
                  placeholder="字段值"
                  class="kv-value"
                />
              </template>
              <el-button
                type="primary"
                link
                size="small"
                class="kv-toggle"
                @click="pair.hasValue = !pair.hasValue"
              >
                {{ pair.hasValue ? '转为独立字段' : '添加值' }}
              </el-button>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removePair(index)"
              />
            </div>
          </div>
          <el-button type="primary" link @click="addPair" class="kv-add-btn">
            + 添加字段
          </el-button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:model-value', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { DeclarationElement } from '@/api/declaration-elements'

interface KvPair {
  key: string
  value: string
  hasValue: boolean
}

const props = defineProps<{
  modelValue: boolean
  element: DeclarationElement | null
}>()

const emit = defineEmits<{
  'update:model-value': [value: boolean]
  saved: []
}>()

const isEdit = computed(() => !!props.element)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = ref({
  hs_code: '',
  declaration_name: '',
})

const kvPairs = ref<KvPair[]>([])

const rules: FormRules = {
  hs_code: [{ required: true, message: '请输入商品编码', trigger: 'blur' }],
  declaration_name: [{ required: true, message: '请输入申报名称', trigger: 'blur' }],
}

function parseElementsText(text: string): KvPair[] {
  if (!text) return []
  return text.split('|').map((segment) => {
    const s = segment.trim()
    if (!s) return null
    const idx = s.indexOf('：')
    if (idx === -1) {
      return { key: s, value: '', hasValue: false }
    }
    return {
      key: s.substring(0, idx).trim(),
      value: s.substring(idx + 1).trim(),
      hasValue: true,
    }
  }).filter((p): p is KvPair => !!p && !!p.key)
}

function buildElementsText(pairs: KvPair[]): string {
  return pairs
    .filter(p => p.key.trim())
    .map(p => {
      if (p.hasValue && p.value.trim()) {
        return `${p.key.trim()}：${p.value.trim()}`
      }
      return p.key.trim()
    })
    .join('|')
}

function addPair() {
  kvPairs.value.push({ key: '', value: '', hasValue: true })
}

function removePair(index: number) {
  kvPairs.value.splice(index, 1)
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && props.element) {
      form.value.hs_code = props.element.hs_code
      form.value.declaration_name = props.element.declaration_name
      kvPairs.value = parseElementsText(props.element.elements_text)
    } else if (visible) {
      form.value.hs_code = ''
      form.value.declaration_name = ''
      kvPairs.value = []
    }
  }
)

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const elements_text = buildElementsText(kvPairs.value)
    const payload = {
      hs_code: form.value.hs_code,
      declaration_name: form.value.declaration_name,
      elements_text,
    }

    const { declarationElementsApi } = await import('@/api/declaration-elements')
    if (isEdit.value && props.element) {
      const res = await declarationElementsApi.update(props.element.id, payload)
      if ((res.data as any).error) {
        ElMessage.error((res.data as any).error)
        return
      }
    } else {
      const res = await declarationElementsApi.create(payload)
      if ((res.data as any).error) {
        ElMessage.error((res.data as any).error)
        return
      }
    }
    ElMessage.success(isEdit.value ? '已更新' : '已新增')
    emit('update:model-value', false)
    emit('saved')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.kv-editor {
  width: 100%;
}
.kv-empty {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  padding: 12px 0;
}
.kv-row {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
}
.kv-row-main {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.kv-key {
  width: 150px;
  flex-shrink: 0;
}
.kv-separator {
  flex-shrink: 0;
  color: var(--el-text-color-regular);
  line-height: 32px;
}
.kv-value {
  flex: 1;
}
.kv-toggle {
  flex-shrink: 0;
  margin-top: 4px;
}
.kv-add-btn {
  margin-top: 4px;
}
</style>
