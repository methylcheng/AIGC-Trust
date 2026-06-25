"""
图片AIGC检测完整流程（与视频检测保持一致）
包含：预处理 → AI检测 → 指纹构建 → 融合打分 → 证书生成 → 日志审计
"""
import os
import uuid
import json
from datetime import datetime

# 导入各功能模块
from inference.image_ai_det import image_ai_score
from fingerprint.phash_img import calc_phash
from crypto.sm3_hash import get_file_sm3, str_sm3
from core.fusion_decide import fusion_risk
from cert.cert_gen import build_cert_json
from audit.audit_log import create_audit
from db.db_conn import get_db_session
from db.models import Content, DetectionTask, FingerPrint, Cert, ModelResult
import cv2
import numpy as np


def detect_image_aigc(
    image_path: str,
    edge_node_id: str = "center",
    use_deep_model: bool = True,
    task_id: str = None,  # 新增参数：如果提供则使用现有任务，否则创建新任务
    user_id: int = None   # 新增参数：用户ID
) -> dict:
    """
    图片AIGC检测完整流程
    
    Args:
        image_path: 图片文件路径
        edge_node_id: 边缘节点ID（默认为中心平台）
        use_deep_model: 是否使用深度学习模型（否则使用启发式快速检测）
        task_id: 任务ID（可选，由消费者传入时不创建新任务）
    
    Returns:
        检测结果字典，包含所有分析数据和证书信息
    """
    # 如果没有传入task_id，则生成新的；否则使用传入的
    if task_id is None:
        task_id = str(uuid.uuid4())
        print(f"\n{'='*60}")
        print(f"开始图片AIGC检测 - 任务ID: {task_id} (新建)")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"开始图片AIGC检测 - 任务ID: {task_id} (复用)")
        print(f"{'='*60}\n")
    
    try:
        # ==================== 步骤1: 验证文件 ====================
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        print("[步骤1/7] 验证图片文件...")
        file_size = os.path.getsize(image_path)
        print(f"  文件大小: {file_size / (1024*1024):.2f} MB")
        
        # ==================== 步骤2: 计算SM3哈希 ====================
        print("\n[步骤2/7] 计算图片SM3哈希...")
        image_sm3 = get_file_sm3(image_path)
        print(f"  SM3: {image_sm3[:32]}...")
        
        # ==================== 步骤3: 图片预处理（统一标准） ====================
        print("\n[步骤3/7] 图片预处理（统一640x360标准）...")
        
        # 读取图片（支持中文路径）
        img_array = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("无法解码图片文件")
        
        original_height, original_width = img.shape[:2]
        
        # 统一缩放到640x360（与视频帧保持一致）
        target_width, target_height = 640, 360
        img_resized = cv2.resize(img, (target_width, target_height), cv2.INTER_AREA)
        
        image_meta = {
            'original_width': original_width,
            'original_height': original_height,
            'processed_width': target_width,
            'processed_height': target_height,
            'channels': img.shape[2] if len(img.shape) > 2 else 1
        }
        
        print(f"  原始分辨率: {original_width}x{original_height}")
        print(f"  处理后分辨率: {target_width}x{target_height}")
        print(f"  通道数: {image_meta['channels']}")
        
        # ==================== 步骤4: AI检测 ====================
        print("\n[步骤4/7] AI生成内容检测...")
        
        if use_deep_model:
            print("  [4.1] 使用深度学习模型检测...")
            ai_probability = image_ai_score(image_path=image_path)
            print(f"    AI生成概率: {ai_probability:.4f}")
        else:
            print("  [4.1] 使用启发式快速检测...")
            # 启发式方法（如果需要可以单独实现）
            ai_probability = 0.5  # 默认值
            print(f"    AI概率估算: {ai_probability:.4f}")
        
        # ==================== 步骤5: 图片指纹构建 ====================
        print("\n[步骤5/7] 构建图片指纹（pHash）...")
        
        phash_value = calc_phash(img_resized)
        print(f"  pHash指纹: {phash_value[:32]}...")
        
        # 同时计算图片内容的SM3哈希作为辅助指纹
        content_bytes = img_resized.tobytes()
        content_sm3 = str_sm3(content_bytes.hex())
        print(f"  内容SM3: {content_sm3[:32]}...")
        
        # ==================== 步骤6: 多通道融合打分定级 ====================
        print("\n[步骤6/7] 多通道融合打分定级...")
        
        # 提取关键指标
        model_score = ai_probability
        
        # 简化的hash_match和cert_exist检查（实际应从数据库查询）
        hash_match = True  # TODO: 与历史指纹对比
        cert_exist = False  # 新图片暂无证书
        
        risk_level, final_score = fusion_risk(
            model_score=model_score,
            noise_score=0.0,  # 图片不使用噪声评分
            hash_match=hash_match,
            cert_exist=cert_exist
        )
        
        print(f"  模型评分: {model_score:.4f}")
        print(f"  最终风险分: {final_score:.4f}")
        print(f"  风险等级: {risk_level}")
        
        # ==================== 步骤7: 生成国密可信证书 ====================
        print("\n[步骤7/7] 生成国密可信证书...")
        print("  >>> DEBUG: build_cert_json 即将被调用 <<<")  # 调试标记
        
        content_id = image_sm3  # 使用SM3哈希作为内容ID
        
        cert_data = build_cert_json(
            content_id=content_id,
            content_type="image",
            sm3_hash=image_sm3,
            fingerprint=phash_value,
            model_version="image_detector_v1.0",
            detection_score=final_score,
            risk_level=risk_level,
            watermark_result="none",  # TODO: 水印检测
            edge_node_id=edge_node_id
        )
        
        print(f"  >>> DEBUG: build_cert_json 已返回 <<<")  # 调试标记
        print(f"  证书ID: {cert_data['certificate_id']}")
        print(f"  签发时间: {cert_data['issued_at']}")
        print(f"  签名算法: SM2")
        
        # ==================== 步骤8: 日志审计存入数据库 ====================
        print("\n[步骤8/8] 日志审计和数据持久化...")
        
        db = get_db_session()
        
        try:
            # 8.1 保存或更新内容记录（处理重复检测）
            existing_content = db.query(Content).filter(Content.content_id == content_id).first()
            if existing_content:
                # 已存在，更新信息
                print(f"  ℹ️  内容记录已存在，更新检测数据...")
                existing_content.path = image_path
                existing_content.source = edge_node_id
                existing_content.created_at = datetime.now()
            else:
                # 不存在，新建记录
                content = Content(
                    content_id=content_id,
                    user_id=user_id if user_id else 1,  # 使用传入的user_id，默认为1
                    type="image",
                    path=image_path,
                    sm3_hash=image_sm3,
                    source=edge_node_id
                )
                db.add(content)
            
            db.flush()  # 立即刷新，确保 content_id 存在
            
            # 8.2 准备任务结果数据
            task_result = {
                "risk_level": risk_level,
                "final_score": final_score,
                "ai_probability": ai_probability,
                "image_meta": image_meta
            }
            
            # 8.3 保存或更新检测任务（避免重复创建）
            existing_task = db.query(DetectionTask).filter(DetectionTask.task_id == task_id).first()
            if existing_task:
                # 任务已存在（由消费者创建），只更新结果
                print(f"  ℹ️  任务记录已存在，更新检测结果...")
                existing_task.status = "completed"
                existing_task.progress = 1.0
                existing_task.node_id = edge_node_id
                existing_task.result = json.dumps(task_result, ensure_ascii=False)
            else:
                # 任务不存在（直接调用检测器时创建）
                task = DetectionTask(
                    task_id=task_id,
                    content_id=content_id,
                    user_id=user_id if user_id else 1,  # 使用传入的user_id，默认为1
                    status="completed",
                    progress=1.0,
                    node_id=edge_node_id,
                    result=json.dumps(task_result, ensure_ascii=False)
                )
                db.add(task)
            
            # 8.4 保存图片指纹
            fingerprint = FingerPrint(
                content_id=content_id,
                phash=phash_value,
                simhash="",
                frame_merkle_root=""  # 图片不使用Merkle树
            )
            db.add(fingerprint)
            
            # 8.5 保存模型结果
            model_result = ModelResult(
                task_id=task_id,
                model_name="image_aigc_detector",
                model_version="v1.0",
                score=final_score,
                label=risk_level
            )
            db.add(model_result)
            
            # 8.6 保存证书
            cert = Cert(
                cert_id=cert_data['certificate_id'],
                content_id=content_id,
                user_id=user_id if user_id else 1,  # 使用传入的user_id，默认为1
                risk_level=risk_level,
                signature=json.dumps(cert_data, ensure_ascii=False)
            )
            db.add(cert)
            
            db.commit()
            print("  ✓ 数据已存入数据库")
            
        except Exception as e:
            db.rollback()
            print(f"  ✗ 数据库保存失败: {e}")
            raise
        finally:
            db.close()
        
        # 8.7 创建审计日志
        audit_action = f"图片AIGC检测完成 - 风险等级:{risk_level}, 评分:{final_score:.4f}"
        log_hash = create_audit(action=audit_action, operator=edge_node_id)
        print(f"  ✓ 审计日志已记录: {log_hash[:16]}...")
        
        # ==================== 汇总结果 ====================
        print(f"\n{'='*60}")
        print(f"检测完成！")
        print(f"{'='*60}")
        print(f"  任务ID: {task_id}")
        print(f"  内容ID: {content_id}")
        print(f"  风险等级: {risk_level}")
        print(f"  风险评分: {final_score:.4f}")
        print(f"  AI概率: {ai_probability:.4f}")
        print(f"  证书ID: {cert_data['certificate_id']}")
        print(f"{'='*60}\n")
        
        return {
            "task_id": task_id,
            "content_id": content_id,
            "status": "success",
            "risk_level": risk_level,
            "risk_score": final_score,
            "ai_probability": ai_probability,
            "image_meta": image_meta,
            "phash": phash_value,
            "certificate": cert_data,
            "sm3_hash": image_sm3
        }
        
    except Exception as e:
        print(f"\n✗ 检测失败: {str(e)}")
        
        # 记录失败的审计日志
        try:
            create_audit(
                action=f"图片AIGC检测失败: {str(e)}",
                operator=edge_node_id
            )
        except:
            pass
        
        return {
            "task_id": task_id,
            "status": "error",
            "error_message": str(e)
        }


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) > 1:
        image_file = sys.argv[1]
        result = detect_image_aigc(image_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("用法: python image_detector.py <图片文件路径>")
