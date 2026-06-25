import json
import pika
import sys
import os

# 动态加载项目根路径
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURR_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from db.db_conn import get_db_session
from db.models import DetectionTask, Content, FingerPrint, Cert
from core.multimodal_analyzer import analyze_content
from fingerprint.phash_img import calc_phash
from cert.cert_gen import build_cert_json
from crypto.trust_chain import get_trust_anchor
import cv2

def callback(ch, method, properties, body):
    data = json.loads(body)
    task_id = data["task_id"]
    content_id = data["content_id"]
    node_id = data["node_id"]

    print(f"收到任务: {task_id}, 内容ID: {content_id}")

    db = get_db_session()
    task = db.query(DetectionTask).filter(DetectionTask.task_id == task_id).first()
    if not task:
        print(f"任务记录不存在: {task_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        db.close()
        return

    # 更新状态为运行中
    task.status = "running"
    task.progress = 0.1
    db.commit()

    # 查询文件信息
    content = db.query(Content).filter(Content.content_id == content_id).first()
    if not content:
        print(f"文件记录不存在: {content_id}")
        task.status = "failed"
        task.progress = 1.0
        db.commit()
        db.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    file_path = content.path
    task.progress = 0.3
    db.commit()

    try:
        # 执行内容分析（传递 task_id 和 user_id）
        result = analyze_content(file_path, content.type, task_id, user_id=task.user_id)
        task.progress = 0.6
        db.commit()

        # 生成指纹（根据内容类型）
        phash_value = None
        simhash_value = None
        merkle_root = None
        
        if content.type == "image":
            try:
                # 使用 numpy + imdecode 支持中文路径
                import numpy as np
                img_array = np.fromfile(file_path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    phash_value = calc_phash(img)
                    print(f"图片pHash生成完成: {phash_value[:16]}...")
                else:
                    print(f"无法解码图片: {file_path}")
            except Exception as e:
                print(f"生成图片指纹失败: {str(e)}")
        
        # 保存指纹到数据库
        if phash_value or simhash_value or merkle_root:
            fp = FingerPrint(
                content_id=content_id,
                phash=phash_value,
                simhash=simhash_value,
                frame_merkle_root=merkle_root
            )
            db.add(fp)
            db.commit()
            print(f"指纹已保存")
        
        task.progress = 0.8
        db.commit()

        # 注意：证书已在检测模块（image_detector/video_detector/text_detector）中生成
        # 这里只需要从 result 中提取证书信息即可，不需要重复生成

        # 写入分析结果到 result 字段
        task.status = "completed"  # 使用 completed 而不是 success，与前端保持一致
        task.progress = 1.0
        task.result = json.dumps(result, ensure_ascii=False)
        db.commit()
        print(f"任务完成: {task_id}")

    except Exception as e:
        print(f"任务处理异常: {str(e)}")
        task.status = "failed"
        task.progress = 1.0
        task.result = json.dumps({"error": str(e)}, ensure_ascii=False)
        db.commit()

    db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    # 初始化信任系统，确保加载正确的密钥
    print("\n" + "="*60)
    print("初始化信任系统...")
    try:
        anchor = get_trust_anchor()
        print(f"✓ 信任系统初始化完成")
        print(f"  CA ID: {anchor.root_ca_config['ca_id']}")
        print(f"  算法: {anchor.root_ca_config['algorithm']}")
    except Exception as e:
        print(f"✗ 信任系统初始化失败: {str(e)}")
        print("请检查密钥文件是否存在，或手动初始化系统")
        return
    print("="*60 + "\n")
    
    # 连接 RabbitMQ
    credentials = pika.PlainCredentials("guest", "guest")
    conn_params = pika.ConnectionParameters("localhost", 5672, "/", credentials)
    
    try:
        conn = pika.BlockingConnection(conn_params)
    except pika.exceptions.AMQPConnectionError as e:
        print(f"错误: 无法连接到 RabbitMQ")
        print(f"请检查:")
        print(f"  1. RabbitMQ 服务是否正在运行")
        print(f"  2. 端口 5672 是否可访问 (netstat -ano | findstr :5672)")
        print(f"  3. 能否访问 http://localhost:15672")
        print(f"\n详细错误: {str(e)}")
        return
    
    ch = conn.channel()

    queue_name = "aigc_trust_task"
    ch.queue_declare(queue=queue_name, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=queue_name, on_message_callback=callback)

    print("AIGC-Trust 消费者启动完成，等待任务...")
    ch.start_consuming()

if __name__ == "__main__":
    start_consumer()
