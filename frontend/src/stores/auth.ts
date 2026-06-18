import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/api/axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const userName = ref<string | null>(localStorage.getItem('user_name'))

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(newToken: string, name: string) {
    token.value = newToken
    userName.value = name
    localStorage.setItem('access_token', newToken)
    localStorage.setItem('user_name', name)
  }

  function logout() {
    token.value = null
    userName.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_name')
  }

  async function login(name: string, password: string) {
    const response = await apiClient.post('/auth/login', { name, password })
    const { access_token } = response.data
    setAuth(access_token, name)
    return true
  }

  return {
    token,
    userName,
    isLoggedIn,
    setAuth,
    logout,
    login,
  }
})
