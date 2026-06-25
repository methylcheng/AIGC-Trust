import os
from crypto.sm3_hash import get_file_sm3
from inference.bert_text_detector import text_ai_score
from inference.image_ai_det import image_ai_score
from core.video_detector import detect_video_aigc
from core.image_detector import detect_image_aigc
from core.text_detector import detect_text_aigc


def analyze_content(file_path: str, content_type: str, task_id: str = None, user_id: int = None) -> dict:
    """
    统一内容分析入口（图片/视频/文本）
    集成 MindSpore AI 检测模型
    
    Args:
        file_path: 文件路径
        content_type: 内容类型 (image/video/text)
        task_id: 任务ID（可选，如果提供则不创建新任务）
        user_id: 用户ID（可选，用于关联数据）
    """
    if not os.path.exists(file_path):
        return {
            "status": "error",
            "msg": "文件不存在",
            "risk_level": "unknown"
        }

    # 计算 SM3 哈希
    file_hash = get_file_sm3(file_path)
    
    risk_score = 0.2
    risk_level = "low"
    ai_probability = None

    try:
        if content_type == "image":
            # 使用完整的图片AIGC检测流程（包含证书生成）
            print("启动图片AIGC检测流程...")
            image_result = detect_image_aigc(
                image_path=file_path,
                edge_node_id="center",
                use_deep_model=True,  # 使用深度学习模型
                task_id=task_id,  # 传递任务ID，避免重复创建
                user_id=user_id   # 传递用户ID
            )
            
            if image_result.get("status") == "success":
                risk_score = image_result["risk_score"]
                risk_level = image_result["risk_level"]
                ai_probability = image_result.get("ai_probability")
            else:
                # 检测失败时使用默认值
                risk_score = 0.5
                risk_level = "medium"
                ai_probability = None
                
        elif content_type == "video":
            # 使用完整的视频AIGC检测流程
            print("启动视频AIGC检测流程...")
            video_result = detect_video_aigc(
                video_path=file_path,
                edge_node_id="center",
                use_deep_model=True,  # 使用深度学习模型
                task_id=task_id,  # 传递任务ID，避免重复创建
                user_id=user_id   # 传递用户ID
            )
            
            if video_result.get("status") == "success":
                risk_score = video_result["risk_score"]
                risk_level = video_result["risk_level"]
                ai_probability = video_result.get("deepfake_analysis", {}).get("avg_score")
            else:
                # 检测失败时使用默认值
                risk_score = 0.5
                risk_level = "medium"
                ai_probability = None
            
        elif content_type == "text":
            # 使用完整的文本AIGC检测流程（包含证书生成）
            print("启动文本AIGC检测流程...")
            text_result = detect_text_aigc(
                text_path=file_path,
                edge_node_id="center",
                use_deep_model=True,  # 使用深度学习模型
                task_id=task_id,  # 传递任务ID，避免重复创建
                user_id=user_id   # 传递用户ID
            )
            
            if text_result.get("status") == "success":
                risk_score = text_result["risk_score"]
                risk_level = text_result["risk_level"]
                ai_probability = text_result.get("ai_probability")
            else:
                # 检测失败时使用默认值
                risk_score = 0.5
                risk_level = "medium"
                ai_probability = None
                
    except Exception as e:
        print(f"AI 检测失败: {str(e)}")
        # 检测失败时使用默认值
        risk_score = 0.5
        risk_level = "medium"

    result = {
        "file_path": file_path,
        "sm3_hash": file_hash,
        "content_type": content_type,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "detect_status": "success"
    }
    
    # 如果有 AI 概率值，添加到结果中
    if ai_probability is not None:
        result["ai_probability"] = ai_probability
    
    # 如果是视频检测，返回完整结果（包含 frequency_analysis, deepfake_analysis, video_meta 等）
    if content_type == "video" and 'video_result' in locals():
        if video_result.get("status") == "success":
            # 合并视频检测的完整结果
            result.update({
                "frequency_analysis": video_result.get("frequency_analysis", {}),
                "deepfake_analysis": video_result.get("deepfake_analysis", {}),
                "video_meta": video_result.get("video_meta", {}),
                "merkle_root": video_result.get("merkle_root", ""),
                "certificate": video_result.get("certificate", {})
            })
    
    # 如果是图片检测，返回完整结果
    elif content_type == "image" and 'image_result' in locals():
        if image_result.get("status") == "success":
            result.update({
                "image_meta": image_result.get("image_meta", {}),
                "phash": image_result.get("phash", ""),
                "certificate": image_result.get("certificate", {})
            })
    
    # 如果是文本检测，返回完整结果
    elif content_type == "text" and 'text_result' in locals():
        if text_result.get("status") == "success":
            result.update({
                "text_meta": text_result.get("text_meta", {}),
                "simhash": text_result.get("simhash", ""),
                "certificate": text_result.get("certificate", {})
            })
    
    return result
