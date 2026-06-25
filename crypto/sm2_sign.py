import os
from gmssl import sm2, func

priv_key = "00123456789abcdef00123456789abcdef00123456789abcdef00123456789abcdef"
pub_key = "04123456789abcdef00123456789abcdef00123456789abcdef00123456789abcdef00123456789abcdef00123456789abcdef"
sm2_crypt = sm2.CryptSM2(public_key=pub_key, private_key=priv_key)

def sm2_sign_data(plain_text: str) -> str:
    data = plain_text.encode("utf-8")
    # 生成随机数用于签名
    random_hex = os.urandom(32).hex()
    try:
        sign_bytes = sm2_crypt.sign(data, random_hex)
        # 如果返回的是bytes，转换为hex字符串
        if isinstance(sign_bytes, bytes):
            return sign_bytes.hex()
        else:
            return sign_bytes
    except AttributeError:
        # 兼容旧版本 API
        sign_bytes = sm2_crypt.sign(data)
        if isinstance(sign_bytes, bytes):
            return sign_bytes.hex()
        else:
            return sign_bytes

def sm2_verify(plain_text: str, sign_hex: str) -> bool:
    data = plain_text.encode("utf-8")
    sign_bytes = bytes.fromhex(sign_hex)
    return sm2_crypt.verify(sign_bytes, data)
