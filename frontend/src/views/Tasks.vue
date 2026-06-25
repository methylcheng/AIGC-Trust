<template>
    <div class="tasks">
        <div class="container">
            <el-card>
                <!-- 页面标题 -->
                <div class="page-header">
                    <h2><el-icon><Monitor /></el-icon> 任务监控台</h2>
                    <p style="color: #909399; margin-top: 10px;">实时监控和管理所有检测任务</p>
                </div>
                
                <!-- 筛选器区域 -->
                <div class="filter-section">
                    <el-row :gutter="20">
                        <el-col :span="6">
                            <el-select v-model="statusFilter" placeholder="任务状态" clearable @change="applyFilters">
                                <el-option label="全部状态" value="" />
                                <el-option label="排队中" value="pending">
                                    <el-icon><Clock /></el-icon> 排队中
                                </el-option>
                                <el-option label="检测中" value="processing">
                                    <el-icon><Loading /></el-icon> 检测中
                                </el-option>
                                <el-option label="已完成" value="completed">
                                    <el-icon><CircleCheck /></el-icon> 已完成
                                </el-option>
                                <el-option label="失败" value="failed">
                                    <el-icon><CircleClose /></el-icon> 失败
                                </el-option>
                            </el-select>
                        </el-col>
                        <el-col :span="6">
                            <el-select v-model="riskFilter" placeholder="风险等级" clearable @change="applyFilters">
                                <el-option label="全部等级" value="" />
                                <el-option label="可信" value="可信">
                                    <el-tag type="success">可信</el-tag>
                                </el-option>
                                <el-option label="轻度可疑" value="轻度可疑">
                                    <el-tag type="warning">轻度可疑</el-tag>
                                </el-option>
                                <el-option label="高风险" value="高风险">
                                    <el-tag type="danger">高风险</el-tag>
                                </el-option>
                                <el-option label="不可信" value="不可信">
                                    <el-tag type="info">不可信</el-tag>
                                </el-option>
                            </el-select>
                        </el-col>
                        <el-col :span="6">
                            <el-select v-model="typeFilter" placeholder="检测类型" clearable @change="applyFilters">
                                <el-option label="全部类型" value="" />
                                <el-option label="视频" value="video">
                                    <el-icon><VideoCamera /></el-icon> 视频
                                </el-option>
                                <el-option label="图片" value="image">
                                    <el-icon><Picture /></el-icon> 图片
                                </el-option>
                                <el-option label="文本" value="text">
                                    <el-icon><Document /></el-icon> 文本
                                </el-option>
                            </el-select>
                        </el-col>
                        <el-col :span="6">
                            <el-button type="primary" @click="refreshTasks" :loading="loading">
                                <el-icon><Refresh /></el-icon> 刷新
                            </el-button>
                            <el-button @click="resetFilters">
                                <el-icon><Delete /></el-icon> 重置筛选
                            </el-button>
                        </el-col>
                    </el-row>
                </div>
                
                <!-- 统计卡片 -->
                <div class="stats-cards">
                    <el-row :gutter="20">
                        <el-col :span="6">
                            <el-card shadow="hover" class="stat-card">
                                <div class="stat-content">
                                    <div class="stat-icon" style="background: #409eff;"><el-icon><List /></el-icon></div>
                                    <div class="stat-info">
                                        <div class="stat-value">{{ totalTasks }}</div>
                                        <div class="stat-label">总任务数</div>
                                    </div>
                                </div>
                            </el-card>
                        </el-col>
                        <el-col :span="6">
                            <el-card shadow="hover" class="stat-card">
                                <div class="stat-content">
                                    <div class="stat-icon" style="background: #e6a23c;"><el-icon><Loading /></el-icon></div>
                                    <div class="stat-info">
                                        <div class="stat-value">{{ processingTasks }}</div>
                                        <div class="stat-label">进行中</div>
                                    </div>
                                </div>
                            </el-card>
                        </el-col>
                        <el-col :span="6">
                            <el-card shadow="hover" class="stat-card">
                                <div class="stat-content">
                                    <div class="stat-icon" style="background: #67c23a;"><el-icon><SuccessFilled /></el-icon></div>
                                    <div class="stat-info">
                                        <div class="stat-value">{{ completedTasks }}</div>
                                        <div class="stat-label">已完成</div>
                                    </div>
                                </div>
                            </el-card>
                        </el-col>
                        <el-col :span="6">
                            <el-card shadow="hover" class="stat-card">
                                <div class="stat-content">
                                    <div class="stat-icon" style="background: #f56c6c;"><el-icon><WarningFilled /></el-icon></div>
                                    <div class="stat-info">
                                        <div class="stat-value">{{ highRiskTasks }}</div>
                                        <div class="stat-label">高风险</div>
                                    </div>
                                </div>
                            </el-card>
                        </el-col>
                    </el-row>
                </div>
                
                <!-- 任务表格 -->
                <!-- 批量操作工具栏 -->
                <div class="batch-actions" v-if="selectedTaskIds.length > 0">
                    <el-alert
                        :title="'已选中 ' + selectedTaskIds.length + ' 个任务'"
                        type="info"
                        :closable="false"
                        show-icon
                    />
                    <el-button 
                        type="danger" 
                        size="small"
                        @click="handleBatchDeleteTasks"
                        style="margin-top: 10px;"
                    >
                        <el-icon><Delete /></el-icon> 批量删除选中任务
                    </el-button>
                </div>
                
                <el-table 
                    :data="paginatedTasks" 
                    style="margin-top: 20px;" 
                    v-loading="loading"
                    stripe
                    border
                    :default-sort="{prop: 'created_at', order: 'descending'}"
                    @selection-change="handleSelectionChange"
                >
                    <el-table-column type="selection" width="55" align="center" />
                    <el-table-column prop="task_id" label="任务ID" width="280" show-overflow-tooltip />
                    <el-table-column label="内容类型" width="100" align="center">
                        <template #default="{ row }">
                            <el-tag :type="getContentTypeColor(row.content_type)">
                                <el-icon><component :is="getContentTypeIcon(row.content_type)" /></el-icon>
                                {{ getContentTypeName(row.content_type) }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="detect_mode" label="检测模式" width="120">
                        <template #default="{ row }">
                            <el-tag size="small" :type="row.detect_mode === 'edge_01' ? 'success' : 'primary'">
                                {{ row.detect_mode === 'edge_01' ? '边缘节点' : '中心节点' }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="status" label="状态" width="120" align="center">
                        <template #default="{ row }">
                            <el-tag :type="getStatusType(row.status)">
                                <el-icon><component :is="getStatusIcon(row.status)" /></el-icon>
                                {{ getStatusText(row.status) }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="progress" label="进度" width="150">
                        <template #default="{ row }">
                            <el-progress 
                                :percentage="Math.round(row.progress * 100)" 
                                :status="getProgressStatus(row.status)"
                                :stroke-width="8"
                            />
                        </template>
                    </el-table-column>
                    <el-table-column label="风险等级" width="120" align="center">
                        <template #default="{ row }">
                            <el-tag v-if="row.result?.risk_level" :type="getRiskLevelType(row.result.risk_level)">
                                {{ row.result.risk_level }}
                            </el-tag>
                            <span v-else style="color: #909399;">-</span>
                        </template>
                    </el-table-column>
                    <el-table-column label="AI概率" width="120" align="center">
                        <template #default="{ row }">
                            <span v-if="row.result?.ai_probability !== undefined" style="font-weight: bold; color: #409eff;">
                                {{ (row.result.ai_probability * 100).toFixed(1) }}%
                            </span>
                            <span v-else style="color: #909399;">-</span>
                        </template>
                    </el-table-column>
                    <el-table-column prop="node_id" label="节点来源" width="120" />
                    <el-table-column prop="created_at" label="创建时间" width="180" sortable>
                        <template #default="{ row }">
                            {{ formatTime(row.created_at) }}
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="350" fixed="right">
                        <template #default="{ row }">
                            <el-button 
                                size="small" 
                                type="primary"
                                @click="viewResult(row)"
                                :disabled="row.status !== 'completed'"
                            >
                                <el-icon><View /></el-icon> 查看结果
                            </el-button>
                            <el-button 
                                size="small" 
                                type="success"
                                @click="viewCertificate(row)"
                                :disabled="!row.result?.certificate"
                                v-if="row.status === 'completed'"
                            >
                                <el-icon><Stamp /></el-icon> 查看证书
                            </el-button>
                            <el-button 
                                size="small" 
                                type="warning"
                                @click="retestTask(row)"
                            >
                                <el-icon><RefreshRight /></el-icon> 重测
                            </el-button>
                            <el-button 
                                size="small" 
                                type="danger"
                                @click="handleDeleteTask(row)"
                            >
                                <el-icon><Delete /></el-icon> 删除
                            </el-button>
                        </template>
                    </el-table-column>
                </el-table>
                
                <!-- 分页组件 -->
                <div class="pagination-container">
                    <el-pagination
                        v-model:current-page="currentPage"
                        v-model:page-size="pageSize"
                        :page-sizes="[10, 20, 50, 100]"
                        :total="filteredTasks.length"
                        layout="total, sizes, prev, pager, next, jumper"
                        @size-change="handleSizeChange"
                        @current-change="handleCurrentChange"
                    />
                </div>
                
                <!-- 空状态 -->
                <el-empty v-if="!loading && paginatedTasks.length === 0" description="暂无任务数据" />
            </el-card>
        </div>
        
        <!-- 任务详情对话框 -->
        <el-dialog v-model="dialogVisible" title="任务详情" width="800px">
            <el-descriptions :column="2" border v-if="currentTask">
                <el-descriptions-item label="任务ID">{{ currentTask.task_id }}</el-descriptions-item>
                <el-descriptions-item label="内容ID">{{ currentTask.content_id }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                    <el-tag :type="getStatusType(currentTask.status)">{{ currentTask.status }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="进度">
                    <el-progress :percentage="currentTask.progress * 100" />
                </el-descriptions-item>
                <el-descriptions-item label="节点ID">{{ currentTask.node_id }}</el-descriptions-item>
                <el-descriptions-item label="创建时间">{{ currentTask.created_at }}</el-descriptions-item>
            </el-descriptions>
            
            <h3 style="margin-top: 20px;">检测结果</h3>
            <div v-if="currentTask?.result" style="margin-top: 10px;">
                <!-- 视频检测结果 -->
                <div v-if="currentTask.result.video_meta">
                    <el-descriptions :column="2" border title="视频信息">
                        <el-descriptions-item label="分辨率">
                            {{ currentTask.result.video_meta.width }}x{{ currentTask.result.video_meta.height }}
                        </el-descriptions-item>
                        <el-descriptions-item label="时长">
                            {{ currentTask.result.video_meta.duration?.toFixed(2) }} 秒
                        </el-descriptions-item>
                        <el-descriptions-item label="总帧数">
                            {{ currentTask.result.video_meta.total_frames }}
                        </el-descriptions-item>
                        <el-descriptions-item label="检测帧数">
                            {{ currentTask.result.video_meta.sampled_frames }} 帧
                        </el-descriptions-item>
                    </el-descriptions>
                    
                    <el-descriptions :column="2" border title="频域分析" style="margin-top: 15px;">
                        <el-descriptions-item label="平均噪声分数">
                            {{ currentTask.result.frequency_analysis?.avg_noise_score?.toFixed(4) || 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="噪声方差">
                            {{ currentTask.result.frequency_analysis?.noise_variance?.toFixed(4) || 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="高频异常指数">
                            {{ currentTask.result.frequency_analysis?.high_freq_anomaly?.toFixed(4) || 'N/A' }}
                        </el-descriptions-item>
                    </el-descriptions>
                    
                    <el-descriptions :column="2" border title="深度伪造分析" style="margin-top: 15px;">
                        <el-descriptions-item label="平均AI概率">
                            {{ ((currentTask.result.deepfake_analysis?.avg_score || 0) * 100).toFixed(2) }}%
                        </el-descriptions-item>
                        <el-descriptions-item label="最大AI概率">
                            {{ ((currentTask.result.deepfake_analysis?.max_score || 0) * 100).toFixed(2) }}%
                        </el-descriptions-item>
                        <el-descriptions-item label="高风险帧比例">
                            {{ ((currentTask.result.deepfake_analysis?.high_risk_frame_ratio || 0) * 100).toFixed(2) }}%
                        </el-descriptions-item>
                        <el-descriptions-item label="时序一致性(方差)">
                            {{ currentTask.result.deepfake_analysis?.score_variance?.toFixed(4) || 'N/A' }}
                        </el-descriptions-item>
                    </el-descriptions>
                </div>
                
                <!-- 图片/文本检测结果 -->
                <div v-else>
                    <el-descriptions :column="2" border>
                        <el-descriptions-item label="AI生成概率">
                            {{ ((currentTask.result.ai_probability || 0) * 100).toFixed(2) }}%
                        </el-descriptions-item>
                        <el-descriptions-item label="风险评分">
                            {{ (currentTask.result.risk_score || 0).toFixed(4) }}
                        </el-descriptions-item>
                    </el-descriptions>
                </div>
                
                <!-- 证书信息 -->
                <div v-if="currentTask.result.certificate" style="margin-top: 15px;">
                    <h4>国密证书</h4>
                    <el-descriptions :column="2" border>
                        <el-descriptions-item label="证书ID">
                            {{ currentTask.result.certificate.certificate_id }}
                        </el-descriptions-item>
                        <el-descriptions-item label="签发时间">
                            {{ currentTask.result.certificate.issued_at }}
                        </el-descriptions-item>
                        <el-descriptions-item label="签名算法">SM2 with SM3</el-descriptions-item>
                    </el-descriptions>
                </div>
            </div>
            <el-empty v-else description="暂无检测结果" />
            
            <template #footer>
                <el-button @click="dialogVisible = false">关闭</el-button>
            </template>
        </el-dialog>
        
        <!-- 证书详情对话框 -->
        <el-dialog v-model="certDialogVisible" title="国密可信证书详情" width="900px">
            <!-- 验签状态醒目展示 -->
            <div v-if="currentCert" class="verify-banner" :class="getVerifyBannerClass(currentCert.verify_status)">
                <div class="verify-icon">
                    <el-icon size="48"><component :is="getVerifyStatusIcon(currentCert.verify_status)" /></el-icon>
                </div>
                <div class="verify-content">
                    <h3 class="verify-title">{{ getVerifyBannerTitle(currentCert.verify_status) }}</h3>
                    <p class="verify-desc">{{ getVerifyBannerDesc(currentCert.verify_status) }}</p>
                </div>
                <div class="verify-badge">
                    <el-tag size="large" :type="getVerifyStatusType(currentCert.verify_status)" effect="dark">
                        {{ getVerifyStatusText(currentCert.verify_status) }}
                    </el-tag>
                </div>
            </div>
            
            <!-- 验签详细信息 -->
            <el-card v-if="currentCert" class="verify-details-card" shadow="never">
                <template #header>
                    <div class="card-header">
                        <el-icon><Stamp /></el-icon>
                        <span>验签结果</span>
                    </div>
                </template>
                <el-descriptions :column="2" border>
                    <el-descriptions-item label="验签状态">
                        <el-tag :type="getVerifyStatusType(currentCert.verify_status)">
                            {{ getVerifyStatusText(currentCert.verify_status) }}
                        </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="签名算法">
                        <el-tag type="info">SM2</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="摘要算法">
                        <el-tag type="info">SM3</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="签发节点">
                        <el-tag :type="currentCert.node_id?.includes('edge') ? 'success' : 'primary'">
                            {{ currentCert.node_id?.includes('edge') ? '边缘节点' : '中心节点' }}
                        </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="证书编号" :span="2">
                        <el-text type="primary" style="font-family: monospace;">{{ currentCert.certificate_id || currentCert.cert_id }}</el-text>
                        <el-button size="small" text @click="copyToClipboard(currentCert.certificate_id || currentCert.cert_id)">
                            <el-icon><CopyDocument /></el-icon>
                        </el-button>
                    </el-descriptions-item>
                    <el-descriptions-item label="内容哈希" :span="2">
                        <el-text type="info" style="font-family: monospace; font-size: 12px;">
                            {{ currentCert.content_hash || currentCert.sm3_hash || currentCert.signature?.fingerprint || 'N/A' }}
                        </el-text>
                        <el-button size="small" text @click="copyToClipboard(currentCert.content_hash || currentCert.sm3_hash || currentCert.signature?.fingerprint)">
                            <el-icon><CopyDocument /></el-icon>
                        </el-button>
                    </el-descriptions-item>
                </el-descriptions>
            </el-card>
            
            <el-descriptions :column="2" border v-if="currentCert" style="margin-top: 20px;">
                <el-descriptions-item label="证书ID">{{ currentCert.certificate_id || currentCert.cert_id }}</el-descriptions-item>
                <el-descriptions-item label="内容ID">{{ currentCert.content_id }}</el-descriptions-item>
                <el-descriptions-item label="风险等级">
                    <el-tag :type="getRiskType(currentCert.risk_level)">{{ currentCert.risk_level }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="签发时间">{{ currentCert.issued_at }}</el-descriptions-item>
            </el-descriptions>
            
            <h3 style="margin-top: 20px;">证书签名信息</h3>
            <!-- 优先显示 signature 对象，如果不存在则从 cert_data 构建 -->
            <el-card v-if="currentCert?.signature || currentCert?.sm2_signature" style="margin-top: 10px;">
                <div v-if="typeof currentCert.signature === 'object' && currentCert.signature !== null">
                    <!-- 新格式：完整的签名对象 -->
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="证书ID">
                            {{ currentCert.signature.certificate_id || currentCert.certificate_id || currentCert.cert_id }}
                        </el-descriptions-item>
                        <el-descriptions-item label="内容ID">
                            {{ currentCert.signature.content_id || currentCert.content_id }}
                        </el-descriptions-item>
                        <el-descriptions-item label="内容类型">
                            {{ currentCert.signature.content_type || 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="风险等级">
                            {{ currentCert.signature.risk_level || currentCert.risk_level }}
                        </el-descriptions-item>
                        <el-descriptions-item label="检测评分">
                            {{ (currentCert.signature.detection_score || 0).toFixed(4) }}
                        </el-descriptions-item>
                        <el-descriptions-item label="指纹信息">
                            {{ currentCert.signature.fingerprint ? currentCert.signature.fingerprint.substring(0, 64) + '...' : 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="SM2签名">
                            <span style="font-size: 12px; word-break: break-all;">
                                {{ currentCert.signature.sm2_signature || 'N/A' }}
                            </span>
                        </el-descriptions-item>
                    </el-descriptions>
                </div>
                <div v-else>
                    <!-- 旧格式：直接从 cert_data 构建签名信息 -->
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="证书ID">
                            {{ currentCert.certificate_id || currentCert.cert_id }}
                        </el-descriptions-item>
                        <el-descriptions-item label="内容ID">
                            {{ currentCert.content_id }}
                        </el-descriptions-item>
                        <el-descriptions-item label="内容类型">
                            {{ currentCert.content_type || 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="风险等级">
                            {{ currentCert.risk_level }}
                        </el-descriptions-item>
                        <el-descriptions-item label="检测评分">
                            {{ (currentCert.detection_score || 0).toFixed(4) }}
                        </el-descriptions-item>
                        <el-descriptions-item label="指纹信息">
                            {{ currentCert.fingerprint ? currentCert.fingerprint.substring(0, 64) + '...' : 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="SM2签名">
                            <span style="font-size: 12px; word-break: break-all;">
                                {{ currentCert.sm2_signature || currentCert.signature || 'N/A' }}
                            </span>
                        </el-descriptions-item>
                    </el-descriptions>
                </div>
            </el-card>
            <el-empty v-else description="暂无签名信息" />
            
            <template #footer>
                <el-button @click="certDialogVisible = false">关闭</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAllTasks, deleteTask, batchDeleteTasks } from '../api/detection'
import { 
    Monitor, Clock, Loading, CircleCheck, CircleClose,
    VideoCamera, Picture, Document, Refresh, Delete,
    List, SuccessFilled, WarningFilled, View, Stamp,
    RefreshRight, CopyDocument, Check, Close
} from '@element-plus/icons-vue'

const loading = ref(false)
const tasks = ref([])
const dialogVisible = ref(false)
const currentTask = ref(null)

// 证书对话框相关
const certDialogVisible = ref(false)
const currentCert = ref(null)

// 批量选择相关
const selectedTaskIds = ref([])

// 筛选器状态
const statusFilter = ref('')
const riskFilter = ref('')
const typeFilter = ref('')

// 分页状态
const currentPage = ref(1)
const pageSize = ref(20)

// 计算属性：过滤后的任务列表
const filteredTasks = computed(() => {
    let result = tasks.value
    
    // 按状态筛选
    if (statusFilter.value) {
        result = result.filter(task => task.status === statusFilter.value)
    }
    
    // 按风险等级筛选
    if (riskFilter.value) {
        result = result.filter(task => task.result?.risk_level === riskFilter.value)
    }
    
    // 按检测类型筛选
    if (typeFilter.value) {
        result = result.filter(task => task.content_type === typeFilter.value)
    }
    
    return result
})

// 计算属性：选中的任务对象
const selectedTasks = computed(() => {
    return tasks.value.filter(task => selectedTaskIds.value.includes(task.task_id))
})

// 统计信息
const totalTasks = computed(() => tasks.value.length)
const processingTasks = computed(() => tasks.value.filter(t => t.status === 'processing').length)
const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed').length)
const highRiskTasks = computed(() => tasks.value.filter(t => t.result?.risk_level === '高风险' || t.result?.risk_level === '不可信').length)

// 计算属性：分页后的任务列表
const paginatedTasks = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return filteredTasks.value.slice(start, end)
})

// 加载任务列表
const loadTasks = async () => {
    loading.value = true
    try {
        const response = await getAllTasks({ limit: 100 })
        tasks.value = response.tasks || []
        
        // 调试：打印所有任务的 content_type 值
        if (tasks.value.length > 0) {
            console.log('=== 任务内容类型调试信息 ===')
            const typeCounts = {}
            tasks.value.forEach(task => {
                const type = task.content_type
                typeCounts[type] = (typeCounts[type] || 0) + 1
            })
            console.log('内容类型统计:', typeCounts)
            console.log('前3个任务示例:', tasks.value.slice(0, 3).map(t => ({
                task_id: t.task_id,
                content_type: t.content_type,
                status: t.status
            })))
        }
    } catch (error) {
        ElMessage.error('加载任务列表失败')
        console.error(error)
    } finally {
        loading.value = false
    }
}

// 刷新任务
const refreshTasks = async () => {
    await loadTasks()
    ElMessage.success('刷新成功')
}

// 应用筛选
const applyFilters = () => {
    // 计算属性会自动更新，这里只需显示提示
    const filterCount = [statusFilter.value, riskFilter.value, typeFilter.value].filter(Boolean).length
    if (filterCount > 0) {
        ElMessage.info(`已应用 ${filterCount} 个筛选条件`)
    }
}

// 重置筛选
const resetFilters = () => {
    statusFilter.value = ''
    riskFilter.value = ''
    typeFilter.value = ''
    currentPage.value = 1 // 重置页码
    ElMessage.success('已重置筛选')
}

// 分页处理函数
const handleSizeChange = (val) => {
    pageSize.value = val
    currentPage.value = 1 // 改变每页数量时回到第一页
    ElMessage.info(`每页显示 ${val} 条`)
}

const handleCurrentChange = (val) => {
    currentPage.value = val
    ElMessage.info(`跳转到第 ${val} 页`)
}

// 获取内容类型图标
const getContentTypeIcon = (type) => {
    const icons = {
        'video': 'VideoCamera',
        'image': 'Picture',
        'text': 'Document'
    }
    return icons[type] || 'Document'
}

// 获取内容类型名称
const getContentTypeName = (type) => {
    const names = {
        'video': '视频',
        'image': '图片',
        'text': '文本'
    }
    // 如果类型未知，直接显示原始值（方便调试）
    return names[type] || type || '未知'
}

// 获取内容类型颜色
const getContentTypeColor = (type) => {
    const colors = {
        'video': '',
        'image': 'success',
        'text': 'warning'
    }
    return colors[type] || 'info'  // 未知类型使用 info 蓝色
}

// 获取状态文本
const getStatusText = (status) => {
    const texts = {
        'pending': '排队中',
        'processing': '检测中',
        'completed': '已完成',
        'failed': '失败'
    }
    return texts[status] || status
}

// 获取状态图标
const getStatusIcon = (status) => {
    const icons = {
        'pending': 'Clock',
        'processing': 'Loading',
        'completed': 'CircleCheck',
        'failed': 'CircleClose'
    }
    return icons[status] || 'Clock'
}

// 获取进度条状态
const getProgressStatus = (status) => {
    if (status === 'completed') return 'success'
    if (status === 'failed') return 'exception'
    return undefined
}

// 获取风险等级标签类型
const getRiskLevelType = (level) => {
    const types = {
        '可信': 'success',
        '轻度可疑': 'warning',
        '高风险': 'danger',
        '不可信': 'info'
    }
    return types[level] || ''
}

// 格式化时间
const formatTime = (timeStr) => {
    if (!timeStr) return '-'
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    })
}

const getStatusType = (status) => {
    const types = {
        'pending': '',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger'
    }
    return types[status] || ''
}

// 查看结果
const viewResult = async (task) => {
    currentTask.value = task
    dialogVisible.value = true
}

// 查看证书
const viewCertificate = (task) => {
    if (!task.result?.certificate) {
        ElMessage.warning('该任务没有证书')
        return
    }
    
    // 设置当前证书并打开对话框
    const cert = task.result.certificate
    
    // 如果证书缺少 verify_status，设置默认值
    if (!cert.verify_status) {
        cert.verify_status = 'issued'  // 默认为已签发
    }
    
    // 如果证书缺少 node_id，设置默认值
    if (!cert.node_id) {
        cert.node_id = 'center'  // 默认为中心节点
    }
    
    currentCert.value = cert
    certDialogVisible.value = true
}

// 复制到剪贴板
const copyToClipboard = async (text) => {
    if (!text) {
        ElMessage.warning('没有可复制的内容')
        return
    }
    try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('已复制到剪贴板')
    } catch (error) {
        ElMessage.error('复制失败')
    }
}

// 获取风险等级类型
const getRiskType = (level) => {
    const types = {
        '可信': 'success',
        '轻度可疑': 'warning',
        '高风险': 'danger',
        '不可信': 'info'
    }
    return types[level] || ''
}

// 获取验签状态文本
const getVerifyStatusText = (status) => {
    const texts = {
        'verified': '验签通过',
        'issued': '已签发',
        'error': '证书异常',
        'pending': '待验证'
    }
    return texts[status] || status || '未知'
}

// 获取验签状态图标
const getVerifyStatusIcon = (status) => {
    const icons = {
        'verified': 'Check',
        'issued': 'Stamp',
        'error': 'Close',
        'pending': 'Clock'
    }
    return icons[status] || 'Clock'
}

// 获取验签状态类型
const getVerifyStatusType = (status) => {
    const types = {
        'verified': 'success',
        'issued': '',
        'error': 'danger',
        'pending': 'warning'
    }
    return types[status] || ''
}

// 获取验签横幅样式类
const getVerifyBannerClass = (status) => {
    const classes = {
        'verified': 'banner-success',
        'issued': 'banner-info',
        'error': 'banner-danger',
        'pending': 'banner-warning'
    }
    return classes[status] || ''
}

// 获取验签横幅标题
const getVerifyBannerTitle = (status) => {
    const titles = {
        'verified': '证书验签通过',
        'issued': '证书已签发',
        'error': '证书验签失败',
        'pending': '等待验签'
    }
    return titles[status] || '未知状态'
}

// 获取验签横幅描述
const getVerifyBannerDesc = (status) => {
    const descs = {
        'verified': '该证书签名有效，内容未被篡改，检测结果可信',
        'issued': '证书已由国密算法签发，可进行验签验证',
        'error': '证书签名验证失败，可能存在篡改或损坏',
        'pending': '证书尚未完成验签流程'
    }
    return descs[status] || '未知状态'
}

// 重新检测
const retestTask = async (task) => {
    try {
        await ElMessageBox.confirm(
            `确定要重新检测任务 ${task.task_id.substring(0, 8)}... 吗？`,
            '确认重测',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )
        
        // TODO: 调用重新检测 API
        ElMessage.success('已提交重测请求')
        await loadTasks()
    } catch (error) {
        // 用户取消
    }
}

// 删除单个任务
const handleDeleteTask = async (task) => {
    try {
        await ElMessageBox.confirm(
            `确定要删除任务 ${task.task_id.substring(0, 8)}... 吗？此操作不可恢复！`,
            '确认删除',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )
        
        const response = await deleteTask(task.task_id)
        if (response.success) {
            ElMessage.success(response.message || '删除成功')
            await loadTasks()
        }
    } catch (error) {
        if (error !== 'cancel') {
            console.error('删除任务失败:', error)
            ElMessage.error(error.response?.data?.detail || '删除失败')
        }
    }
}

// 批量删除任务
const handleBatchDeleteTasks = async () => {
    if (selectedTaskIds.value.length === 0) {
        ElMessage.warning('请先选择要删除的任务')
        return
    }
    
    try {
        await ElMessageBox.confirm(
            `确定要删除选中的 ${selectedTaskIds.value.length} 个任务吗？此操作不可恢复！`,
            '确认批量删除',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )
        
        const response = await batchDeleteTasks(selectedTaskIds.value)
        if (response.success) {
            ElMessage.success(response.message || `成功删除 ${response.deleted_count} 个任务`)
            selectedTaskIds.value = [] // 清空选中
            await loadTasks()
        }
    } catch (error) {
        if (error !== 'cancel') {
            console.error('批量删除任务失败:', error)
            ElMessage.error(error.response?.data?.detail || '批量删除失败')
        }
    }
}

// 表格选择变化处理
const handleSelectionChange = (selection) => {
    selectedTaskIds.value = selection.map(item => item.task_id)
}

// 组件挂载时加载数据
onMounted(() => {
    loadTasks()
})
</script>

<style scoped>
.tasks {
    padding: 40px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    min-height: 100vh;
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

/* 筛选器区域 */
.filter-section {
    margin-top: 30px;
    padding: 20px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.filter-section .el-select {
    width: 100%;
}

.filter-section .el-button {
    margin-left: 10px;
}

/* 统计卡片 */
.stats-cards {
    margin-top: 20px;
}

.stat-card {
    transition: all 0.3s ease;
    cursor: pointer;
}

.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.stat-content {
    display: flex;
    align-items: center;
    gap: 15px;
}

.stat-icon {
    width: 60px;
    height: 60px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 28px;
}

.stat-info {
    flex: 1;
}

.stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #303133;
    line-height: 1;
}

.stat-label {
    font-size: 14px;
    color: #909399;
    margin-top: 8px;
}

/* 表格优化 */
.el-table {
    margin-top: 30px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.el-table :deep(.el-tag) {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.el-table :deep(.el-progress) {
    margin: 0;
}

/* 分页容器 */
.pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
    padding: 10px 0;
}

.pagination-container :deep(.el-pagination) {
    font-weight: 500;
}

.pagination-container :deep(.el-pagination__total) {
    color: #606266;
}

.pagination-container :deep(.el-pagination__jump) {
    color: #606266;
}

/* 对话框优化 */
.el-dialog :deep(.el-descriptions__title) {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 10px;
}

/* 证书验签横幅 */
.verify-banner {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 24px;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.verify-banner.banner-success {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2f1 100%);
    border-left: 4px solid #67c23a;
}

.verify-banner.banner-info {
    background: linear-gradient(135deg, #f4f4f5 0%, #e8eaf6 100%);
    border-left: 4px solid #409eff;
}

.verify-banner.banner-danger {
    background: linear-gradient(135deg, #fef0f0 0%, #ffebee 100%);
    border-left: 4px solid #f56c6c;
}

.verify-banner.banner-warning {
    background: linear-gradient(135deg, #fdf6ec 0%, #fff8e1 100%);
    border-left: 4px solid #e6a23c;
}

.verify-icon {
    color: inherit;
    font-size: 48px;
}

.verify-content {
    flex: 1;
}

.verify-title {
    font-size: 20px;
    font-weight: bold;
    margin: 0 0 8px 0;
    color: #303133;
}

.verify-desc {
    font-size: 14px;
    margin: 0;
    color: #606266;
}

.verify-badge {
    flex-shrink: 0;
}

/* 批量操作工具栏 */
.batch-actions {
    margin-top: 20px;
    padding: 15px;
    background: #f4f4f5;
    border-radius: 4px;
    border: 1px solid #dcdfe6;
}

.batch-actions .el-alert {
    margin-bottom: 10px;
}

/* 验签详细信息卡片 */
.verify-details-card {
    margin-bottom: 20px;
    border: 1px solid #ebeef5;
}

.verify-details-card :deep(.card-header) {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: bold;
    color: #303133;
}

/* 响应式设计 */
@media (max-width: 1200px) {
    .tasks {
        padding: 20px;
    }
    
    .stat-value {
        font-size: 24px;
    }
    
    .stat-icon {
        width: 50px;
        height: 50px;
        font-size: 24px;
    }
}
</style>
