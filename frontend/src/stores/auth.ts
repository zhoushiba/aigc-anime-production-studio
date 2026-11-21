import { defineStore } from 'pinia'
import { ref } from 'vue'

import { authApi, type UserInfo } from '@/api'

/** 登录态与当前用户，token 持久化在 localStorage */
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('aigc_token') || '')
  const user = ref<UserInfo | null>(JSON.parse(localStorage.getItem('aigc_user') || 'null'))

  function persist(nextToken: string, nextUser: UserInfo | null) {
    token.value = nextToken
    user.value = nextUser
    if (nextToken) {
      localStorage.setItem('aigc_token', nextToken)
    } else {
      localStorage.removeItem('aigc_token')
    }
    if (nextUser) {
      localStorage.setItem('aigc_user', JSON.stringify(nextUser))
    } else {
      localStorage.removeItem('aigc_user')
    }
  }

  async function login(username: string, password: string) {
    const data = await authApi.login({ username, password })
    persist(data.token, data.user)
    return data
  }

  async function register(payload: { username: string; password: string; display_name?: string; role?: string }) {
    const data = await authApi.register(payload)
    persist(data.token, data.user)
    return data
  }

  async function refresh() {
    if (!token.value) return null
    const me = await authApi.me()
    persist(token.value, me)
    return me
  }

  function logout() {
    persist('', null)
  }

  return { token, user, login, register, refresh, logout }
})
