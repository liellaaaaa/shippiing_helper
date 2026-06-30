<template>
  <div id="app">
    <nav class="main-nav">
      <div class="nav-container">
        <div class="nav-brand">
          <div class="brand-mark">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <path d="M14 2L25 8V20L14 26L3 20V8L14 2Z" stroke="currentColor" stroke-width="2" fill="none"/>
              <path d="M14 10L19 13V19L14 22L9 19V13L14 10Z" fill="currentColor"/>
            </svg>
          </div>
          <div class="brand-text">
            <span class="brand-name">ShippingHelper</span>
            <span class="brand-tag">船务效率工具</span>
          </div>
        </div>

        <div class="nav-links">
          <router-link to="/workflow" class="nav-link nav-link-home">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
            </span>
            <span class="link-text">订单处理</span>
          </router-link>
          <router-link to="/phase2" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </span>
            <span class="link-text">文档编辑</span>
          </router-link>
          <router-link to="/phase3" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
              </svg>
            </span>
            <span class="link-text">报关资料</span>
          </router-link>
          <router-link to="/dashboard" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
              </svg>
            </span>
            <span class="link-text">数据看板</span>
          </router-link>
          <router-link to="/data-center" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </span>
            <span class="link-text">数据中心</span>
          </router-link>
        </div>

        <div class="nav-actions">
          <div class="nav-divider"></div>
          <el-popover
            placement="bottom"
            :width="320"
            trigger="click"
            v-model:visible="healthPopoverVisible">
            <template #reference>
              <el-button class="health-btn" :loading="healthLoading" circle title="系统检测" @click="checkHealth">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </el-button>
            </template>
            <div v-if="healthLoading">检查中...</div>
            <div v-else-if="healthData">
              <div class="health-header" style="margin-bottom:12px">
                <span :class="['health-badge', healthData.status]">
                  {{ healthData.status === 'ok' ? '✅ 全部正常' : '⚠️ 部分异常' }}
                </span>
              </div>
              <div class="health-row" v-for="(val, key) in healthData.checks" :key="key"
                   style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <span>{{ getCheckIcon(val.status) }}</span>
                <span style="font-weight:500;width:80px">{{ key === 'api' ? 'API' :
                  key === 'onlyoffice' ? 'OnlyOffice' :
                  key === 'database' ? '数据库' : 'Tesseract' }}</span>
                <span style="color:var(--text-secondary);font-size:12px">{{ val.message }}</span>
              </div>
              <el-button size="small" style="margin-top:10px;width:100%" @click="checkHealth">
                重新检测
              </el-button>
            </div>
            <div v-else style="color:var(--text-secondary)">检测失败</div>
          </el-popover>
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-badge">
              <el-icon><User /></el-icon>
              <span class="user-name">{{ authStore.userName }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </nav>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { healthApi, type HealthResponse } from '@/api/health'

const router = useRouter()
const authStore = useAuthStore()

const healthPopoverVisible = ref(false)
const healthData = ref<HealthResponse | null>(null)
const healthLoading = ref(false)

async function checkHealth() {
  healthLoading.value = true
  healthPopoverVisible.value = true
  try {
    healthData.value = await healthApi.check()
  } catch {
    healthData.value = null
  } finally {
    healthLoading.value = false
  }
}

function getCheckIcon(s: 'ok' | 'error') {
  return s === 'ok' ? '✅' : '❌'
}

function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style>
@import '@/styles/global.css';

.user-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.user-badge:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.user-name {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.health-btn {
  border: none !important;
  background: transparent !important;
}
.health-btn:hover {
  background: var(--bg-hover) !important;
}
.health-badge.ok {
  color: #67c23a;
}
.health-badge.degraded {
  color: #e6a23c;
}
</style>