"""
统计 API - 提供平台统计数据
"""
import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter, HTTPException
from db.db_conn import get_db_session
from db.models import DetectionTask, Content, Cert, EdgeNode

router = APIRouter()

@router.get("/overview")
async def get_statistics():
    """获取平台整体统计数据"""
    try:
        db = get_db_session()
        
        # 总检测次数
        total_tasks = db.query(DetectionTask).count()
        
        # 按状态统计
        pending_count = db.query(DetectionTask).filter(DetectionTask.status == "pending").count()
        processing_count = db.query(DetectionTask).filter(DetectionTask.status == "processing").count()
        completed_count = db.query(DetectionTask).filter(DetectionTask.status == "completed").count()
        failed_count = db.query(DetectionTask).filter(DetectionTask.status == "failed").count()
        
        # 内容统计
        total_contents = db.query(Content).count()
        video_count = db.query(Content).filter(Content.type == "video").count()
        image_count = db.query(Content).filter(Content.type == "image").count()
        text_count = db.query(Content).filter(Content.type == "text").count()
        
        # 证书统计
        total_certs = db.query(Cert).count()
        
        # 边缘节点统计
        total_edge_nodes = db.query(EdgeNode).count()
        active_edge_nodes = db.query(EdgeNode).filter(EdgeNode.status == "active").count()
        
        # 风险等级分布（从已完成的任务中统计）
        completed_tasks = db.query(DetectionTask).filter(DetectionTask.status == "completed").all()
        
        risk_stats = {
            "trusted": 0,  # 可信
            "suspicious": 0,  # 可疑
            "fake": 0  # 伪造
        }
        
        for task in completed_tasks:
            if task.result:
                try:
                    result_data = eval(task.result) if isinstance(task.result, str) else task.result
                    risk_level = result_data.get("risk_level", "")
                    
                    if risk_level == "可信":
                        risk_stats["trusted"] += 1
                    elif risk_level == "可疑":
                        risk_stats["suspicious"] += 1
                    elif risk_level == "伪造":
                        risk_stats["fake"] += 1
                except:
                    pass
        
        db.close()
        
        return {
            "total_detections": total_tasks,
            "total_contents": total_contents,
            "total_certificates": total_certs,
            "edge_nodes": {
                "total": total_edge_nodes,
                "active": active_edge_nodes
            },
            "task_status": {
                "pending": pending_count,
                "processing": processing_count,
                "completed": completed_count,
                "failed": failed_count
            },
            "content_types": {
                "video": video_count,
                "image": image_count,
                "text": text_count
            },
            "risk_distribution": risk_stats
        }
        
    except Exception as e:
        print("获取统计数据失败:", str(e))
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
