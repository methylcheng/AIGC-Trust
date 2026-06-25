<template>
    <div class="login-container">
        <div class="login-box">
            <div class="login-header">
                <h1>AIGC-Trust</h1>
                <p>内容真实性检测与可信溯源平台</p>
            </div>
            
            <el-tabs v-model="activeTab" class="login-tabs">
                <!-- 登录表单 -->
                <el-tab-pane label="登录" name="login">
                    <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef">
                        <el-form-item prop="username">
                            <el-input 
                                v-model="loginForm.username" 
                                placeholder="用户名"
                                prefix-icon="User"
                                size="large"
                            />
                        </el-form-item>
                        
                        <el-form-item prop="password">
                            <el-input 
                                v-model="loginForm.password" 
                                type="password"
                                placeholder="密码"
                                prefix-icon="Lock"
                                size="large"
                                show-password
                                @keyup.enter="handleLogin"
                            />
                        </el-form-item>
                        
                        <!-- 验证码 -->
                        <el-form-item prop="captcha">
                            <div class="captcha-row">
                                <el-input 
                                    v-model="loginForm.captcha" 
                                    placeholder="请输入验证码"
                                    prefix-icon="Key"
                                    size="large"
                                    style="flex: 1; margin-right: 10px"
                                    @keyup.enter="handleLogin"
                                />
                                <Captcha ref="loginCaptchaRef" v-model="loginCaptchaCode" />
                            </div>
                        </el-form-item>
                        
                        <el-form-item>
                            <el-button 
                                type="primary" 
                                size="large"
                                :loading="loading"
                                @click="handleLogin"
                                style="width: 100%"
                            >
                                登录
                            </el-button>
                        </el-form-item>
                    </el-form>
                </el-tab-pane>
                
                <!-- 注册表单 -->
                <el-tab-pane label="注册" name="register">
                    <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef">
                        <el-form-item prop="username">
                            <el-input 
                                v-model="registerForm.username" 
                                placeholder="用户名（3-50个字符）"
                                prefix-icon="User"
                                size="large"
                            />
                        </el-form-item>
                        
                        <el-form-item prop="password">
                            <el-input 
                                v-model="registerForm.password" 
                                type="password"
                                placeholder="密码（至少8个字符，包含大小写字母、数字和特殊字符）"
                                prefix-icon="Lock"
                                size="large"
                                show-password
                            />
                        </el-form-item>
                        
                        <!-- 密码强度提示 -->
                        <div class="password-tips">
                            <div class="tip-title">密码必须包含：</div>
                            <div class="tip-item">• 至少8个字符</div>
                            <div class="tip-item">• 至少一个大写字母 (A-Z)</div>
                            <div class="tip-item">• 至少一个小写字母 (a-z)</div>
                            <div class="tip-item">• 至少一个数字 (0-9)</div>
                            <div class="tip-item">• 至少一个特殊字符 (!@#$%^&*等)</div>
                            <div class="tip-item">• 不能包含空格</div>
                        </div>
                        
                        <el-form-item prop="confirmPassword">
                            <el-input 
                                v-model="registerForm.confirmPassword" 
                                type="password"
                                placeholder="确认密码"
                                prefix-icon="Lock"
                                size="large"
                                show-password
                            />
                        </el-form-item>
                        
                        <!-- 注册验证码 -->
                        <el-form-item prop="captcha">
                            <div class="captcha-row">
                                <el-input 
                                    v-model="registerForm.captcha" 
                                    placeholder="请输入验证码"
                                    prefix-icon="Key"
                                    size="large"
                                    style="flex: 1; margin-right: 10px"
                                />
                                <Captcha ref="registerCaptchaRef" v-model="registerCaptchaCode" />
                            </div>
                        </el-form-item>
                        
                        <el-form-item>
                            <el-button 
                                type="primary" 
                                size="large"
                                :loading="loading"
                                @click="handleRegister"
                                style="width: 100%"
                            >
                                注册
                            </el-button>
                        </el-form-item>
                    </el-form>
                </el-tab-pane>
            </el-tabs>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/auth'
import Captcha from '../components/Captcha.vue'

const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const loginCaptchaRef = ref(null)
const registerCaptchaRef = ref(null)
const loginCaptchaCode = ref('')
const registerCaptchaCode = ref('')

// 登录表单
const loginForm = reactive({
    username: '',
    password: '',
    captcha: ''
})

const validateCaptcha = (rule, value, callback) => {
    if (value === '') {
        callback(new Error('请输入验证码'))
    } else if (value.toLowerCase() !== loginCaptchaCode.value.toLowerCase()) {
        callback(new Error('验证码错误'))
    } else {
        callback()
    }
}

const loginRules = {
    username: [
        { required: true, message: '请输入用户名', trigger: 'blur' }
    ],
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' }
    ],
    captcha: [
        { required: true, validator: validateCaptcha, trigger: 'blur' }
    ]
}

// 注册表单
const registerForm = reactive({
    username: '',
    password: '',
    confirmPassword: '',
    captcha: ''
})

const validateRegisterCaptcha = (rule, value, callback) => {
    if (value === '') {
        callback(new Error('请输入验证码'))
    } else if (value.toLowerCase() !== registerCaptchaCode.value.toLowerCase()) {
        callback(new Error('验证码错误'))
    } else {
        callback()
    }
}

const validatePassConfirm = (rule, value, callback) => {
    if (value === '') {
        callback(new Error('请再次输入密码'))
    } else if (value !== registerForm.password) {
        callback(new Error('两次输入的密码不一致'))
    } else {
        callback()
    }
}

// 密码强度验证
const validatePasswordStrength = (rule, value, callback) => {
    if (value === '') {
        callback(new Error('请输入密码'))
    } else {
        // 检查长度度
        if (value.length < 8) {
            callback(new Error('密码长度至少8个字符'))
        } 
        // 检查是否包含大写字母
        else if (!/[A-Z]/.test(value)) {
            callback(new Error('密码必须包含至少一个大写字母'))
        }
        // 检查是否包含小写字母
        else if (!/[a-z]/.test(value)) {
            callback(new Error('密码必须包含至少一个小写字母'))
        }
        // 检查是否包含数字
        else if (!/[0-9]/.test(value)) {
            callback(new Error('密码必须包含至少一个数字'))
        }
        // 检查是否包含特殊字符
        else if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(value)) {
            callback(new Error('密码必须包含至少一个特殊字符(!@#$%^&*等)'))
        }
        // 检查是否包含空格
        else if (/\s/.test(value)) {
            callback(new Error('密码不能包含空格'))
        }
        else {
            callback()
        }
    }
}

const registerRules = {
    username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 50, message: '用户名长度在3到50个字符之间', trigger: 'blur' }
    ],
    password: [
        { required: true, validator: validatePasswordStrength, trigger: 'blur' }
    ],
    confirmPassword: [
        { required: true, validator: validatePassConfirm, trigger: 'blur' }
    ],
    captcha: [
        { required: true, validator: validateRegisterCaptcha, trigger: 'blur' }
    ]
}

// 处理登录
const handleLogin = async () => {
    if (!loginFormRef.value) return
    
    await loginFormRef.value.validate(async (valid) => {
        if (valid) {
            loading.value = true
            try {
                const response = await login({
                    username: loginForm.username,
                    password: loginForm.password
                })
                
                // 保存 token 和用户信息
                localStorage.setItem('access_token', response.access_token)
                localStorage.setItem('user_info', JSON.stringify(response.user))
                
                ElMessage.success('登录成功')
                
                // 跳转到首页或之前访问的页面
                const redirect = router.currentRoute.value.query.redirect || '/'
                router.push(redirect)
            } catch (error) {
                console.error('登录失败:', error)
                // 登录失败后刷新验证码
                if (loginCaptchaRef.value) {
                    loginCaptchaRef.value.refresh()
                }
                loginForm.captcha = ''
            } finally {
                loading.value = false
            }
        }
    })
}

// 处理注册
const handleRegister = async () => {
    if (!registerFormRef.value) return
    
    await registerFormRef.value.validate(async (valid) => {
        if (valid) {
            loading.value = true
            try {
                await register({
                    username: registerForm.username,
                    password: registerForm.password,
                    role: 'user'
                })
                
                ElMessage.success('注册成功，请登录')
                
                // 切换到登录 tab
                activeTab.value = 'login'
                
                // 自动填充用户名
                loginForm.username = registerForm.username
                loginForm.password = ''
                
                // 清空注册表单
                registerForm.captcha = ''
                if (registerCaptchaRef.value) {
                    registerCaptchaRef.value.refresh()
                }
            } catch (error) {
                console.error('注册失败:', error)
                // 注册失败后刷新验证码
                if (registerCaptchaRef.value) {
                    registerCaptchaRef.value.refresh()
                }
                registerForm.captcha = ''
            } finally {
                loading.value = false
            }
        }
    })
}
</script>

<style scoped>
.login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    position: relative;
    overflow: hidden;
}

.login-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="rgba(255,255,255,0.1)"/></svg>');
    background-size: 200px;
    opacity: 0.3;
}

.login-box {
    width: 450px;
    padding: 40px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    position: relative;
    z-index: 1;
}

.login-header {
    text-align: center;
    margin-bottom: 30px;
}

.login-header h1 {
    font-size: 36px;
    color: #303133;
    margin: 0 0 10px 0;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.login-header p {
    font-size: 14px;
    color: #909399;
    margin: 0;
}

.login-tabs {
    margin-top: 20px;
}

.login-tabs :deep(.el-tabs__header) {
    margin-bottom: 30px;
}

.login-tabs :deep(.el-tabs__item) {
    font-size: 16px;
    font-weight: 500;
}

:deep(.el-input__wrapper) {
    padding: 12px 15px;
    border-radius: 8px;
}

:deep(.el-button--large) {
    padding: 14px 20px;
    font-size: 16px;
    border-radius: 8px;
}

/* 密码强度提示 */
.password-tips {
    margin-top: -10px;
    margin-bottom: 20px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;
    border-left: 3px solid #667eea;
}

.tip-title {
    font-size: 13px;
    color: #303133;
    font-weight: 600;
    margin-bottom: 8px;
}

.tip-item {
    font-size: 12px;
    color: #606266;
    line-height: 1.8;
}

/* 验证码行 */
.captcha-row {
    display: flex;
    align-items: center;
    gap: 10px;
}
</style>
