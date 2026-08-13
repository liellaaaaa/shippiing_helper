<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑产品' : '新增产品'"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="top"
    >
      <!-- 产品名称 -->
      <el-form-item label="商品名称" prop="product_name">
        <el-input
          v-model="form.product_name"
          placeholder="请输入商品名称"
          :disabled="isEdit"
        />
      </el-form-item>

      <!-- 网站商品名称 -->
      <el-form-item label="网站商品名称" prop="website_name">
        <el-input
          v-model="form.website_name"
          placeholder="请输入网站商品名称（可选）"
        />
      </el-form-item>

      <!-- 商品描述 -->
      <el-form-item label="商品描述" prop="product_description">
        <el-input
          v-model="form.product_description"
          type="textarea"
          :rows="2"
          placeholder="请输入商品描述（可选）"
        />
      </el-form-item>

      <!-- 动态字段 -->
      <el-divider content-position="left">申报要素</el-divider>
      <div class="fields-grid">
        <el-form-item
          v-for="field in fields"
          :key="field.field_name"
          :label="field.field_name"
          :prop="`values.${field.field_name}`"
          :required="field.is_required"
          class="field-item"
        >
          <el-input
            v-model="form.values[field.field_name]"
            :placeholder="`请输入${field.field_name}`"
            :type="field.field_type === 'textarea' ? 'textarea' : 'text'"
            :rows="field.field_type === 'textarea' ? 2 : undefined"
          />
        </el-form-item>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { declarationLedgerApi, type DeclarationProduct, type HsCodeField } from '@/api/declaration-ledger'

const props = defineProps<{
  modelValue: boolean
  hsCode: string
  product: DeclarationProduct | null
  fields: HsCodeField[]
}>()

const emit = defineEmits<{
  'update:model-value': [value: boolean]
  saved: []
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:model-value', val)
})

const isEdit = computed(() => !!props.product)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = ref({
  product_name: '',
  website_name: '',
  product_description: '',
  values: {} as Record<string, string>
})

const rules: FormRules = {
  product_name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' }
  ]
}

// 监听弹窗打开，初始化表单
watch(() => props.modelValue, (visible) => {
  if (visible) {
    if (props.product) {
      // 编辑模式
      form.value = {
        product_name: props.product.product_name,
        website_name: props.product.website_name || '',
        product_description: props.product.product_description || '',
        values: { ...props.product.values }
      }
    } else {
      // 新增模式
      form.value = {
        product_name: '',
        website_name: '',
        product_description: '',
        values: {}
      }
    }
  }
})

// 关闭弹窗
function handleClose() {
  formRef.value?.resetFields()
}

// 保存
async function handleSave() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      if (isEdit.value && props.product) {
        // 编辑模式：更新产品信息和要素值
        await declarationLedgerApi.updateProduct(props.product.id, {
          website_name: form.value.website_name,
          product_description: form.value.product_description
        })
        await declarationLedgerApi.updateValues(props.product.id, {
          values: form.value.values
        })
        ElMessage.success('更新成功')
      } else {
        // 新增模式
        const res = await declarationLedgerApi.createProduct(props.hsCode, {
          product_name: form.value.product_name,
          website_name: form.value.website_name,
          product_description: form.value.product_description
        })
        // 如果有要素值，批量更新
        if (Object.keys(form.value.values).length > 0) {
          await declarationLedgerApi.updateValues(res.data.id, {
            values: form.value.values
          })
        }
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      emit('saved')
    } catch (error: any) {
      const message = error.response?.data?.detail || '操作失败'
      ElMessage.error(message)
    } finally {
      saving.value = false
    }
  })
}
</script>

<style scoped>
.fields-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0 16px;
}

.field-item {
  margin-bottom: 16px;
}

@media (max-width: 600px) {
  .fields-grid {
    grid-template-columns: 1fr;
  }
}
</style>
