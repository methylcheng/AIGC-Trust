import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import json
from pydantic import BaseModel
from db.db_conn import get_db_session
from db.models import Cert, Content
from api.auth import get_current_user
from crypto.trust_chain import get_chain_verifier, get_crl, get_trust_anchor
from audit.audit_log import log_verification
from audit.security_alert import check_and_alert_verify_failure
from datetime import datetime
router = APIRouter()

# 请求模型定义
class BatchDeleteRequest(BaseModel):
    cert_ids: List[str]

class CertificateVerifyRequest(BaseModel):
    """证书验证请求"""
    certificate_id: str
    
class CertificateRevokeRequest(BaseModel):
    """证书吊销请求"""
    cert_id: str
    reason: str

# 获取所有证书列表（新增）
@router.get("")
async def get_all_certs(
    risk_level: Optional[str] = Query(None, description="风险等级筛选"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的证书列表"""
    try:
        db = get_db_session()
        
        # 构建查询 - 只查询当前用户的证书
        query = db.query(Cert).filter(Cert.user_id == current_user["user_id"])
        
        # 风险等级筛选
        if risk_level:
            query = query.filter(Cert.risk_level == risk_level)
        
        # 按签发时间倒序
        certs = query.order_by(Cert.issued_at.desc())\
                     .offset(offset)\
                     .limit(limit)\
                     .all()
        
        # 转换为字典列表
        cert_list = []
        for cert in certs:
            # 获取关联的内容信息
            content = db.query(Content).filter(Content.content_id == cert.content_id).first()
            content_type = content.type if content else "unknown"
            
            # 解析签名字段（数据库中存储的是SM2签名字符串）
            signature_data = None
            if cert.signature:
                try:
                    # 尝试解析为JSON对象
                    signature_data = json.loads(cert.signature)
                except:
                    # 如果不是JSON，则是SM2签名字符串，构建签名对象
                    signature_data = {
                        "certificate_id": cert.cert_id,
                        "content_id": cert.content_id,
                        "content_type": content_type,
                        "risk_level": cert.risk_level,
                        "detection_score": 0.0,  # 需要从检测结果中获取
                        "fingerprint": "",  # 需要从指纹表中获取
                        "sm2_signature": cert.signature  # SM2签名字符串
                    }
            
            # 执行证书链验证
            verify_status = "issued"  # 默认状态
            verification_details = None
            if signature_data:
                try:
                    verifier = get_chain_verifier()
                    verify_result = verifier.verify_certificate_chain(signature_data)
                    
                    # 调试日志
                    print(f"证书 {cert.cert_id} 验签结果: verified={verify_result['verified']}")
                    print(f"  checks: {verify_result.get('checks', {})}")
                    print(f"  errors: {verify_result.get('errors', [])}")
                    print(f"  warnings: {verify_result.get('warnings', [])}")
                    
                    if verify_result["verified"]:
                        verify_status = "verified"
                    elif verify_result["errors"]:
                        verify_status = "invalid"
                    else:
                        verify_status = "pending"
                    
                    verification_details = verify_result
                except Exception as e:
                    print(f"证书验证失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    verify_status = "error"
            
            # 检查数据库中的吊销状态
            if cert.is_revoked == 1:
                verify_status = "revoked"
            
            cert_list.append({
                "cert_id": cert.cert_id,
                "content_id": cert.content_id,
                "content_type": content_type,
                "risk_level": cert.risk_level,
                "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
                "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,  # 新增
                "is_revoked": cert.is_revoked == 1,  # 新增
                "signature": signature_data,
                "verify_status": verify_status,  # 动态验签状态
                "verification_details": verification_details,  # 详细验证信息
                "node_id": "center"  # 默认节点：中心节点
            })
        
        db.close()
        
        return {
            "total": len(cert_list),
            "certificates": cert_list
        }
        
    except Exception as e:
        print("获取证书列表失败:", str(e))
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

# 搜索证书（新增）
@router.get("/search/{keyword}")
async def search_certs(keyword: str, current_user: dict = Depends(get_current_user)):
    """根据证书ID或内容哈希搜索证书（仅当前用户）"""
    try:
        db = get_db_session()
        
        # 模糊搜索 - 只搜索当前用户的证书
        certs = db.query(Cert).filter(
            ((Cert.cert_id.like(f"%{keyword}%")) |
             (Cert.content_id.like(f"%{keyword}%"))) &
            (Cert.user_id == current_user["user_id"])
        ).all()
        
        cert_list = []
        for cert in certs:
            # 获取关联的内容信息
            content = db.query(Content).filter(Content.content_id == cert.content_id).first()
            content_type = content.type if content else "unknown"
            
            # 解析签名字段（数据库中存储的是SM2签名字符串）
            signature_data = None
            if cert.signature:
                try:
                    # 尝试解析为JSON对象
                    signature_data = json.loads(cert.signature)
                except:
                    # 如果不是JSON，则是SM2签名字符串，构建签名对象
                    signature_data = {
                        "certificate_id": cert.cert_id,
                        "content_id": cert.content_id,
                        "content_type": content_type,
                        "risk_level": cert.risk_level,
                        "detection_score": 0.0,
                        "fingerprint": "",
                        "sm2_signature": cert.signature
                    }
            
            cert_list.append({
                "cert_id": cert.cert_id,
                "content_id": cert.content_id,
                "content_type": content_type,
                "risk_level": cert.risk_level,
                "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
                "signature": signature_data,
                "verify_status": "issued",  # 默认状态：已签发
                "node_id": "center"  # 默认节点：中心节点
            })
        
        db.close()
        return {"certificates": cert_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# 3. 删除单个证书
@router.delete("/{cert_id}")
async def delete_cert(cert_id: str, current_user: dict = Depends(get_current_user)):
    """删除当前用户的单个证书"""
    try:
        db = get_db_session()
        
        # 检查证书是否存在且属于当前用户
        cert = db.query(Cert).filter(
            Cert.cert_id == cert_id,
            Cert.user_id == current_user["user_id"]
        ).first()
        if not cert:
            db.close()
            raise HTTPException(status_code=404, detail=f"证书不存在或无权删除: {cert_id}")
        
        # 删除证书
        db.delete(cert)
        db.commit()
        db.close()
        
        return {
            "success": True,
            "message": f"证书 {cert_id} 已删除",
            "cert_id": cert_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"删除证书失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"删除证书失败: {str(e)}")

# 4. 批量删除证书
@router.post("/batch-delete")
async def batch_delete_certs(request: BatchDeleteRequest, current_user: dict = Depends(get_current_user)):
    """批量删除当前用户的证书"""
    try:
        if not request.cert_ids:
            raise HTTPException(status_code=400, detail="证书ID列表不能为空")
        
        db = get_db_session()
        
        # 查询存在的证书，且必须属于当前用户
        certs = db.query(Cert).filter(
            Cert.cert_id.in_(request.cert_ids),
            Cert.user_id == current_user["user_id"]
        ).all()
        
        deleted_count = len(certs)
        
        if deleted_count == 0:
            db.close()
            raise HTTPException(status_code=404, detail="未找到要删除的证书或无权删除")
        
        # 批量删除
        for cert in certs:
            db.delete(cert)
        
        db.commit()
        db.close()
        
        return {
            "success": True,
            "message": f"成功删除 {deleted_count} 个证书",
            "deleted_count": deleted_count,
            "cert_ids": [cert.cert_id for cert in certs]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"批量删除证书失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"批量删除证书失败: {str(e)}")


# 5. 验证单个证书（新增）
@router.post("/verify/{cert_id}")
async def verify_certificate(cert_id: str, current_user: dict = Depends(get_current_user)):
    """
    验证证书完整性和有效性
    
    验证步骤:
    1. 检查证书格式
    2. 验证有效期
    3. 检查吊销状态
    4. 验证SM2签名
    5. 验证防重放nonce
    6. 验证信任链
    """
    try:
        db = get_db_session()
        
        # 查询证书
        cert = db.query(Cert).filter(
            Cert.cert_id == cert_id,
            Cert.user_id == current_user["user_id"]
        ).first()
        
        if not cert:
            db.close()
            raise HTTPException(status_code=404, detail="证书不存在或无权访问")
        
        # 获取内容信息
        content = db.query(Content).filter(Content.content_id == cert.content_id).first()
        content_type = content.type if content else "unknown"
        
        # 解析签名数据
        signature_data = None
        if cert.signature:
            try:
                signature_data = json.loads(cert.signature)
            except:
                signature_data = {
                    "certificate_id": cert.cert_id,
                    "content_id": cert.content_id,
                    "content_type": content_type,
                    "risk_level": cert.risk_level,
                    "detection_score": 0.0,
                    "fingerprint": "",
                    "sm2_signature": cert.signature
                }
        
        db.close()
        
        if not signature_data:
            raise HTTPException(status_code=400, detail="证书签名数据缺失")
        
        # 执行证书链验证
        verifier = get_chain_verifier()
        verify_result = verifier.verify_certificate_chain(signature_data)
        
        # 记录审计日志
        try:
            log_verification(
                cert_id=cert_id,
                result=verify_result["verified"],
                user_id=current_user["user_id"],
                details=verify_result
            )
        except Exception as e:
            print(f"[AUDIT] 记录验签日志失败: {str(e)}")
        
        # 检查并发送安全告警
        try:
            check_and_alert_verify_failure(
                cert_id=cert_id,
                user_id=current_user["user_id"],
                verify_result=verify_result
            )
        except Exception as e:
            print(f"[ALERT] 安全检查失败: {str(e)}")
        
        return {
            "success": True,
            "cert_id": cert_id,
            "verification_result": verify_result,
            "verified": verify_result["verified"],
            "checks": verify_result["checks"],
            "errors": verify_result["errors"],
            "warnings": verify_result["warnings"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"证书验证失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


# 6. 吊销证书（新增）
@router.post("/revoke")
async def revoke_certificate(request: CertificateRevokeRequest, current_user: dict = Depends(get_current_user)):
    """
    吊销指定证书
    
    吊销原因可选值:
    - key_compromise: 私钥泄露
    - certificate_hold: 暂时挂起
    - cessation_of_operation: 停止运营
    - unspecified: 未指定
    """
    try:
        db = get_db_session()
        
        # 检查证书是否存在且属于当前用户
        cert = db.query(Cert).filter(
            Cert.cert_id == request.cert_id,
            Cert.user_id == current_user["user_id"]
        ).first()
        
        if not cert:
            db.close()
            raise HTTPException(status_code=404, detail="证书不存在或无权吊销")
        
        # 检查是否已吊销
        crl = get_crl()
        if crl.is_revoked(request.cert_id):
            db.close()
            raise HTTPException(status_code=400, detail="证书已被吊销")
        
        # 执行吊销
        crl.revoke_certificate(
            request.cert_id,
            request.reason,
            current_user.get("username", "unknown")
        )
        
        # 同步更新数据库
        cert.is_revoked = 1
        cert.revocation_reason = request.reason
        cert.revoked_at = datetime.now()
        db.commit()
        
        db.close()
        
        return {
            "success": True,
            "message": f"证书 {request.cert_id} 已吊销",
            "cert_id": request.cert_id,
            "revoked_at": datetime.now().isoformat(),
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"证书吊销失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"吊销失败: {str(e)}")


# 7. 获取CRL列表（新增）
@router.get("/crl")
async def get_certificate_revocation_list(current_user: dict = Depends(get_current_user)):
    """获取证书吊销列表"""
    try:
        crl = get_crl()
        return {
            "total_revoked": len(crl.revoked_certs),
            "revoked_certificates": list(crl.revoked_certs.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取CRL失败: {str(e)}")


# 8. 密钥轮换（新增，仅管理员）
@router.post("/key-rotate")
async def rotate_keys(reason: str = "scheduled", current_user: dict = Depends(get_current_user)):
    """
    执行密钥轮换（仅管理员可用）
    
    注意：此操作会影响所有新签发的证书
    """
    try:
        # 检查是否为管理员
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可执行密钥轮换")
        
        from crypto.trust_chain import get_key_manager
        key_manager = get_key_manager()
        result = key_manager.rotate_keys(reason)
        
        return {
            "success": True,
            "message": "密钥轮换成功",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"密钥轮换失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"密钥轮换失败: {str(e)}")


# 9. 获取信任锚信息（新增）
@router.get("/trust-anchor")
async def get_trust_anchor_info(current_user: dict = Depends(get_current_user)):
    """获取根信任锚配置信息（不含私钥）"""
    try:
        anchor = get_trust_anchor()
        config = anchor.root_ca_config.copy()
        
        # 移除敏感信息
        if "private_key" in config:
            del config["private_key"]
        
        return {
            "success": True,
            "trust_anchor": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信任锚信息失败: {str(e)}")


