<template>
  <router-view v-if="authReady" />
  <div v-else class="auth-loading" />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient } from '@/api/axios'
import { useAuthStore } from '@/stores/auth'

const authReady = ref(false)
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    authReady.value = true
    return
  }
  try {
    // Verify token is still valid by calling an auth-protected endpoint
    await apiClient.get('/dashboard/orders')
    authReady.value = true
  } catch (e: any) {
    if (e.response?.status === 401) {
      authStore.logout()
      router.push('/login')
    }
    authReady.value = true
  }
})
</script>

<style>
.auth-loading {
  width: 100vw;
  height: 100vh;
}
</style>
