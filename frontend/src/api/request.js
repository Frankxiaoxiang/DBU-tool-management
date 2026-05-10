import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import '../utils/datetime'
import { TOKEN_KEY, REFRESH_KEY, readSafeToken } from '../utils/storage'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = readSafeToken(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response,
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
      window.location.href = '/login'
      return Promise.reject(err)
    }
    if (status === 409) {
      ElMessageBox.alert(
        '该数据已被他人修改，请刷新页面后重试。',
        '数据冲突',
        { type: 'warning', confirmButtonText: '刷新' }
      ).then(() => window.location.reload())
      return Promise.reject(err)
    }
    return Promise.reject(err)
  }
)

export default request
