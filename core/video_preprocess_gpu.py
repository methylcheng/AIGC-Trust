"""
FFmpeg + OpenCV GPU 加速视频预处理模块
利用 FFmpeg CUDA 硬件解码 + OpenCV GPU 处理实现高性能视频抽帧
"""
import os
import subprocess
import tempfile
import numpy as np
import cv2
from typing import List, Tuple, Dict


class GPUVideoProcessor:
    """GPU加速视频处理器"""
    
    def __init__(self, use_gpu: bool = True, gpu_device: int = 0):
        """
        初始化GPU视频处理器
        
        Args:
            use_gpu: 是否使用GPU加速
            gpu_device: GPU设备ID（默认0）
        """
        self.use_gpu = use_gpu
        self.gpu_device = gpu_device
        self._check_gpu_support()
    
    def _check_gpu_support(self):
        """检查GPU支持情况"""
        if not self.use_gpu:
            print("⚠️  未启用GPU加速，将使用CPU模式")
            return
        
        # 检查FFmpeg CUDA支持
        try:
            result = subprocess.run(
                ['ffmpeg', '-hwaccels'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'cuda' in result.stdout.lower():
                print("✅ FFmpeg CUDA 硬件加速可用")
            else:
                print("⚠️  FFmpeg 不支持 CUDA，降级到CPU模式")
                self.use_gpu = False
        except Exception as e:
            print(f"⚠️  检查FFmpeg失败: {e}，降级到CPU模式")
            self.use_gpu = False
        
        # 检查OpenCV CUDA支持
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            print(f"✅ OpenCV CUDA 可用 (GPU {self.gpu_device})")
            cv2.cuda.setDevice(self.gpu_device)
        else:
            print("⚠️  OpenCV 不支持 CUDA，将使用CPU处理图像")
    
    def extract_frames_ffmpeg_gpu(
        self,
        video_path: str,
        output_dir: str = None,
        sample_interval: int = 10,
        max_frames: int = 50,
        target_width: int = 640,
        target_height: int = 360
    ) -> Tuple[List[np.ndarray], Dict]:
        """
        使用FFmpeg GPU解码提取视频帧
        
        Args:
            video_path: 视频文件路径
            output_dir: 临时输出目录（可选）
            sample_interval: 抽帧间隔
            max_frames: 最大抽取帧数
            target_width: 目标宽度
            target_height: 目标高度
        
        Returns:
            frames: 帧列表
            meta: 视频元数据
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 获取视频信息
        meta = self._get_video_info(video_path)
        
        # 计算实际抽帧参数
        fps = meta['fps']
        total_frames = meta['total_frames']
        duration = meta['duration']
        
        # 计算选择器参数
        select_filter = f"select='not(mod(n,{sample_interval}))'"
        
        # 创建临时目录
        if output_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="ffmpeg_extract_")
        else:
            temp_dir = output_dir
            os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 构建FFmpeg命令（使用CUDA硬件解码）
            if self.use_gpu:
                # GPU解码 + CPU缩放（最稳定方案）
                # 说明：hwaccel只用于解码加速，缩放用CPU的scale滤镜
                # 关键：hwdownload必须在scale之前，且需要format=nv12转换格式
                cmd = [
                    'ffmpeg',
                    '-hwaccel', 'cuda',
                    '-hwaccel_device', str(self.gpu_device),
                    '-hwaccel_output_format', 'cuda',  # 保持GPU内存
                    '-i', video_path,
                    '-vf', f"{select_filter},hwdownload,format=nv12,scale={target_width}:{target_height}",
                    '-vsync', '0',
                    '-q:v', '2',  # 高质量
                    os.path.join(temp_dir, 'frame_%04d.jpg')
                ]
            else:
                # CPU解码
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', f"{select_filter},scale={target_width}:{target_height}",
                    '-vsync', '0',
                    '-q:v', '2',
                    os.path.join(temp_dir, 'frame_%04d.jpg')
                ]
            
            print(f"🎬 执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                # 增加错误信息截取长度以完整暴露问题
                error_msg = result.stderr[:2000] if len(result.stderr) > 2000 else result.stderr
                print(f"⚠️  FFmpeg执行警告: {error_msg}")
                # 如果GPU失败，自动降级到CPU
                if self.use_gpu:
                    print("🔄 GPU处理失败，自动降级到CPU模式...")
                    return self._extract_frames_cpu(video_path, sample_interval, max_frames, target_width, target_height, temp_dir, meta)
            
            # 读取提取的帧
            frames = []
            frame_files = sorted([
                f for f in os.listdir(temp_dir) 
                if f.endswith('.jpg') or f.endswith('.png')
            ])
            
            # 如果没有找到帧文件，尝试降级
            if not frame_files and self.use_gpu:
                print("⚠️  未找到输出帧文件，降级到CPU模式...")
                return self._extract_frames_cpu(video_path, sample_interval, max_frames, target_width, target_height, temp_dir, meta)
            
            for frame_file in frame_files[:max_frames]:
                frame_path = os.path.join(temp_dir, frame_file)
                
                # 使用OpenCV读取（支持中文路径）
                img_array = np.fromfile(frame_path, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    frames.append(frame)
                
                if len(frames) >= max_frames:
                    break
            
            meta['sampled_frames'] = len(frames)
            meta['sample_interval'] = sample_interval
            meta['extraction_method'] = 'ffmpeg_gpu' if self.use_gpu else 'ffmpeg_cpu'
            
            print(f"✅ 成功提取 {len(frames)} 帧")
            
            return frames, meta
            
        finally:
            # 清理临时文件
            if output_dir is None and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _extract_frames_cpu(
        self,
        video_path: str,
        sample_interval: int,
        max_frames: int,
        target_width: int,
        target_height: int,
        temp_dir: str,
        meta: Dict
    ) -> Tuple[List[np.ndarray], Dict]:
        """
        CPU模式提取帧（FFmpeg软件解码）
        """
        import shutil
        
        # 清理之前的临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 使用CPU解码
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"select='not(mod(n,{sample_interval}))',scale={target_width}:{target_height}",
            '-vsync', '0',
            '-q:v', '2',
            os.path.join(temp_dir, 'frame_%04d.jpg')
        ]
        
        print(f"🎬 CPU模式执行: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"❌ FFmpeg CPU模式也失败: {result.stderr[:500]}")
            # 最后降级到OpenCV
            return self._extract_frames_opencv_fallback(video_path, sample_interval, max_frames, (target_width, target_height), meta)
        
        # 读取帧
        frames = []
        frame_files = sorted([
            f for f in os.listdir(temp_dir)
            if f.endswith('.jpg')
        ])
        
        for frame_file in frame_files[:max_frames]:
            frame_path = os.path.join(temp_dir, frame_file)
            img_array = np.fromfile(frame_path, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is not None:
                frames.append(frame)
        
        meta['sampled_frames'] = len(frames)
        meta['sample_interval'] = sample_interval
        meta['extraction_method'] = 'ffmpeg_cpu'
        print(f"✅ CPU模式成功提取 {len(frames)} 帧")
        
        return frames, meta
    
    def _extract_frames_opencv_fallback(
        self,
        video_path: str,
        sample_interval: int,
        max_frames: int,
        target_size: Tuple[int, int],
        meta: Dict
    ) -> Tuple[List[np.ndarray], Dict]:
        """
        OpenCV降级方案（最后的备选）
        """
        print("🔄 使用OpenCV作为最后备选方案...")
        return self.extract_frames_opencv_gpu(
            video_path,
            sample_interval=sample_interval,
            max_frames=max_frames,
            target_size=target_size
        )
    
    def extract_frames_opencv_gpu(
        self,
        video_path: str,
        sample_interval: int = 10,
        max_frames: int = 50,
        target_size: Tuple[int, int] = (640, 360)
    ) -> Tuple[List[np.ndarray], Dict]:
        """
        使用OpenCV GPU处理视频帧（传统方法增强版）
        
        Args:
            video_path: 视频文件路径
            sample_interval: 抽帧间隔
            max_frames: 最大抽取帧数
            target_size: 目标尺寸 (宽, 高)
        
        Returns:
            frames: 帧列表
            meta: 视频元数据
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 尝试使用GPU解码器
        if self.use_gpu and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            try:
                # 创建CUDA流
                stream = cv2.cuda_Stream()
                
                # 上传GpuMat
                gpu_frame = cv2.cuda_GpuMat()
                gpu_resized = cv2.cuda_GpuMat()
                
                print("✅ 使用OpenCV CUDA加速处理")
            except Exception as e:
                print(f"⚠️  OpenCV CUDA初始化失败: {e}，降级到CPU")
                stream = None
        else:
            stream = None
        
        frames = []
        idx = 0
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if idx % sample_interval == 0:
                try:
                    if stream is not None:
                        # GPU处理流程
                        gpu_frame.upload(frame, stream)
                        cv2.cuda.resize(gpu_frame, target_size, gpu_resized, stream=stream)
                        processed_frame = gpu_resized.download(stream)
                    else:
                        # CPU处理流程
                        processed_frame = cv2.resize(frame, target_size, cv2.INTER_AREA)
                    
                    frames.append(processed_frame)
                    frame_count += 1
                    
                    if frame_count >= max_frames:
                        break
                        
                except Exception as e:
                    print(f"⚠️  帧 {idx} 处理失败: {e}，跳过")
            
            idx += 1
        
        cap.release()
        
        meta = {
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'duration': duration,
            'sampled_frames': len(frames),
            'sample_interval': sample_interval,
            'extraction_method': 'opencv_gpu' if stream is not None else 'opencv_cpu'
        }
        
        print(f"✅ 成功提取 {len(frames)} 帧")
        
        return frames, meta
    
    def _get_video_info(self, video_path: str) -> Dict:
        """获取视频详细信息"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'duration': duration
        }
    
    def batch_extract(
        self,
        video_paths: List[str],
        sample_interval: int = 10,
        max_frames: int = 50,
        use_ffmpeg: bool = True
    ) -> Dict[str, Tuple[List[np.ndarray], Dict]]:
        """
        批量处理多个视频
        
        Args:
            video_paths: 视频路径列表
            sample_interval: 抽帧间隔
            max_frames: 最大帧数
            use_ffmpeg: 是否使用FFmpeg（否则用OpenCV）
        
        Returns:
            字典 {视频路径: (帧列表, 元数据)}
        """
        results = {}
        
        for i, video_path in enumerate(video_paths):
            print(f"\n[{i+1}/{len(video_paths)}] 处理: {os.path.basename(video_path)}")
            
            try:
                if use_ffmpeg:
                    frames, meta = self.extract_frames_ffmpeg_gpu(
                        video_path,
                        sample_interval=sample_interval,
                        max_frames=max_frames
                    )
                else:
                    frames, meta = self.extract_frames_opencv_gpu(
                        video_path,
                        sample_interval=sample_interval,
                        max_frames=max_frames
                    )
                
                results[video_path] = (frames, meta)
                
            except Exception as e:
                print(f"❌ 处理失败: {e}")
                results[video_path] = ([], {})
        
        return results


# 全局单例
_gpu_processor = None


def get_gpu_processor(use_gpu: bool = True, gpu_device: int = 0) -> GPUVideoProcessor:
    """获取GPU处理器单例"""
    global _gpu_processor
    if _gpu_processor is None:
        _gpu_processor = GPUVideoProcessor(use_gpu=use_gpu, gpu_device=gpu_device)
    return _gpu_processor


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python video_preprocess_gpu.py <视频文件路径> [method]")
        print("  method: ffmpeg 或 opencv (默认: ffmpeg)")
        sys.exit(1)
    
    video_file = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "ffmpeg"
    
    processor = get_gpu_processor(use_gpu=True)
    
    print(f"\n{'='*80}")
    print(f"测试视频: {video_file}")
    print(f"处理方法: {method}")
    print(f"{'='*80}\n")
    
    if method.lower() == "ffmpeg":
        frames, meta = processor.extract_frames_ffmpeg_gpu(
            video_file,
            sample_interval=10,
            max_frames=20
        )
    else:
        frames, meta = processor.extract_frames_opencv_gpu(
            video_file,
            sample_interval=10,
            max_frames=20
        )
    
    print(f"\n{'='*80}")
    print("视频元数据:")
    print(f"{'='*80}")
    for key, value in meta.items():
        print(f"  {key}: {value}")
    
    if frames:
        print(f"\n✅ 第一帧尺寸: {frames[0].shape}")
        print(f"✅ 总帧数: {len(frames)}")
    else:
        print("\n❌ 未提取到帧")
