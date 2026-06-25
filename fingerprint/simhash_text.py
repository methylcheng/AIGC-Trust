import hashlib

def text_simhash(text: str, bits=64) -> str:
    weights = {}
    words = text.split()
    for w in words:
        h = hashlib.sha256(w.encode()).digest()
        num = int.from_bytes(h, "big")
        weights[num] = weights.get(num, 0) + 1
    vec = [0]*bits
    for num, w in weights.items():
        for i in range(bits):
            mask = 1 << i
            if num & mask:
                vec[i] += w
            else:
                vec[i] -= w
    out = 0
    for i in range(bits):
        if vec[i] > 0:
            out |= (1 << i)
    return hex(out)[2:]
