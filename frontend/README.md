# AIGC-Trust 前端

基于 Vue 3 + Element Plus 的现代化前端界面

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Element Plus** - 基于 Vue 3 的组件库
- **Vue Router** - 官方路由管理器
- **Axios** - HTTP 客户端
- **ECharts** - 数据可视化图表库

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口
│   │   └── detection.js
│   ├── components/       # 公共组件
│   │   └── Header.vue
│   ├── router/          # 路由配置
│   │   └── index.js
│   ├── utils/           # 工具函数
│   │   └── request.js
│   ├── views/           # 页面组件
│   │   ├── Home.vue
│   │   ├── Detection.vue
│   │   ├── Tasks.vue
│   │   └── Certificates.vue
│   ├── App.vue          # 根组件
│   └── main.js          # 入口文件
├── index.html           # HTML 模板
├── package.json         # 依赖配置
└── vite.config.js       # Vite 配置
```

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录

### 4. 预览生产构建

```bash
npm run preview
```

## 功能特性

### 1. 首页 (Home)
- 平台介绍和特色功能展示
- 实时统计数据展示
- 快速入口导航

### 2. 内容检测 (Detection)
- 支持视频和图片上传
- 中心平台和边缘模式切换
- GPU加速选项
- 实时检测进度显示
- 可视化检测结果
  - 风险等级徽章
  - 仪表盘评分展示
  - 详细指标分析
  - 国密证书信息
- 检测报告下载

### 3. 任务管理 (Tasks)
- 检测任务列表
- 任务状态追踪
- 进度实时监控
- 任务详情查看

### 4. 证书查询 (Certificates)
- 证书搜索功能
- 证书列表展示
- 风险等级标识
- 证书详情查看

## API 代理配置

开发环境下，前端通过 Vite 代理转发 API 请求到后端服务：

```javascript
// vite.config.js
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  }
}
```

确保后端服务在 8000 端口运行。

## 响应式设计

前端采用响应式布局，支持：
- 桌面端（≥1200px）
- 平板端（768px - 1199px）
- 移动端（<768px）

## 主题定制

使用渐变色主题：
- 主色：#667eea → #764ba2
- 成功：#67c23a
- 警告：#e6a23c
- 危险：#f56c6c

## 浏览器兼容性

- Chrome ≥ 87
- Firefox ≥ 78
- Safari ≥ 14
- Edge ≥ 88

## 部署建议

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name aigc-trust.example.com;
    
    root /var/www/aigc-trust/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 开发注意事项

1. **跨域问题**：开发环境已通过 Vite 代理解决
2. **大文件上传**：视频文件可能较大，已设置 5 分钟超时
3. **进度反馈**：上传和检测过程提供实时进度提示
4. **错误处理**：统一的错误提示机制

## 后续优化方向

1. 添加用户认证和权限管理
2. 实现 WebSocket 实时推送检测结果
3. 增加更多数据可视化图表
4. 添加国际化支持
5. 性能优化（代码分割、懒加载等）
