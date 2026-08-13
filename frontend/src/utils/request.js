import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, removeToken, removeUser } from './auth'

const service = axios.create({
  baseURL: '/api',
  timeout: 120000  // 上传 + AI解析可能较慢，设120秒超时
})

// 请求拦截器 — 自动携带 token
service.interceptors.request.use(config => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 — 统一错误处理
service.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response) {
      const { status, data } = err.response
      if (status === 401) {
        // token 无效或过期 — 清除登录信息，跳转登录页
        removeToken()
        removeUser()
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
      } else if (status === 403) {
        ElMessage.error(data?.detail || '权限不足')
      } else if (status === 422) {
        console.error('参数验证错误', data)
        ElMessage.error('请求参数错误')
      } else if (status >= 500) {
        ElMessage.error('服务器内部错误')
      }
    } else if (err.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else if (!err.response) {
      ElMessage.error('网络连接失败，请检查后端服务')
    }
    console.error('请求失败', err)
    return Promise.reject(err)
  }
)

export default service
