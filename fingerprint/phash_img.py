import cv2
import numpy as np

def calc_phash(img_bgr: np.ndarray, size=32) -> str:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (size, size))
    dct = cv2.dct(gray.astype(np.float32))
    dct_low = dct[0:8, 0:8]
    avg = np.mean(dct_low)
    bits = (dct_low > avg).flatten()
    hash_str = "".join(["1" if b else "0" for b in bits])
    return hash_str
