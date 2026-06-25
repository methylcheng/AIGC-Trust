import request from '../utils/request'

// 通用内容检测（支持视频/图片/文本）
export function detectContent(formData, contentType, params = {}) {
    // 视频使用专用接口
    if (contentType === 'video') {
        return request({
            url: '/contents/video/detect',  // 修复：content -> contents
            method: 'post',
            data: formData,
            params,
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
    } else {
        // 图片和文本使用通用接口
        return request({
            url: '/contents',  // 修复：content -> contents
            method: 'post',
            params: { c_type: contentType },
            data: formData,
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        }).then(response => {
            // 上传后自动分析
            return analyzeContent(response.content_id)
        })
    }
}

// 上传文件（不立即检测，用于异步流程）
export function uploadContent(formData, contentType) {
    return request({
        url: '/contents',
        method: 'post',
        params: { c_type: contentType },
        data: formData,
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

// 上传图片
export function uploadImage(file, type) {
    const formData = new FormData()
    formData.append('file', file)
    return request({
        url: '/contents',  // 修复：content -> contents
        method: 'post',
        params: { c_type: type },
        data: formData,
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

// 分析已上传内容
export function analyzeContent(contentId, useDeepModel = true) {
    return request({
        url: `/contents/${contentId}/analyze`,  // 修复：content -> contents
        method: 'post',
        params: { use_deep_model: useDeepModel }
    })
}

// 文本直接检测（无需上传文件）
export function detectText(textContent) {
    return request({
        url: '/contents/text/detect',
        method: 'post',
        data: textContent,
        headers: {
            'Content-Type': 'text/plain'
        }
    })
}

// 创建检测任务
export function createTask(contentId, nodeId = 'local-01') {
    return request({
        url: '/tasks',
        method: 'post',
        params: { content_id: contentId, edge_node_id: nodeId }
    })
}

// 查询任务状态
export function getTaskStatus(taskId) {
    return request({
        url: `/tasks/${taskId}`,
        method: 'get'
    })
}

// 获取所有任务列表
export function getAllTasks(params = {}) {
    return request({
        url: '/tasks/list',
        method: 'get',
        params
    })
}

// 获取统计数据
export function getStatistics() {
    return request({
        url: '/stats/overview',
        method: 'get'
    })
}

// 获取所有证书列表
export function getAllCertificates(params = {}) {
    return request({
        url: '/certificates',
        method: 'get',
        params
    })
}

// 搜索证书
export function searchCertificates(keyword) {
    return request({
        url: `/certificates/search/${keyword}`,
        method: 'get'
    })
}

// ==================== 删除功能 API ====================

// 删除单个任务
export function deleteTask(taskId) {
    return request({
        url: `/tasks/${taskId}`,
        method: 'delete'
    })
}

// 批量删除任务
export function batchDeleteTasks(taskIds) {
    return request({
        url: '/tasks/batch-delete',
        method: 'post',
        data: { task_ids: taskIds }
    })
}

// 删除单个证书
export function deleteCertificate(certId) {
    return request({
        url: `/certificates/${certId}`,
        method: 'delete'
    })
}

// 批量删除证书
export function batchDeleteCertificates(certIds) {
    return request({
        url: '/certificates/batch-delete',
        method: 'post',
        data: { cert_ids: certIds }
    })
}

// 验证单个证书（在线签验）
export function verifyCertificate(certId) {
    return request({
        url: `/certificates/verify/${certId}`,
        method: 'post'
    })
}
