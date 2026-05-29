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
          <router-link to="/order-paste" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/>
                <rect x="14" y="14" width="7" height="7" rx="1"/>
              </svg>
            </span>
            <span class="link-text">订单粘贴解析</span>
          </router-link>
          <router-link to="/pi-extract" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </span>
            <span class="link-text">PI 文件提取</span>
          </router-link>
          <router-link to="/package-calc" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
            </span>
            <span class="link-text">包装计算</span>
          </router-link>
          <router-link to="/data-merge" class="nav-link">
            <span class="link-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
            </span>
            <span class="link-text">数据关联</span>
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
        </div>

        <div class="nav-actions">
          <div class="nav-divider"></div>
        </div>
      </div>
    </nav>

    <router-view />
  </div>
</template>

<script setup lang="ts">
</script>

<style>
@import '@/styles/global.css';
</style>