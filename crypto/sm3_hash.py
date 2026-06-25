import hashlib
try:
    # 尝试使用标准库（Python 3.13+ 可能支持）
    h = hashlib.new('sm3')
    HAS_SM3 = True
except ValueError:
    # 如果标准库不支持，使用 gmssl
    try:
        from gmssl import sm3
        HAS_SM3 = False
    except ImportError:
        raise ImportError("请安装 gmssl: pip install gmssl")

def get_file_sm3(file_path: str) -> str:
    """
    计算文件的 SM3 哈希值
    """
    if HAS_SM3:
        h = hashlib.new('sm3')
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                h.update(chunk)
        return h.hexdigest()
    else:
        # 使用 gmssl
        func = sm3.sm3_hash
        with open(file_path, "rb") as f:
            data = f.read()
        # gmssl 需要十六进制字符串输入
        hex_data = data.hex()
        return func(hex_data)

def str_sm3(data: str) -> str:
    """
    计算字符串的 SM3 哈希值
    """
    if HAS_SM3:
        h = hashlib.new('sm3')
        h.update(data.encode("utf-8"))
        return h.hexdigest()
    else:
        from gmssl import sm3
        hex_data = data.encode("utf-8").hex()
        return sm3.sm3_hash(hex_data)
