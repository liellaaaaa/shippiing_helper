<template>
  <div class="packaging-calculator">
    <div class="calc-form">
      <div class="form-row">
        <span class="form-label">包装种类</span>
        <el-select
          v-model="selectedPackage"
          placeholder="选择包装种类"
          size="small"
          filterable
          @change="onPackageChange"
        >
          <el-option
            v-for="p in packageTypes"
            :key="p.name"
            :label="p.name"
            :value="p.name"
          >
            <span class="pkg-opt">{{ p.name }}</span>
            <span class="pkg-dims">{{ p.dims }}</span>
          </el-option>
        </el-select>
      </div>

      <div class="form-row">
        <span class="form-label">订单数量</span>
        <el-input-number
          v-model="orderQtyKg"
          :min="0"
          :step="100"
          size="small"
          controls-position="right"
        />
        <span class="unit">kg</span>
      </div>

      <div class="form-row">
        <span class="form-label">卡板</span>
        <el-radio-group v-model="usePallet" size="small">
          <el-radio-button :value="false">不打卡板</el-radio-button>
          <el-radio-button :value="true">打卡板</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="usePallet" class="form-row">
        <span class="form-label">托盘规格</span>
        <el-select v-model="selectedPallet" placeholder="选择托盘" size="small">
          <el-option
            v-for="p in palletTypes"
            :key="p.name"
            :label="p.name"
            :value="p.name"
          />
        </el-select>
      </div>

      <el-button
        type="primary"
        size="default"
        :loading="calculating"
        :disabled="!selectedPackage || orderQtyKg <= 0"
        @click="runCalculate"
      >
        计算包装
      </el-button>
    </div>

    <!-- 结果展示 -->
    <div v-if="result" class="calc-result">
      <el-divider content-position="left">计算结果</el-divider>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="总桶数">
          <strong>{{ result.drums }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="托盘数">
          <strong>{{ result.pallets || 0 }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="每托桶数">{{ result.drums_per_pallet || '-' }}</el-descriptions-item>
        <el-descriptions-item label="总体积">{{ result.total_cbm }} CBM</el-descriptions-item>
        <el-descriptions-item label="总毛重">{{ result.total_weight_kg }} kg</el-descriptions-item>
        <el-descriptions-item label="货柜判断">
          <el-tag
            :type="result.recommended === '20GP' ? 'success' : result.recommended === '40GP' ? 'warning' : 'danger'"
            size="small"
          >
            {{ result.recommended }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 20GP/40GP 明细 -->
      <div class="container-badges">
        <el-tag :type="result.fits_20gp ? 'success' : 'info'" size="small">20GP {{ result.fits_20gp ? '✅' : '❌' }}</el-tag>
        <el-tag :type="result.fits_40gp ? 'success' : 'info'" size="small">40GP {{ result.fits_40gp ? '✅' : '❌' }}</el-tag>
      </div>
    </div>

    <!-- 全方案比较 -->
    <div v-if="allSchemes.length > 1" class="all-schemes">
      <el-divider content-position="left">可用方案对比</el-divider>
      <el-table :data="allSchemes" border size="small" max-height="200">
        <el-table-column prop="pallet_type" label="卡板" width="100">
          <template #default="{ row }">
            {{ row.pallet_type ? row.pallet_type : '不打卡板' }}
          </template>
        </el-table-column>
        <el-table-column prop="drums" label="桶数" width="70" />
        <el-table-column prop="pallets" label="托数" width="70" />
        <el-table-column prop="drums_per_pallet" label="每托桶数" width="90" />
        <el-table-column prop="total_cbm" label="总体积(CBM)" width="110" />
        <el-table-column prop="total_weight_kg" label="总毛重(kg)" width="110" />
        <el-table-column prop="recommended" label="推荐货柜" width="90">
          <template #default="{ row }">
            <el-tag :type="row.recommended === '20GP' ? 'success' : 'warning'" size="small">{{ row.recommended }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import packagingApi, { type PackageType, type PalletType, type PackingScheme } from '@/api/packaging'

const emit = defineEmits<{
  (e: 'calculated', result: PackingScheme): void
}>()

const packageTypes = ref<PackageType[]>([])
const palletTypes = ref<PalletType[]>([])
const selectedPackage = ref('')
const selectedPallet = ref('1.1*1.1m')
const orderQtyKg = ref(0)
const usePallet = ref(false)
const calculating = ref(false)
const result = ref<PackingScheme | null>(null)
const allSchemes = ref<any[]>([])

onMounted(async () => {
  try {
    const [pkgs, pallets] = await Promise.all([
      packagingApi.getTypes(),
      packagingApi.getPallets(),
    ])
    packageTypes.value = pkgs
    palletTypes.value = pallets
  } catch (e) {
    console.error('加载包装数据失败', e)
  }
})

function onPackageChange() {
  result.value = null
  allSchemes.value = []
}

async function runCalculate() {
  if (!selectedPackage.value || orderQtyKg.value <= 0) return
  calculating.value = true
  result.value = null
  allSchemes.value = []
  try {
    // 查所有方案
    const schemes = await packagingApi.calculateSchemes({
      packaging_name: selectedPackage.value,
      order_qty_kg: orderQtyKg.value,
      use_pallet: usePallet.value,
    })
    allSchemes.value = schemes

    // 选中的方案
    if (usePallet.value) {
      const match = schemes.find(s => s.pallet_type === selectedPallet.value)
      result.value = match || schemes[0]
    } else {
      result.value = schemes.find(s => !s.pallet_type) || schemes[0]
    }

    if (result.value) {
      emit('calculated', result.value)
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '计算失败')
  } finally {
    calculating.value = false
  }
}

// 供父组件调用，初始化数量
function setQuantity(kg: number) {
  orderQtyKg.value = kg
}

// 供父组件调用，选中包装种类
function selectPackage(name: string) {
  const found = packageTypes.value.find(p => p.name === name)
  if (found) selectedPackage.value = name
}

defineExpose({ setQuantity, selectPackage })
</script>

<style scoped>
.packaging-calculator { padding: 4px 0; }
.calc-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.form-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
.unit { font-size: 13px; color: #909399; }
.pkg-opt { font-weight: 500; }
.pkg-dims { font-size: 12px; color: #909399; margin-left: 8px; }
.calc-result { margin-top: 8px; }
.container-badges { display: flex; gap: 8px; margin-top: 8px; }
.all-schemes { margin-top: 8px; }
</style>