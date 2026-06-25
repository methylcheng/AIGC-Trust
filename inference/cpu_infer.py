import torch
import cv2
import numpy as np
def img_aigc_score(frame):
    img = cv2.resize(frame, (640,360))
    img = img.astype(np.float32)/255.0
    score = 0.3
    return score
