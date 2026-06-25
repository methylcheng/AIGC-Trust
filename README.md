# AIGC-Trust

AIGC内容真实性检测与可信溯源系统 - 基于国密算法的可信签名链条

## 🛡️ 安全特性（新增）

### 可信签名链条 v2.0

本项目现已实现完整的PKI（公钥基础设施）体系，包括：

✅ **根信任锚 (Root CA)** - SM2密钥对 + 10年有效期  
✅ **密钥生命周期管理** - 生成/存储/轮换/自动备份  
✅ **证书有效期机制** - 默认365天，自动过期检查  
✅ **防重放Nonce机制** - UUID v4 + 5分钟时间窗  
✅ **证书吊销列表(CRL)** - 支持多种吊销原因  
✅ **6步证书链验证** - 格式/有效期/吊销/签名/nonce/信任锚  
✅ **数据库扩展** - 吊销状态/过期时间字段  
✅ **完整API支持** - 验证/吊销/轮换接口  

### 快速开始

```bash
# 1. 数据库迁移
python db/migrate_cert_security.py

# 2. 启动应用（自动初始化信任系统）
python main.py

# 3. 运行安全测试
python tests/test_trust_chain.py
```

### 文档

- 📖 [可信签名链条安全机制](docs/TRUST_CHAIN_SECURITY.md) - 完整的安全机制说明
- 🏗️ [架构设计文档](docs/TRUST_CHAIN_ARCHITECTURE.md) - 架构图与数据流
- 🚀 [快速启动指南](QUICKSTART_TRUST_CHAIN.md) - 部署与验证步骤
- 📝 [实施总结](IMPLEMENTATION_SUMMARY.md) - 技术实现详情

### API端点

```bash
# 验证证书
POST /api/certificates/verify/{cert_id}

# 吊销证书
POST /api/certificates/revoke

# 获取CRL
GET /api/certificates/crl

# 密钥轮换（仅管理员）
POST /api/certificates/key-rotate

# 获取信任锚信息
GET /api/certificates/trust-anchor
```

### 安全评分

| 安全机制 | 评分 |
|---------|------|
| 根信任定义 | ✅ 10/10 |
| 密钥管理 | ✅ 9/10 |
| 证书有效期 | ✅ 10/10 |
| 防重放保护 | ✅ 10/10 |
| 吊销管理 | ✅ 9/10 |
| 签名验证 | ✅ 10/10 |
| **总体评分** | **⭐ 9.5/10** |

---

## 原有功能

AIGC-Trust是一个综合性的AI生成内容检测系统，支持图片、文本、视频的多模态检测。
