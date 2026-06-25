import uuid
from datetime import datetime
from crypto.sm3_hash import str_sm3
from db.db_conn import get_db_session
from db.models import AuditLog

def create_audit(action: str, operator: str):
    db = get_db_session()
    last_log = db.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    prev_hash = last_log.log_hash if last_log else "0"
    log_id = str(uuid.uuid4())
    raw = f"{log_id}{action}{operator}{prev_hash}"
    log_hash = str_sm3(raw)
    new_log = AuditLog(log_id=log_id, action=action, prev_hash=prev_hash, log_hash=log_hash, operator=operator)
    db.add(new_log)
    db.commit()
    db.close()
    return log_hash

def log_verification(cert_id: str, result: bool, user_id: str, ip_address: str = None, details: dict = None):
    """
    记录证书验签操作
    
    Args:
        cert_id: 证书ID
        result: 验签结果（True/False）
        user_id: 用户ID
        ip_address: IP地址（可选）
        details: 详细验证信息（可选）
    """
    try:
        action = f"CERT_VERIFY|cert_id={cert_id}|result={'PASS' if result else 'FAIL'}"
        if ip_address:
            action += f"|ip={ip_address}"
        if details and details.get('errors'):
            action += f"|errors={','.join(details['errors'])}"
        
        operator = f"user:{user_id}"
        
        # 创建审计日志
        create_audit(action, operator)
        
        print(f"[AUDIT] 验签日志已记录: {action}")
        
    except Exception as e:
        print(f"[AUDIT ERROR] 记录验签日志失败: {str(e)}")
