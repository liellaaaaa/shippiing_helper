<template>
  <div class="package-calc-page">
    <!-- 顶部控制面板 -->
    <div class="control-panel">
      <!-- 运输模式切换 -->
      <div class="control-section">
        <label class="control-label">运输模式</label>
        <el-radio-group v-model="transportMode" class="mode-radio">
          <el-radio-button value="sea">海运</el-radio-button>
          <el-radio-button value="air">空运</el-radio-button>
          <el-radio-button value="land">陆运</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 输入模式切换（仅海运显示） -->
      <div class="control-section" v-if="transportMode === 'sea'">
        <label class="control-label">输入模式</label>
        <el-radio-group v-model="inputMode" class="mode-radio">
          <el-radio-button value="order">按订单计算</el-radio-button>
          <el-radio-button value="manual">手动输入</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 海运模式：输入面板 -->
    <div class="input-panel" v-if="transportMode === 'sea'">
      <!-- 按订单模式 -->
      <div v-if="inputMode === 'order'" class="order-input-mode">
        <el-select
          v-model="selectedOrderId"
          filterable
          remote
          placeholder="搜索订单号或客户名称"
          :remote-method="searchOrders"
          :loading="searchingOrders"
          class="order-select"
          @change="handleOrderChange"
        >
          <el-option
            v-for="order in searchResults"
            :key="order.id"
            :label="order.order_no"
            :value="order.id"
          >
            <span>{{ order.order_no }}</span>
            <span class="customer-tag">{{ order.customer_code }}</span>
          </el-option>
        </el-select>

        <el-select
          v-model="selectedInternalCode"
          placeholder="选择产品（内部编码）"
          class="product-select"
          :disabled="!selectedOrderId"
          @change="handleProductChange"
        >
          <el-option
            v-for="item in orderItems"
            :key="item.internal_code"
            :label="item.internal_code"
            :value="item.internal_code"
          >
            {{ item.internal_code }} — {{ item.product_cn }}
          </el-option>
        </el-select>
      </div>

      <!-- 手动输入模式 -->
      <div v-else class="manual-input-mode">
        <el-input-number
          v-model="quantityKg"
          :min="0"
          :step="100"
          placeholder="订单量 (kg)"
          class="quantity-input"
        />
      </div>

      <!-- 通用：包装类型选择 -->
      <PackagingTypeSelect
        v-model="packagingName"
        :recommended="packagingRecommendation"
        @change="handlePackagingChange"
      />

      <!-- 通用：数量输入（手动模式时显示） -->
      <div class="form-row" v-if="inputMode === 'manual' || transportMode !== 'sea'">
        <label class="form-label">订单量 (kg)</label>
        <el-input-number v-model="quantityKg" :min="0" :step="100" />
      </div>

      <!-- 海运：卡板设置 -->
      <div class="form-row" v-if="transportMode === 'sea'">
        <label class="form-label">卡板规格</label>
        <el-radio-group v-model="palletSpec" :disabled="noPallet">
          <el-radio-button value="1.0x1.0">1.0×1.0m</el-radio-button>
          <el-radio-button value="1.1x1.1">1.1×1.1m</el-radio-button>
        </el-radio-group>

        <label class="form-label" style="margin-left: 16px;">单板数量</label>
        <el-input-number
          v-model="palletQty"
          :min="0"
          :disabled="noPallet"
          class="pallet-qty-input"
        />

        <el-checkbox v-model="noPallet" class="no-pallet-checkbox">不打卡板</el-checkbox>
      </div>
    </div>

    <!-- 非海运：通用输入面板 -->
    <div class="input-panel" v-if="transportMode !== 'sea'">
      <div class="form-row">
        <label class="form-label">订单量 (kg)</label>
        <el-input-number v-model="quantityKg" :min="0" :step="100" />
      </div>

      <PackagingTypeSelect
        v-model="packagingName"
        :recommended="packagingRecommendation"
        @change="handlePackagingChange"
      />
    </div>

    <!-- 计算结果区 -->
    <div class="result-panel" v-if="hasValidInput" v-loading="calculating">
      <!-- 海运结果 -->
      <template v-if="transportMode === 'sea' && seaResult">
        <!-- 智能结论区 -->
        <div class="smart-conclusion" :class="containerStatusClass">
          <p class="conclusion-text">{{ seaResult.packing_scheme }}</p>
          <p class="container-advice">
            当前体积约 {{ seaResult.total_cbm }} CBM，
            {{ seaResult.container.status === 'ok'
              ? `强烈建议使用 ${seaResult.container.recommended}（装载率 ${seaResult.container.load_rate}%）`
              : `建议升级为 ${seaResult.container.recommended}（装载率 ${seaResult.container.load_rate}%）` }}。
          </p>
        </div>

        <!-- 核心指标卡片 -->
        <div class="metric-cards">
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.drums }}</div>
            <div class="metric-label">桶/箱数</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.pallets }}</div>
            <div class="metric-label">卡板数</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.total_cbm.toFixed(2) }}</div>
            <div class="metric-label">总体积 (CBM)</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.total_weight_kg.toLocaleString() }}</div>
            <div class="metric-label">总毛重 (KG)</div>
          </el-card>
        </div>
      </template>

      <!-- 空运结果 -->
      <template v-if="transportMode === 'air' && airResult">
        <AirFreightPanel :result="airResult" />
      </template>

      <!-- 陆运结果 -->
      <template v-if="transportMode === 'land' && landResult">
        <LandTransportPanel :result="landResult" />
      </template>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-else-if="!calculating">
      <el-empty description="请填写参数后查看计算结果" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  calculatePackage,
  getPackagingTypes,
  recommendPackaging,
  type SeaCalculationResult,
  type AirCalculationResult,
  type LandCalculationResult,
  type PackagingType,
} from '@/api/packages'
import PackagingTypeSelect from '@/components/phase1/PackagingTypeSelect.vue'
import AirFreightPanel from '@/components/phase1/AirFreightPanel.vue'
import LandTransportPanel from '@/components/phase1/LandTransportPanel.vue'

const route = useRoute()

// ── State ────────────────────────────────────────────────────────────────────
const transportMode = ref<'sea' | 'air' | 'land'>('sea')
const inputMode = ref<'order' | 'manual'>('manual')
const selectedOrderId = ref<number | null>(null)
const selectedInternalCode = ref<string>('')
const quantityKg = ref<number | null>(null)
const packagingName = ref<string>('')
const palletSpec = ref<'1.0x1.0' | '1.1x1.1'>('1.1x1.1')
const palletQty = ref<number>(0)
const noPallet = ref(false)

const packagingTypes = ref<PackagingType[]>([])
const packagingRecommendation = ref<string | null>(null)
const seaResult = ref<SeaCalculationResult | null>(null)
const airResult = ref<AirCalculationResult | null>(null)
const landResult = ref<LandCalculationResult | null>(null)
const calculating = ref(false)
const searchResults = ref<any[]>([])
const searchingOrders = ref(false)
const orderItems = ref<any[]>([])

// ── Computed ────────────────────────────────────────────────────────────────
const hasValidInput = computed(() => {
  if (!quantityKg.value || quantityKg.value <= 0) return false
  if (!packagingName.value) return false
  return true
})

const containerStatusClass = computed(() => {
  if (!seaResult.value) return ''
  const status = seaResult.value.container.status
  if (status === 'ok') return 'status-ok'
  if (status === 'upgrade') return 'status-upgrade'
  return 'status-overlimit'
})

// ── Debounce ────────────────────────────────────────────────────────────────
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const debouncedCalculate = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    performCalculate()
  }, 300)
}

// ── Methods ────────────────────────────────────────────────────────────────
const loadPackagingTypes = async () => {
  const data = await getPackagingTypes()
  packagingTypes.value = data.types
  // 默认选第一个
  if (packagingTypes.value.length > 0) {
    packagingName.value = packagingTypes.value[0].name
    updatePalletQty()
  }
}

const updatePalletQty = () => {
  const type = packagingTypes.value.find(t => t.name === packagingName.value)
  if (!type) return
  palletQty.value = palletSpec.value === '1.0x1.0'
    ? (type.pallet_1x1 || 0)
    : (type.pallet_1_1x1_1 || 0)
}

const handlePackagingChange = () => {
  updatePalletQty()
  packagingRecommendation.value = null // 人工接管，清除推荐标记
  debouncedCalculate()
}

const searchOrders = async (query: string) => {
  if (!query) return
  searchingOrders.value = true
  try {
    const { getOrderList } = await import('@/api/merge')
    const data = await getOrderList({ search: query, page_size: 10 })
    searchResults.value = data.orders
  } catch (e) {
    console.error('Search orders failed:', e)
  } finally {
    searchingOrders.value = false
  }
}

const handleOrderChange = async (orderId: number) => {
  // 加载订单产品明细
  const { getOrderComparison } = await import('@/api/merge')
  const data = await getOrderComparison(orderId)
  orderItems.value = data.items
  if (orderItems.value.length > 0) {
    selectedInternalCode.value = orderItems.value[0].internal_code
    handleProductChange(selectedInternalCode.value)
  }
}

const handleProductChange = async (internalCode: string) => {
  if (!internalCode) return
  // 查询知识库推荐
  try {
    const rec = await recommendPackaging(internalCode)
    if (rec.recommended_packaging) {
      packagingName.value = rec.recommended_packaging
      packagingRecommendation.value = rec.recommended_packaging
      updatePalletQty()
    }
  } catch (e) {
    // 无推荐，继续用当前选择
  }
  debouncedCalculate()
}

// 监听所有输入变化，触发重新计算
watch([quantityKg, packagingName, palletSpec, palletQty, noPallet, transportMode], () => {
  if (hasValidInput.value) {
    debouncedCalculate()
  }
})

const performCalculate = async () => {
  if (!hasValidInput.value) return
  calculating.value = true
  try {
    const result = await calculatePackage({
      mode: inputMode.value,
      quantity_kg: quantityKg.value!,
      packaging_name: packagingName.value,
      pallet_spec: palletSpec.value,
      pallet_qty: palletQty.value,
      no_pallet: noPallet.value,
      transport_mode: transportMode.value,
      order_id: selectedOrderId.value || undefined,
      internal_code: selectedInternalCode.value || undefined,
    })

    if (transportMode.value === 'sea') {
      seaResult.value = result as SeaCalculationResult
    } else if (transportMode.value === 'air') {
      airResult.value = result as AirCalculationResult
    } else {
      landResult.value = result as LandCalculationResult
    }
  } catch (error) {
    console.error('Calculation failed:', error)
  } finally {
    calculating.value = false
  }
}

// URL 联动：检测从 FR-3.x 跳转过来的参数
onMounted(() => {
  loadPackagingTypes()

  const mode = route.query.mode as string
  const internalCode = route.query.internal_code as string
  if (mode === 'order' && internalCode) {
    inputMode.value = 'order'
    selectedInternalCode.value = internalCode
    // 尝试直接推荐
    handleProductChange(internalCode)
  }
})
</script>

<style scoped>
.package-calc-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

.control-panel { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.control-section { display: flex; align-items: center; gap: 12px; }
.control-label { font-size: 13px; color: #606266; font-weight: 500; }

.input-panel { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.order-input-mode { display: flex; gap: 12px; margin-bottom: 16px; }
.order-select { width: 280px; }
.product-select { width: 320px; }
.customer-tag { margin-left: 8px; color: #909399; font-size: 12px; }
.manual-input-mode { margin-bottom: 16px; }
.quantity-input { width: 200px; }

.form-row { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.form-label { font-size: 13px; color: #606266; min-width: 80px; }
.pallet-qty-input { width: 120px; }
.no-pallet-checkbox { margin-left: 16px; }

.result-panel { display: flex; flex-direction: column; gap: 16px; }
.smart-conclusion { padding: 16px 20px; border-radius: 8px; font-size: 15px; line-height: 1.6; }
.smart-conclusion.status-ok { background: #f0f9eb; border: 1px solid #c2e7b0; }
.smart-conclusion.status-upgrade { background: #fdf6ec; border: 1px solid #f5dab1; }
.smart-conclusion.status-overlimit { background: #fef0f0; border: 1px solid #fbc4c4; }
.conclusion-text { margin: 0 0 4px 0; font-weight: 500; }
.container-advice { margin: 0; color: #606266; font-size: 13px; }

.metric-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.metric-card { text-align: center; }
.metric-value { font-size: 28px; font-weight: 700; color: #303133; }
.metric-label { font-size: 12px; color: #909399; margin-top: 4px; }

.empty-state { padding: 60px 0; }

@media (max-width: 768px) {
  .metric-cards { grid-template-columns: repeat(2, 1fr); }
}
</style>