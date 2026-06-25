"""
openEuler 边缘轻量化视频检测
针对边缘设备优化的快速检测流程，减少计算资源消耗
支持 FFmpeg + OpenCV GPU 加速预处理
"""
import os
import uuid
import json
from datetime import datetime

from core.video_preprocess_gpu import get_gpu_processor
from core.frequency_analysis import analyze_video_frequency, calc_noise_residual
from fingerprint.merkle_video import build_merkle_root
from crypto.sm3_hash import get_file_sm3, str_sm3
from core.fusion_decide import fusion_risk
from cert.cert_gen import build_cert_json
from audit.audit_log import create_audit
from db.db_conn import get_db_session
from db.models import Content, DetectionTask, FrequencyFeature, FingerPrint, Cert, ModelResult


def detect_video_edge_lightweight(
    video_path: str,
    edge_node_id: str = "edge_01",
    use_gpu: bool = True,
    user_id: int = None   # 新增参数：用户ID
) -> dict:
    """
    openEuler边缘轻量化视频检测
    
    优化策略：
    1. 减少抽帧数量（最多20帧）
    2. 使用启发式快速检测（不加载深度学习模型）
    3. 简化频域分析（仅噪声残差）
    4. 降低分辨率处理（最大480p）
    5. GPU加速预处理（可选）
    
    Args:
        video_path: 视频文件路径
        edge_node_id: 边缘节点ID
        use_gpu: 是否使用GPU加速
    
    Returns:
        检测结果字典
    """
    task_id = str(uuid.uuid4())
    print(f"\n{'='*60}")
    print(f"openEuler边缘轻量化检测 - 任务ID: {task_id}")
    print(f"节点ID: {edge_node_id}")
    print(f"{'='*60}\n")
    
    try:
        # ==================== 步骤1: 验证文件 ====================
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        print("[步骤1/6] 验证视频文件...")
        file_size = os.path.getsize(video_path)
        print(f"  文件大小: {file_size / (1024*1024):.2f} MB")
        
        # ==================== 步骤2: 计算SM3哈希 ====================
        print("\n[步骤2/6] 计算SM3哈希...")
        video_sm3 = get_file_sm3(video_path)
        print(f"  SM3: {video_sm3[:32]}...")
        
        # ==================== 步骤3: 轻量化抽帧（GPU加速） ====================
        print("\n[步骤3/6] 轻量化抽帧（最大20帧，480p）...")
        
        processor = get_gpu_processor(use_gpu=use_gpu)
        
        if use_gpu:
            # 使用FFmpeg GPU加速（边缘模式：适中精度）
            frames, video_meta = processor.extract_frames_ffmpeg_gpu(
                video_path,
                sample_interval=15,  # 从30改为15，抽取更多帧
                max_frames=40,       # 从20改为40，提高精度
                target_width=640,
                target_height=360
            )
        else:
            # CPU模式
            from core.multimodal_pre import preprocess_video
            frames, video_meta = preprocess_video(
                video_path,
                sample_interval=15,  # 从30改为15
                max_frames=40        # 从20改为40
            )
            video_meta['extraction_method'] = 'cpu_legacy'
        
        print(f"  总帧数: {video_meta.get('total_frames', video_meta.get('total_frame', 0))}")
        print(f"  抽取帧数: {video_meta['sampled_frames']}")
        print(f"  视频时长: {video_meta.get('duration', 0):.2f}秒")
        print(f"  处理方法: {video_meta.get('extraction_method', 'unknown')}")
        
        if not frames:
            raise ValueError("无法从视频中抽取帧")
        
        # ==================== 步骤4: 快速取证检测 ====================
        print("\n[步骤4/6] 快速取证检测（仅噪声分析）...")
        
        # 简化的频域分析（仅噪声残差）
        noise_scores = []
        for frame in frames:
            noise = calc_noise_residual(frame)
            noise_scores.append(noise)
        
        avg_noise = sum(noise_scores) / len(noise_scores)
        
        freq_result = {
            "avg_noise_score": round(avg_noise, 4),
            "noise_variance": 0.0,  # 边缘端省略方差计算
            "high_freq_anomaly": 0.0,  # 边缘端省略FFT
            "frame_count": len(frames)
        }
        
        print(f"  平均噪声分数: {freq_result['avg_noise_score']}")
        
        # 启发式快速评分（不加载深度学习模型）
        from inference.video_face_fake import _heuristic_video_detect
        
        quick_scores = []
        for frame in frames:
            score = _heuristic_video_detect(frame)
            quick_scores.append(score)
        
        import numpy as np
        scores_array = np.array(quick_scores)
        
        deepfake_result = {
            "avg_score": round(float(np.mean(scores_array)), 4),
            "max_score": round(float(np.max(scores_array)), 4),
            "score_variance": round(float(np.var(scores_array)), 4),
            "high_risk_frame_ratio": round(float(np.sum(scores_array > 0.7) / len(scores_array)), 4),
            "total_frames": len(frames),
            "method": "heuristic_fast"
        }
        
        print(f"  快速AI概率: {deepfake_result['avg_score']}")
        print(f"  高风险帧比例: {deepfake_result['high_risk_frame_ratio']}")
        
        # ==================== 步骤5: 构建轻量指纹 ====================
        print("\n[步骤5/6] 构建轻量指纹...")
        
        # 仅对关键帧计算哈希（每5帧取1帧）
        key_frame_hashes = []
        for i in range(0, len(frames), 5):
            frame_bytes = frames[i].tobytes()
            frame_hash = str_sm3(frame_bytes.hex())
            key_frame_hashes.append(frame_hash)
        
        merkle_root = build_merkle_root(key_frame_hashes)
        print(f"  Merkle根哈希: {merkle_root[:32]}...")
        print(f"  关键帧数量: {len(key_frame_hashes)}")
        
        # ==================== 步骤6: 融合打分和证书生成 ====================
        print("\n[步骤6/6] 融合打分和生成证书...")
        
        model_score = deepfake_result['avg_score']
        noise_score = freq_result['avg_noise_score']
        
        hash_match = True
        cert_exist = False
        
        risk_level, final_score = fusion_risk(
            model_score=model_score,
            noise_score=noise_score,
            hash_match=hash_match,
            cert_exist=cert_exist
        )
        
        print(f"  最终风险分: {final_score:.4f}")
        print(f"  风险等级: {risk_level}")
        
        # 生成证书
        content_id = video_sm3
        
        cert_data = build_cert_json(
            content_id=content_id,
            content_type="video",
            sm3_hash=video_sm3,
            fingerprint=merkle_root,
            model_version="edge_lightweight_v1.0",
            detection_score=final_score,
            risk_level=risk_level,
            watermark_result="none",
            edge_node_id=edge_node_id
        )
        
        print(f"  证书ID: {cert_data['certificate_id']}")
        
        # 数据持久化
        db = get_db_session()
        
        try:
            # 保存或更新内容记录（处理重复检测）
            existing_content = db.query(Content).filter(Content.content_id == content_id).first()
            if existing_content:
                print(f"  ℹ️  内容记录已存在，更新检测数据...")
                existing_content.path = video_path
                existing_content.source = edge_node_id
                existing_content.created_at = datetime.now()
            else:
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
            
            # 保存检测任务
            task_result = {
                "risk_level": risk_level,
                "final_score": final_score,
                "freq_analysis": freq_result,
                "deepfake_analysis": deepfake_result,
                "video_meta": video_meta,
                "mode": "edge_lightweight"
            }
            
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
            
            # 保存频域特征
            freq_feature = FrequencyFeature(
                content_id=content_id,
                fft_feature=json.dumps(freq_result),
                dct_feature="",
                noise_score=freq_result['avg_noise_score']
            )
            db.add(freq_feature)
            
            # 保存视频指纹
            fingerprint = FingerPrint(
                content_id=content_id,
                phash="",
                simhash="",
                frame_merkle_root=merkle_root
            )
            db.add(fingerprint)
            
            # 保存模型结果
            model_result = ModelResult(
                task_id=task_id,
                model_name="edge_lightweight_detector",
                model_version="v1.0",
                score=final_score,
                label=risk_level
            )
            db.add(model_result)
            
            # 保存证书
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
        
        # 审计日志
        audit_action = f"边缘轻量化视频检测完成 - 风险等级:{risk_level}, 评分:{final_score:.4f}"
        log_hash = create_audit(action=audit_action, operator=edge_node_id)
        print(f"  ✓ 审计日志已记录")
        
        print(f"\n{'='*60}")
        print(f"边缘检测完成！")
        print(f"{'='*60}")
        print(f"  任务ID: {task_id}")
        print(f"  风险等级: {risk_level}")
        print(f"  风险评分: {final_score:.4f}")
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
            "sm3_hash": video_sm3,
            "mode": "edge_lightweight"
        }
        
    except Exception as e:
        print(f"\n✗ 边缘检测失败: {str(e)}")
        
        try:
            create_audit(
                action=f"边缘视频检测失败: {str(e)}",
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
    import sys
    
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        edge_node = sys.argv[2] if len(sys.argv) > 2 else "edge_01"
        result = detect_video_edge_lightweight(video_file, edge_node)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("用法: python video_detector_edge.py <视频文件路径> [边缘节点ID]")
