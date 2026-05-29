<template>
  <div class="packaging-select">
    <label class="form-label">包装类型</label>
    <el-select
      :model-value="modelValue"
      @change="$emit('update:modelValue', $event)"
      placeholder="选择包装类型"
      class="packaging-select-input"
      :class="{ 'has-recommendation': recommended }"
    >
      <el-option
        v-for="type in packagingTypes"
        :key="type.id"
        :label="type.name"
        :value="type.name"
      >
        <span>{{ type.name }}</span>
        <span class="specs-tag">{{ type.net_kg }}kg</span>
      </el-option>
    </el-select>

    <div class="recommendation-tip" v-if="recommended && !manualOverride">
      <el-icon><InfoFilled /></el-icon>
      <span>💡 系统根据产品知识库自动推荐：{{ recommended }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { getPackagingTypes, type PackagingType } from '@/api/packages'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: string
  recommended: string | null
}>()

defineEmits(['update:modelValue'])

const packagingTypes = ref<PackagingType[]>([])
const manualOverride = ref(false)

watch(() => props.modelValue, (newVal) => {
  if (props.recommended && newVal !== props.recommended) {
    manualOverride.value = true
  }
})

onMounted(async () => {
  const data = await getPackagingTypes()
  packagingTypes.value = data.types
})
</script>

<style scoped>
.packaging-select { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.form-label { font-size: 13px; color: #606266; min-width: 80px; }
.packaging-select-input { width: 240px; }
.packaging-select-input.has-recommendation :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #67c23a inset;
}
.specs-tag { margin-left: 8px; color: #909399; font-size: 12px; }
.recommendation-tip { font-size: 12px; color: #409eff; display: flex; align-items: center; gap: 4px; }
</style>