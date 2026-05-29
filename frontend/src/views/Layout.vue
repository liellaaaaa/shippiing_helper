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