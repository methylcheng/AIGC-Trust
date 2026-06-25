import sys
import os
import traceback
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter, HTTPException, Query, Depends
import uuid
import json
import pika
from typing import List, Optional
from pydantic import BaseModel
from db.db_conn import get_db_session
from db.models import DetectionTask, Content, ModelResult, Cert
from api.auth import get_current_user

router = APIRouter()

# 请求模型定义
class BatchDeleteRequest(BaseModel):
    task_ids: List[str]

# 0. 获取所有任务列表（新增）- 使用 /list 路径避免冲突
@router.get("/list")
async def get_all_tasks(
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: dict = Depends(get_current_user)
):
    """获取检测任务列表（仅当前用户的任务）"""
    try:
        db = get_db_session()
        
        # 构建查询 - 只查询当前用户的任务
        query = db.query(DetectionTask).filter(DetectionTask.user_id == current_user["user_id"])
        
        # 状态筛选
        if status:
            query = query.filter(DetectionTask.status == status)
        
        # 按创建时间倒序
        tasks = query.order_by(DetectionTask.created_at.desc())\
                    .offset(offset)\
                    .limit(limit)\
                    .all()
        
        # 转换为字典列表
        task_list = []
        for task in tasks:
            result_data = None
            if task.result:
                try:
                    result_data = json.loads(task.result)
                except:
                    result_data = task.result
            
            # 查询对应的内容类型
            content_type = None
            if task.content_id:
                content = db.query(Content).filter(Content.content_id == task.content_id).first()
                if content:
                    content_type = content.type  # Content表中的字段名是type
            
            task_list.append({
                "task_id": task.task_id,
                "content_id": task.content_id,
                "status": task.status,
                "progress": task.progress,
                "node_id": task.node_id,
                "content_type": content_type,  # 添加内容类型字段
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "result": result_data
            })
        
        db.close()
        
        return {
            "total": len(task_list),
            "tasks": task_list
        }
        
    except Exception as e:
        print("获取任务列表失败:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

# 1. 查询单个任务详情接口
@router.get("/{task_id}")
async def get_task_info(task_id: str):
    try:
        db = get_db_session()
        task = db.query(DetectionTask).filter(DetectionTask.task_id == task_id).first()
        db.close()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 解析result字段为JSON对象
        result_data = None
        if task.result:
            try:
                result_data = json.loads(task.result)
            except:
                result_data = task.result
        
        return {
            "task_id": task.task_id,
            "content_id": task.content_id,
            "status": task.status,
            "progress": task.progress,
            "node_id": task.node_id,
            "result": result_data
        }

    except Exception as e:
        print("查询任务失败:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

# 2. 创建任务接口（带日志）
@router.post("")
async def create_detect_task(
    content_id: str,
    edge_node_id: str = "local-01",
    current_user: dict = Depends(get_current_user)
):
    try:
        task_id = str(uuid.uuid4())
        print(f"创建任务: {task_id}, content_id: {content_id}, user_id: {current_user['user_id']}")

        db = get_db_session()
        new_task = DetectionTask(
            task_id=task_id,
            content_id=content_id,
            user_id=current_user["user_id"],
            status="pending",
            progress=0.0,
            node_id=edge_node_id
        )
        db.add(new_task)
        db.commit()
        db.close()

        conn = pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1"))
        ch = conn.channel()
        queue_name = "aigc_trust_task"
        ch.queue_declare(queue=queue_name, durable=True)
        
        body = json.dumps({
            "task_id": task_id,
            "content_id": content_id,
            "node_id": edge_node_id
        })
        
        ch.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        conn.close()
        
        print(f"消息已发送到队列 {queue_name}")
        return {"task_id": task_id}

    except Exception as e:
        print("创建任务失败:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

# 3. 删除单个任务
@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """删除单个检测任务（级联删除相关数据）"""
    try:
        db = get_db_session()
        
        # 检查任务是否存在
        task = db.query(DetectionTask).filter(DetectionTask.task_id == task_id).first()
        if not task:
            db.close()
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        # 先删除依赖的子表记录（按外键依赖顺序）
        # 1. 删除模型推理结果
        db.query(ModelResult).filter(ModelResult.task_id == task_id).delete(synchronize_session=False)
        
        # 2. 删除任务本身
        db.delete(task)
        db.commit()
        db.close()
        
        return {
            "success": True,
            "message": f"任务 {task_id} 已删除",
            "task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"删除任务失败: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")

# 4. 批量删除任务
@router.post("/batch-delete")
async def batch_delete_tasks(request: BatchDeleteRequest):
    """批量删除检测任务（级联删除相关数据）"""
    try:
        if not request.task_ids:
            raise HTTPException(status_code=400, detail="任务ID列表不能为空")
        
        db = get_db_session()
        
        # 查询存在的任务
        tasks = db.query(DetectionTask).filter(
            DetectionTask.task_id.in_(request.task_ids)
        ).all()
        
        deleted_count = len(tasks)
        
        if deleted_count == 0:
            db.close()
            raise HTTPException(status_code=404, detail="未找到要删除的任务")
        
        # 批量删除：先删除所有子表记录
        for task_id in request.task_ids:
            # 删除模型推理结果
            db.query(ModelResult).filter(ModelResult.task_id == task_id).delete(synchronize_session=False)
        
        # 再删除任务本身
        for task in tasks:
            db.delete(task)
        
        db.commit()
        db.close()
        
        return {
            "success": True,
            "message": f"成功删除 {deleted_count} 个任务",
            "deleted_count": deleted_count,
            "task_ids": [task.task_id for task in tasks]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"批量删除任务失败: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"批量删除任务失败: {str(e)}")
