<template>
  <div class="reference-panel">
    <el-collapse v-model="activeNames" accordion>
      <!-- Tab 1: Phase1数据 -->
      <el-collapse-item title="Phase1数据" name="phase1">
        <div v-if="phase1Data" class="field-list">
          <div class="field-row">
            <el-tag type="info">发货人</el-tag>
            <el-input :model-value="phase1Data.shipper || 'HONGHAO CHEMICAL CO., LTD.'" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.shipper || 'HONGHAO CHEMICAL CO., LTD.')">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">收货人</el-tag>
            <el-input :model-value="phase1Data.consignee" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.consignee)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">通知人</el-tag>
            <el-input :model-value="phase1Data.consignee" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.consignee)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">卸货港</el-tag>
            <el-input :model-value="phase1Data.port" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.port)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">品名中文</el-tag>
            <el-input :model-value="phase1Data.product_name_cn" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.product_name_cn)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">品名英文</el-tag>
            <el-input :model-value="phase1Data.product_name_en" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.product_name_en)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">H.S.Code</el-tag>
            <el-input :model-value="phase1Data.hs_code" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.hs_code)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">毛重</el-tag>
            <el-input :model-value="phase1Data.gross_weight" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.gross_weight)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="field-row">
            <el-tag type="info">体积(CBM)</el-tag>
            <el-input :model-value="phase1Data.volume" readonly>
              <template #append>
                <el-button @click="copy(phase1Data.volume)">
                  <i class="el-icon-document-copy"></i>
                </el-button>
              </template>
            </el-input>
          </div>
        </div>
        <el-empty v-else description="暂无数据" />
      </el-collapse-item>

      <!-- Tab 2: MSDS摘要 -->
      <el-collapse-item title="MSDS摘要" name="msds">
        <div v-if="msdsData" class="field-list">
          <div class="field-row">
            <el-tag type="info">产品名称</el-tag>
            <el-input :model-value="msdsData.product_name_cn" readonly />
          </div>
          <div class="field-row">
            <el-tag type="info">物理形态</el-tag>
            <el-input :model-value="msdsData.physical_form" readonly />
          </div>
          <div class="field-row">
            <el-tag type="info">离子类型</el-tag>
            <el-input :model-value="msdsData.ion_type" readonly />
          </div>
          <div class="field-row">
            <el-tag type="info">pH值</el-tag>
            <el-input :model-value="msdsData.ph" readonly />
          </div>
        </div>
        <el-empty v-else description="未找到MSDS数据" />
      </el-collapse-item>

      <!-- Tab 3: 运输鉴定报告 -->
      <el-collapse-item title="运输鉴定报告" name="transport">
        <el-upload
          drag
          accept=".pdf"
          :auto-upload="false"
          :on-change="handleTransportUpload"
          class="upload-area"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">拖拽PDF文件或<em>点击上传</em></div>
        </el-upload>
        <div v-if="transportData" class="field-list">
          <div class="field-row">
            <el-tag type="info">产品名称</el-tag>
            <el-input v-model="transportData.product_name" />
          </div>
          <div class="field-row">
            <el-tag type="info">英文名</el-tag>
            <el-input v-model="transportData.english_name" />
          </div>
          <div class="field-row">
            <el-tag type="info">报告编号</el-tag>
            <el-input v-model="transportData.report_number" />
          </div>
          <div class="field-row">
            <el-tag type="info">样品描述</el-tag>
            <el-input v-model="transportData.sample_description" />
          </div>
        </div>
      </el-collapse-item>

      <!-- Tab 4: 出口商品编码 -->
      <el-collapse-item title="出口商品编码" name="exportcodes">
        <div class="search-row">
          <el-input v-model="exportCodeQuery" placeholder="输入商品编码" />
          <el-button type="primary" @click="searchExportCodes">查询</el-button>
        </div>
        <div v-if="exportCodeData" class="field-list">
          <div class="field-row">
            <el-tag type="info">HS编码</el-tag>
            <el-input :model-value="exportCodeData.hs_code" readonly />
          </div>
          <div class="field-row">
            <el-tag type="info">报关名称</el-tag>
            <el-input :model-value="exportCodeData.customs_name" readonly />
          </div>
          <div class="field-row">
            <el-tag type="info">成分</el-tag>
            <el-input :model-value="exportCodeData.composition" readonly />
          </div>
        </div>
        <el-empty v-else description="暂无数据" />
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { phase2Api } from '@/api/phase2'

const props = defineProps<{
  orderId: number | null
  productName: string
  internalCode: string
}>()

const activeNames = ref(['phase1'])
const phase1Data = ref<any>(null)
const msdsData = ref<any>(null)
const transportData = ref<any>(null)
const exportCodeData = ref<any>(null)
const exportCodeQuery = ref('')

async function copy(text: string) {
  if (!text) return
  await navigator.clipboard.writeText(text)
  ElMessage.success('已复制')
}

watch(() => props.orderId, async (id) => {
  if (!id) return
  const res = await fetch(`/api/v1/merge/orders/${id}/comparison`)
  phase1Data.value = await res.json()
}, { immediate: true })

watch(() => props.productName, async (name) => {
  if (!name) return
  const res = await phase2Api.listMsds({ search: name, pageSize: 1 })
  msdsData.value = res.data.items?.[0] || null
}, { immediate: true })

watch(() => props.internalCode, (code) => {
  exportCodeQuery.value = code
})

async function handleTransportUpload(uploadFile: { raw?: File }) {
  const file = uploadFile.raw
  if (!file) return
  const res = await phase2Api.uploadTransportReport(file)
  transportData.value = res.data
}

async function searchExportCodes() {
  if (!exportCodeQuery.value) return
  const res = await phase2Api.getExportCodes(exportCodeQuery.value)
  exportCodeData.value = res.data.error ? null : res.data
}
</script>

<style scoped>
.reference-panel {
  padding: 8px;
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.field-row .el-tag {
  min-width: 100px;
  text-align: center;
}

.field-row .el-input {
  flex: 1;
}

.search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.search-row .el-input {
  flex: 1;
}

.upload-area {
  margin-bottom: 16px;
}
</style>
