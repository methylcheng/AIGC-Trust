<template>
    <div class="home">
        <!-- 顶部 Hero 区 -->
        <div class="hero-section">
            <h1>AIGC 内容真实性检测与可信溯源平台</h1>
            <p class="subtitle">支持图像、视频、文本多模态检测，生成可验签、可追溯的可信证书</p>
            
            <div class="button-group">
                <el-button type="primary" size="large" @click="$router.push('/detect')" class="cta-button">
                    开始检测
                    <el-icon><arrow-right /></el-icon>
                </el-button>
                
                <el-button 
                    v-if="!isLoggedIn" 
                    size="large" 
                    @click="$router.push('/login')" 
                    class="login-button"
                >
                    登录/注册
                </el-button>
            </div>
        </div>
        
        <!-- 中间核心能力卡片 -->
        <div class="capabilities-section">
            <h2 class="section-title">核心能力</h2>
            <div class="capability-grid">
                <el-card class="capability-card" shadow="hover">
                    <div class="card-icon multimodal">
                        <el-icon :size="48"><monitor /></el-icon>
                    </div>
                    <h3>多模态检测</h3>
                    <p>支持图像、视频、文本的AI生成内容检测，融合多维度特征分析</p>
                </el-card>
                
                <el-card class="capability-card" shadow="hover">
                    <div class="card-icon certificate">
                        <el-icon :size="48"><stamp /></el-icon>
                    </div>
                    <h3>国密可信证书</h3>
                    <p>基于SM2/SM3算法生成数字证书，确保检测结果不可篡改</p>
                </el-card>
                
                <el-card class="capability-card" shadow="hover">
                    <div class="card-icon audit">
                        <el-icon :size="48"><connection /></el-icon>
                    </div>
                    <h3>审计哈希链</h3>
                    <p>区块链式审计日志，完整记录所有操作，实现全流程可追溯</p>
                </el-card>
                
                <el-card class="capability-card" shadow="hover">
                    <div class="card-icon edge">
                        <el-icon :size="48"><platform /></el-icon>
                    </div>
                    <h3>边缘快速初筛</h3>
                    <p>openEuler边缘节点轻量化检测，大幅降低中心平台负载</p>
                </el-card>
            </div>
        </div>
        
        <!-- 底部数据总览 -->
        <div class="stats-section">
            <h2 class="section-title">平台数据总览</h2>
            <el-row :gutter="30">
                <el-col :span="6">
                    <div class="stat-card">
                        <div class="stat-icon detection">
                            <el-icon :size="32"><data-analysis /></el-icon>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">{{ stats.totalDetections }}</div>
                            <div class="stat-label">检测任务数</div>
                        </div>
                    </div>
                </el-col>
                <el-col :span="6">
                    <div class="stat-card">
                        <div class="stat-icon certificate">
                            <el-icon :size="32"><document-checked /></el-icon>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">{{ stats.totalCertificates }}</div>
                            <div class="stat-label">已签发证书数</div>
                        </div>
                    </div>
                </el-col>
                <el-col :span="6">
                    <div class="stat-card">
                        <div class="stat-icon high-risk">
                            <el-icon :size="32"><warning /></el-icon>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">{{ stats.highRiskCount }}</div>
                            <div class="stat-label">高风险内容数</div>
                        </div>
                    </div>
                </el-col>
                <el-col :span="6">
                    <div class="stat-card">
                        <div class="stat-icon edge-node">
                            <el-icon :size="32"><server /></el-icon>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">{{ stats.edgeNodes }}</div>
                            <div class="stat-label">边缘节点数</div>
                        </div>
                    </div>
                </el-col>
            </el-row>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getStatistics } from '../api/detection'

const stats = ref({
    totalDetections: 0,
    totalCertificates: 0,
    highRiskCount: 0,
    edgeNodes: 0
})

// 检查是否已登录
const isLoggedIn = computed(() => {
    return !!localStorage.getItem('access_token')
})

// 加载统计数据
const loadStats = async () => {
    try {
        const response = await getStatistics()
        stats.value = {
            totalDetections: response.total_detections || 0,
            totalCertificates: response.total_certificates || 0,
            highRiskCount: (response.risk_distribution?.fake || 0) + (response.risk_distribution?.suspicious || 0),
            edgeNodes: response.edge_nodes?.total || 0
        }
    } catch (error) {
        console.error('加载统计数据失败:', error)
    }
}

// 组件挂载时加载数据
onMounted(() => {
    loadStats()
})
</script>

<style scoped>
.home {
    padding: 0;
}

/* ========== 顶部 Hero 区 ========== */
.hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 100px 40px 80px;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.hero-section::before {
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

.hero-section h1 {
    font-size: 52px;
    color: white;
    margin-bottom: 20px;
    line-height: 1.3;
    font-weight: 700;
    position: relative;
    z-index: 1;
    text-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

.subtitle {
    font-size: 22px;
    color: rgba(255,255,255,0.95);
    margin-bottom: 50px;
    position: relative;
    z-index: 1;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.6;
}

.cta-button {
    padding: 18px 50px;
    font-size: 20px;
    border-radius: 35px;
    position: relative;
    z-index: 1;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transition: all 0.3s;
}

.cta-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
}

.button-group {
    display: flex;
    gap: 20px;
    justify-content: center;
    position: relative;
    z-index: 1;
}

.login-button {
    padding: 18px 50px;
    font-size: 20px;
    border-radius: 35px;
    background: rgba(255,255,255,0.2);
    border: 2px solid white;
    color: white;
    transition: all 0.3s;
}

.login-button:hover {
    background: rgba(255,255,255,0.3);
    transform: translateY(-2px);
}

/* ========== 中间核心能力区 ========== */
.capabilities-section {
    padding: 80px 40px;
    background: #f5f7fa;
}

.section-title {
    text-align: center;
    font-size: 36px;
    color: #303133;
    margin-bottom: 50px;
    font-weight: 600;
}

.capability-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 30px;
    max-width: 1400px;
    margin: 0 auto;
}

.capability-card {
    text-align: center;
    padding: 40px 25px;
    border-radius: 12px;
    transition: all 0.3s;
    cursor: pointer;
    height: 100%;
}

.capability-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.15);
}

.card-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    color: white;
}

.card-icon.multimodal {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.card-icon.certificate {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.card-icon.audit {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.card-icon.edge {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.capability-card h3 {
    margin: 15px 0 12px;
    color: #303133;
    font-size: 20px;
    font-weight: 600;
}

.capability-card p {
    color: #909399;
    font-size: 15px;
    line-height: 1.6;
}

/* ========== 底部数据总览区 ========== */
.stats-section {
    padding: 80px 40px;
    background: white;
}

.stat-card {
    display: flex;
    align-items: center;
    padding: 30px;
    background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    transition: all 0.3s;
    height: 140px;
}

.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
}

.stat-icon {
    width: 70px;
    height: 70px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 20px;
    color: white;
    flex-shrink: 0;
}

.stat-icon.detection {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.certificate {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.high-risk {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
}

.stat-icon.edge-node {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-content {
    flex: 1;
}

.stat-number {
    font-size: 42px;
    font-weight: bold;
    color: #303133;
    margin-bottom: 8px;
    line-height: 1;
}

.stat-label {
    font-size: 16px;
    color: #909399;
}

/* ========== 响应式设计 ========== */
@media (max-width: 1200px) {
    .capability-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 768px) {
    .hero-section h1 {
        font-size: 36px;
    }
    
    .subtitle {
        font-size: 18px;
    }
    
    .capability-grid {
        grid-template-columns: 1fr;
    }
    
    .stats-section .el-col {
        margin-bottom: 20px;
    }
}
</style>
