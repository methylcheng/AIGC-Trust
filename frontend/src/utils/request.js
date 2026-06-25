import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
    baseURL: '/api',
    timeout: 300000 // 5分钟超时，用于视频检测
})

// 请求拦截器
request.interceptors.request.use(
    config => {
        // 从 localStorage 获取 token
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    error => {
        ElMessage.error('请求失败')
        return Promise.reject(error)
    }
)

// 响应拦截器
let isRedirectingToLogin = false // 防止重复跳转

request.interceptors.response.use(
    response => {
        return response.data
    },
    error => {
        const message = error.response?.data?.detail || '请求失败'
        
        // 401 未授权，跳转到登录页
        if (error.response?.status === 401 && !isRedirectingToLogin) {
            isRedirectingToLogin = true
            ElMessage.error('登录已过期，请重新登录')
            localStorage.removeItem('access_token')
            localStorage.removeItem('user_info')
            
            // 延迟跳转，避免与其他导航冲突
            setTimeout(() => {
                window.location.href = '/login'
                isRedirectingToLogin = false
            }, 500)
            
            return Promise.reject(error)
        }
        
        ElMessage.error(message)
        return Promise.reject(error)
    }
)

export default request
