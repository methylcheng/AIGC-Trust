"""
基于 PyTorch Swin Transformer V2 的 AIGC 图像检测（推荐）
检测图片是否由 AI 生成（Stable Diffusion, Midjourney, DALL-E 等）
优势：
1. 层次化特征提取，更适合图像检测
2. 滑动窗口注意力机制，捕捉局部细节
3. 对AI生成的纹理异常更敏感
4. 比ViT在AIGC检测任务上通常高3-5%精度
"""
import numpy as np
import cv2
import os


class AIGCImageDetector:
    """AIGC 图像检测器 (Swin Transformer V2)"""
    
    def __init__(self, model_path=None):
        """
        初始化图像检测器
        
        Args:
            model_path: 预训练模型路径，如果为 None 则自动选择最佳模型
        """
        self.model_path = model_path
        self.model = None
        self.network = None  # 保存网络引用用于推理
        self._load_model()
    
    def _load_model(self):
        """加载预训练模型（优先级：PyTorch Swin > PyTorch ViT > 启发式方法）"""
        # ==================== 优先尝试 PyTorch Swin Transformer ====================
        pytorch_swin_path = os.path.join(os.path.dirname(__file__), "models", "image_detector_swin.pth")
        
        if self.model_path is None and os.path.exists(pytorch_swin_path):
            print(f"✅ 检测到 PyTorch Swin Transformer V2 模型: {pytorch_swin_path}")
            self._load_pytorch_swin(pytorch_swin_path)
            return
        
        # ==================== 降级到 PyTorch ViT ====================
        pytorch_vit_path = os.path.join(os.path.dirname(__file__), "models", "image_detector_vit.pth")
        
        if self.model_path is None and os.path.exists(pytorch_vit_path):
            print(f"✅ 检测到 PyTorch ViT 模型: {pytorch_vit_path}")
            self._load_pytorch_vit(pytorch_vit_path)
            return
        
        # ==================== 都没有找到，使用None ====================
        print("未找到预训练模型，将使用启发式检测方法")
        self.model = None
    
    def _load_pytorch_swin(self, model_path):
        """加载 PyTorch Swin Transformer V2 模型"""
        try:
            import torch
            from torchvision import models
            
            print(f"加载 PyTorch Swin-V2-Tiny 预训练模型...")
            
            # 创建与训练时相同的模型架构
            swin_model = models.swin_v2_t(weights=None)  # 不加载ImageNet权重
            
            # 修改分类头为2分类
            num_features = swin_model.head.in_features
            swin_model.head = torch.nn.Linear(num_features, 2)
            
            # 加载训练好的权重
            state_dict = torch.load(model_path, map_location='cpu')
            swin_model.load_state_dict(state_dict)
            
            # 设置为评估模式
            swin_model.eval()
            
            # 检测设备
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            swin_model = swin_model.to(self.device)
            
            self.pytorch_model = swin_model
            self.model_framework = "pytorch"
            self.use_model = "swin_v2_tiny"
            
            print(f"✅ PyTorch Swin Transformer V2 模型加载成功 (设备: {self.device})")
            
        except Exception as e:
            print(f"❌ PyTorch Swin Transformer 模型加载失败: {str(e)}")
            print("降级到 ViT 或启发式方法...")
            self.model = None
    
    def _load_pytorch_vit(self, model_path):
        """加载 PyTorch ViT 模型（降级方案）"""
        try:
            import torch
            from torchvision import models as tv_models
            
            print(f"加载 PyTorch ViT-Base 预训练模型...")
            
            # 创建与训练时相同的模型架构
            vit_model = tv_models.vit_b_16(weights=None)  # 不加载ImageNet权重
            
            # 修改分类头为2分类
            num_features = vit_model.heads.head.in_features
            vit_model.heads.head = torch.nn.Linear(num_features, 2)
            
            # 加载训练好的权重
            state_dict = torch.load(model_path, map_location='cpu')
            vit_model.load_state_dict(state_dict)
            
            # 设置为评估模式
            vit_model.eval()
            
            # 检测设备
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            vit_model = vit_model.to(self.device)
            
            self.pytorch_model = vit_model
            self.model_framework = "pytorch"
            self.use_model = "vit_pytorch"
            
            print(f"✅ PyTorch ViT 模型加载成功 (设备: {self.device})")
            
        except Exception as e:
            print(f"❌ PyTorch ViT 模型加载失败: {str(e)}")
            print("降级到启发式方法...")
            self.model = None
    
    def detect(self, image_path: str = None, image_array: np.ndarray = None) -> float:
        """
        检测图片是否为 AI 生成
        
        Args:
            image_path: 图片文件路径
            image_array: 或者直接传入 numpy 数组 (BGR 格式)
            
        Returns:
            float: AI 生成的概率 (0-1)，越高越可能是 AI 生成
        """
        if image_path is None and image_array is None:
            raise ValueError("必须提供 image_path 或 image_array")
        
        # 读取图片
        if image_array is not None:
            img = image_array
        else:
            # 支持中文路径
            img_array = np.fromfile(image_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        if self.model is not None:
            # 使用真实模型推理
            return self._model_predict(img)
        else:
            # 使用启发式方法
            return self._heuristic_predict(img)
    
    def _model_predict(self, img: np.ndarray) -> float:
        """使用模型进行预测（自动选择 Swin 或 ViT）"""
        try:
            # 使用 PyTorch 模型
            if hasattr(self, 'model_framework') and self.model_framework == 'pytorch':
                return self._pytorch_predict(img)
            
            # 如果没有模型，使用启发式方法
            return self._heuristic_predict(img)
            
        except Exception as e:
            print(f"模型推理失败: {str(e)}")
            return self._heuristic_predict(img)
    
    def _pytorch_predict(self, img: np.ndarray) -> float:
        """使用 PyTorch 模型进行预测（Swin 或 ViT）"""
        try:
            import torch
            from torchvision import transforms
            
            # 预处理（与训练时完全一致）
            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            
            # BGR -> RGB
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 应用变换
            input_tensor = transform(rgb).unsqueeze(0).to(self.device)
            
            # 推理
            with torch.no_grad():
                outputs = self.pytorch_model(input_tensor)
                probs = torch.softmax(outputs, dim=1)
                ai_probability = probs[0][1].item()  # 类别1为AI生成
            
            return max(0.0, min(1.0, ai_probability))
            
        except Exception as e:
            print(f"PyTorch 模型推理失败: {str(e)}")
            return self._heuristic_predict(img)
    
    def _heuristic_predict(self, img: np.ndarray) -> float:
        """
        基于启发式规则的 AIGC 图像检测
        
        检测 AI 生成图像的典型特征：
        - 过度平滑的纹理
        - 不自然的色彩分布
        - 频域异常
        - 噪声模式异常
        """
        score = 0.0
        
        # 特征1：检查图像平滑度（AI 图像往往过度平滑）
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # 方差小说明图像平滑
        if variance < 100:
            score += 0.25
        elif variance < 200:
            score += 0.15
        
        # 特征2：检查色彩饱和度（AI 图像可能过饱和）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].mean() / 255.0
        
        if saturation > 0.6:
            score += 0.2
        elif saturation > 0.4:
            score += 0.1
        
        # 特征3：检查直方图均衡性
        hist_b = cv2.calcHist([img], [0], None, [256], [0, 256])
        hist_variance = np.var(hist_b)
        
        # AI 图像的直方图可能过于均匀
        if hist_variance < 1000:
            score += 0.15
        
        # 特征4：检查边缘清晰度
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        if edge_density < 0.05:
            score += 0.15
        
        # 特征5：频域分析（简单的 DCT）
        gray_float = gray.astype(np.float32)
        dct = cv2.dct(gray_float)
        
        # 检查高频分量比例
        h, w = dct.shape
        high_freq = dct[h//2:, w//2:]
        low_freq = dct[:h//2, :w//2]
        
        high_energy = np.sum(np.abs(high_freq))
        low_energy = np.sum(np.abs(low_freq))
        
        if low_energy > 0:
            ratio = high_energy / low_energy
            if ratio < 0.1:  # 高频能量过低
                score += 0.15
        
        # 限制在 0-1 范围
        return min(score, 1.0)


# 全局单例
_detector = None

def get_detector():
    """获取检测器单例"""
    global _detector
    if _detector is None:
        _detector = AIGCImageDetector()
    return _detector

def image_ai_score(image_path: str = None, image_array: np.ndarray = None) -> float:
    """
    检测图片是否为 AI 生成
    
    Args:
        image_path: 图片文件路径
        image_array: 或者直接传入 numpy 数组
        
    Returns:
        float: AI 生成概率 (0-1)
    """
    detector = get_detector()
    return detector.detect(image_path=image_path, image_array=image_array)


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        score = image_ai_score(image_path=test_image)
        print(f"图片路径: {test_image}")
        print(f"AI 生成概率: {score:.2f}")
    else:
        print("用法: python image_ai_det.py <图片路径>")
