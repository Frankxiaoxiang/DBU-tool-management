import { defineStore } from 'pinia'
import * as authApi from '../api/auth'
import { TOKEN_KEY, REFRESH_KEY, readSafeToken } from '../utils/storage'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: readSafeToken(TOKEN_KEY),
    refreshToken: readSafeToken(REFRESH_KEY),
  }),
  getters: {
    isAuthenticated: (s) => !!s.accessToken && !!s.user,
    roleCode: (s) => s.user?.role_code || null,
  },
  actions: {
    async login(username, password) {
      const resp = await authApi.login({ username, password })
      const data = resp.data.data
      this.accessToken = data.access_token
      this.refreshToken = data.refresh_token
      this.user = data.user
      localStorage.setItem(TOKEN_KEY, this.accessToken)
      localStorage.setItem(REFRESH_KEY, this.refreshToken)
    },
    async fetchMe() {
      const resp = await authApi.me()
      this.user = resp.data.data
    },
    async logout() {
      try { await authApi.logout() } catch { /* 兜底，本地一定要清 */ }
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
      window.location.href = '/login'
    },
    hasPermission() {
      // FE #6 雏形：本期仅区分 super_admin / 其他
      // TODO Phase 1+：派生自 utils/permissions.js + Doc/05_permissions.md
      if (!this.user) return false
      if (this.roleCode === 'super_admin') return true
      return false
    },
  },
})
