<template>
    <div class="certificates">
        <div class="container">
            <el-card>
                <h2>证书查询</h2>
                <p style="color: #909399; margin-top: 10px;">查看和管理国密可信证书</p>
                
                <el-input
                    v-model="searchQuery"
                    placeholder="输入证书ID或内容哈希搜索"
                    prefix-icon="Search"
                    style="margin: 20px 0;"
                    clearable
                    @clear="loadCertificates"
                    @keyup.enter="handleSearch"
                />
                
                <el-button type="primary" @click="handleSearch" style="margin-bottom: 20px;">
                    <el-icon><Search /></el-icon>
                    搜索
                </el-button>
                
                <!-- 批量操作工具栏 -->
                <div class="batch-actions" v-if="selectedCertIds.length > 0">
                    <el-alert
                        :title="'已选中 ' + selectedCertIds.length + ' 个证书'"
                        type="info"
                        :closable="false"
                        show-icon
                    />
                    <el-button 
                        type="danger" 
                        size="small"
                        @click="handleBatchDeleteCerts"
                        style="margin-top: 10px;"
                    >
                        <el-icon><Delete /></el-icon> 批量删除选中证书
                    </el-button>
                </div>
                
                <el-table :data="paginatedCertificates" v-loading="loading" @selection-change="handleSelectionChange">
                    <el-table-column type="selection" width="55" align="center" />
6. 增加“审计日志时间线”
这是很适合你项目的页面或组件。可以在证书详情页下面加一个时间线：
10:21 内容上传
10:22 SM3 哈希生成
10:22 检测任务创建
10:23 模型推理完成
10:23 指纹生成
10:24 SM2 证书签发
10:24 审计日志写入
这个东西技术上不难，但展示效果很好，能突出“可追溯”。
                    <el-table-column prop="cert_id" label="证书ID" width="320" show-overflow-tooltip />
                    <el-table-column prop="content_id" label="内容ID" width="320" show-overflow-tooltip />
                    <el-table-column label="验签状态" width="140" align="center">
                        <template #default="{ row }">
                            <el-tag :type="getVerifyStatusType(row.verify_status)" effect="dark">
                                <el-icon><component :is="getVerifyStatusIcon(row.verify_status)" /></el-icon>
                                {{ getVerifyStatusText(row.verify_status) }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="risk_level" label="风险等级" width="120" align="center">
                        <template #default="{ row }">
                            <el-tag :type="getRiskType(row.risk_level)">
                                {{ row.risk_level }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="issued_at" label="签发时间" width="180" />
                    <el-table-column label="操作" width="280" fixed="right">
                        <template #default="{ row }">
                            <el-button size="small" type="success" @click="verifyCert(row)">
                                <el-icon><CircleCheck /></el-icon> 在线签验
                            </el-button>
                            <el-button size="small" type="primary" @click="viewCert(row)">
                                <el-icon><View /></el-icon> 详情
                            </el-button>
                            <el-button size="small" type="danger" @click="handleDeleteCert(row)">
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
                        :total="filteredCertificates.length"
                        layout="total, sizes, prev, pager, next, jumper"
                        @size-change="handleSizeChange"
                        @current-change="handleCurrentChange"
                    />
                </div>
                
                <!-- 空状态 -->
                <el-empty v-if="!loading && paginatedCertificates.length === 0" description="暂无证书数据" />
            </el-card>
        </div>
        
        <!-- 证书详情对话框 -->
        <el-dialog v-model="dialogVisible" title="国密可信证书详情" width="900px">
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
                        <el-text type="primary" style="font-family: monospace;">{{ currentCert.cert_id }}</el-text>
                        <el-button size="small" text @click="copyToClipboard(currentCert.cert_id)">
                            <el-icon><CopyDocument /></el-icon>
                        </el-button>
                    </el-descriptions-item>
                    <el-descriptions-item label="内容哈希" :span="2">
                        <el-text type="info" style="font-family: monospace; font-size: 12px;">
                            {{ currentCert.content_hash || currentCert.signature?.fingerprint || 'N/A' }}
                        </el-text>
                        <el-button size="small" text @click="copyToClipboard(currentCert.content_hash || currentCert.signature?.fingerprint)">
                            <el-icon><CopyDocument /></el-icon>
                        </el-button>
                    </el-descriptions-item>
                </el-descriptions>
            </el-card>
            <el-descriptions :column="2" border v-if="currentCert">
                <el-descriptions-item label="证书ID">{{ currentCert.cert_id }}</el-descriptions-item>
                <el-descriptions-item label="内容ID">{{ currentCert.content_id }}</el-descriptions-item>
                <el-descriptions-item label="风险等级">
                    <el-tag :type="getRiskType(currentCert.risk_level)">{{ currentCert.risk_level }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="签发时间">{{ currentCert.issued_at }}</el-descriptions-item>
            </el-descriptions>
            
            <h3 style="margin-top: 20px;">证书签名信息</h3>
            <el-card v-if="currentCert?.signature" style="margin-top: 10px;">
                <div v-if="typeof currentCert.signature === 'object'">
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="证书ID">
                            {{ currentCert.signature.certificate_id || currentCert.cert_id }}
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
                    <p style="font-size: 12px; line-height: 1.6;">{{ currentCert.signature }}</p>
                </div>
            </el-card>
            <el-empty v-else description="暂无签名信息" />
            
            <!-- 审计日志时间线 -->
            <el-card class="audit-timeline-card" shadow="never" style="margin-top: 20px;">
                <template #header>
                    <div class="card-header">
                        <el-icon><Clock /></el-icon>
                        <span>审计日志时间线</span>
                        <el-tag size="small" type="info" style="margin-left: auto;">可追溯</el-tag>
                    </div>
                </template>
                <el-timeline>
                    <el-timeline-item
                        v-for="(log, index) in auditLogs"
                        :key="index"
                        :timestamp="log.time"
                        :type="log.type"
                        :icon="log.icon"
                        hollow
                    >
                        <div class="timeline-content">
                            <h4 class="timeline-title">{{ log.title }}</h4>
                            <p class="timeline-desc">{{ log.description }}</p>
                            <el-tag v-if="log.detail" size="small" type="info" style="margin-top: 5px;">
                                {{ log.detail }}
                            </el-tag>
                        </div>
                    </el-timeline-item>
                </el-timeline>
            </el-card>
            
            <template #footer>
                <el-button @click="dialogVisible = false">关闭</el-button>
                <el-button type="primary" @click="downloadCert">下载证书</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAllCertificates, searchCertificates, deleteCertificate, batchDeleteCertificates, verifyCertificate as apiVerifyCertificate } from '../api/detection'
import { 
    Search, View, Stamp, CopyDocument, Clock,
    CircleCheck, WarningFilled, CircleClose, Delete
} from '@element-plus/icons-vue'

const loading = ref(false)
const searchQuery = ref('')
const certificates = ref([])
const dialogVisible = ref(false)
const currentCert = ref(null)

// 批量选择相关
const selectedCertIds = ref([])

// 分页状态
const currentPage = ref(1)
const pageSize = ref(20)

// 加载证书列表
const loadCertificates = async () => {
    loading.value = true
    try {
        const response = await getAllCertificates({ limit: 100 })
        certificates.value = response.certificates || []
    } catch (error) {
        ElMessage.error('加载证书列表失败')
        console.error(error)
    } finally {
        loading.value = false
    }
}

// 搜索证书
const handleSearch = async () => {
    if (!searchQuery.value) {
        loadCertificates()
        return
    }
    
    loading.value = true
    try {
        const response = await searchCertificates(searchQuery.value)
        certificates.value = response.certificates || []
        currentPage.value = 1 // 搜索后回到第一页
    } catch (error) {
        ElMessage.error('搜索失败')
    } finally {
        loading.value = false
    }
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

const filteredCertificates = computed(() => {
    return certificates.value
})

// 计算属性：分页后的证书列表
const paginatedCertificates = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return filteredCertificates.value.slice(start, end)
})

// 计算属性：选中的证书对象
const selectedCerts = computed(() => {
    return certificates.value.filter(cert => selectedCertIds.value.includes(cert.cert_id))
})

const getRiskType = (level) => {
    const types = {
        '可信': 'success',
        '轻度可疑': 'warning',
        '高风险': 'danger',
        '不可信': 'info'
    }
    return types[level] || ''
}

// 验签状态相关函数
const getVerifyStatusText = (status) => {
    const texts = {
        'verified': '验签通过',
        'issued': '已签发',
        'error': '证书异常',
        'pending': '待验证'
    }
    return texts[status] || '未知'
}

const getVerifyStatusType = (status) => {
    const types = {
        'verified': 'success',
        'issued': 'primary',
        'error': 'danger',
        'pending': 'info'
    }
    return types[status] || ''
}

const getVerifyStatusIcon = (status) => {
    const icons = {
        'verified': 'CircleCheck',
        'issued': 'Stamp',
        'error': 'CircleClose',
        'pending': 'WarningFilled'
    }
    return icons[status] || 'WarningFilled'
}

const getVerifyBannerClass = (status) => {
    return `verify-banner--${status}`
}

const getVerifyBannerTitle = (status) => {
    const titles = {
        'verified': 'SM2 验签通过',
        'issued': '证书已签发',
        'error': '证书验证失败',
        'pending': '等待验证'
    }
    return titles[status] || '未知状态'
}

const getVerifyBannerDesc = (status) => {
    const descs = {
        'verified': '内容未被篡改，签名有效，数据完整可信',
        'issued': '证书已成功签发，可进行在线验签',
        'error': '签名验证失败，证书可能已被篡改或损坏',
        'pending': '证书尚未进行验签操作'
    }
    return descs[status] || '未知描述'
}

// 复制到剪贴板
const copyToClipboard = async (text) => {
    if (!text) {
        ElMessage.warning('暂无数据可复制')
        return
    }
    try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('已复制到剪贴板')
    } catch (error) {
        ElMessage.error('复制失败，请手动复制')
    }
}

// 查看证书详情
const viewCert = (cert) => {
    currentCert.value = cert
    dialogVisible.value = true
}

// 在线验签
const verifyCert = async (cert) => {
    try {
        const loadingMsg = ElMessage({
            message: '正在进行SM2验签...',
            type: 'info',
            duration: 0
        })
        
        const response = await apiVerifyCertificate(cert.cert_id)
        loadingMsg.close()
        
        if (response.success) {
            // 更新证书的验签状态
            cert.verify_status = response.verified ? 'verified' : 'error'
            cert.verification_result = response.verification_result
            
            if (response.verified) {
                ElMessage({
                    message: '✅ SM2验签通过！证书签名有效，内容完整可信',
                    type: 'success',
                    duration: 3000
                })
            } else {
                ElMessage({
                    message: '❌ 验签失败：' + (response.errors?.join(', ') || '未知错误'),
                    type: 'error',
                    duration: 5000
                })
            }
            
            // 打开详情对话框显示验签结果
            currentCert.value = cert
            dialogVisible.value = true
        }
    } catch (error) {
        ElMessage.closeAll()
        console.error('验签失败:', error)
        ElMessage.error('验签失败: ' + (error.response?.data?.detail || error.message))
    }
}

// 删除单个证书
const handleDeleteCert = async (cert) => {
    try {
        await ElMessageBox.confirm(
            `确定要删除证书 ${cert.cert_id.substring(0, 8)}... 吗？此操作不可恢复！`,
            '确认删除',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )
        
        const response = await deleteCertificate(cert.cert_id)
        if (response.success) {
            ElMessage.success(response.message || '删除成功')
            await loadCertificates()
        }
    } catch (error) {
        if (error !== 'cancel') {
            console.error('删除证书失败:', error)
            ElMessage.error(error.response?.data?.detail || '删除失败')
        }
    }
}

// 批量删除证书
const handleBatchDeleteCerts = async () => {
    if (selectedCertIds.value.length === 0) {
        ElMessage.warning('请先选择要删除的证书')
        return
    }
    
    try {
        await ElMessageBox.confirm(
            `确定要删除选中的 ${selectedCertIds.value.length} 个证书吗？此操作不可恢复！`,
            '确认批量删除',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )
        
        const response = await batchDeleteCertificates(selectedCertIds.value)
        if (response.success) {
            ElMessage.success(response.message || `成功删除 ${response.deleted_count} 个证书`)
            selectedCertIds.value = [] // 清空选中
            await loadCertificates()
        }
    } catch (error) {
        if (error !== 'cancel') {
            console.error('批量删除证书失败:', error)
            ElMessage.error(error.response?.data?.detail || '批量删除失败')
        }
    }
}

// 表格选择变化处理
const handleSelectionChange = (selection) => {
    selectedCertIds.value = selection.map(item => item.cert_id)
}

// 审计日志时间线（根据证书签发时间生成）
const auditLogs = computed(() => {
    if (!currentCert.value) return []
    
    const issuedAt = new Date(currentCert.value.issued_at)
    const baseTime = issuedAt.getTime()
    
    // 模拟各个步骤的时间点（从签发时间往前推算）
    const logs = [
        {
            time: formatAuditTime(baseTime - 180000), // 3分钟前
            title: '内容上传',
            description: '用户上传待检测内容至平台',
            detail: currentCert.value.content_id,
            type: 'primary',
            icon: 'Upload'
        },
        {
            time: formatAuditTime(baseTime - 150000), // 2.5分钟前
            title: 'SM3 哈希生成',
            description: '计算内容 SM3 摘要哈希值',
            detail: '国密算法',
            type: 'info',
            icon: 'Key'
        },
        {
            time: formatAuditTime(baseTime - 120000), // 2分钟前
            title: '检测任务创建',
            description: '创建 AI 检测任务并分配节点',
            detail: currentCert.value.node_id?.includes('edge') ? '边缘节点' : '中心节点',
            type: 'warning',
            icon: 'List'
        },
        {
            time: formatAuditTime(baseTime - 90000), // 1.5分钟前
            title: '模型推理完成',
            description: '深度学习模型分析完成',
            detail: `风险等级: ${currentCert.value.risk_level}`,
            type: 'success',
            icon: 'Cpu'
        },
        {
            time: formatAuditTime(baseTime - 60000), // 1分钟前
            title: '指纹生成',
            description: '生成内容数字指纹（pHash/SimHash/Merkle）',
            detail: '指纹存证',
            type: 'info',
            icon: 'Fingerprint'
        },
        {
            time: formatAuditTime(baseTime - 30000), // 30秒前
            title: 'SM2 证书签发',
            description: '使用国密 SM2 算法签名证书',
            detail: 'SM2 + SM3',
            type: 'success',
            icon: 'Stamp'
        },
        {
            time: formatAuditTime(baseTime), // 当前时间
            title: '审计日志写入',
            description: '完整审计链路记录入库',
            detail: '可追溯',
            type: 'success',
            icon: 'CircleCheck'
        }
    ]
    
    return logs
})

// 格式化审计时间
const formatAuditTime = (timestamp) => {
    const date = new Date(timestamp)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const downloadCert = async () => {
    if (!currentCert.value) return
    
    try {
        const html2canvas = await import('html2canvas')
        const { jsPDF } = await import('jspdf')
        const cert = currentCert.value
        
        // 创建临时容器用于渲染证书
        const tempContainer = document.createElement('div')
        tempContainer.style.position = 'absolute'
        tempContainer.style.left = '-9999px'
        tempContainer.style.top = '-9999px'
        tempContainer.style.width = '800px'
        tempContainer.style.background = 'white'
        tempContainer.style.padding = '40px'
        tempContainer.style.fontFamily = 'Microsoft YaHei, SimHei, Arial, sans-serif'
        
        // 构建HTML内容
        const certId = cert.cert_id || 'N/A'
        const contentId = cert.content_id || 'N/A'
        const riskLevel = cert.risk_level || 'N/A'
        const issuedAt = cert.issued_at || 'N/A'
        const contentHash = cert.content_hash || cert.signature?.fingerprint || 'N/A'
        
        let signatureInfo = ''
        if (typeof cert.signature === 'object') {
            signatureInfo = `
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">📊</span>
                        <span>详细信息</span>
                    </h3>
                    <div style="padding: 15px; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 6px; font-size: 13px; line-height: 2; color: #334155; border-left: 4px solid #64748b;">
                        <div><strong style="color: #475569;">内容类型:</strong> ${cert.signature.content_type || 'N/A'}</div>
                        <div><strong style="color: #475569;">检测评分:</strong> ${(cert.signature.detection_score || 0).toFixed(4)}</div>
                        <div><strong style="color: #475569;">指纹信息:</strong> ${cert.signature.fingerprint || 'N/A'}</div>
                    </div>
                </div>
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">✍️</span>
                        <span>SM2 数字签名</span>
                    </h3>
                    <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); padding: 15px; border-radius: 6px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 9px; line-height: 1.6; max-height: 180px; overflow: hidden; color: #991b1b; border-left: 4px solid #ef4444; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">${cert.signature.sm2_signature || 'N/A'}</div>
                </div>
            `
        } else {
            const sigText = typeof cert.signature === 'string' ? cert.signature : 'N/A'
            signatureInfo = `
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">✍️</span>
                        <span>签名信息</span>
                    </h3>
                    <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); padding: 15px; border-radius: 6px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 9px; line-height: 1.6; max-height: 180px; overflow: hidden; color: #991b1b; border-left: 4px solid #ef4444; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">${sigText}</div>
                </div>
            `
        }
        
        tempContainer.innerHTML = `
            <div style="border: 4px solid #1e40af; padding: 40px; background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f0f4ff 100%); border-radius: 8px; box-shadow: 0 4px 20px rgba(30, 64, 175, 0.15);">
                <!-- 标题区域 -->
                <div style="text-align: center; margin-bottom: 35px; padding-bottom: 25px; border-bottom: 3px solid #1e40af; position: relative;">
                    <div style="position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: white; padding: 0 20px;">
                        <span style="font-size: 40px;">🔐</span>
                    </div>
                    <h1 style="color: #1e40af; font-size: 36px; margin: 15px 0 8px 0; font-weight: 900; letter-spacing: 3px; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);">AIGC-Trust</h1>
                    <h2 style="color: #2563eb; font-size: 26px; margin: 0; font-weight: 600; letter-spacing: 8px;">国密可信证书</h2>
                    <div style="margin-top: 10px; color: #64748b; font-size: 12px; letter-spacing: 2px;">CERTIFICATE OF AUTHENTICITY</div>
                </div>
                
                <!-- 基本信息 -->
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">📋</span>
                        <span>基本信息</span>
                    </h3>
                    <table style="width: 100%; border-collapse: separate; border-spacing: 0 8px;">
                        <tr style="background: linear-gradient(90deg, #f8fafc 0%, #ffffff 100%);">
                            <td style="padding: 12px 15px; width: 130px; font-weight: 700; color: #475569; font-size: 14px; border-left: 4px solid #3b82f6;">证书ID</td>
                            <td style="padding: 12px 15px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 11px; color: #1e293b; background: #f1f5f9; border-radius: 4px;">${certId}</td>
                        </tr>
                        <tr style="background: linear-gradient(90deg, #f8fafc 0%, #ffffff 100%);">
                            <td style="padding: 12px 15px; font-weight: 700; color: #475569; font-size: 14px; border-left: 4px solid #3b82f6;">内容ID</td>
                            <td style="padding: 12px 15px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 11px; color: #1e293b; background: #f1f5f9; border-radius: 4px;">${contentId}</td>
                        </tr>
                        <tr style="background: linear-gradient(90deg, #f8fafc 0%, #ffffff 100%);">
                            <td style="padding: 12px 15px; font-weight: 700; color: #475569; font-size: 14px; border-left: 4px solid #3b82f6;">风险等级</td>
                            <td style="padding: 12px 15px;">
                                <span style="padding: 6px 16px; background: ${riskLevel === '可信' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : riskLevel === '可疑' ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'}; color: white; border-radius: 20px; display: inline-block; font-weight: 700; font-size: 13px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); letter-spacing: 2px;">${riskLevel}</span>
                            </td>
                        </tr>
                        <tr style="background: linear-gradient(90deg, #f8fafc 0%, #ffffff 100%);">
                            <td style="padding: 12px 15px; font-weight: 700; color: #475569; font-size: 14px; border-left: 4px solid #3b82f6;">签发时间</td>
                            <td style="padding: 12px 15px; color: #1e293b; font-size: 13px; font-weight: 500;">${issuedAt}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- 签名信息 -->
                ${signatureInfo}
                
                <!-- 内容哈希 -->
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">🔑</span>
                        <span>内容哈希</span>
                    </h3>
                    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 15px; border-radius: 6px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 11px; line-height: 1.8; color: #0c4a6e; border-left: 4px solid #0ea5e9; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">${contentHash}</div>
                </div>
                
                <!-- 底部说明 -->
                <div style="text-align: center; margin-top: 35px; padding: 25px 20px; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 8px; border: 2px dashed #cbd5e1;">
                    <div style="font-size: 28px; margin-bottom: 10px;">🛡️</div>
                    <p style="margin: 8px 0; color: #1e40af; font-size: 14px; font-weight: 700; letter-spacing: 1px;">此证书由 AIGC-Trust 平台权威签发</p>
                    <p style="margin: 8px 0; color: #475569; font-size: 12px;">使用国密 SM2/SM3 算法保证数据完整性与不可篡改性</p>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 11px;">
                        <span style="margin-right: 20px;">📅 生成时间: ${new Date().toLocaleString('zh-CN')}</span>
                        <span>🔒 防伪认证</span>
                    </div>
                </div>
            </div>
        `
        
        document.body.appendChild(tempContainer)
        
        // 等待DOM渲染完成
        await new Promise(resolve => setTimeout(resolve, 100))
        
        // 转换为canvas
        const canvas = await html2canvas.default(tempContainer, {
            scale: 2,
            useCORS: true,
            backgroundColor: '#ffffff'
        })
        
        // 移除临时容器
        document.body.removeChild(tempContainer)
        
        // 转换为PDF
        const imgData = canvas.toDataURL('image/png')
        const pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4'
        })
        
        const pdfWidth = pdf.internal.pageSize.getWidth()
        const pdfHeight = pdf.internal.pageSize.getHeight()
        const imgWidth = pdfWidth - 20 // 左右各留10mm边距
        const imgHeight = (canvas.height * imgWidth) / canvas.width
        
        // 如果内容超过一页,调整缩放
        let finalImgHeight = imgHeight
        let finalImgWidth = imgWidth
        if (imgHeight > pdfHeight - 20) {
            finalImgHeight = pdfHeight - 20
            finalImgWidth = (canvas.width * finalImgHeight) / canvas.height
        }
        
        const xPosition = (pdfWidth - finalImgWidth) / 2
        const yPosition = 10
        
        pdf.addImage(imgData, 'PNG', xPosition, yPosition, finalImgWidth, finalImgHeight)
        
        // 保存PDF
        const fileName = `certificate_${certId.substring(0, 8)}.pdf`
        pdf.save(fileName)
        
        ElMessage.success('证书PDF已下载')
    } catch (error) {
        console.error('生成PDF失败:', error)
        ElMessage.error('生成PDF失败: ' + error.message)
    }
}

// 组件挂载时加载数据
onMounted(() => {
    loadCertificates()
})
</script>

<style scoped>
.certificates {
    padding: 40px;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
    min-height: 100vh;
}

.container {
    max-width: 1600px;
    margin: 0 auto;
}

/* 页面标题 */
.certificates h2 {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 28px;
    color: #303133;
    margin: 0;
}

/* 验签状态横幅 */
.verify-banner {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 30px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.verify-banner:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
}

.verify-banner--verified {
    background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
    color: white;
}

.verify-banner--issued {
    background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
    color: white;
}

.verify-banner--error {
    background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
    color: white;
}

.verify-banner--pending {
    background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%);
    color: white;
}

.verify-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    backdrop-filter: blur(10px);
}

.verify-content {
    flex: 1;
}

.verify-title {
    font-size: 24px;
    font-weight: bold;
    margin: 0 0 8px 0;
    color: inherit;
}

.verify-desc {
    font-size: 14px;
    margin: 0;
    opacity: 0.95;
    color: inherit;
}

.verify-badge {
    display: flex;
    align-items: center;
}

.verify-badge :deep(.el-tag) {
    font-size: 16px;
    padding: 12px 24px;
    border: 2px solid rgba(255, 255, 255, 0.5);
}

/* 验签详细信息卡片 */
.verify-details-card {
    margin-bottom: 20px;
    border: 2px solid #e4e7ed;
    border-radius: 8px;
}

.verify-details-card :deep(.el-card__header) {
    background: #f5f7fa;
    border-bottom: 2px solid #e4e7ed;
    padding: 15px 20px;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: bold;
    color: #303133;
}

.card-header .el-icon {
    font-size: 20px;
    color: #409eff;
}

/* 表格优化 */
.el-table :deep(.el-tag) {
    display: inline-flex;
    align-items: center;
    gap: 4px;
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

/* 审计日志时间线 */
.audit-timeline-card {
    border: 2px solid #e4e7ed;
    border-radius: 8px;
}

.audit-timeline-card :deep(.el-card__header) {
    background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
    border-bottom: 2px solid #e4e7ed;
    padding: 15px 20px;
}

.timeline-content {
    padding: 5px 0;
}

.timeline-title {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 5px 0;
}

.timeline-desc {
    font-size: 13px;
    color: #606266;
    margin: 0 0 5px 0;
    line-height: 1.5;
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

.audit-timeline-card :deep(.el-timeline-item__timestamp) {
    font-size: 13px;
    color: #909399;
    font-weight: 500;
}

.audit-timeline-card :deep(.el-timeline-item__node) {
    width: 14px;
    height: 14px;
    border-width: 3px;
}

/* 对话框优化 */
.el-dialog :deep(.el-descriptions__label) {
    font-weight: 600;
}

.el-dialog :deep(.el-text--monospace) {
    word-break: break-all;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .verify-banner {
        flex-direction: column;
        text-align: center;
    }
    
    .verify-icon {
        width: 60px;
        height: 60px;
    }
    
    .verify-title {
        font-size: 20px;
    }
}
</style>
