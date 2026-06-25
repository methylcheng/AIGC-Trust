"""
文本AIGC检测完整流程（与视频/图片检测保持一致）
包含：预处理 → AI检测 → 指纹构建 → 融合打分 → 证书生成 → 日志审计
支持 TXT、DOCX、PDF 格式
"""
import os
import uuid
import json
from datetime import datetime

# 导入各功能模块
from inference.bert_text_detector import text_ai_score
from fingerprint.simhash_text import text_simhash
from crypto.sm3_hash import get_file_sm3, str_sm3
from core.fusion_decide import fusion_risk
from cert.cert_gen import build_cert_json
from audit.audit_log import create_audit
from db.db_conn import get_db_session
from db.models import Content, DetectionTask, FingerPrint, Cert, ModelResult
from core.document_extractor import extract_text_from_file
from core.document_extractor import extract_text_from_file


def detect_text_aigc(
    text_path: str,
    edge_node_id: str = "center",
    use_deep_model: bool = True,
    task_id: str = None,  # 新增参数：如果提供则使用现有任务，否则创建新任务
    user_id: int = None   # 新增参数：用户ID
) -> dict:
    """
    文本AIGC检测完整流程
    
    Args:
        text_path: 文本文件路径（支持 .txt, .docx, .pdf）
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
        print(f"开始文本AIGC检测 - 任务ID: {task_id} (新建)")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"开始文本AIGC检测 - 任务ID: {task_id} (复用)")
        print(f"{'='*60}\n")
    
    try:
        # ==================== 步骤1: 验证文件 ====================
        if not os.path.exists(text_path):
            raise FileNotFoundError(f"文件不存在: {text_path}")
        
        file_ext = os.path.splitext(text_path)[1].lower()
        if file_ext not in ['.txt', '.docx', '.pdf']:
            raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 .txt, .docx, .pdf")
        
        print("\n[步骤1/7] 验证文件...")
        file_size = os.path.getsize(text_path)
        print(f"  文件大小: {file_size / 1024:.2f} KB")
        print(f"  文件格式: {file_ext}")
        
        # ==================== 步骤2: 计算SM3哈希 ====================
        print("\n[步骤2/7] 计算文本SM3哈希...")
        text_sm3 = get_file_sm3(text_path)
        print(f"  SM3: {text_sm3[:32]}...")
        
        # ==================== 步骤3: 文本提取与预处理 ====================
        print("\n[步骤3/7] 文本提取与预处理（标准化清洗）...")
        
        try:
            # 根据文件格式自动提取文本
            raw_text = extract_text_from_file(text_path)
            print(f"  ✓ 文本提取成功")
        except Exception as e:
            raise Exception(f"文本提取失败: {str(e)}")
        
        # 统计原始信息
        original_length = len(raw_text)
        original_lines = raw_text.count('\n') + 1
        
        # 标准化清洗
        cleaned_text = raw_text.replace('\n', ' ').replace('\r', ' ')
        cleaned_text = ' '.join(cleaned_text.split())  # 去除多余空格
        
        # 分词处理
        words = cleaned_text.split()
        word_count = len(words)
        
        text_meta = {
            'original_length': original_length,
            'original_lines': original_lines,
            'cleaned_length': len(cleaned_text),
            'word_count': word_count,
            'encoding': 'utf-8'
        }
        
        print(f"  原始长度: {original_length} 字符")
        print(f"  原始行数: {original_lines}")
        print(f"  清洗后长度: {len(cleaned_text)} 字符")
        print(f"  单词数量: {word_count}")
        
        # ==================== 步骤4: AI检测 ====================
        print("\n[步骤4/7] AI生成内容检测...")
        
        if use_deep_model:
            print("  [4.1] 使用深度学习模型检测...")
            # text_ai_score 接受文本内容，不是文件路径
            ai_probability = text_ai_score(cleaned_text)
            print(f"    AI生成概率: {ai_probability:.4f}")
        else:
            print("  [4.1] 使用启发式快速检测...")
            # 启发式方法（如果需要可以单独实现）
            ai_probability = 0.5  # 默认值
            print(f"    AI概率估算: {ai_probability:.4f}")
        
        # ==================== 步骤5: 文本指纹构建 ====================
        print("\n[步骤5/7] 构建文本指纹（SimHash）...")
        
        simhash_value = text_simhash(cleaned_text)
        print(f"  SimHash指纹: {simhash_value[:32]}...")
        
        # 同时计算文本内容的SM3哈希作为辅助指纹
        content_sm3 = str_sm3(cleaned_text.encode('utf-8').hex())
        print(f"  内容SM3: {content_sm3[:32]}...")
        
        # ==================== 步骤6: 多通道融合打分定级 ====================
        print("\n[步骤6/7] 多通道融合打分定级...")
        
        # 提取关键指标
        model_score = ai_probability
        
        # 简化的hash_match和cert_exist检查（实际应从数据库查询）
        hash_match = True  # TODO: 与历史指纹对比
        cert_exist = False  # 新文本暂无证书
        
        risk_level, final_score = fusion_risk(
            model_score=model_score,
            noise_score=0.0,  # 文本不使用噪声评分
            hash_match=hash_match,
            cert_exist=cert_exist
        )
        
        print(f"  模型评分: {model_score:.4f}")
        print(f"  最终风险分: {final_score:.4f}")
        print(f"  风险等级: {risk_level}")
        
        # ==================== 步骤7: 生成国密可信证书 ====================
        print("\n[步骤7/7] 生成国密可信证书...")
        
        content_id = text_sm3  # 使用SM3哈希作为内容ID
        
        cert_data = build_cert_json(
            content_id=content_id,
            content_type="text",
            sm3_hash=text_sm3,
            fingerprint=simhash_value,
            model_version="bert_text_detector_v2.0",
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
                existing_content.path = text_path
                existing_content.source = edge_node_id
                existing_content.created_at = datetime.now()
            else:
                # 不存在，新建记录
                content = Content(
                    content_id=content_id,
                    user_id=user_id if user_id else 1,  # 使用传入的user_id，默认为1
                    type="text",
                    path=text_path,
                    sm3_hash=text_sm3,
                    source=edge_node_id
                )
                db.add(content)
            
            db.flush()  # 立即刷新，确保 content_id 存在
            
            # 8.2 准备任务结果数据
            task_result = {
                "risk_level": risk_level,
                "final_score": final_score,
                "ai_probability": ai_probability,
                "text_meta": text_meta
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
            
            # 8.4 保存文本指纹
            fingerprint = FingerPrint(
                content_id=content_id,
                phash="",  # 文本不使用pHash
                simhash=simhash_value,
                frame_merkle_root=""  # 文本不使用Merkle树
            )
            db.add(fingerprint)
            
            # 8.5 保存模型结果
            model_result = ModelResult(
                task_id=task_id,
                model_name="bert_text_aigc_detector",
                model_version="v2.0",
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
        audit_action = f"文本AIGC检测完成 - 风险等级:{risk_level}, 评分:{final_score:.4f}"
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
            "text_meta": text_meta,
            "simhash": simhash_value,
            "certificate": cert_data,
            "sm3_hash": text_sm3
        }
        
    except Exception as e:
        print(f"\n✗ 检测失败: {str(e)}")
        
        # 记录失败的审计日志
        try:
            create_audit(
                action=f"文本AIGC检测失败: {str(e)}",
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
        text_file = sys.argv[1]
        result = detect_text_aigc(text_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("用法: python text_detector.py <文本文件路径>")
