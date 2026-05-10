import request from './request'
import { REFRESH_KEY, readSafeToken } from '../utils/storage'

export function login({ username, password }) {
  return request.post('/auth/login', { username, password })
}

export function refresh() {
  const refreshToken = readSafeToken(REFRESH_KEY)
  return request.post('/auth/refresh', {}, {
    headers: { Authorization: `Bearer ${refreshToken}` },
  })
}

export function logout() {
  return request.post('/auth/logout')
}

export function me() {
  return request.get('/auth/me')
}
