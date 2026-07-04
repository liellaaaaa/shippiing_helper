<template>
  <el-dialog
    v-model="visible"
    title="生成订舱单"
    width="640px"
    :append-to-body="true"
    class="booking-confirm-dialog"
    @closed="onClosed"
  >
    <el-form label-width="120px" label-position="left">
      <!-- 收发货 -->
      <div class="form-section-title">收发货</div>
      <el-form-item label="发货人">
        <el-input v-model="form.shipper" type="textarea" :rows="2" placeholder="公司名称+地址+TEL" />
      </el-form-item>
      <el-form-item label="收货人">
        <el-input v-model="form.consignee" type="textarea" :rows="2" placeholder="公司名称+地址+TEL" />
      </el-form-item>
      <el-form-item label="通知人">
        <el-input v-model="form.notify" type="textarea" :rows="2" placeholder="默认 SAME AS CONSIGNEE" />
      </el-form-item>

      <!-- 港口 -->
      <div class="form-section-title">港口</div>
      <el-form-item label="收货地">
        <el-input v-model="form.place_of_receipt" placeholder="如 GUANGZHOU,CHINA" />
      </el-form-item>
      <el-form-item label="装货港">
        <el-select v-model="form.pol" placeholder="选择装货港" style="width: 100%">
          <el-option label="NanSha, China (南沙)" value="NanSha, China" />
          <el-option label="SheKou, China (蛇口)" value="SheKou, China" />
          <el-option label="GuangZhou, China (广州)" value="GuangZhou, China" />
        </el-select>
      </el-form-item>
      <el-form-item label="卸货港">
        <el-input v-model="form.pod" placeholder="如 LAT KRABANG,THAILAND" />
      </el-form-item>
      <el-form-item label="交货地">
        <el-input v-model="form.place_of_delivery" placeholder="如 LAT KRABANG,THAILAND" />
      </el-form-item>
      <el-form-item label="截关日期">
        <el-input v-model="form.cut_off_date" placeholder="货代提供" />
      </el-form-item>

      <!-- 货物 -->
      <div class="form-section-title">货物</div>
      <el-form-item label="件数/柜型">
        <el-input v-model="form.no_kind_pkg" placeholder="如 4 PALLETS" />
      </el-form-item>
      <el-form-item label="唛头">
        <el-input v-model="form.marks" placeholder="可留空" />
      </el-form-item>
      <el-table :data="goodsRows" border size="small" class="goods-table">
        <el-table-column label="报关名称" prop="customsName" />
        <el-table-column label="毛重(KGS)">
          <template #default="{ row, $index }">
            <el-input v-model="row.grossWeight" :disabled="$index > 0" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="尺码(CBM)">
          <template #default="{ row, $index }">
            <el-input v-model="row.measurement" :disabled="$index > 0" size="small" />
          </template>
        </el-table-column>
      </el-table>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onConfirm">确认生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

export interface BookingForm {
  shipper: string
  consignee: string
  consignee_name: string
  consignee_address: string
  consignee_tel: string
  shipment_title: string
  notify: string
  cut_off_date: string
  place_of_receipt: string
  pol: string
  pod: string
  place_of_delivery: string
  marks: string
  no_kind_pkg: string
  customs_names: string[]
  gross_weight: string
  measurement: string
  drum_count?: string
  pallet_count?: string
}

interface GoodsRow {
  customsName: string
  grossWeight: string
  measurement: string
}

const defaultForm = (): BookingForm => ({
  shipper: '',
  consignee: '',
  consignee_name: '',
  consignee_address: '',
  consignee_tel: '',
  shipment_title: '',
  notify: 'SAME AS CONSIGNEE',
  cut_off_date: '',
  place_of_receipt: 'NanSha, China',
  pol: 'NanSha, China',
  pod: '',
  place_of_delivery: '',
  marks: '',
  no_kind_pkg: '',
  customs_names: [],
  gross_weight: '',
  measurement: '',
})

const props = defineProps<{
  modelValue: boolean
  initialValues?: Partial<BookingForm> & { port?: string }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [fields: BookingForm]
}>()

const form = ref<BookingForm>(defaultForm())
const loading = ref(false)
const visible = ref(props.modelValue)
const goodsRows = ref<GoodsRow[]>([])

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    const defaults = defaultForm()
    const initial = props.initialValues || {}
    form.value = {
      ...defaults,
      ...initial,
      // 特殊默认值
      notify: initial.notify || 'SAME AS CONSIGNEE',
      place_of_receipt: initial.place_of_receipt || 'NanSha, China',
      pol: initial.pol || 'NanSha, China',
    }
    // 卸货港默认值同装货港（如果initialValues有port）
    if (!initial.pod && initial.port) {
      form.value.pod = initial.port
      form.value.place_of_delivery = initial.port
    }
    // 初始化货物表格
    const names = (initial as any).customs_names || []
    goodsRows.value = names.map((n: string) => ({
      customsName: n,
      grossWeight: '',
      measurement: '',
    }))
    if (goodsRows.value.length) {
      goodsRows.value[0].grossWeight = (initial as any).gross_weight || ''
      goodsRows.value[0].measurement = (initial as any).measurement || ''
    }
    // 件数/柜型：优先用托盘数，其次桶数
    const palletCount = (initial as any).pallet_count
    const drumCount = (initial as any).drum_count
    if (palletCount) {
      form.value.no_kind_pkg = palletCount
    } else if (drumCount) {
      form.value.no_kind_pkg = drumCount
    }
  }
})

watch(visible, (v) => emit('update:modelValue', v))

function onConfirm() {
  loading.value = true
  emit('confirm', {
    ...form.value,
    customs_names: goodsRows.value.map(r => r.customsName),
    gross_weight: goodsRows.value[0]?.grossWeight || '',
    measurement: goodsRows.value[0]?.measurement || '',
  })
  loading.value = false
  visible.value = false
}

function onClosed() {
  form.value = defaultForm()
  loading.value = false
}
</script>

<style scoped>
.form-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin: 12px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #dcdfe6;
}
.goods-table {
  margin-bottom: 12px;
}
</style>