<template>
    <div class="detection">
        <div class="container">
            <!-- 检测流程步骤条 -->
            <el-card class="steps-card">
                <el-steps :active="currentStep" finish-status="success" align-center>
                    <el-step title="内容上传" description="拖拽或选择文件" />
                    <el-step title="预处理" description="格式转换与标准化" />
                    <el-step title="模型检测" description="AI生成概率分析" />
                    <el-step title="取证分析" description="频域/噪声特征提取" />
                    <el-step title="融合判定" description="多维度风险决策" />
                    <el-step title="证书生成" description="国密SM2签名" />
                </el-steps>
            </el-card>
            
            <!-- 主操作区 -->
            <el-row :gutter="30" class="main-content">
                <!-- 左侧：文件上传/文本输入区 -->
                <el-col :span="14">
                    <el-card class="upload-section">
                        <template #header>
                            <div class="card-header">
                                <h3><el-icon><upload-filled /></el-icon> 内容输入</h3>
                            </div>
                        </template>
                        
                        <!-- 输入方式选项卡 -->
                        <el-tabs v-model="inputMode" type="border-card">
                            <!-- 文件上传 -->
                            <el-tab-pane label="文件上传" name="file">
                                <el-upload
                                    drag
                                    :http-request="handleUpload"
                                    :before-upload="beforeUpload"
                                    accept=".mp4,.avi,.mov,.mkv,.jpg,.jpeg,.png,.txt,.docx,.pdf"
                                    :show-file-list="false"
                                    :disabled="uploading"
                                >
                                    <el-icon class="el-icon--upload" :size="60"><upload-filled /></el-icon>
                                    <div class="el-upload__text">
                                        拖拽文件到此处<br/>或 <em>点击上传</em>
                                    </div>
                                    <template #tip>
                                        <div class="el-upload__tip">
                                            支持视频（MP4/AVI/MOV/MKV）、图片（JPG/PNG）和文档（TXT/DOCX/PDF）格式
                                        </div>
                                    </template>
                                </el-upload>
                                
                                <!-- 当前上传文件信息 -->
                                <div v-if="currentFile" class="file-info">
                                    <el-icon><document /></el-icon>
                                    <span>{{ currentFile.name }}</span>
                                    <span class="file-size">({{ formatFileSize(currentFile.size) }})</span>
                                </div>
                            </el-tab-pane>
                            
                            <!-- 文本直接输入 -->
                            <el-tab-pane label="文本输入" name="text">
                                <div class="text-input-area">
                                    <el-input
                                        v-model="textInputContent"
                                        type="textarea"
                                        :rows="12"
                                        :placeholder="'请输入要检测的文本内容...\n\n支持中文、英文等各种语言\n至少输入5个字符即可检测，建议50+字符以获得更准确的结果'"
                                        :disabled="uploading"
                                    />
                                    <div class="text-stats">
                                        <span>已输入: {{ textInputContent.length }} 字符</span>
                                        <span v-if="textInputContent.length > 0 && textInputContent.length < 5" style="color: #f56c6c; margin-left: 10px;">
                                            ⚠️ 至少需要5个字符
                                        </span>
                                        <span v-else-if="textInputContent.length >= 5 && textInputContent.length < 50" style="color: #e6a23c; margin-left: 10px;">
                                            ✓ 可以检测（建议50+字符）
                                        </span>
                                        <span v-else-if="textInputContent.length >= 50" style="color: #67c23a; margin-left: 10px;">
                                            ✓ 字符数充足
                                        </span>
                                    </div>
                                </div>
                            </el-tab-pane>
                        </el-tabs>
                    </el-card>
                </el-col>
                
                <!-- 右侧：检测配置区 -->
                <el-col :span="10">
                    <el-card class="config-section">
                        <template #header>
                            <div class="card-header">
                                <h3><el-icon><setting /></el-icon> 检测配置</h3>
                            </div>
                        </template>
                        
                        <el-form label-position="top" size="large">
                            <!-- 检测模式 -->
                            <el-form-item label="检测模式">
                                <el-select v-model="detectMode" style="width: 100%">
                                    <el-option label="中心平台完整检测" value="center">
                                        <span>🏢 中心平台完整检测</span>
                                        <small style="color: #909399; display: block; margin-top: 4px;">多维度深度分析，生成完整证书</small>
                                    </el-option>
                                    <el-option label="边缘轻量化初筛" value="edge">
                                        <span>⚡ 边缘轻量化初筛</span>
                                        <small style="color: #909399; display: block; margin-top: 4px;">快速筛查，降低中心负载</small>
                                    </el-option>
                                </el-select>
                            </el-form-item>
                            
                            <!-- 内容类型 -->
                            <el-form-item label="内容类型">
                                <el-radio-group v-model="contentType" style="width: 100%">
                                    <el-radio-button label="auto">自动识别</el-radio-button>
                                    <el-radio-button label="image">图像</el-radio-button>
                                    <el-radio-button label="video">视频</el-radio-button>
                                    <el-radio-button label="text">文本</el-radio-button>
                                </el-radio-group>
                            </el-form-item>
                            
                            <!-- 是否生成证书 -->
                            <el-form-item label="证书生成">
                                <el-switch
                                    v-model="generateCert"
                                    active-text="生成国密证书"
                                    inactive-text="不生成"
                                />
                            </el-form-item>
                            
                            <!-- GPU加速 -->
                            <el-form-item label="GPU加速">
                                <el-switch
                                    v-model="useGPU"
                                    active-text="启用GPU加速"
                                    inactive-text="CPU模式"
                                />
                                <div class="form-tip">GPU可大幅提升视频处理速度</div>
                            </el-form-item>
                            
                            <!-- 开始检测按钮 -->
                            <el-form-item>
                                <el-button 
                                    type="primary" 
                                    size="large" 
                                    style="width: 100%"
                                    @click="startDetection"
                                    :disabled="!canStartDetection || uploading"
                                    :loading="uploading"
                                >
                                    <el-icon v-if="!uploading"><circle-check /></el-icon>
                                    {{ uploading ? '检测中...' : '开始检测' }}
                                </el-button>
                                <div class="form-tip" v-if="inputMode === 'text'">
                                    💡 直接输入文本内容，无需上传文件
                                </div>
                            </el-form-item>
                        </el-form>
                    </el-card>
                </el-col>
            </el-row>
            
            <!-- 下方：检测进度与结果 -->
            <el-card v-if="uploading || result" class="progress-result-section">
                <!-- 进度条 -->
                <div v-if="uploading" class="progress-display">
                    <el-progress 
                        :percentage="progress" 
                        :status="progressStatus"
                        :stroke-width="25"
                        striped
                        striped-flow
                    />
                    <div class="progress-info">
                        <el-icon class="rotating"><loading /></el-icon>
                        <span>{{ progressText }}</span>
                        <el-tag :type="getStepTagType()" size="large">{{ getStepName() }}</el-tag>
                    </div>
                </div>
                
                <!-- 检测结果 -->
                <div v-if="result" class="result-display">
                    <el-divider content-position="left">
                        <h2><el-icon><circle-check-filled /></el-icon> 检测结果报告</h2>
                    </el-divider>
                    
                    <!-- A. 风险结论卡片 -->
                    <div class="risk-conclusion-card">
                        <el-row :gutter="30">
                            <!-- 左侧：仪表盘和风险等级 -->
                            <el-col :span="8">
                                <div class="gauge-container">
                                    <!-- 仪表盘 -->
                                    <div class="gauge-wrapper">
                                        <svg class="gauge" viewBox="0 0 200 200">
                                            <!-- 背景圆环 -->
                                            <circle cx="100" cy="100" r="85" fill="none" stroke="#e5e7eb" stroke-width="16"/>
                                            <!-- 进度圆环 -->
                                            <circle 
                                                cx="100" 
                                                cy="100" 
                                                r="85" 
                                                fill="none" 
                                                :stroke="gaugeColor" 
                                                stroke-width="16"
                                                :stroke-dasharray="`${(result.risk_score || result.final_score || 0) * 534} 534`"
                                                stroke-linecap="round"
                                                transform="rotate(-90 100 100)"
                                                class="gauge-progress"
                                            />
                                            <!-- 中心文字 -->
                                            <text x="100" y="85" text-anchor="middle" class="gauge-value">
                                                {{ ((result.risk_score || result.final_score || 0) * 100).toFixed(1) }}%
                                            </text>
                                            <text x="100" y="115" text-anchor="middle" class="gauge-label">综合风险</text>
                                        </svg>
                                    </div>
                                    
                                    <!-- 风险等级徽章 -->
                                    <div :class="['risk-badge-large', riskClass]">
                                        <div class="badge-icon">
                                            <el-icon v-if="riskClass === 'risk-trustworthy'" size="32"><circle-check-filled /></el-icon>
                                            <el-icon v-else-if="riskClass === 'risk-suspicious'" size="32"><warning-filled /></el-icon>
                                            <el-icon v-else size="32"><circle-close-filled /></el-icon>
                                        </div>
                                        <div class="badge-text">{{ result.risk_level }}</div>
                                    </div>
                                    
                                    <!-- AI生成概率 -->
                                    <div class="ai-probability-box">
                                        <div class="prob-label">AI生成概率</div>
                                        <div class="prob-value" :style="{ color: gaugeColor }">
                                            {{ ((result.ai_probability || result.deepfake_analysis?.avg_score || 0) * 100).toFixed(2) }}%
                                        </div>
                                        <el-progress 
                                            :percentage="parseFloat(((result.ai_probability || result.deepfake_analysis?.avg_score || 0) * 100).toFixed(2))" 
                                            :color="gaugeColor"
                                            :show-text="false"
                                            :stroke-width="8"
                                        />
                                    </div>
                                </div>
                            </el-col>
                            
                            <!-- 右侧：检测信息概览 -->
                            <el-col :span="16">
                                <div class="detection-overview">
                                    <div class="overview-title">
                                        <el-icon size="24"><info-filled /></el-icon>
                                        <span>检测概览</span>
                                    </div>
                                    <div class="overview-grid">
                                        <div class="grid-item">
                                            <div class="item-label">检测模态</div>
                                            <el-tag size="large" effect="dark" type="primary">
                                                {{ getContentTypeName(result.content_type) }}
                                            </el-tag>
                                        </div>
                                        <div class="grid-item">
                                            <div class="item-label">检测模式</div>
                                            <el-tag size="large" effect="dark" :type="detectMode === 'center' ? 'success' : 'warning'">
                                                {{ detectMode === 'center' ? '中心完整' : '边缘初筛' }}
                                            </el-tag>
                                        </div>
                                        <div class="grid-item">
                                            <div class="item-label">检测时间</div>
                                            <div class="item-value">{{ formatDateTime(result.detected_at || new Date()) }}</div>
                                        </div>
                                        <div class="grid-item">
                                            <div class="item-label">文件名</div>
                                            <div class="item-value file-name">{{ currentFile?.name || '未知' }}</div>
                                        </div>
                                    </div>
                                </div>
                            </el-col>
                        </el-row>
                    </div>
                    
                    <!-- B. 多证据详情 -->
                    <div class="evidence-section">
                        <h3><el-icon><magnet /></el-icon> 多通道证据链分析</h3>
                        <p class="section-desc">基于多维度特征融合的AI生成内容检测</p>
                        
                        <el-row :gutter="20">
                            <!-- 模型分数 Sm -->
                            <el-col :xs="24" :sm="12" :md="8">
                                <div class="evidence-card evidence-primary">
                                    <div class="card-header-evidence">
                                        <el-icon size="28"><cpu /></el-icon>
                                        <span>深度学习模型</span>
                                        <el-tag type="danger" size="small">权重 80%</el-tag>
                                    </div>
                                    <div class="evidence-value">
                                        {{ ((result.ai_probability || result.deepfake_analysis?.avg_score || 0) * 100).toFixed(2) }}%
                                    </div>
                                    <div class="evidence-label">AI生成概率 (Sm)</div>
                                    <el-progress 
                                        :percentage="parseFloat(((result.ai_probability || result.deepfake_analysis?.avg_score || 0) * 100).toFixed(2))" 
                                        :color="getEvidenceColor(result.ai_probability || result.deepfake_analysis?.avg_score)"
                                        :stroke-width="10"
                                    />
                                </div>
                            </el-col>
                            
                            <!-- 噪声特征 Sn -->
                            <el-col :xs="24" :sm="12" :md="8">
                                <div class="evidence-card evidence-warning">
                                    <div class="card-header-evidence">
                                        <el-icon size="28"><trend-charts /></el-icon>
                                        <span>噪声分析</span>
                                        <el-tag type="warning" size="small">权重 8%</el-tag>
                                    </div>
                                    <div class="evidence-value">
                                        {{ (result.frequency_analysis?.avg_noise_score || 0).toFixed(4) }}
                                    </div>
                                    <div class="evidence-label">噪声异常分数 (Sn)</div>
                                    <el-progress 
                                        :percentage="parseFloat((Math.min(result.frequency_analysis?.avg_noise_score || 0, 1) * 100).toFixed(2))" 
                                        :color="getEvidenceColor(result.frequency_analysis?.avg_noise_score)"
                                        :stroke-width="10"
                                    />
                                </div>
                            </el-col>
                            
                            <!-- 频域特征 Sf -->
                            <el-col :xs="24" :sm="12" :md="8">
                                <div class="evidence-card evidence-info">
                                    <div class="card-header-evidence">
                                        <el-icon size="28"><odometer /></el-icon>
                                        <span>频域分析</span>
                                        <el-tag type="info" size="small">权重 3%</el-tag>
                                    </div>
                                    <div class="evidence-value">
                                        {{ (result.frequency_analysis?.high_freq_anomaly || 0).toFixed(4) }}
                                    </div>
                                    <div class="evidence-label">高频异常指数 (Sf)</div>
                                    <el-progress 
                                        :percentage="parseFloat((Math.min(result.frequency_analysis?.high_freq_anomaly || 0, 1) * 100).toFixed(2))" 
                                        :color="getEvidenceColor(result.frequency_analysis?.high_freq_anomaly)"
                                        :stroke-width="10"
                                    />
                                </div>
                            </el-col>
                            
                            <!-- 时序特征 St -->
                            <el-col :xs="24" :sm="12" :md="8">
                                <div class="evidence-card evidence-success">
                                    <div class="card-header-evidence">
                                        <el-icon size="28"><connection /></el-icon>
                                        <span>时序分析</span>
                                        <el-tag type="success" size="small">权重 5%</el-tag>
                                    </div>
                                    <div class="evidence-value">
                                        {{ (result.deepfake_analysis?.score_variance || 0).toFixed(4) }}
                                    </div>
                                    <div class="evidence-label">时序一致性方差 (St)</div>
                                    <el-progress 
                                        :percentage="parseFloat((Math.min(result.deepfake_analysis?.score_variance || 0, 1) * 100).toFixed(2))" 
                                        :color="getEvidenceColor(result.deepfake_analysis?.score_variance)"
                                        :stroke-width="10"
                                    />
                                </div>
                            </el-col>
                            
                            <!-- 指纹匹配 Sh -->
                            <el-col :xs="24" :sm="12" :md="8">
                                <div class="evidence-card evidence-purple">
                                    <div class="card-header-evidence">
                                        <el-icon size="28"><key /></el-icon>
                                        <span>内容指纹</span>
                                        <el-tag type="primary" size="small">权重 2%</el-tag>
                                    </div>
                                    <div class="evidence-value">
                                        {{ result.fingerprint_match ? '已匹配' : '未匹配' }}
                                    </div>
                                    <div class="evidence-label">指纹库匹配状态 (Sh)</div>
                                    <el-tag 
                                        :type="result.fingerprint_match ? 'success' : 'info'" 
                                        effect="dark" 
                                        size="large"
                                        style="width: 100%; margin-top: 10px;"
                                    >
                                        {{ result.fingerprint_match ? '✓ 发现相似内容' : '✗ 无历史记录' }}
                                    </el-tag>
                                </div>
                            </el-col>
                            
                            <!-- 证书状态 Sc -->
                            <el-col :xs="24" :sm="12" :md="8">
                                <div class="evidence-card evidence-gold">
                                    <div class="card-header-evidence">
                                        <el-icon size="28"><stamp /></el-icon>
                                        <span>可信证书</span>
                                        <el-tag type="success" size="small">权重 2%</el-tag>
                                    </div>
                                    <div class="evidence-value">
                                        {{ result.certificate ? '已签发' : '未签发' }}
                                    </div>
                                    <div class="evidence-label">国密证书状态 (Sc)</div>
                                    <el-tag 
                                        :type="result.certificate ? 'success' : 'info'" 
                                        effect="dark" 
                                        size="large"
                                        style="width: 100%; margin-top: 10px;"
                                    >
                                        {{ result.certificate ? '✓ SM2签名有效' : '— 未生成证书' }}
                                    </el-tag>
                                </div>
                            </el-col>
                        </el-row>
                        
                        <!-- 融合决策公式说明 -->
                        <div class="fusion-formula">
                            <el-alert
                                title="融合决策算法"
                                type="info"
                                :closable="false"
                                show-icon
                            >
                                <template #default>
                                    <code>S(x) = 0.80×Sm + 0.08×Sn + 0.05×St + 0.03×Sf + 0.02×Sh + 0.02×Sc</code>
                                    <br>
                                    <small>其中 S(x) 为综合风险评分，Sm~Sc 为各维度特征分数</small>
                                </template>
                            </el-alert>
                        </div>
                    </div>
                    
                    <!-- C. 内容指纹 -->
                    <div class="fingerprint-section">
                        <h3><el-icon><key /></el-icon> 内容指纹与哈希</h3>
                        <p class="section-desc">基于SM3国密算法和多种指纹技术的内容标识</p>
                        
                        <el-row :gutter="20">
                            <el-col :span="24">
                                <div class="hash-card">
                                    <div class="hash-header">
                                        <el-icon size="24"><lock /></el-icon>
                                        <span>SM3 内容哈希（国密标准）</span>
                                    </div>
                                    <el-input
                                        :value="result.sm3_hash || '暂无哈希数据'"
                                        readonly
                                        type="textarea"
                                        :rows="2"
                                        class="hash-input"
                                    >
                                        <template #suffix>
                                            <el-button 
                                                type="primary" 
                                                link 
                                                @click="copyToClipboard(result.sm3_hash)"
                                                :icon="CopyDocument"
                                            >
                                                复制
                                            </el-button>
                                        </template>
                                    </el-input>
                                </div>
                            </el-col>
                        </el-row>
                        
                        <el-row :gutter="20" style="margin-top: 15px;">
                            <!-- pHash (图片) -->
                            <el-col :span="12" v-if="result.content_type === 'image'">
                                <div class="hash-card">
                                    <div class="hash-header">
                                        <el-icon size="20"><picture /></el-icon>
                                        <span>pHash 感知哈希</span>
                                    </div>
                                    <el-input
                                        :value="result.phash || '暂无pHash数据'"
                                        readonly
                                        class="hash-input"
                                    >
                                        <template #suffix>
                                            <el-button 
                                                type="primary" 
                                                link 
                                                @click="copyToClipboard(result.phash)"
                                                :icon="CopyDocument"
                                            >
                                                复制
                                            </el-button>
                                        </template>
                                    </el-input>
                                </div>
                            </el-col>
                            
                            <!-- SimHash (文本) -->
                            <el-col :span="12" v-if="result.content_type === 'text'">
                                <div class="hash-card">
                                    <div class="hash-header">
                                        <el-icon size="20"><document /></el-icon>
                                        <span>SimHash 文本指纹</span>
                                    </div>
                                    <el-input
                                        :value="result.simhash || '暂无SimHash数据'"
                                        readonly
                                        class="hash-input"
                                    >
                                        <template #suffix>
                                            <el-button 
                                                type="primary" 
                                                link 
                                                @click="copyToClipboard(result.simhash)"
                                                :icon="CopyDocument"
                                            >
                                                复制
                                            </el-button>
                                        </template>
                                    </el-input>
                                </div>
                            </el-col>
                            
                            <!-- Merkle Root (视频) -->
                            <el-col :span="12" v-if="result.content_type === 'video'">
                                <div class="hash-card">
                                    <div class="hash-header">
                                        <el-icon size="20"><film /></el-icon>
                                        <span>Merkle Tree 根哈希</span>
                                    </div>
                                    <el-input
                                        :value="result.merkle_root || '暂无Merkle Root数据'"
                                        readonly
                                        class="hash-input"
                                    >
                                        <template #suffix>
                                            <el-button 
                                                type="primary" 
                                                link 
                                                @click="copyToClipboard(result.merkle_root)"
                                                :icon="CopyDocument"
                                            >
                                                复制
                                            </el-button>
                                        </template>
                                    </el-input>
                                </div>
                            </el-col>
                            
                            <!-- 文件元数据 -->
                            <el-col :span="12">
                                <div class="hash-card">
                                    <div class="hash-header">
                                        <el-icon size="20"><files /></el-icon>
                                        <span>文件元数据</span>
                                    </div>
                                    <div class="metadata-grid">
                                        <div class="meta-item">
                                            <span class="meta-label">文件大小:</span>
                                            <span class="meta-value">{{ formatFileSize(currentFile?.size) }}</span>
                                        </div>
                                        <div class="meta-item">
                                            <span class="meta-label">文件类型:</span>
                                            <span class="meta-value">{{ currentFile?.type || '未知' }}</span>
                                        </div>
                                    </div>
                                </div>
                            </el-col>
                        </el-row>
                    </div>
                    
                    <!-- D. 可信证书 -->
                    <div v-if="result.certificate" class="certificate-section">
                        <h3><el-icon><stamp /></el-icon> 国密数字证书</h3>
                        <p class="section-desc">基于SM2/SM3国密算法的可信存证</p>
                        
                        <div class="certificate-detail-card">
                            <el-row :gutter="30">
                                <el-col :span="16">
                                    <el-descriptions :column="2" border>
                                        <el-descriptions-item label="证书编号">
                                            <code class="cert-code">{{ result.certificate.certificate_id }}</code>
                                            <el-button 
                                                type="primary" 
                                                link 
                                                size="small"
                                                @click="copyToClipboard(result.certificate.certificate_id)"
                                                style="margin-left: 8px;"
                                            >
                                                <el-icon><CopyDocument /></el-icon>
                                            </el-button>
                                        </el-descriptions-item>
                                        <el-descriptions-item label="签发时间">
                                            {{ formatDateTime(result.certificate.issued_at) }}
                                        </el-descriptions-item>
                                        <el-descriptions-item label="签名算法">
                                            <el-tag type="success" effect="dark">SM2 with SM3</el-tag>
                                        </el-descriptions-item>
                                        <el-descriptions-item label="验签状态">
                                            <el-tag type="success" effect="dark">
                                                <el-icon><circle-check-filled /></el-icon>
                                                签名有效
                                            </el-tag>
                                        </el-descriptions-item>
                                        <el-descriptions-item label="内容哈希" :span="2">
                                            <code class="hash-code">{{ result.certificate.content_hash || result.sm3_hash }}</code>
                                        </el-descriptions-item>
                                        <el-descriptions-item label="SM2签名" :span="2">
                                            <div class="signature-block">
                                                <code>{{ result.certificate.sm2_signature || '暂无签名数据' }}</code>
                                                <el-button 
                                                    type="primary" 
                                                    link 
                                                    size="small"
                                                    @click="copyToClipboard(result.certificate.sm2_signature)"
                                                >
                                                    <el-icon><CopyDocument /></el-icon>
                                                    复制签名
                                                </el-button>
                                            </div>
                                        </el-descriptions-item>
                                    </el-descriptions>
                                </el-col>
                                
                                <el-col :span="8">
                                    <div class="certificate-actions">
                                        <el-button 
                                            type="success" 
                                            size="large" 
                                            @click="downloadCertificate"
                                            :icon="Download"
                                            style="width: 100%;"
                                        >
                                            下载证书
                                        </el-button>
                                    </div>
                                </el-col>
                            </el-row>
                        </div>
                    </div>
                    
                    <!-- 操作按钮 -->
                    <div class="result-actions">
                        <el-button type="primary" size="large" @click="downloadReport">
                            <el-icon><download /></el-icon>
                            下载报告
                        </el-button>
                        <el-button size="large" @click="reset">
                            <el-icon><refresh /></el-icon>
                            重新检测
                        </el-button>
                    </div>
                </div>
            </el-card>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { detectContent } from '../api/detection'
import { 
    CircleCheckFilled, 
    WarningFilled, 
    CircleCloseFilled,
    InfoFilled,
    Magnet,
    Cpu,
    TrendCharts,
    Odometer,
    Connection,
    Stamp,
    Lock,
    Picture,
    Document,
    Film,
    Files,
    Key
} from '@element-plus/icons-vue'
import { CopyDocument, Download, Check } from '@element-plus/icons-vue'

const inputMode = ref('file') // 'file' 或 'text'
const textInputContent = ref('') // 文本输入内容
const detectMode = ref('center')
const contentType = ref('auto')
const generateCert = ref(true)
const useGPU = ref(true)
const uploading = ref(false)
const progress = ref(0)
const progressStatus = ref('')
const progressText = ref('')
const result = ref(null)
const currentFile = ref(null)
const currentStep = ref(0) // 当前步骤：0-5

// 计算是否可以开始检测
const canStartDetection = computed(() => {
    if (inputMode.value === 'file') {
        return !!currentFile.value
    } else {
        // 文本模式：至少需要5个字符
        const isValid = textInputContent.value.length >= 5
        console.log('文本输入状态:', {
            length: textInputContent.value.length,
            isValid,
            content: textInputContent.value.substring(0, 20)
        })
        return isValid
    }
})

const riskClass = computed(() => {
    if (!result.value) return ''
    const level = result.value.risk_level
    if (level === '可信') return 'risk-trustworthy'
    if (level === '可疑') return 'risk-suspicious'
    if (level === '伪造' || level === '不可信') return 'risk-fake'
    return ''
})

// 格式化文件大小
const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 获取内容类型名称
const getContentTypeName = (type) => {
    const names = {
        'video': '视频',
        'image': '图片',
        'text': '文本'
    }
    return names[type] || type
}

// 获取步骤名称
const getStepName = () => {
    const steps = ['内容上传', '预处理', '模型检测', '取证分析', '融合判定', '证书生成']
    return steps[currentStep.value] || '完成'
}

// 获取步骤标签类型
const getStepTagType = () => {
    const types = ['', 'info', 'warning', 'primary', 'danger', 'success']
    return types[currentStep.value] || 'success'
}

const beforeUpload = (file) => {
    const isVideo = file.type.startsWith('video/')
    const isImage = file.type.startsWith('image/')
    const isText = file.type === 'text/plain' || file.name.endsWith('.txt')
    const isWord = file.name.endsWith('.docx')
    const isPDF = file.name.endsWith('.pdf')
    
    if (!isVideo && !isImage && !isText && !isWord && !isPDF) {
        ElMessage.error('只能上传视频、图片、文本文档、Word或PDF文件！')
        return false
    }
    
    // 自动识别类型
    if (contentType.value === 'auto') {
        if (isVideo) contentType.value = 'video'
        else if (isImage) contentType.value = 'image'
        else if (isText || isWord || isPDF) contentType.value = 'text'  // 文档都归类为text
    }
    
    currentFile.value = file
    return true
}

const startDetection = async () => {
    // 根据输入模式进行不同的处理
    if (inputMode.value === 'file') {
        if (!currentFile.value) {
            ElMessage.warning('请先上传文件')
            return
        }
        await handleUpload({ file: currentFile.value })
    } else {
        // 文本输入模式
        if (!textInputContent.value.trim()) {
            ElMessage.warning('请输入要检测的文本内容')
            return
        }
        if (textInputContent.value.length < 5) {
            ElMessage.warning('文本内容过短，请至少输入5个字符')
            return
        }
        await handleTextDetection()
    }
}

const handleUpload = async ({ file }) => {
    uploading.value = true
    currentStep.value = 0
    progress.value = 5
    progressText.value = '正在上传文件...'
    
    try {
        // 确定文件类型
        let finalType = contentType.value
        if (finalType === 'auto') {
            if (file.type.startsWith('video/')) finalType = 'video'
            else if (file.type.startsWith('image/')) finalType = 'image'
            else if (file.type === 'text/plain' || file.name.endsWith('.txt') || 
                     file.name.endsWith('.docx') || file.name.endsWith('.pdf')) {
                finalType = 'text'  // 所有文档类型都作为text处理
            }
        }
        
        // 创建FormData
        const formData = new FormData()
        formData.append('file', file)
        
        // 第一步：上传文件
        currentStep.value = 0
        const { uploadContent } = await import('../api/detection')
        const uploadResponse = await uploadContent(formData, finalType)
        
        currentStep.value = 1
        progress.value = 15
        progressText.value = '文件上传成功，正在进行预处理...'
        
        // 第二步：创建检测任务（异步）
        const { createTask } = await import('../api/detection')
        const taskResponse = await createTask(
            uploadResponse.content_id, 
            detectMode.value === 'edge' ? 'edge_01' : 'center'
        )
        
        currentStep.value = 2
        progress.value = 30
        progressText.value = '任务已创建，AI模型检测中...'
        
        // 第三步：轮询任务状态
        const { getTaskStatus } = await import('../api/detection')
        const taskId = taskResponse.task_id
        
        let attempts = 0
        const maxAttempts = 60 // 最多等待 60 次（约 5 分钟）
        
        const pollInterval = setInterval(async () => {
            attempts++
            
            try {
                const statusResponse = await getTaskStatus(taskId)
                
                // 根据进度更新步骤
                const taskProgress = statusResponse.progress || 0
                
                if (taskProgress < 0.2) {
                    currentStep.value = 1 // 预处理
                } else if (taskProgress < 0.4) {
                    currentStep.value = 2 // 模型检测
                } else if (taskProgress < 0.6) {
                    currentStep.value = 3 // 取证分析
                } else if (taskProgress < 0.8) {
                    currentStep.value = 4 // 融合判定
                } else {
                    currentStep.value = 5 // 证书生成
                }
                
                progress.value = 30 + (taskProgress * 70) // 30-100%
                progressText.value = `检测中... ${Math.round(taskProgress * 100)}%`
                
                // 检查是否完成
                if (statusResponse.status === 'completed' || statusResponse.status === 'success') {
                    clearInterval(pollInterval)
                    currentStep.value = 6 // 全部完成
                    progress.value = 100
                    progressStatus.value = 'success'
                    progressText.value = '检测完成！'
                    
                    // 解析结果
                    setTimeout(() => {
                        result.value = statusResponse.result || statusResponse
                        uploading.value = false
                        ElMessage.success('检测完成！')
                    }, 500)
                } else if (statusResponse.status === 'failed' || statusResponse.status === 'error') {
                    clearInterval(pollInterval)
                    uploading.value = false
                    progressStatus.value = 'exception'
                    progressText.value = '检测失败'
                    ElMessage.error('检测失败：' + (statusResponse.error || '未知错误'))
                } else if (attempts >= maxAttempts) {
                    // 超时
                    clearInterval(pollInterval)
                    uploading.value = false
                    progressStatus.value = 'exception'
                    progressText.value = '检测超时'
                    ElMessage.warning('检测超时，请稍后查看任务列表')
                }
            } catch (error) {
                console.error('轮询失败:', error)
                if (attempts >= maxAttempts) {
                    clearInterval(pollInterval)
                    uploading.value = false
                    ElMessage.error('检测失败')
                }
            }
        }, 5000) // 每 5 秒轮询一次
        
    } catch (error) {
        uploading.value = false
        progressStatus.value = 'exception'
        progressText.value = '检测失败'
        ElMessage.error('检测失败：' + error.message)
    }
}

// 处理文本直接检测
const handleTextDetection = async () => {
    uploading.value = true
    currentStep.value = 0
    progress.value = 5
    progressText.value = '正在提交文本内容...'
    
    try {
        // 调用文本检测API
        const { detectText } = await import('../api/detection')
        
        currentStep.value = 2
        progress.value = 30
        progressText.value = 'AI模型检测中...'
        
        // 直接调用文本检测接口（同步返回结果）
        const result_data = await detectText(textInputContent.value)
        
        currentStep.value = 6
        progress.value = 100
        progressStatus.value = 'success'
        progressText.value = '检测完成！'
        
        setTimeout(() => {
            result.value = result_data
            uploading.value = false
            ElMessage.success('文本检测完成！')
        }, 500)
        
    } catch (error) {
        uploading.value = false
        progressStatus.value = 'exception'
        progressText.value = '检测失败'
        ElMessage.error('文本检测失败：' + error.message)
    }
}

const downloadReport = () => {
    if (!result.value) return
    
    const reportData = JSON.stringify(result.value, null, 2)
    const blob = new Blob([reportData], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `detection_report_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    
    ElMessage.success('报告已下载')
}

// 仪表盘颜色计算
const gaugeColor = computed(() => {
    if (!result.value) return '#409eff'
    const score = result.value.risk_score || result.value.final_score || 0
    if (score < 0.3) return '#67c23a' // 绿色 - 可信
    if (score < 0.6) return '#e6a23c' // 黄色 - 可疑
    return '#f56c6c' // 红色 - 高风险
})

// 证据卡片颜色
const getEvidenceColor = (value) => {
    if (!value && value !== 0) return '#909399'
    if (value < 0.3) return '#67c23a'
    if (value < 0.6) return '#e6a23c'
    return '#f56c6c'
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
    if (!dateStr) return '—'
    try {
        const date = new Date(dateStr)
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        })
    } catch (e) {
        return dateStr
    }
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

// 下载证书
const downloadCertificate = async () => {
    if (!result.value?.certificate) {
        ElMessage.warning('暂无证书可下载')
        return
    }
    
    try {
        const html2canvas = await import('html2canvas')
        const { jsPDF } = await import('jspdf')
        const cert = result.value.certificate
        
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
        const certId = cert.certificate_id || cert.cert_id || 'N/A'
        const contentId = cert.content_id || 'N/A'
        const riskLevel = cert.risk_level || 'N/A'
        const issuedAt = cert.issued_at || new Date().toISOString()
        const sm3Hash = cert.sm3_hash || cert.content_hash || 'N/A'
        const sm2Sig = cert.sm2_signature || 'N/A'
        
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
                            <td style="padding: 12px 15px; width: 130px; font-weight: 700; color: #475569; font-size: 14px; border-left: 4px solid #3b82f6;">证书编号</td>
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
                
                <!-- 内容哈希 -->
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">🔑</span>
                        <span>SM3 内容哈希</span>
                    </h3>
                    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 15px; border-radius: 6px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 11px; line-height: 1.8; color: #0c4a6e; border-left: 4px solid #0ea5e9; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">${sm3Hash}</div>
                </div>
                
                <!-- SM2签名 -->
                <div style="margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                    <h3 style="color: #1e40af; font-size: 18px; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #e0e7ff; display: flex; align-items: center;">
                        <span style="margin-right: 8px;">✍️</span>
                        <span>SM2 数字签名</span>
                    </h3>
                    <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); padding: 15px; border-radius: 6px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 9px; line-height: 1.6; max-height: 180px; overflow: hidden; color: #991b1b; border-left: 4px solid #ef4444; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">${sm2Sig}</div>
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


const reset = () => {
    result.value = null
    currentFile.value = null
    textInputContent.value = ''
    inputMode.value = 'file'
    progress.value = 0
    progressText.value = ''
    progressStatus.value = ''
    currentStep.value = 0
}
</script>

<style scoped>
.detection {
    padding: 30px 40px;
    background: #f5f7fa;
    min-height: calc(100vh - 60px);
}

.container {
    max-width: 1400px;
    margin: 0 auto;
}

/* ========== 步骤条卡片 ========== */
.steps-card {
    margin-bottom: 30px;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.steps-card :deep(.el-step__title) {
    font-size: 16px;
    font-weight: 600;
}

.steps-card :deep(.el-step__description) {
    font-size: 13px;
}

/* ========== 主内容区 ========== */
.main-content {
    margin-bottom: 30px;
}

.card-header h3 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 18px;
    color: #303133;
}

/* ========== 上传区域 ========== */
.upload-section {
    border-radius: 12px;
    height: 100%;
}

.upload-section :deep(.el-upload-dragger) {
    padding: 50px 30px;
    border-radius: 12px;
    transition: all 0.3s;
}

.upload-section :deep(.el-upload-dragger:hover) {
    border-color: #409eff;
    background: #ecf5ff;
}

.el-icon--upload {
    color: #409eff;
    margin-bottom: 16px;
}

.el-upload__text {
    color: #606266;
    font-size: 16px;
    line-height: 1.8;
}

.el-upload__text em {
    color: #409eff;
    font-style: normal;
    font-weight: 600;
}

.el-upload__tip {
    margin-top: 12px;
    color: #909399;
    font-size: 14px;
}

.file-info {
    margin-top: 20px;
    padding: 12px 16px;
    background: #f0f9ff;
    border-radius: 8px;
    border-left: 4px solid #409eff;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #303133;
}

.file-info .file-size {
    color: #909399;
    font-size: 13px;
}

/* ========== 文本输入区域 ========== */
.text-input-area {
    padding: 10px 0;
}

.text-stats {
    margin-top: 12px;
    padding: 8px 12px;
    background: #f5f7fa;
    border-radius: 6px;
    font-size: 14px;
    color: #606266;
    display: flex;
    align-items: center;
}

/* ========== 配置区域 ========== */
.config-section {
    border-radius: 12px;
    height: 100%;
}

.form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
}

/* ========== 进度与结果区域 ========== */
.progress-result-section {
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.progress-display {
    padding: 20px 0;
}

.progress-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 20px;
    padding: 16px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 8px;
    border: 2px solid #0ea5e9;
}

.progress-info .rotating {
    animation: rotate 1s linear infinite;
    font-size: 20px;
    color: #0ea5e9;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.progress-info span {
    font-size: 16px;
    color: #303133;
    font-weight: 500;
}

/* ========== 结果显示区 ========== */
.result-display {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.result-display h2 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    color: #303133;
}

.risk-overview {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 30px;
    padding: 30px;
    background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
    border-radius: 12px;
}

.risk-badge {
    padding: 16px 40px;
    border-radius: 40px;
    font-size: 28px;
    font-weight: bold;
    color: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

.risk-trustworthy {
    background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.risk-suspicious {
    background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%);
}

.risk-fake {
    background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
}

.score-circle {
    width: 180px;
    height: 180px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
}

.score-number {
    font-size: 42px;
    font-weight: bold;
    color: white;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

.score-label {
    font-size: 15px;
    color: rgba(255,255,255,0.9);
    margin-top: 8px;
}

.certificate-box {
    margin-top: 30px;
    padding: 24px;
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border-radius: 12px;
    border: 2px solid #f59e0b;
}

.certificate-box h3 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 16px 0;
    color: #92400e;
    font-size: 18px;
}

.certificate-box code {
    font-family: 'Courier New', monospace;
    font-size: 12px;
    background: rgba(255,255,255,0.6);
    padding: 2px 6px;
    border-radius: 4px;
}

.result-actions {
    text-align: center;
    margin-top: 30px;
    padding-top: 30px;
    border-top: 2px dashed #e5e7eb;
}

.result-actions .el-button {
    margin: 0 12px;
}

/* ========== A. 风险结论卡片样式 ========== */
.risk-conclusion-card {
    margin-bottom: 30px;
    padding: 30px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
}

.gauge-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
}

.gauge-wrapper {
    width: 200px;
    height: 200px;
}

.gauge {
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.15));
}

.gauge-progress {
    transition: stroke-dasharray 0.8s ease-in-out;
}

.gauge-value {
    font-size: 32px;
    font-weight: bold;
    fill: white;
}

.gauge-label {
    font-size: 14px;
    fill: rgba(255, 255, 255, 0.9);
}

.risk-badge-large {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 32px;
    border-radius: 50px;
    background: white;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    animation: pulse 2s ease-in-out infinite;
}

.risk-badge-large .badge-icon {
    display: flex;
    align-items: center;
    justify-content: center;
}

.risk-badge-large .badge-text {
    font-size: 24px;
    font-weight: bold;
}

.risk-badge-large.risk-trustworthy .badge-text {
    color: #67c23a;
}

.risk-badge-large.risk-suspicious .badge-text {
    color: #e6a23c;
}

.risk-badge-large.risk-fake .badge-text {
    color: #f56c6c;
}

.ai-probability-box {
    width: 100%;
    padding: 16px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    backdrop-filter: blur(10px);
}

.prob-label {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.9);
    margin-bottom: 8px;
}

.prob-value {
    font-size: 28px;
    font-weight: bold;
    color: white;
    margin-bottom: 12px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.detection-overview {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.overview-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
    font-weight: bold;
    color: #303133;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #e5e7eb;
}

.overview-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}

.grid-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.item-label {
    font-size: 13px;
    color: #909399;
}

.item-value {
    font-size: 15px;
    color: #303133;
    font-weight: 500;
}

.item-value.file-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ========== B. 多证据详情样式 ========== */
.evidence-section {
    margin: 30px 0;
    padding: 30px;
    background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
    border-radius: 16px;
    border: 2px solid #e5e7eb;
}

.evidence-section h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 8px 0;
    font-size: 20px;
    color: #303133;
}

.section-desc {
    margin: 0 0 24px 0;
    font-size: 14px;
    color: #909399;
}

.evidence-card {
    padding: 20px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    transition: all 0.3s;
    margin-bottom: 20px;
    border-left: 4px solid;
}

.evidence-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.evidence-primary { border-left-color: #409eff; }
.evidence-warning { border-left-color: #e6a23c; }
.evidence-info { border-left-color: #909399; }
.evidence-success { border-left-color: #67c23a; }
.evidence-purple { border-left-color: #9c27b0; }
.evidence-gold { border-left-color: #f59e0b; }

.card-header-evidence {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    font-size: 16px;
    font-weight: bold;
    color: #303133;
}

.evidence-value {
    font-size: 32px;
    font-weight: bold;
    color: #303133;
    margin-bottom: 8px;
}

.evidence-label {
    font-size: 13px;
    color: #909399;
    margin-bottom: 12px;
}

.fusion-formula {
    margin-top: 24px;
}

.fusion-formula code {
    font-family: 'Courier New', monospace;
    font-size: 14px;
    color: #409eff;
    font-weight: bold;
}

.fusion-formula small {
    color: #909399;
    font-size: 12px;
}

/* ========== C. 内容指纹样式 ========== */
.fingerprint-section {
    margin: 30px 0;
    padding: 30px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 16px;
    border: 2px solid #0ea5e9;
}

.fingerprint-section h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 8px 0;
    font-size: 20px;
    color: #303133;
}

.hash-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.hash-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    font-size: 16px;
    font-weight: bold;
    color: #303133;
}

.hash-input :deep(.el-textarea__inner) {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    background: #f5f7fa;
    border: 1px solid #dcdfe6;
}

.hash-input :deep(.el-input__inner) {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    background: #f5f7fa;
}

.metadata-grid {
    display: grid;
    gap: 12px;
}

.meta-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
}

.meta-label {
    font-size: 13px;
    color: #909399;
}

.meta-value {
    font-size: 14px;
    color: #303133;
    font-weight: 500;
}

/* ========== D. 可信证书样式 ========== */
.certificate-section {
    margin: 30px 0;
    padding: 30px;
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border-radius: 16px;
    border: 2px solid #f59e0b;
}

.certificate-section h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 8px 0;
    font-size: 20px;
    color: #92400e;
}

.certificate-detail-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.cert-code {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    background: #f5f7fa;
    padding: 4px 8px;
    border-radius: 4px;
    color: #409eff;
}

.hash-code {
    font-family: 'Courier New', monospace;
    font-size: 12px;
    word-break: break-all;
}

.signature-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.signature-block code {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    word-break: break-all;
    background: #f5f7fa;
    padding: 8px;
    border-radius: 4px;
}

.certificate-actions {
    display: flex;
    flex-direction: column;
    gap: 16px;
    align-items: center;
}

.certificate-actions .el-button {
    width: 100%;
}

.qr-code-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 20px;
    background: #f5f7fa;
    border-radius: 12px;
    border: 2px dashed #dcdfe6;
}

.qr-code-placeholder p {
    margin: 0;
    font-size: 14px;
    color: #909399;
}

/* ========== 响应式设计 ========== */
@media (max-width: 1200px) {
    .main-content .el-col {
        margin-bottom: 20px;
    }
}

@media (max-width: 768px) {
    .detection {
        padding: 20px;
    }
    
    .risk-overview {
        padding: 20px;
    }
    
    .score-circle {
        width: 150px;
        height: 150px;
    }
    
    .score-number {
        font-size: 36px;
    }
}
</style>
