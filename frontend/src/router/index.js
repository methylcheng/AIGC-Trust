import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Detection from '../views/Detection.vue'
import Tasks from '../views/Tasks.vue'
import Certificates from '../views/Certificates.vue'
import Dashboard from '../views/Dashboard.vue'
import Login from '../views/Login.vue'

const routes = [
    { path: '/login', component: Login },
    { path: '/', component: Home },
    { path: '/detect', component: Detection, meta: { requiresAuth: true } },
    { path: '/tasks', component: Tasks, meta: { requiresAuth: true } },
    { path: '/certificates', component: Certificates, meta: { requiresAuth: true } },
    { path: '/dashboard', component: Dashboard, meta: { requiresAuth: true } }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// 路由守卫：检查是否需要登录
router.beforeEach(async (to, from, next) => {
    const token = localStorage.getItem('access_token')
    
    if (to.meta.requiresAuth) {
        if (!token) {
            // 需要登录但未登录，跳转到登录页
            next({
                path: '/login',
                query: { redirect: to.fullPath }
            })
        } else {
            // 有token，尝试验证是否有效
            try {
                // 导入axios实例
                const { default: request } = await import('../utils/request')
                
                // 尝试获取用户信息来验证token
                const response = await request.get('/auth/me', {
                    headers: { Authorization: `Bearer ${token}` }
                })
                
                // Token有效，允许访问
                next()
            } catch (error) {
                // Token无效或过期，清除并跳转登录
                console.warn('Token验证失败:', error.message)
                localStorage.removeItem('access_token')
                localStorage.removeItem('user_info')
                
                next({
                    path: '/login',
                    query: { redirect: to.fullPath }
                })
            }
        }
    } else if (to.path === '/login' && token) {
        // 已登录但访问登录页，跳转到首页
        next('/')
    } else {
        next()
    }
})

export default router
