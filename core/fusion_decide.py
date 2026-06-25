def fusion_risk(
    model_score: float, 
    noise_score: float, 
    hash_match: bool, 
    cert_exist: bool,
    temporal_score: float = None,      # 新增：时序一致性评分 (0-1)
    high_freq_anomaly: float = None    # 新增：高频异常指数
) -> tuple[str, float]:
    """
    多通道融合风险决策（增强版 - 模型主导模式）
    
    Args:
        model_score: ViT模型AI概率 (0-1)
        noise_score: 噪声残差分数 (0-20+)
        hash_match: 哈希是否匹配历史指纹
        cert_exist: 是否存在有效证书
        temporal_score: 时序一致性评分 (0-1, 越高越一致)
        high_freq_anomaly: 高频异常指数 (频域特征)
    
    Returns:
        (风险等级, 最终风险分数)
    """
    # ========== 核心改进：提高模型权重至80% ==========
    # 策略：ViT模型作为主要判断依据，其他特征作为微调
    
    # 1. 模型评分作为基础（权重80%）- 绝对主导
    base = model_score * 0.80
    
    # 2. 噪声分析贡献（权重8%）- 辅助验证
    noise_contribution = 0.0
    if noise_score < 2.0:
        # 极低噪声 - 可能为AI生成或过度压缩
        noise_contribution = 0.15
    elif noise_score < 4.0:
        # 低噪声 - 高度压缩或AI生成
        noise_contribution = 0.08
    elif noise_score > 15.0:
        # 高噪声 - 可能为原始视频
        noise_contribution = -0.10
    base += noise_contribution * 0.08
    
    # 3. 时序一致性分析（权重5%，仅视频）- 微调
    temporal_contribution = 0.0
    if temporal_score is not None:
        if temporal_score < 0.3:
            # 时序不一致 - AI生成视频常见
            temporal_contribution = 0.20
        elif temporal_score < 0.6:
            # 中等一致性
            temporal_contribution = 0.08
        else:
            # 高一致性 - 真实视频特征
            temporal_contribution = -0.10
    base += temporal_contribution * 0.05
    
    # 4. 高频异常分析（权重3%，频域特征）- 微调
    freq_contribution = 0.0
    if high_freq_anomaly is not None:
        if high_freq_anomaly > 0.8:
            # 高频能量异常高 - AI生成特征
            freq_contribution = 0.15
        elif high_freq_anomaly < 0.3:
            # 高频能量过低 - 过度平滑
            freq_contribution = 0.10
    base += freq_contribution * 0.03
    
    # 5. 哈希匹配检查（权重2%）- 轻微调整
    hash_contribution = 0.30 if not hash_match else 0.0
    base += hash_contribution * 0.02
    
    # 6. 证书存在性检查（权重2%）- 轻微调整
    cert_contribution = 0.15 if not cert_exist else 0.0
    base += cert_contribution * 0.02
    
    # 限制在 0-1 范围
    final_score = max(0.0, min(1.0, base))
    
    # 风险等级判定（更细致的分级）
    if final_score < 0.25:
        level = "可信"
    elif final_score < 0.50:
        level = "轻度可疑"
    elif final_score < 0.75:
        level = "高风险"
    else:
        level = "不可信"
    
    return level, final_score
