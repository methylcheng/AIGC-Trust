import uuid
from crypto.trust_chain import get_trust_anchor, get_crl, get_chain_verifier
from datetime import datetime, timedelta
from gmssl import sm2
import json

def build_cert_json(content_id: str, content_type: str, sm3_hash: str, fingerprint: str, model_version: str, detection_score: float, risk_level: str, watermark_result: str, edge_node_id: str):
    """
    生成增强型可信证书，包含完整的安全机制
    
    新增安全特性:
    - 证书有效期（默认1年）
    - 防重放nonce
    - 信任锚信息
    - 完整的密钥标识
    """
    cert_id = str(uuid.uuid4())
    now = datetime.now()
    
    # 获取信任系统组件
    trust_anchor = get_trust_anchor()
    crl = get_crl()
    nonce_manager = get_chain_verifier().nonce_manager
    
    # 生成防重放nonce
    nonce = nonce_manager.generate_nonce()
    nonce_timestamp = now.timestamp()
    
    # 计算有效期（默认1年）
    expires_at = now + timedelta(days=365)
    
    # 获取根CA信息
    ca_config = trust_anchor.root_ca_config
    
    cert_data = {
        "certificate_id": cert_id,
        "content_id": content_id,
        "content_type": content_type,
        "sm3_hash": sm3_hash,
        "fingerprint": fingerprint,
        "model_version": model_version,
        "detection_score": detection_score,
        "risk_level": risk_level,
        "watermark_result": watermark_result,
        "issuer": "AIGC-Trust中心平台",
        "issuer_ca_id": ca_config["ca_id"],  # 签发CA标识
        "edge_node_id": edge_node_id,
        "issued_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),  # 新增：过期时间
        "nonce": nonce,  # 新增：防重放nonce
        "nonce_timestamp": str(nonce_timestamp),  # 新增：nonce时间戳
        "trust_anchor": {  # 新增：信任锚信息
            "ca_id": ca_config["ca_id"],
            "ca_name": ca_config["ca_name"],
            "algorithm": ca_config["algorithm"]
        }
    }
    
    # 使用根CA私钥进行SM2签名（确保字典顺序一致）
    plain_text = json.dumps(cert_data, sort_keys=True, ensure_ascii=False)
    
    # 调试：打印签名数据
    print(f"\n[签名调试] 待签名数据:")
    print(f"  数据长度: {len(plain_text)}字符")
    print(f"  完整数据: {plain_text}")
    print(f"  SM3哈希: {cert_data.get('sm3_hash', 'N/A')[:32]}...")
    
    # 加载根CA私钥
    ca_data = trust_anchor.load_root_ca()
    private_key = ca_data["private_key"]
    public_key = ca_data["public_key"]
    
    print(f"  私钥: {private_key[:32]}...")
    print(f"  公钥: {public_key[:32]}...\n")
    
    # 创建SM2签名对象
    sm2_crypt = sm2.CryptSM2(public_key=public_key, private_key=private_key)
    
    # 执行签名
    data_bytes = plain_text.encode("utf-8")
    random_hex = uuid.uuid4().hex  # 随机数用于签名
    sign_result = sm2_crypt.sign(data_bytes, random_hex)
    
    # 强制转换为hex字符串存储
    if isinstance(sign_result, bytes):
        sign = sign_result.hex()
        print(f"✓ SM2签名成功 (bytes -> hex): {sign[:32]}...")
    elif isinstance(sign_result, str):
        # 如果已经是字符串，检查是否是hex格式
        try:
            # 验证是否为有效的hex字符串
            bytes.fromhex(sign_result)
            sign = sign_result
            print(f"✓ SM2签名成功 (str): {sign[:32]}...")
        except ValueError:
            # 如果不是hex，可能是其他格式，强制转换
            sign = sign_result.encode('utf-8').hex()
            print(f"⚠ SM2签名格式异常，已转换: {sign[:32]}...")
    else:
        print(f"✗ SM2签名返回未知类型: {type(sign_result)}")
        raise Exception(f"SM2签名返回类型错误: {type(sign_result)}")
    
    cert_data["sm2_signature"] = sign
    
    return cert_data
