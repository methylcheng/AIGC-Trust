"""
视频深度伪造检测模块
基于逐帧AI图像检测 + 时序一致性分析
"""
import numpy as np
from .image_ai_det import image_ai_score
import tempfile
import cv2
import os


def video_fake_score(frame_list: list, use_model_scoring=True) -> dict:
    """
    视频伪造评分
    
    Args:
        frame_list: 视频帧列表（numpy数组）
        use_model_scoring: 是否使用深度学习模型（否则使用启发式）
    
    Returns:
        检测结果字典，包含：
        - avg_score: 平均AI概率
        - max_score: 最大AI概率
        - score_variance: 分数方差（时序一致性）
        - high_risk_frame_ratio: 高风险帧比例
        - total_frames: 总帧数
    """
    if not frame_list:
        return {
            "avg_score": 0.0,
            "max_score": 0.0,
            "score_variance": 0.0,
            "high_risk_frame_ratio": 0.0,
            "total_frames": 0
        }
    
    scores = []
    
    if use_model_scoring:
        # 方法1：使用深度学习模型逐帧检测
        for i, frame in enumerate(frame_list):
            try:
                # 将帧保存为临时图片
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                
                cv2.imwrite(tmp_path, frame)
                
                # 调用图像AI检测模型
                score = image_ai_score(image_path=tmp_path)
                scores.append(score)
                
                # 删除临时文件
                os.unlink(tmp_path)
                
            except Exception as e:
                print(f"帧 {i} 检测失败: {e}")
                continue
    else:
        # 方法2：启发式检测（快速但精度较低）
        for frame in frame_list:
            score = _heuristic_video_detect(frame)
            scores.append(score)
    
    if not scores:
        return {
            "avg_score": 0.5,
            "max_score": 0.5,
            "score_variance": 0.0,
            "high_risk_frame_ratio": 0.0,
            "total_frames": len(frame_list)
        }
    
    scores_array = np.array(scores)
    
    result = {
        "avg_score": round(float(np.mean(scores_array)), 4),
        "max_score": round(float(np.max(scores_array)), 4),
        "score_variance": round(float(np.var(scores_array)), 4),
        "high_risk_frame_ratio": round(float(np.sum(scores_array > 0.7) / len(scores_array)), 4),
        "total_frames": len(frame_list)
    }
    
    return result


def _heuristic_video_detect(frame: np.ndarray) -> float:
    """
    启发式视频伪造检测（快速方法）
    
    基于以下特征：
    - 噪声模式异常
    - 边缘不自然
    - 色彩分布异常
    """
    import cv2
    
    score = 0.3  # 基础分
    
    # 1. 噪声分析
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    noise = np.abs(gray.astype(np.float32) - blur.astype(np.float32))
    avg_noise = np.mean(noise)
    
    if avg_noise < 5 or avg_noise > 20:
        score += 0.15  # 噪声异常
    
    # 2. 边缘检测
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
    
    if edge_ratio > 0.3 or edge_ratio < 0.05:
        score += 0.1  # 边缘异常
    
    # 3. 色彩直方图均匀性
    hist_b = cv2.calcHist([frame], [0], None, [256], [0, 256])
    hist_g = cv2.calcHist([frame], [1], None, [256], [0, 256])
    hist_r = cv2.calcHist([frame], [2], None, [256], [0, 256])
    
    # 计算直方图熵
    def calc_entropy(hist):
        hist_norm = hist / (np.sum(hist) + 1e-8)
        hist_norm = hist_norm[hist_norm > 0]
        return -np.sum(hist_norm * np.log2(hist_norm))
    
    entropy_avg = (calc_entropy(hist_b) + calc_entropy(hist_g) + calc_entropy(hist_r)) / 3
    
    if entropy_avg < 6 or entropy_avg > 7.5:
        score += 0.1  # 色彩分布异常
    
    return min(score, 1.0)
