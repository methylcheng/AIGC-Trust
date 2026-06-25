"""
安全告警模块
用于检测并记录异常行为，如验签失败、重放攻击等
"""
import json
from datetime import datetime
from typing import Optional, Dict
from audit.audit_log import create_audit

# 告警级别
ALERT_LEVEL_CRITICAL = "CRITICAL"  # 严重
ALERT_LEVEL_HIGH = "HIGH"          # 高
ALERT_LEVEL_MEDIUM = "MEDIUM"      # 中
ALERT_LEVEL_LOW = "LOW"            # 低

# 告警类型
ALERT_TYPE_VERIFY_FAIL = "VERIFY_FAILURE"           # 验签失败
ALERT_TYPE_REPLAY_ATTACK = "REPLAY_ATTACK"          # 重放攻击
ALERT_TYPE_CERT_TAMPERED = "CERTIFICATE_TAMPERED"   # 证书篡改
ALERT_TYPE_KEY_COMPROMISE = "KEY_COMPROMISE"        # 密钥泄露
ALERT_TYPE_BRUTE_FORCE = "BRUTE_FORCE"              # 暴力破解

def send_alert(
    alert_type: str,
    level: str,
    message: str,
    user_id: str = None,
    cert_id: str = None,
    ip_address: str = None,
    details: Dict = None
):
    """
    发送安全告警
    
    Args:
        alert_type: 告警类型
        level: 告警级别
        message: 告警消息
        user_id: 用户ID（可选）
        cert_id: 证书ID（可选）
        ip_address: IP地址（可选）
        details: 详细信息（可选）
    """
    try:
        # 构建告警信息
        alert_info = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "level": level,
            "message": message,
            "user_id": user_id,
            "cert_id": cert_id,
            "ip_address": ip_address,
            "details": details or {}
        }
        
        # 记录到审计日志
        action = f"SECURITY_ALERT|type={alert_type}|level={level}|{message}"
        operator = f"user:{user_id}" if user_id else "system"
        create_audit(action, operator)
        
        # 打印告警（生产环境应发送到监控平台）
        print(f"\n{'='*60}")
        print(f"🚨 [安全告警] {level}")
        print(f"类型: {alert_type}")
        print(f"消息: {message}")
        if user_id:
            print(f"用户: {user_id}")
        if cert_id:
            print(f"证书: {cert_id}")
        if ip_address:
            print(f"IP: {ip_address}")
        if details:
            print(f"详情: {json.dumps(details, ensure_ascii=False)}")
        print(f"{'='*60}\n")
        
        # TODO: 在生产环境中，这里可以添加：
        # 1. 发送邮件/短信通知管理员
        # 2. 推送到企业微信/钉钉
        # 3. 写入专门的告警数据库
        # 4. 触发自动化响应（如封禁IP）
        
        return alert_info
        
    except Exception as e:
        print(f"[ALERT ERROR] 发送告警失败: {str(e)}")
        return None


def check_and_alert_verify_failure(
    cert_id: str,
    user_id: str,
    verify_result: Dict,
    ip_address: str = None
):
    """
    检查验签失败并发送告警
    
    Args:
        cert_id: 证书ID
        user_id: 用户ID
        verify_result: 验签结果
        ip_address: IP地址
    """
    if not verify_result.get("verified"):
        errors = verify_result.get("errors", [])
        
        # 判断告警级别
        if "SM2签名验证失败" in errors:
            # 签名被篡改 - 严重
            send_alert(
                alert_type=ALERT_TYPE_CERT_TAMPERED,
                level=ALERT_LEVEL_CRITICAL,
                message=f"证书签名验证失败，可能被篡改",
                user_id=user_id,
                cert_id=cert_id,
                ip_address=ip_address,
                details={"errors": errors}
            )
        elif "nonce已被使用" in errors:
            # 重放攻击 - 高
            send_alert(
                alert_type=ALERT_TYPE_REPLAY_ATTACK,
                level=ALERT_LEVEL_HIGH,
                message=f"检测到重放攻击尝试",
                user_id=user_id,
                cert_id=cert_id,
                ip_address=ip_address,
                details={"errors": errors}
            )
        elif "证书已吊销" in errors:
            # 使用已吊销证书 - 中
            send_alert(
                alert_type=ALERT_TYPE_VERIFY_FAIL,
                level=ALERT_LEVEL_MEDIUM,
                message=f"尝试验证已吊销的证书",
                user_id=user_id,
                cert_id=cert_id,
                ip_address=ip_address,
                details={"errors": errors}
            )
        else:
            # 其他验签失败 - 低
            send_alert(
                alert_type=ALERT_TYPE_VERIFY_FAIL,
                level=ALERT_LEVEL_LOW,
                message=f"证书验签失败",
                user_id=user_id,
                cert_id=cert_id,
                ip_address=ip_address,
                details={"errors": errors}
            )


def check_brute_force(user_id: str, attempt_count: int, time_window: int = 300):
    """
    检查暴力破解行为
    
    Args:
        user_id: 用户ID
        attempt_count: 尝试次数
        time_window: 时间窗口（秒）
    """
    if attempt_count > 10:  # 5分钟内超过10次
        send_alert(
            alert_type=ALERT_TYPE_BRUTE_FORCE,
            level=ALERT_LEVEL_HIGH,
            message=f"检测到暴力破解行为：{attempt_count}次尝试/{time_window}秒",
            user_id=user_id,
            details={"attempt_count": attempt_count, "time_window": time_window}
        )
