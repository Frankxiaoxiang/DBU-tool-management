export const TOKEN_KEY = 'access_token'
export const REFRESH_KEY = 'refresh_token'

export function readSafeToken(key) {
  const v = localStorage.getItem(key)
  return v && v !== 'undefined' && v !== 'null' ? v : null
}
