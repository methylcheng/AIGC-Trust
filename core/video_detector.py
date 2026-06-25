"""
视频AIGC检测完整流程
包含：抽帧 → 频域取证 + 深度伪造检测 → 指纹构建 → 融合打分 → 证书生成 → 日志审计
支持 FFmpeg + OpenCV GPU 加速预处理
"""
import os
import uuid
import json
from datetime import datetime

# 导入各功能模块
from core.video_preprocess_gpu import get_gpu_processor
from core.frequency_analysis import analyze_video_frequency
# GPU加速版本：使用PyTorch ViT模型
try:
    from inference.video_face_fake_gpu import video_fake_score
    print("✅ 视频检测启用 PyTorch GPU 加速")
except ImportError:
    # 降级到原有MindSpore CPU版本
    from inference.video_face_fake import video_fake_score
    print("⚠️  使用 MindSpore CPU 版本（较慢）")
from fingerprint.merkle_video import build_merkle_root
from crypto.sm3_hash import get_file_sm3, str_sm3
from core.fusion_decide import fusion_risk
from cert.cert_gen import build_cert_json
from audit.audit_log import create_audit
from db.db_conn import get_db_session
from db.models import Content, DetectionTask, FrequencyFeature, FingerPrint, Cert, ModelResult


def detect_video_aigc(
    video_path: str,
    edge_node_id: str = "center",
    use_deep_model: bool = True,
    use_gpu: bool = True,
    gpu_method: str = "ffmpeg",
    task_id: str = None,  # 新增参数：如果提供则使用现有任务，否则创建新任务
    user_id: int = None   # 新增参数：用户ID
) -> dict:
    """
    视频AIGC检测完整流程
    
    Args:
        video_path: 视频文件路径
        edge_node_id: 边缘节点ID（默认为中心平台）
        use_deep_model: 是否使用深度学习模型（否则使用启发式快速检测）
        use_gpu: 是否使用GPU加速预处理
        gpu_method: GPU预处理方法 ('ffmpeg' 或 'opencv')
        task_id: 任务ID（可选，由消费者传入时不创建新任务）
    
    Returns:
        检测结果字典，包含所有分析数据和证书信息
    """
    # 如果没有传入task_id，则生成新的；否则使用传入的
    if task_id is None:
        task_id = str(uuid.uuid4())
        print(f"\n{'='*60}")
        print(f"开始视频AIGC检测 - 任务ID: {task_id} (新建)")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"开始视频AIGC检测 - 任务ID: {task_id} (复用)")
        print(f"{'='*60}\n")
    
    try:
        # ==================== 步骤1: 验证文件 ====================
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        print("[步骤1/8] 验证视频文件...")
        file_size = os.path.getsize(video_path)
        print(f"  文件大小: {file_size / (1024*1024):.2f} MB")
        
        # ==================== 步骤2: 计算SM3哈希 ====================
        print("\n[步骤2/8] 计算视频SM3哈希...")
        video_sm3 = get_file_sm3(video_path)
        print(f"  SM3: {video_sm3[:32]}...")
        
        # ==================== 步骤3: 视频预处理和抽帧（GPU加速） ====================
        print("\n[步骤3/8] 视频预处理和抽帧（GPU加速）...")
        
        # 使用GPU处理器
        processor = get_gpu_processor(use_gpu=use_gpu)
        
        if use_gpu and gpu_method.lower() == "ffmpeg":
            # FFmpeg GPU解码 + CUDA缩放（高精度模式：更多帧）
            frames, video_meta = processor.extract_frames_ffmpeg_gpu(
                video_path,
                sample_interval=5,      # 从10改为5，抽取更密集
                max_frames=100,         # 从50改为100，最多100帧
                target_width=640,
                target_height=360
            )
        elif use_gpu and gpu_method.lower() == "opencv":
            # OpenCV CUDA处理（高精度模式：更多帧）
            frames, video_meta = processor.extract_frames_opencv_gpu(
                video_path,
                sample_interval=5,      # 从10改为5
                max_frames=100,         # 从50改为100
                target_size=(640, 360)
            )
        else:
            # 降级到CPU模式（原有方法）
            from core.multimodal_pre import preprocess_video
            frames, video_meta = preprocess_video(
                video_path,
                sample_interval=5,      # 从10改为5
                max_frames=100          # 从50改为100
            )
            video_meta['extraction_method'] = 'cpu_legacy'
        
        print(f"  总帧数: {video_meta.get('total_frames', video_meta.get('total_frame', 0))}")
        print(f"  抽取帧数: {video_meta['sampled_frames']}")
        print(f"  视频时长: {video_meta.get('duration', 0):.2f}秒")
        print(f"  分辨率: {video_meta.get('width', 0)}x{video_meta.get('height', 0)}")
        print(f"  处理方法: {video_meta.get('extraction_method', 'unknown')}")
        
        if not frames:
            raise ValueError("无法从视频中抽取帧")
        
        # ==================== 步骤4: 多维度取证检测 ====================
        print("\n[步骤4/8] 多维度取证检测...")
        
        # 4.1 频域取证分析（高精度模式）
        print("  [4.1] 频域取证分析（多尺度噪声 + 多频段FFT + 时序一致性）...")
        freq_result = analyze_video_frequency(frames, high_precision=True)
        print(f"    平均噪声分数: {freq_result['avg_noise_score']}")
        print(f"    噪声方差: {freq_result['noise_variance']}")
        print(f"    高频异常指数: {freq_result['high_freq_anomaly']}")
        if 'temporal_consistency_score' in freq_result:
            print(f"    时序一致性评分: {freq_result['temporal_consistency_score']}")
        
        # 4.2 深度伪造模型检测
        print(f"  [4.2] 深度伪造检测（{'深度学习模型' if use_deep_model else '启发式快速检测'}）...")
        deepfake_result = video_fake_score(frames, use_model_scoring=use_deep_model)
        print(f"    平均AI概率: {deepfake_result['avg_score']}")
        print(f"    最大AI概率: {deepfake_result['max_score']}")
        print(f"    高风险帧比例: {deepfake_result['high_risk_frame_ratio']}")
        print(f"    时序一致性(方差): {deepfake_result['score_variance']}")
        
        # ==================== 步骤5: 视频指纹构建 ====================
        print("\n[步骤5/8] 构建视频指纹（Merkle树）...")
        frame_hashes = []
        for i, frame in enumerate(frames):
            # 对每帧计算SM3哈希
            frame_bytes = frame.tobytes()
            frame_hash = str_sm3(frame_bytes.hex())
            frame_hashes.append(frame_hash)
        
        merkle_root = build_merkle_root(frame_hashes)
        print(f"  Merkle根哈希: {merkle_root[:32]}...")
        print(f"  帧哈希数量: {len(frame_hashes)}")
        
        # ==================== 步骤6: 多通道融合打分定级（增强版） ====================
        print("\n[步骤6/8] 多通道融合打分定级（增强版）...")
        
        # 提取关键指标
        model_score = deepfake_result['avg_score']
        noise_score = freq_result['avg_noise_score']
        
        # 新增：使用时序一致性作为额外特征
        temporal_score = freq_result.get('temporal_consistency_score', 0.5)
        high_freq_anomaly = freq_result.get('high_freq_anomaly', 0.5)
        
        # 简化的hash_match和cert_exist检查（实际应从数据库查询）
        hash_match = True  # TODO: 与历史指纹对比
        cert_exist = False  # 新视频暂无证书
        
        # 增强版融合决策：加入时序一致性和频域特征
        risk_level, final_score = fusion_risk(
            model_score=model_score,
            noise_score=noise_score,
            hash_match=hash_match,
            cert_exist=cert_exist,
            temporal_score=temporal_score,      # 新增
            high_freq_anomaly=high_freq_anomaly  # 新增
        )
        
        print(f"  模型评分: {model_score:.4f}")
        print(f"  噪声评分: {noise_score:.4f}")
        print(f"  最终风险分: {final_score:.4f}")
        print(f"  风险等级: {risk_level}")
        
        # ==================== 步骤7: 生成国密可信证书 ====================
        print("\n[步骤7/8] 生成国密可信证书...")
        
        content_id = video_sm3  # 使用SM3哈希作为内容ID
        
        cert_data = build_cert_json(
            content_id=content_id,
            content_type="video",
            sm3_hash=video_sm3,
            fingerprint=merkle_root,
            model_version="video_detector_v1.0",
            detection_score=final_score,
            risk_level=risk_level,
            watermark_result="none",  # TODO: 水印检测
            edge_node_id=edge_node_id
        )
        
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
                existing_content.path = video_path
                existing_content.source = edge_node_id
                existing_content.created_at = datetime.now()
            else:
                # 不存在，新建记录
                content = Content(
                    content_id=content_id,
                    user_id=user_id if user_id else 1,  # 使用传入的user_id，默认为1
                    type="video",
                    path=video_path,
                    sm3_hash=video_sm3,
                    source=edge_node_id
                )
                db.add(content)
            
            db.flush()  # 立即刷新，确保 content_id 存在
            
            # 8.2 准备任务结果数据
            task_result = {
                "risk_level": risk_level,
                "final_score": final_score,
                "freq_analysis": freq_result,
                "deepfake_analysis": deepfake_result,
                "video_meta": video_meta
            }
            
            # 8.3 保存或更新检测任务（避免重复创建）
            existing_task = db.query(DetectionTask).filter(DetectionTask.task_id == task_id).first()
            if existing_task:
                # 任务已存在（由消费者创建），只更新结果
                print(f"  ️  任务记录已存在，更新检测结果...")
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
            
            # 8.4 保存频域特征
            freq_feature = FrequencyFeature(
                content_id=content_id,
                fft_feature=json.dumps(freq_result),
                dct_feature="",  # 可选
                noise_score=freq_result['avg_noise_score']
            )
            db.add(freq_feature)
            
            # 8.5 保存视频指纹
            fingerprint = FingerPrint(
                content_id=content_id,
                phash="",  # 视频不使用pHash
                simhash="",
                frame_merkle_root=merkle_root
            )
            db.add(fingerprint)
            
            # 8.6 保存模型结果
            model_result = ModelResult(
                task_id=task_id,
                model_name="video_deepfake_detector",
                model_version="v1.0",
                score=final_score,
                label=risk_level
            )
            db.add(model_result)
            
            # 8.7 保存证书
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
        
        # 8.8 创建审计日志
        audit_action = f"视频AIGC检测完成 - 风险等级:{risk_level}, 评分:{final_score:.4f}"
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
        print(f"  证书ID: {cert_data['certificate_id']}")
        print(f"{'='*60}\n")
        
        return {
            "task_id": task_id,
            "content_id": content_id,
            "status": "success",
            "risk_level": risk_level,
            "risk_score": final_score,
            "video_meta": video_meta,
            "frequency_analysis": freq_result,
            "deepfake_analysis": deepfake_result,
            "merkle_root": merkle_root,
            "certificate": cert_data,
            "sm3_hash": video_sm3
        }
        
    except Exception as e:
        print(f"\n✗ 检测失败: {str(e)}")
        
        # 记录失败的审计日志
        try:
            create_audit(
                action=f"视频AIGC检测失败: {str(e)}",
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
        video_file = sys.argv[1]
        result = detect_video_aigc(video_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("用法: python video_detector.py <视频文件路径>")
