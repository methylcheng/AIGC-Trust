import cv2
import numpy as np

def calc_fft_feature(img_bgr: np.ndarray):
    """计算FFT频域特征"""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = 20 * np.log(np.abs(fshift) + 1e-8)
    return mag.tolist()

def calc_dct_block(img_bgr: np.ndarray):
    """计算DCT分块特征"""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    dct_vals = []
    block = 8
    for y in range(0, h, block):
        for x in range(0, w, block):
            patch = gray[y:y+block].astype(np.float32)
            dct = cv2.dct(patch)
            dct_vals.extend(dct.flatten().tolist())
    return dct_vals

def calc_noise_residual(img_bgr: np.ndarray, method='multi_scale') -> float:
    """
    计算噪声残差（用于检测图像篡改）
    
    Args:
        img_bgr: BGR格式图像
        method: 'single' (原方法) 或 'multi_scale' (多尺度改进)
    
    Returns:
        噪声强度值
    """
    if method == 'single':
        # 原有单尺度方法(保留兼容)
        blur = cv2.GaussianBlur(img_bgr, (5,5), 0)
        residual = np.abs(img_bgr.astype(np.float32) - blur.astype(np.float32))
        return float(np.mean(residual))
    
    else:
        # 改进的多尺度噪声检测
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        # 尺度1: 小尺度噪声 (3x3)
        blur_small = cv2.GaussianBlur(gray, (3, 3), 0)
        noise_small = np.abs(gray - blur_small)
        
        # 尺度2: 中等尺度噪声 (7x7)
        blur_medium = cv2.GaussianBlur(gray, (7, 7), 0)
        noise_medium = np.abs(gray - blur_medium)
        
        # 尺度3: 大尺度噪声 (15x15)
        blur_large = cv2.GaussianBlur(gray, (15, 15), 0)
        noise_large = np.abs(gray - blur_large)
        
        # 加权融合(小尺度权重更高,因为真实相机噪声主要在高频)
        weighted_noise = (
            0.5 * np.mean(noise_small) + 
            0.3 * np.mean(noise_medium) + 
            0.2 * np.mean(noise_large)
        )
        
        return float(weighted_noise)

def analyze_video_frequency(frames: list, high_precision: bool = True) -> dict:
    """
    视频频域取证分析（高精度版本）
    
    Args:
        frames: 视频帧列表
        high_precision: 是否使用高精度模式（多尺度+时序一致性）
    
    Returns:
        频域分析结果字典
    """
    if not frames:
        return {
            "avg_noise_score": 0.0,
            "noise_variance": 0.0,
            "high_freq_anomaly": 0.0,
            "frame_count": 0
        }
    
    noise_scores = []
    high_freq_scores = []
    temporal_consistency = []  # 新增：时序一致性分析
    
    prev_noise = None
    
    for i, frame in enumerate(frames):
        # 1. 噪声残差分析(使用改进的多尺度方法)
        noise = calc_noise_residual(frame, method='multi_scale')
        noise_scores.append(noise)
        
        # 2. 时序噪声一致性（真实视频噪声在时间上连续）
        if prev_noise is not None and high_precision:
            noise_diff = abs(noise - prev_noise)
            temporal_consistency.append(noise_diff)
        prev_noise = noise
        
        # 3. 高频异常检测（通过FFT + 多频段分析）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)
        
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        
        if high_precision:
            # 高精度：分多个频段分析
            # 低频 (中心25%)
            mask_low = np.zeros((h, w), dtype=np.uint8)
            r_low = int(min(center_h, center_w) * 0.25)
            cv2.circle(mask_low, (center_w, center_h), r_low, 1, -1)
            mask_low = mask_low.astype(bool)
            
            # 中频 (25%-50%)
            mask_mid = np.zeros((h, w), dtype=np.uint8)
            r_mid_outer = int(min(center_h, center_w) * 0.50)
            cv2.circle(mask_mid, (center_w, center_h), r_mid_outer, 1, -1)
            mask_mid = mask_mid.astype(bool)
            mask_mid &= ~mask_low
            
            # 高频 (50%-75%)
            mask_high = np.zeros((h, w), dtype=np.uint8)
            r_high_outer = int(min(center_h, center_w) * 0.75)
            cv2.circle(mask_high, (center_w, center_h), r_high_outer, 1, -1)
            mask_high = mask_high.astype(bool)
            mask_high &= ~mask_mid & ~mask_low
            
            # 计算各频段能量
            energy_low = np.sum(magnitude[mask_low]) / (np.sum(mask_low) + 1e-8)
            energy_mid = np.sum(magnitude[mask_mid]) / (np.sum(mask_mid) + 1e-8)
            energy_high = np.sum(magnitude[mask_high]) / (np.sum(mask_high) + 1e-8)
            
            # 高频/低频比值（AI生成图像往往高频异常）
            freq_ratio = energy_high / (energy_low + 1e-8)
            high_freq_scores.append(freq_ratio)
        else:
            # 原有简单方法
            mask = np.ones((h, w), dtype=bool)
            mask[int(center_h*0.75):int(center_h*1.25), int(center_w*0.75):int(center_w*1.25)] = False
            high_freq_energy = np.sum(magnitude[mask])
            total_energy = np.sum(magnitude)
            high_freq_ratio = high_freq_energy / (total_energy + 1e-8)
            high_freq_scores.append(high_freq_ratio)
    
    avg_noise = float(np.mean(noise_scores))
    noise_var = float(np.var(noise_scores))
    avg_high_freq = float(np.mean(high_freq_scores))
    
    # 归一化噪声分数到0-1范围
    normalized_noise = min(avg_noise / 10.0, 1.0)
    
    result = {
        "avg_noise_score": round(avg_noise, 4),
        "normalized_noise_score": round(normalized_noise, 4),
        "noise_variance": round(noise_var, 4),
        "high_freq_anomaly": round(avg_high_freq, 4),
        "frame_count": len(frames),
        "noise_interpretation": _interpret_noise_level(avg_noise)
    }
    
    # 高精度模式：添加时序一致性指标
    if high_precision and temporal_consistency:
        avg_temporal_diff = float(np.mean(temporal_consistency))
        temporal_var = float(np.var(temporal_consistency))
        
        result['temporal_noise_consistency'] = round(avg_temporal_diff, 4)
        result['temporal_variance'] = round(temporal_var, 4)
        
        # 时序一致性评分（差异越小越一致，真实视频通常更一致）
        temporal_score = max(0, 1.0 - avg_temporal_diff / 5.0)
        result['temporal_consistency_score'] = round(temporal_score, 4)
    
    return result

def _interpret_noise_level(noise_score: float) -> str:
    """
    解释噪声分数含义
    
    Args:
        noise_score: 原始噪声分数
    
    Returns:
        解释字符串
    """
    if noise_score < 2.0:
        return "极低噪声 - 可能为AI生成或过度压缩"
    elif noise_score < 4.0:
        return "低噪声 - 高度压缩或AI生成"
    elif noise_score < 8.0:
        return "中等噪声 - 正常压缩视频"
    elif noise_score < 15.0:
        return "较高噪声 - 轻微压缩或未压缩视频"
    else:
        return "高噪声 - 原始视频或传感器噪声明显"
