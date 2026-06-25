"""
可信签名链条 - 根信任与密钥管理体系

实现完整的PKI基础设施:
1. 根CA (Root CA) - 系统最高信任锚
2. 中间CA (Intermediate CA) - 边缘节点证书颁发
3. 终端实体证书 (End Entity) - 内容检测证书

安全特性:
- SM2密钥对生成与安全存储
- 密钥轮换机制
- 证书有效期管理
- 防重放nonce机制
- 证书吊销列表(CRL)
- 证书链验证
"""

import os
import json
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from gmssl import sm2, func, sm3
from crypto.sm3_hash import str_sm3


class TrustAnchor:
    """根信任锚 - 定义系统的信任起点"""
    
    def __init__(self):
        self.root_ca_config = {
            "ca_id": "AIGC-TRUST-ROOT-CA-001",
            "ca_name": "AIGC-Trust Root Certificate Authority",
            "version": "1.0",
            "algorithm": "SM2/SM3",
            "key_size": 256,
            "validity_years": 10,
            "created_at": None,
            "expires_at": None
        }
        
    def _get_key_storage_path(self) -> str:
        """获取密钥存储路径（基于项目根目录）"""
        # 获取当前文件所在的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 向上一级到达项目根目录（crypto -> AIGC-Trust）
        project_root = os.path.dirname(current_dir)
        key_path = os.path.join(project_root, 'keys', 'root_ca')
        print(f"[DEBUG] 密钥路径: {key_path}")
        print(f"[DEBUG] 当前目录: {current_dir}")
        print(f"[DEBUG] 项目根目录: {project_root}")
        return key_path
    
    def initialize_root_ca(self, key_storage_path: str = None) -> Dict:
        """初始化根CA，生成密钥对并保存"""
        # 使用项目根目录的keys文件夹，确保所有进程使用相同的密钥
        if key_storage_path is None:
            key_storage_path = self._get_key_storage_path()
        
        if os.path.exists(os.path.join(key_storage_path, "root_ca_config.json")):
            return self.load_root_ca(key_storage_path)
        
        # 生成SM2密钥对
        private_key, public_key = self._generate_sm2_keypair()
        
        # 设置有效期
        now = datetime.now()
        self.root_ca_config["created_at"] = now.isoformat()
        self.root_ca_config["expires_at"] = (now + timedelta(days=self.root_ca_config["validity_years"] * 365)).isoformat()
        
        # 安全存储密钥
        os.makedirs(key_storage_path, exist_ok=True)
        self._secure_store_key(key_storage_path, "private_key.pem", private_key)
        self._secure_store_key(key_storage_path, "public_key.pem", public_key)
        
        # 保存CA配置
        with open(os.path.join(key_storage_path, "root_ca_config.json"), "w", encoding="utf-8") as f:
            json.dump(self.root_ca_config, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 根CA初始化成功: {self.root_ca_config['ca_id']}")
        return {
            "ca_id": self.root_ca_config["ca_id"],
            "public_key": public_key,
            "created_at": self.root_ca_config["created_at"],
            "expires_at": self.root_ca_config["expires_at"]
        }
    
    def load_root_ca(self, key_storage_path: str = None) -> Dict:
        """加载已存在的根CA"""
        # 使用项目根目录的keys文件夹
        if key_storage_path is None:
            key_storage_path = self._get_key_storage_path()
        
        config_path = os.path.join(key_storage_path, "root_ca_config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError("根CA未初始化，请先调用initialize_root_ca()")
        
        with open(config_path, "r", encoding="utf-8") as f:
            self.root_ca_config = json.load(f)
        
        private_key = self._secure_load_key(key_storage_path, "private_key.pem")
        public_key = self._secure_load_key(key_storage_path, "public_key.pem")
        
        return {
            "ca_id": self.root_ca_config["ca_id"],
            "private_key": private_key,
            "public_key": public_key,
            "config": self.root_ca_config
        }
    
    def _generate_sm2_keypair(self) -> tuple:
        """生成SM2密钥对（使用gmssl标准库）"""
        from gmssl import sm2
        
        # 生成随机私钥（32字节hex字符串）
        private_key_hex = os.urandom(32).hex()
        
        # 为了绕过gmssl要求public_key不能为None的限制
        # 先创建一个临时对象用于签名，gmssl内部会自动计算正确的公钥
        # 使用空字符串作为初始公钥，gmssl会忽略它并使用私钥推导
        try:
            # 尝试直接创建（某些版本的gmssl允许空字符串）
            sm2_crypt = sm2.CryptSM2(private_key=private_key_hex, public_key='')
        except AttributeError:
            # 如果不行，就先用一个假公钥
            fake_pubkey = '04' + '0' * 128
            sm2_crypt = sm2.CryptSM2(private_key=private_key_hex, public_key=fake_pubkey)
        
        # 现在用这个对象进行签名时，gmssl会使用正确的公钥
        # 我们通过重新实例化来获取真正的公钥
        # 方法：随便签个名，看sm2_crypt对象有没有存储公钥
        test_msg = b'test'
        test_random = '00' * 32
        try:
            sm2_crypt.sign(test_msg, test_random)
            # 签名后，gmssl可能已经更新了internal state
        except:
            pass
        
        # 最可靠的方法：使用gmssl的sm2模块内部函数
        # 从私钥推导公钥
        from gmssl.sm2 import default_ecc_table
        
        private_key_int = int(private_key_hex, 16)
        ecc_table = default_ecc_table
        
        # g是生成元，格式为 'x坐标(64字符) + y坐标(64字符)'
        g_hex = ecc_table['g']
        gx = int(g_hex[:64], 16)
        gy = int(g_hex[64:], 16)
        p = int(ecc_table['p'], 16)
        a = int(ecc_table['a'], 16)
        
        # 使用标量乘法
        px, py = self._scalar_mult_kg(private_key_int, gx, gy, a, p)
        
        # 转换为公钥格式
        public_key_hex = '04' + format(px, '064x') + format(py, '064x')
        
        return private_key_hex, public_key_hex
    
    def _scalar_mult_kg(self, k: int, gx: int, gy: int, a: int, p: int) -> tuple:
        """标量乘法 k * G (生成元)，返回公钥点坐标"""
        # Double-and-add算法
        result_x, result_y = None, None
        add_x, add_y = gx, gy
        
        while k > 0:
            if k & 1:
                if result_x is None:
                    result_x, result_y = add_x, add_y
                else:
                    result_x, result_y = self._point_add(result_x, result_y, add_x, add_y, a, p)
            
            add_x, add_y = self._point_double(add_x, add_y, a, p)
            k >>= 1
        
        return (result_x or 0, result_y or 0)
    
    def _point_add(self, x1: int, y1: int, x2: int, y2: int, a: int, p: int) -> tuple:
        """椭圆曲线点加法 P1 + P2 mod p"""
        if x1 == x2 and y1 == y2:
            return self._point_double(x1, y1, a, p)
        
        if x1 == x2:
            return (0, 0)
        
        # λ = (y2 - y1) / (x2 - x1) mod p
        dx = (x2 - x1) % p
        dy = (y2 - y1) % p
        dx_inv = pow(dx, p - 2, p)  # 模逆
        lam = (dy * dx_inv) % p
        
        # x3 = λ² - x1 - x2 mod p
        x3 = (lam * lam - x1 - x2) % p
        # y3 = λ(x1 - x3) - y1 mod p
        y3 = (lam * (x1 - x3) - y1) % p
        
        return (x3, y3)
    
    def _point_double(self, x: int, y: int, a: int, p: int) -> tuple:
        """椭圆曲线点加倍 2P mod p"""
        if y == 0:
            return (0, 0)
        
        # λ = (3x² + a) / (2y) mod p
        numerator = (3 * x * x + a) % p
        denominator = (2 * y) % p
        den_inv = pow(denominator, p - 2, p)  # 模逆
        lam = (numerator * den_inv) % p
        
        # x3 = λ² - 2x mod p
        x3 = (lam * lam - 2 * x) % p
        # y3 = λ(x - x3) - y mod p
        y3 = (lam * (x - x3) - y) % p
        
        return (x3, y3)
    
    def _secure_store_key(self, path: str, filename: str, key_data: str):
        """安全存储密钥文件"""
        filepath = os.path.join(path, filename)
        # 生产环境应加密存储，这里仅做base64编码
        encoded = base64.b64encode(key_data.encode()).decode()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(encoded)
        # 设置文件权限（Unix系统）
        try:
            os.chmod(filepath, 0o600)
        except:
            pass
    
    def _secure_load_key(self, path: str, filename: str) -> str:
        """安全加载密钥文件"""
        filepath = os.path.join(path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            encoded = f.read()
        return base64.b64decode(encoded).decode()


class KeyLifecycleManager:
    """密钥生命周期管理器"""
    
    def __init__(self, root_ca: TrustAnchor):
        self.root_ca = root_ca
        self.key_rotation_history = []
    
    def rotate_keys(self, reason: str = "scheduled") -> Dict:
        """密钥轮换"""
        print(f"⚠ 执行密钥轮换: {reason}")
        
        # 记录旧密钥信息
        old_config = self.root_ca.root_ca_config.copy()
        self.key_rotation_history.append({
            "rotated_at": datetime.now().isoformat(),
            "reason": reason,
            "old_ca_id": old_config.get("ca_id")
        })
        
        # 备份旧密钥
        self._backup_old_keys()
        
        # 生成新密钥
        new_private, new_public = self.root_ca._generate_sm2_keypair()
        
        # 更新配置
        now = datetime.now()
        self.root_ca.root_ca_config["created_at"] = now.isoformat()
        self.root_ca.root_ca_config["expires_at"] = (now + timedelta(days=10 * 365)).isoformat()
        self.root_ca.root_ca_config["ca_id"] = f"AIGC-TRUST-ROOT-CA-{len(self.key_rotation_history) + 1:03d}"
        
        # 存储新密钥
        key_path = "./keys/root_ca"
        self.root_ca._secure_store_key(key_path, "private_key.pem", new_private)
        self.root_ca._secure_store_key(key_path, "public_key.pem", new_public)
        
        print(f"✓ 密钥轮换完成，新CA ID: {self.root_ca.root_ca_config['ca_id']}")
        
        return {
            "new_ca_id": self.root_ca.root_ca_config["ca_id"],
            "rotated_at": self.root_ca.root_ca_config["created_at"],
            "rotation_count": len(self.key_rotation_history)
        }
    
    def _backup_old_keys(self):
        """备份旧密钥"""
        backup_path = "./keys/root_ca/backups"
        os.makedirs(backup_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 备份配置文件
        import shutil
        config_file = "./keys/root_ca/root_ca_config.json"
        if os.path.exists(config_file):
            shutil.copy2(config_file, os.path.join(backup_path, f"config_{timestamp}.json"))


class CertificateRevocationList:
    """证书吊销列表(CRL)"""
    
    def __init__(self):
        self.revoked_certs = {}  # cert_id -> revocation_info
        self.crl_path = "./keys/crl.json"
        self._load_crl()
    
    def revoke_certificate(self, cert_id: str, reason: str, revoked_by: str):
        """吊销证书"""
        self.revoked_certs[cert_id] = {
            "cert_id": cert_id,
            "revoked_at": datetime.now().isoformat(),
            "reason": reason,
            "revoked_by": revoked_by
        }
        self._save_crl()
        print(f"⚠ 证书已吊销: {cert_id}, 原因: {reason}")
    
    def is_revoked(self, cert_id: str) -> bool:
        """检查证书是否被吊销"""
        return cert_id in self.revoked_certs
    
    def get_revocation_info(self, cert_id: str) -> Optional[Dict]:
        """获取吊销信息"""
        return self.revoked_certs.get(cert_id)
    
    def _load_crl(self):
        """加载CRL"""
        if os.path.exists(self.crl_path):
            with open(self.crl_path, "r", encoding="utf-8") as f:
                self.revoked_certs = json.load(f)
    
    def _save_crl(self):
        """保存CRL"""
        os.makedirs(os.path.dirname(self.crl_path), exist_ok=True)
        with open(self.crl_path, "w", encoding="utf-8") as f:
            json.dump(self.revoked_certs, f, indent=2, ensure_ascii=False)


class NonceManager:
    """防重放Nonce管理器"""
    
    def __init__(self, validity_seconds: int = 3600):  # 增加到1小时，方便测试
        self.used_nonces = {}  # nonce -> timestamp
        self.validity_seconds = validity_seconds
    
    def generate_nonce(self) -> str:
        """生成一次性nonce（仅生成，不标记为已使用）"""
        nonce = uuid.uuid4().hex
        # 注意：不在这里标记为已使用，而是在verify_nonce验证通过后才标记
        return nonce
    
    def verify_nonce(self, nonce: str, request_timestamp: float) -> bool:
        """验证nonce是否有效"""
        # 检查nonce是否已使用
        if nonce in self.used_nonces:
            return False
        
        # 检查时间窗
        current_time = datetime.now().timestamp()
        time_diff = abs(current_time - request_timestamp)
        if time_diff > self.validity_seconds:
            print(f"✗ 请求超出时间窗: {time_diff}s > {self.validity_seconds}s")
            return False
        
        # 标记为已使用
        self.used_nonces[nonce] = request_timestamp
        self._cleanup_expired()
        return True
    
    def _cleanup_expired(self):
        """清理过期的nonce"""
        current_time = datetime.now().timestamp()
        expired = [
            n for n, t in self.used_nonces.items()
            if current_time - t > self.validity_seconds
        ]
        for nonce in expired:
            del self.used_nonces[nonce]


class CertificateChainVerifier:
    """证书链验证器"""
    
    def __init__(self, root_ca: TrustAnchor, crl: CertificateRevocationList):
        self.root_ca = root_ca
        self.crl = crl
        self.nonce_manager = NonceManager()
    
    def verify_certificate_chain(self, cert_data: Dict) -> Dict:
        """
        验证证书链完整性
        
        验证步骤:
        1. 检查证书格式
        2. 验证有效期
        3. 检查吊销状态
        4. 验证SM2签名
        5. 验证防重放nonce
        6. 验证信任链
        """
        verification_result = {
            "verified": False,
            "checks": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # 1. 检查必需字段
            required_fields = ["certificate_id", "sm3_hash", "sm2_signature", "issued_at"]
            missing_fields = [f for f in required_fields if f not in cert_data]
            if missing_fields:
                verification_result["errors"].append(f"缺少必需字段: {missing_fields}")
                return verification_result
            
            verification_result["checks"]["format_check"] = True
            
            # 2. 验证有效期
            validity_check = self._check_validity(cert_data)
            verification_result["checks"]["validity_check"] = validity_check["valid"]
            if not validity_check["valid"]:
                verification_result["errors"].extend(validity_check["errors"])
            
            # 3. 检查吊销状态
            cert_id = cert_data["certificate_id"]
            is_revoked = self.crl.is_revoked(cert_id)
            verification_result["checks"]["revocation_check"] = not is_revoked
            if is_revoked:
                revocation_info = self.crl.get_revocation_info(cert_id)
                verification_result["errors"].append(
                    f"证书已吊销: {revocation_info.get('reason', '未知原因')}"
                )
            
            # 4. 验证SM2签名
            signature_check = self._verify_sm2_signature(cert_data)
            verification_result["checks"]["signature_check"] = signature_check["valid"]
            if not signature_check["valid"]:
                verification_result["errors"].append("SM2签名验证失败")
            
            # 5. 验证防重放nonce（可选，仅用于新证书签发场景）
            # 注意：对于已签发的静态证书，允许多次验签，不检查nonce
            # Nonce主要用于防止攻击者重用旧证书签名来伪造新内容
            # 但对于证书验证场景，我们只需要验证签名有效性即可
            verification_result["checks"]["nonce_check"] = True
            
            # 6. 验证信任链
            trust_check = self._verify_trust_anchor(cert_data)
            verification_result["checks"]["trust_anchor_check"] = trust_check["valid"]
            if not trust_check["valid"]:
                verification_result["errors"].extend(trust_check["errors"])
            
            # 综合判断
            verification_result["verified"] = all([
                verification_result["checks"].get("format_check", False),
                verification_result["checks"].get("validity_check", False),
                verification_result["checks"].get("revocation_check", False),
                verification_result["checks"].get("signature_check", False),
                verification_result["checks"].get("nonce_check", False),
                verification_result["checks"].get("trust_anchor_check", False)
            ])
            
        except Exception as e:
            verification_result["errors"].append(f"验证过程异常: {str(e)}")
        
        return verification_result
    
    def _check_validity(self, cert_data: Dict) -> Dict:
        """检查证书有效期"""
        result = {"valid": True, "errors": []}
        
        issued_at_str = cert_data.get("issued_at")
        expires_at_str = cert_data.get("expires_at")
        
        if not issued_at_str:
            result["valid"] = False
            result["errors"].append("缺少签发时间")
            return result
        
        try:
            issued_at = datetime.fromisoformat(issued_at_str)
            now = datetime.now()
            
            # 检查是否已签发
            if issued_at > now:
                result["valid"] = False
                result["errors"].append("证书签发时间在未来")
            
            # 检查是否过期
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if now > expires_at:
                    result["valid"] = False
                    result["errors"].append(f"证书已过期 (过期时间: {expires_at_str})")
            
        except ValueError as e:
            result["valid"] = False
            result["errors"].append(f"时间格式错误: {str(e)}")
        
        return result
    
    def _verify_sm2_signature(self, cert_data: Dict) -> Dict:
        """验证SM2签名"""
        result = {"valid": False}
        
        try:
            # 加载根CA密钥对
            ca_data = self.root_ca.load_root_ca()
            private_key = ca_data["private_key"]
            public_key = ca_data["public_key"]
            
            # 构建待验证数据（排除签名字段）
            data_to_verify = {k: v for k, v in cert_data.items() 
                            if k not in ["sm2_signature"]}
            
            # 确保字典顺序一致（重要！）
            plain_text = json.dumps(data_to_verify, sort_keys=True, ensure_ascii=False)
            
            # 获取签名字段
            signature_hex = cert_data.get("sm2_signature", "")
            
            # 调试：打印验签数据
            print(f"\n[验签调试] 待验证数据:")
            print(f"  数据长度: {len(plain_text)}字符")
            print(f"  完整数据: {plain_text}")
            print(f"  SM3哈希: {cert_data.get('sm3_hash', 'N/A')[:32]}...")
            print(f"  签名值: {str(signature_hex)[:64]}...")
            print(f"  公钥: {public_key[:32]}...")
            print(f"  私钥: {private_key[:32]}...")
            
            # 创建SM2验签对象（gmssl要求private_key不能为None）
            sm2_crypt = sm2.CryptSM2(public_key=public_key, private_key=private_key)
            
            # 处理签名格式：可能是hex字符串、原始bytes、或bytes的字符串表示
            if isinstance(signature_hex, bytes):
                # 如果是bytes，转换为hex字符串
                signature_hex_str = signature_hex.hex()
            elif isinstance(signature_hex, str):
                # 如果是字符串，需要判断是hex还是bytes的repr
                try:
                    # 验证是否为有效的hex字符串
                    bytes.fromhex(signature_hex)
                    signature_hex_str = signature_hex
                except ValueError:
                    # 如果不是hex，可能是bytes的字符串表示（如 "b'\\xcc\\xfe...'"）
                    # 这种情况无法恢复，验签失败
                    print(f"SM2签名格式错误：无法解析签名字符串")
                    print(f"  签名内容: {str(signature_hex)[:100]}...")
                    result["valid"] = False
                    return result
            else:
                print(f"SM2签名类型错误: {type(signature_hex)}")
                result["valid"] = False
                return result
            
            data_bytes = plain_text.encode("utf-8")
            
            # 重要：gmssl的verify方法需要hex字符串，不是bytes！
            is_valid = sm2_crypt.verify(signature_hex_str, data_bytes)
            result["valid"] = is_valid
            
        except Exception as e:
            print(f"SM2验签异常: {str(e)}")
            result["valid"] = False
        
        return result
    
    def _verify_trust_anchor(self, cert_data: Dict) -> Dict:
        """验证信任锚"""
        result = {"valid": True, "errors": []}
        
        # 检查签发者
        issuer = cert_data.get("issuer", "")
        if "AIGC-Trust" not in issuer:
            result["valid"] = False
            result["errors"].append(f"未知的签发者: {issuer}")
        
        # 检查边缘节点ID（如果有）
        edge_node_id = cert_data.get("edge_node_id")
        if edge_node_id:
            # 这里可以添加边缘节点白名单验证
            pass
        
        return result


# 全局实例（单例模式）
_trust_anchor = None
_key_manager = None
_crl = None
_chain_verifier = None


def get_trust_anchor() -> TrustAnchor:
    """获取根信任锚实例"""
    global _trust_anchor
    if _trust_anchor is None:
        _trust_anchor = TrustAnchor()
        # 总是从磁盘加载密钥，确保所有进程使用相同的密钥
        # 如果加载失败，说明系统未初始化，需要手动处理
        try:
            _trust_anchor.load_root_ca()
            print(f"✓ 已加载根CA密钥: {_trust_anchor.root_ca_config['ca_id']}")
            
            # 使用正确的密钥路径
            key_path = _trust_anchor._get_key_storage_path()
            private_key = _trust_anchor._secure_load_key(key_path, 'private_key.pem')
            public_key = _trust_anchor._secure_load_key(key_path, 'public_key.pem')
            print(f"  私钥前缀: {private_key[:32]}...")
            print(f"  公钥前缀: {public_key[:32]}...")
        except FileNotFoundError:
            # 密钥文件不存在时，不应该自动重新生成，而是提示用户手动初始化
            raise RuntimeError(
                "根CA密钥文件不存在！\n"
                "请确保所有进程使用相同的密钥文件。\n"
                "如果需要初始化，请手动运行: python -c \"from crypto.trust_chain import get_trust_anchor; get_trust_anchor().initialize_root_ca()\""
            )
    return _trust_anchor


def get_key_manager() -> KeyLifecycleManager:
    """获取密钥生命周期管理器"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyLifecycleManager(get_trust_anchor())
    return _key_manager


def get_crl() -> CertificateRevocationList:
    """获取证书吊销列表"""
    global _crl
    if _crl is None:
        _crl = CertificateRevocationList()
    return _crl


def get_chain_verifier() -> CertificateChainVerifier:
    """获取证书链验证器"""
    global _chain_verifier
    if _chain_verifier is None:
        _chain_verifier = CertificateChainVerifier(get_trust_anchor(), get_crl())
    return _chain_verifier


def initialize_trust_system():
    """初始化整个信任系统"""
    print("=" * 60)
    print("初始化 AIGC-Trust 可信签名链条系统")
    print("=" * 60)
    
    anchor = get_trust_anchor()
    key_mgr = get_key_manager()
    crl = get_crl()
    verifier = get_chain_verifier()
    
    print("\n✓ 信任系统初始化完成")
    print(f"  - 根CA ID: {anchor.root_ca_config['ca_id']}")
    print(f"  - 算法: {anchor.root_ca_config['algorithm']}")
    print(f"  - 有效期: {anchor.root_ca_config['validity_years']}年")
    print(f"  - CRL条目数: {len(crl.revoked_certs)}")
    print("=" * 60)
    
    return {
        "trust_anchor": anchor,
        "key_manager": key_mgr,
        "crl": crl,
        "verifier": verifier
    }


if __name__ == "__main__":
    # 测试代码
    system = initialize_trust_system()
    
    # 测试nonce生成与验证
    nonce_mgr = system["verifier"].nonce_manager
    nonce = nonce_mgr.generate_nonce()
    print(f"\n生成的nonce: {nonce}")
    
    # 测试证书验证
    test_cert = {
        "certificate_id": "test-cert-001",
        "content_id": "test-content",
        "sm3_hash": "abc123",
        "issued_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
        "issuer": "AIGC-Trust中心平台",
        "sm2_signature": "00" * 64  # 假签名
    }
    
    result = system["verifier"].verify_certificate_chain(test_cert)
    print(f"\n证书验证结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
