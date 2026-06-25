import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter, UploadFile, HTTPException, Query, Depends, Request
import uuid
from db.db_conn import get_db_session
from db.models import Content
from crypto.sm3_hash import get_file_sm3
from core.multimodal_analyzer import analyze_content
from api.auth import get_current_user

router = APIRouter()

@router.post("")
async def upload_content(file: UploadFile, c_type: str, current_user: dict = Depends(get_current_user)):
    try:
        # 验证文件类型与声明的类型是否匹配
        filename = file.filename.lower()
        
        # 定义各类型支持的扩展名
        image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')
        video_exts = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v')
        text_exts = ('.txt', '.docx', '.pdf', '.doc')
        
        # 检查文件扩展名
        is_image = any(filename.endswith(ext) for ext in image_exts)
        is_video = any(filename.endswith(ext) for ext in video_exts)
        is_text = any(filename.endswith(ext) for ext in text_exts)
        
        # 根据c_type验证文件类型
        if c_type == 'image' and not is_image:
            raise HTTPException(
                status_code=400, 
                detail=f"文件类型不匹配：期望图片格式{image_exts}，实际文件: {file.filename}"
            )
        elif c_type == 'video' and not is_video:
            raise HTTPException(
                status_code=400, 
                detail=f"文件类型不匹配：期望视频格式{video_exts}，实际文件: {file.filename}"
            )
        elif c_type == 'text' and not is_text:
            raise HTTPException(
                status_code=400, 
                detail=f"文件类型不匹配：期望文档格式{text_exts}，实际文件: {file.filename}"
            )
        
        # 生成唯一ID和保存路径
        content_id = str(uuid.uuid4())
        save_dir = os.path.join(BASE_PATH, "upload")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{content_id}_{file.filename}")

        # 写入文件
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 计算SM3哈希
        sm3_h = get_file_sm3(save_path)

        # 写入数据库（添加user_id）
        db = get_db_session()
        new_content = Content(
            content_id=content_id,
            user_id=current_user["user_id"],
            type=c_type,
            path=save_path,
            sm3_hash=sm3_h,
            source=None
        )
        db.add(new_content)
        db.commit()
        db.close()

        return {"content_id": content_id, "save_path": save_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/{content_id}/analyze")
async def analyze_uploaded_content(content_id: str, use_deep_model: bool = Query(True), current_user: dict = Depends(get_current_user)):
    """
    对已上传的内容进行AIGC检测
    
    Args:
        content_id: 内容ID
        use_deep_model: 是否使用深度学习模型（仅视频）
    
    Returns:
        检测结果
    """
    try:
        # 查询内容信息
        db = get_db_session()
        content = db.query(Content).filter(Content.content_id == content_id).first()
        db.close()
        
        if not content:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        # 调用统一分析接口，传递user_id
        result = analyze_content(content.path, content.type, user_id=current_user["user_id"])
        
        return {
            "content_id": content_id,
            "type": content.type,
            "analysis_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/text/detect")
async def detect_text(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    文本AIGC检测专用接口（直接输入文本内容）
    
    Args:
        text_content: 文本内容字符串（通过Request body传递）
    
    Returns:
        文本检测结果
    """
    try:
        # 从请求体中读取纯文本
        text_content = await request.body()
        text_content = text_content.decode('utf-8')
        
        if not text_content or len(text_content.strip()) == 0:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        import uuid as uuid_module
        
        # 创建临时文件保存文本
        temp_dir = os.path.join(BASE_PATH, "upload")
        os.makedirs(temp_dir, exist_ok=True)
        
        content_id = str(uuid.uuid4())
        temp_file = os.path.join(temp_dir, f"{content_id}_input.txt")
        
        # 写入文本文件
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # 调用文本检测器
        from core.text_detector import detect_text_aigc
        result = detect_text_aigc(
            temp_file,
            "center",
            use_deep_model=True,
            user_id=current_user["user_id"]  # 传递用户ID
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本检测失败: {str(e)}")


@router.post("/video/detect")
async def detect_video(
    file: UploadFile,
    edge_mode: bool = Query(False),
    edge_node_id: str = Query("edge_01"),
    use_gpu: bool = Query(True),
    gpu_method: str = Query("ffmpeg"),
    current_user: dict = Depends(get_current_user)
):
    """
    视频AIGC检测专用接口（支持GPU加速）
    
    Args:
        file: 视频文件
        edge_mode: 是否使用边缘轻量化模式
        edge_node_id: 边缘节点ID
        use_gpu: 是否使用GPU加速预处理
        gpu_method: GPU处理方法 ('ffmpeg' 或 'opencv')
    
    Returns:
        视频检测结果
    """
    try:
        # 验证文件类型
        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv')):
            raise HTTPException(status_code=400, detail="不支持的视频格式")
        
        # 保存文件
        content_id = str(uuid.uuid4())
        save_dir = os.path.join(BASE_PATH, "upload")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{content_id}_{file.filename}")
        
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 根据模式选择检测方法
        if edge_mode:
            # 边缘轻量化检测
            from core.video_detector_edge import detect_video_edge_lightweight
            result = detect_video_edge_lightweight(
                save_path,
                edge_node_id,
                use_gpu=use_gpu,
                user_id=current_user["user_id"]  # 传递用户ID
            )
        else:
            # 中心平台完整检测
            from core.video_detector import detect_video_aigc
            result = detect_video_aigc(
                save_path,
                "center",
                use_deep_model=True,
                use_gpu=use_gpu,
                gpu_method=gpu_method,
                user_id=current_user["user_id"]  # 传递用户ID
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频检测失败: {str(e)}")
