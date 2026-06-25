<template>
    <header class="header">
        <div class="header-content">
            <h1>🔐 AIGC-Trust</h1>
            <p>内容可信检测平台</p>
        </div>
        <nav class="nav">
            <router-link to="/" class="nav-item">首页</router-link>
            <router-link to="/detect" class="nav-item">内容检测</router-link>
            <router-link to="/tasks" class="nav-item">任务管理</router-link>
            <router-link to="/certificates" class="nav-item">证书查询</router-link>
            <router-link to="/dashboard" class="nav-item">统计看板</router-link>
            
            <!-- 用户信息 -->
            <div v-if="userInfo" class="user-info">
                <el-dropdown @command="handleCommand">
                    <span class="user-name">
                        <el-icon><user /></el-icon>
                        {{ userInfo.username }}
                    </span>
                    <template #dropdown>
                        <el-dropdown-menu>
                            <el-dropdown-item command="logout">
                                <el-icon><switch-button /></el-icon>
                                退出登录
                            </el-dropdown-item>
                        </el-dropdown-menu>
                    </template>
                </el-dropdown>
            </div>
        </nav>
    </header>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userInfo = ref(null)

// 加载用户信息
onMounted(() => {
    const userStr = localStorage.getItem('user_info')
    if (userStr) {
        userInfo.value = JSON.parse(userStr)
    }
})

// 处理下拉菜单命令
const handleCommand = async (command) => {
    if (command === 'logout') {
        try {
            // 调用后端logout接口
            const { logout } = await import('../api/auth')
            await logout()
        } catch (error) {
            console.error('退出登录失败:', error)
            // 即使后端失败，也要清除本地数据
        } finally {
            // 清除本地存储
            localStorage.removeItem('access_token')
            localStorage.removeItem('user_info')
            
            ElMessage.success('已退出登录')
            
            // 跳转到登录页
            router.push('/login')
        }
    }
}
</script>

<style scoped>
.header {
    background: linear-gradient(135deg, #1E3A5F 0%, #1F4E79 100%);
    box-shadow: 0 2px 20px rgba(30, 58, 95, 0.2);
    padding: 20px 40px;
}

.header-content {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 15px;
}

.header-content h1 {
    font-size: 28px;
    color: white;
    font-weight: 600;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-content p {
    color: rgba(255, 255, 255, 0.9);
    font-size: 14px;
}

.nav {
    display: flex;
    gap: 30px;
}

.nav-item {
    color: rgba(255, 255, 255, 0.85);
    text-decoration: none;
    font-size: 16px;
    padding: 8px 16px;
    border-radius: 6px;
    transition: all 0.3s;
    font-weight: 500;
}

.nav-item:hover {
    background: rgba(255, 255, 255, 0.15);
    color: white;
}

.nav-item.router-link-active {
    background: rgba(255, 255, 255, 0.25);
    color: white;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.user-info {
    margin-left: auto;
}

.user-name {
    color: rgba(255, 255, 255, 0.9);
    font-size: 14px;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.3s;
}

.user-name:hover {
    background: rgba(255, 255, 255, 0.15);
    color: white;
}
</style>
