import cv2
import numpy as np

def preprocess_image(img_path: str, max_edge=640):
    img = cv2.imread(img_path)
    h,w = img.shape[:2]
    scale = max_edge / max(w,h) if max(w,h) > max_edge else 1.0
    nw, nh = int(w*scale), int(h*scale)
    img_resize = cv2.resize(img, (nw, nh), cv2.INTER_AREA)
    meta = {"width":nw, "height":nh}
    return img_resize, meta

def preprocess_video(vid_path: str, sample_interval=10, max_frames=50):
    """
    视频预处理和抽帧
    
    Args:
        vid_path: 视频文件路径
        sample_interval: 抽帧间隔（每N帧抽取1帧）
        max_frames: 最大抽取帧数（避免内存溢出）
    
    Returns:
        frames: 抽取的帧列表（numpy数组）
        meta: 视频元数据字典
    """
    cap = cv2.VideoCapture(vid_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {vid_path}")
    
    # 获取视频基本信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0
    
    frames = []
    idx = 0
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # 按间隔抽帧
        if idx % sample_interval == 0:
            # 可选：对帧进行缩放以减少内存占用
            h, w = frame.shape[:2]
            if max(w, h) > 640:
                scale = 640.0 / max(w, h)
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h), cv2.INTER_AREA)
            
            frames.append(frame)
            frame_count += 1
            
            # 达到最大帧数限制
            if frame_count >= max_frames:
                break
        
        idx += 1
    
    cap.release()
    
    meta = {
        "fps": fps,
        "total_frame": total_frames,
        "width": width,
        "height": height,
        "duration": duration,
        "sampled_frames": len(frames),
        "sample_interval": sample_interval
    }
    
    return frames, meta

def preprocess_text(text: str):
    seg = text.replace("\n", " ").split(" ")
    clean = [s.strip() for s in seg if len(s.strip())>0]
    return clean
