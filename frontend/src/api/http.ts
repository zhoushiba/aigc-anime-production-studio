import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'

/** 统一响应体：{ code, message, data, request_id } */
interface Envelope<T> {
  code: number
  message: string
  data: T
  request_id: string
}

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('aigc_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => {
    const body = response.data as Envelope<unknown>
    // 导出类接口是文件流，直接返回原始响应
    if (body === null || body === undefined || typeof body !== 'object' || !('code' in body)) {
      return response
    }
    if (body.code === 0) {
      return body.data as never
    }
    ElMessage.error(body.message || '请求失败')
    return Promise.reject(new Error(body.message))
  },
  (error) => {
    const status = error?.response?.status
    const message =
      error?.response?.data?.message ||
      error?.response?.data?.detail ||
      error?.message ||
      '网络异常，请稍后重试'
    if (status === 401) {
      localStorage.removeItem('aigc_token')
      localStorage.removeItem('aigc_user')
      if (!window.location.hash.startsWith('#/login')) {
        window.location.hash = '#/login'
      }
    }
    ElMessage.error(typeof message === 'string' ? message : '请求失败')
    return Promise.reject(error)
  }
)

export default http
export type { Envelope }
