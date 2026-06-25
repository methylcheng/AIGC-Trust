<template>
    <div class="dashboard">
        <div class="container">
            <!-- 页面标题 -->
            <div class="page-header">
                <h2><el-icon><TrendCharts /></el-icon> 安全治理看板</h2>
                <p style="color: #909399; margin-top: 10px;">实时监控检测数据与风险态势</p>
            </div>

            <!-- 核心指标卡片 -->
            <el-row :gutter="20" class="stats-cards">
                <el-col :xs="24" :sm="12" :md="6">
                    <el-card shadow="hover" class="stat-card stat-total">
                        <div class="stat-content">
                            <div class="stat-icon">
                                <el-icon size="32"><List /></el-icon>
                            </div>
                            <div class="stat-info">
                                <div class="stat-value">{{ stats.totalTasks }}</div>
                                <div class="stat-label">总检测数</div>
                            </div>
                        </div>
                    </el-card>
                </el-col>
                <el-col :xs="24" :sm="12" :md="6">
                    <el-card shadow="hover" class="stat-card stat-trustworthy">
                        <div class="stat-content">
                            <div class="stat-icon">
                                <el-icon size="32"><CircleCheckFilled /></el-icon>
                            </div>
                            <div class="stat-info">
                                <div class="stat-value">{{ stats.trustworthyCount }}</div>
                                <div class="stat-label">可信内容</div>
                            </div>
                        </div>
                    </el-card>
                </el-col>
                <el-col :xs="24" :sm="12" :md="6">
                    <el-card shadow="hover" class="stat-card stat-suspicious">
                        <div class="stat-content">
                            <div class="stat-icon">
                                <el-icon size="32"><WarningFilled /></el-icon>
                            </div>
                            <div class="stat-info">
                                <div class="stat-value">{{ stats.suspiciousCount }}</div>
                                <div class="stat-label">可疑内容</div>
                            </div>
                        </div>
                    </el-card>
                </el-col>
                <el-col :xs="24" :sm="12" :md="6">
                    <el-card shadow="hover" class="stat-card stat-highrisk">
                        <div class="stat-content">
                            <div class="stat-icon">
                                <el-icon size="32"><CircleCloseFilled /></el-icon>
                            </div>
                            <div class="stat-info">
                                <div class="stat-value">{{ stats.highRiskCount }}</div>
                                <div class="stat-label">高风险内容</div>
                            </div>
                        </div>
                    </el-card>
                </el-col>
            </el-row>

            <!-- 图表区域 -->
            <el-row :gutter="20" class="charts-row">
                <!-- 近7日检测趋势 -->
                <el-col :xs="24" :lg="12">
                    <el-card shadow="hover" class="chart-card">
                        <template #header>
                            <div class="card-header">
                                <span><el-icon><TrendCharts /></el-icon> 近7日检测趋势</span>
                            </div>
                        </template>
                        <div ref="trendChartRef" class="chart-container"></div>
                    </el-card>
                </el-col>

                <!-- 检测类型分布 -->
                <el-col :xs="24" :lg="12">
                    <el-card shadow="hover" class="chart-card">
                        <template #header>
                            <div class="card-header">
                                <span><el-icon><PieChart /></el-icon> 检测类型分布</span>
                            </div>
                        </template>
                        <div ref="typeChartRef" class="chart-container"></div>
                    </el-card>
                </el-col>
            </el-row>

            <el-row :gutter="20" class="charts-row">
                <!-- 风险等级分布 -->
                <el-col :xs="24" :lg="12">
                    <el-card shadow="hover" class="chart-card">
                        <template #header>
                            <div class="card-header">
                                <span><el-icon><Histogram /></el-icon> 风险等级分布</span>
                            </div>
                        </template>
                        <div ref="riskChartRef" class="chart-container"></div>
                    </el-card>
                </el-col>

                <!-- 证书验签状态 -->
                <el-col :xs="24" :lg="12">
                    <el-card shadow="hover" class="chart-card">
                        <template #header>
                            <div class="card-header">
                                <span><el-icon><Stamp /></el-icon> 证书验签状态</span>
                            </div>
                        </template>
                        <div ref="certChartRef" class="chart-container"></div>
                    </el-card>
                </el-col>
            </el-row>

            <el-row :gutter="20" class="charts-row">
                <!-- 边缘节点任务占比 -->
                <el-col :xs="24" :lg="12">
                    <el-card shadow="hover" class="chart-card">
                        <template #header>
                            <div class="card-header">
                                <span><el-icon><Connection /></el-icon> 边缘节点任务占比</span>
                            </div>
                        </template>
                        <div ref="edgeChartRef" class="chart-container"></div>
                    </el-card>
                </el-col>

                <!-- 空占位 -->
                <el-col :xs="24" :lg="12">
                    <el-card shadow="hover" class="chart-card">
                        <template #header>
                            <div class="card-header">
                                <span><el-icon><InfoFilled /></el-icon> 平台说明</span>
                            </div>
                        </template>
                        <div class="info-panel">
                            <el-descriptions :column="1" border>
                                <el-descriptions-item label="平台名称">AIGC-Trust 内容可信检测平台</el-descriptions-item>
                                <el-descriptions-item label="检测能力">图像 / 视频 / 文本多模态检测</el-descriptions-item>
                                <el-descriptions-item label="核心技术">深度学习 + 国密算法 + 区块链存证</el-descriptions-item>
                                <el-descriptions-item label="部署架构">中心节点 + 边缘节点协同检测</el-descriptions-item>
                            </el-descriptions>
                        </div>
                    </el-card>
                </el-col>
            </el-row>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { 
    TrendCharts, PieChart, Histogram, Stamp, Connection, InfoFilled,
    List, CircleCheckFilled, WarningFilled, CircleCloseFilled
} from '@element-plus/icons-vue'
import { getAllTasks } from '../api/detection'

// 统计数据
const stats = ref({
    totalTasks: 0,
    trustworthyCount: 0,
    suspiciousCount: 0,
    highRiskCount: 0
})

// 图表引用
const trendChartRef = ref(null)
const typeChartRef = ref(null)
const riskChartRef = ref(null)
const certChartRef = ref(null)
const edgeChartRef = ref(null)

// 图表实例
let trendChart = null
let typeChart = null
let riskChart = null
let certChart = null
let edgeChart = null

// 加载统计数据
const loadStats = async () => {
    try {
        const response = await getAllTasks({ limit: 1000 })
        const tasks = response.tasks || []
        
        // 计算统计数据
        stats.value.totalTasks = tasks.length
        stats.value.trustworthyCount = tasks.filter(t => t.result?.risk_level === '可信').length
        stats.value.suspiciousCount = tasks.filter(t => t.result?.risk_level === '轻度可疑').length
        stats.value.highRiskCount = tasks.filter(t => 
            t.result?.risk_level === '高风险' || t.result?.risk_level === '不可信'
        ).length
        
        // 渲染图表
        renderTrendChart(tasks)
        renderTypeChart(tasks)
        renderRiskChart(tasks)
        renderCertChart(tasks)
        renderEdgeChart(tasks)
        
    } catch (error) {
        console.error('加载统计数据失败:', error)
        ElMessage.error('加载统计数据失败')
    }
}

// 渲染趋势图（折线图）
const renderTrendChart = (tasks) => {
    if (!trendChartRef.value) return
    
    // 生成近7天日期
    const dates = []
    const counts = []
    for (let i = 6; i >= 0; i--) {
        const date = new Date()
        date.setDate(date.getDate() - i)
        const dateStr = `${date.getMonth() + 1}/${date.getDate()}`
        dates.push(dateStr)
        
        // 统计当天的任务数
        const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
        const dayEnd = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1)
        const count = tasks.filter(t => {
            const taskDate = new Date(t.created_at)
            return taskDate >= dayStart && taskDate < dayEnd
        }).length
        counts.push(count)
    }
    
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
        tooltip: {
            trigger: 'axis',
            formatter: '{b}: {c} 次检测'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            boundaryGap: false
        },
        yAxis: {
            type: 'value',
            minInterval: 1
        },
        series: [{
            name: '检测量',
            type: 'line',
            smooth: true,
            data: counts,
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(31, 78, 121, 0.3)' },
                    { offset: 1, color: 'rgba(31, 78, 121, 0.05)' }
                ])
            },
            lineStyle: {
                color: '#1F4E79',
                width: 3
            },
            itemStyle: {
                color: '#1F4E79'
            }
        }]
    })
}

// 渲染类型分布图（饼图）
const renderTypeChart = (tasks) => {
    if (!typeChartRef.value) return
    
    const typeCount = {
        video: tasks.filter(t => t.content_type === 'video').length,
        image: tasks.filter(t => t.content_type === 'image').length,
        text: tasks.filter(t => t.content_type === 'text').length
    }
    
    // 如果所有类型都是0，显示提示
    const totalTasks = typeCount.video + typeCount.image + typeCount.text
    if (totalTasks === 0) {
        typeChart = echarts.init(typeChartRef.value)
        typeChart.setOption({
            title: {
                text: '暂无检测数据',
                left: 'center',
                top: 'center',
                textStyle: {
                    color: '#9CA3AF',
                    fontSize: 14,
                    fontWeight: 'normal'
                }
            }
        })
        return
    }
    
    typeChart = echarts.init(typeChartRef.value)
    typeChart.setOption({
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: {
                color: '#6B7280'
            }
        },
        series: [{
            name: '检测类型',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                formatter: '{b}\n{d}%',
                color: '#1F2937'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            data: [
                { value: typeCount.video, name: '视频', itemStyle: { color: '#1F4E79' } },
                { value: typeCount.image, name: '图片', itemStyle: { color: '#0E9F6E' } },
                { value: typeCount.text, name: '文本', itemStyle: { color: '#F59E0B' } }
            ]
        }]
    })
}

// 渲染风险等级图（柱状图）
const renderRiskChart = (tasks) => {
    if (!riskChartRef.value) return
    
    const riskCount = {
        trustworthy: tasks.filter(t => t.result?.risk_level === '可信').length,
        suspicious: tasks.filter(t => t.result?.risk_level === '轻度可疑').length,
        high: tasks.filter(t => t.result?.risk_level === '高风险').length,
        untrustworthy: tasks.filter(t => t.result?.risk_level === '不可信').length
    }
    
    riskChart = echarts.init(riskChartRef.value)
    riskChart.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: '{b}: {c}'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: ['可信', '轻度可疑', '高风险', '不可信']
        },
        yAxis: {
            type: 'value',
            minInterval: 1
        },
        series: [{
            name: '任务数',
            type: 'bar',
            data: [
                { value: riskCount.trustworthy, itemStyle: { color: '#0E9F6E' } },
                { value: riskCount.suspicious, itemStyle: { color: '#F59E0B' } },
                { value: riskCount.high, itemStyle: { color: '#EF4444' } },
                { value: riskCount.untrustworthy, itemStyle: { color: '#9CA3AF' } }
            ],
            barWidth: '50%',
            itemStyle: {
                borderRadius: [5, 5, 0, 0]
            }
        }]
    })
}

// 渲染证书验签图（环形图）
const renderCertChart = (tasks) => {
    if (!certChartRef.value) return
    
    const certStatus = {
        verified: tasks.filter(t => t.result?.certificate?.verify_status === 'verified' || t.result?.certificate).length,
        pending: tasks.filter(t => !t.result?.certificate).length
    }
    
    certChart = echarts.init(certChartRef.value)
    certChart.setOption({
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            right: 10,
            top: 'center'
        },
        series: [{
            name: '验签状态',
            type: 'pie',
            radius: ['50%', '75%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                formatter: '{b}\n{d}%'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            data: [
                { value: certStatus.verified, name: '已签发', itemStyle: { color: '#67c23a' } },
                { value: certStatus.pending, name: '未签发', itemStyle: { color: '#dcdfe6' } }
            ]
        }]
    })
}

// 渲染边缘节点占比图（环形图）
const renderEdgeChart = (tasks) => {
    if (!edgeChartRef.value) return
    
    const nodeCount = {
        edge: tasks.filter(t => t.detect_mode === 'edge_01').length,
        center: tasks.filter(t => t.detect_mode === 'center' || !t.detect_mode).length
    }
    
    edgeChart = echarts.init(edgeChartRef.value)
    edgeChart.setOption({
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            right: 10,
            top: 'center'
        },
        series: [{
            name: '节点类型',
            type: 'pie',
            radius: ['50%', '75%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                formatter: '{b}\n{d}%'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            data: [
                { value: nodeCount.edge, name: '边缘节点', itemStyle: { color: '#409eff' } },
                { value: nodeCount.center, name: '中心节点', itemStyle: { color: '#909399' } }
            ]
        }]
    })
}

// 窗口大小改变时重新渲染图表
const handleResize = () => {
    trendChart?.resize()
    typeChart?.resize()
    riskChart?.resize()
    certChart?.resize()
    edgeChart?.resize()
}

onMounted(() => {
    loadStats()
    window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    trendChart?.dispose()
    typeChart?.dispose()
    riskChart?.dispose()
    certChart?.dispose()
    edgeChart?.dispose()
})
</script>

<style scoped>
.dashboard {
    padding: 40px;
    background: #F6F8FA;
    min-height: calc(100vh - 60px);
}

.container {
    max-width: 1600px;
    margin: 0 auto;
}

/* 页面标题 */
.page-header h2 {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 28px;
    color: #1E3A5F;
    margin: 0;
}

.page-header h2 .el-icon {
    font-size: 32px;
    color: #1F4E79;
}

/* 统计卡片 */
.stats-cards {
    margin-top: 30px;
    margin-bottom: 30px;
}

.stat-card {
    transition: all 0.3s ease;
    cursor: pointer;
    height: 120px;
}

.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.stat-content {
    display: flex;
    align-items: center;
    gap: 20px;
    height: 100%;
}

.stat-icon {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
}

.stat-total .stat-icon {
    background: linear-gradient(135deg, #1E3A5F 0%, #1F4E79 100%);
}

.stat-trustworthy .stat-icon {
    background: linear-gradient(135deg, #0E9F6E 0%, #10B981 100%);
}

.stat-suspicious .stat-icon {
    background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%);
}

.stat-highrisk .stat-icon {
    background: linear-gradient(135deg, #EF4444 0%, #F87171 100%);
}

.stat-info {
    flex: 1;
}

.stat-value {
    font-size: 36px;
    font-weight: bold;
    color: #303133;
    line-height: 1;
    margin-bottom: 8px;
}

.stat-label {
    font-size: 14px;
    color: #909399;
}

/* 图表卡片 */
.charts-row {
    margin-bottom: 20px;
}

.chart-card {
    margin-bottom: 20px;
    height: 450px;
}

.chart-card :deep(.el-card__header) {
    padding: 15px 20px;
    border-bottom: 2px solid #e4e7ed;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #1E3A5F;
}

.card-header .el-icon {
    font-size: 20px;
    color: #1F4E79;
}

.chart-container {
    width: 100%;
    height: 380px;
}

/* 信息面板 */
.info-panel {
    padding: 20px;
}

.info-panel :deep(.el-descriptions__label) {
    font-weight: 600;
    width: 140px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
    .dashboard {
        padding: 20px;
    }
    
    .stat-value {
        font-size: 28px;
    }
    
    .stat-icon {
        width: 56px;
        height: 56px;
    }
    
    .chart-card {
        height: 400px;
    }
    
    .chart-container {
        height: 330px;
    }
}

@media (max-width: 768px) {
    .stat-card {
        height: 100px;
        margin-bottom: 15px;
    }
    
    .stat-value {
        font-size: 24px;
    }
    
    .stat-icon {
        width: 48px;
        height: 48px;
    }
    
    .chart-card {
        height: 350px;
    }
    
    .chart-container {
        height: 280px;
    }
}
</style>
