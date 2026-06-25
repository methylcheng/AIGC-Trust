"""
基于预训练中文BERT的AI生成文本检测器
使用 HuggingFace Transformers + PyTorch
支持 GPU 加速推理
"""
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import os


class BERTTextClassifier(nn.Module):
    """基于BERT的文本分类器"""
    
    def __init__(self, model_name='bert-base-chinese', num_classes=2, dropout=0.3):
        super(BERTTextClassifier, self).__init__()
        
        # 设置环境变量使用国内镜像和离线模式
        import os
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        os.environ['HF_HUB_OFFLINE'] = '1'  # 强制离线模式
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        
        # 加载预训练的中文BERT模型（优先使用本地缓存）
        print(f"正在加载预训练模型: {model_name} (离线模式)")
        
        # 定义缓存目录
        cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
        
        try:
            # 首先尝试离线模式加载（使用本地缓存）
            self.bert = AutoModel.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=True  # 只使用本地文件
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=True
            )
            print("✓ 从本地缓存加载BERT模型成功")
        except Exception as e:
            print(f"本地缓存加载失败: {str(e)}")
            print("尝试在线加载（使用国内镜像）...")
            
            # 如果离线失败，尝试在线加载
            try:
                os.environ['HF_HUB_OFFLINE'] = '0'  # 临时允许在线
                self.bert = AutoModel.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    local_files_only=False,
                    mirror='https://hf-mirror.com'
                )
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    local_files_only=False,
                    mirror='https://hf-mirror.com'
                )
                print("✓ 在线加载BERT模型成功")
            except Exception as e2:
                print(f"✗ 在线加载也失败: {str(e2)}")
                print("\n解决方案：")
                print("1. 请确保已下载 bert-base-chinese 模型")
                print("2. 或检查网络连接后重试")
                raise
        
        # 获取BERT隐藏层维度
        hidden_size = self.bert.config.hidden_size
        
        # 分类头
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_classes)
        )
        
        print(f"BERT模型加载完成，隐藏层维度: {hidden_size}")
    
    def forward(self, input_ids, attention_mask):
        """
        前向传播
        
        Args:
            input_ids: token IDs [batch_size, seq_len]
            attention_mask: 注意力掩码 [batch_size, seq_len]
            
        Returns:
            logits: 分类输出 [batch_size, num_classes]
        """
        # BERT编码
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        # 使用[CLS] token的输出作为句子表示
        cls_output = outputs.last_hidden_state[:, 0, :]  # [batch_size, hidden_size]
        
        # 分类
        logits = self.classifier(cls_output)
        
        return logits


class AIGCTextDetector:
    """AI文本检测器（单例模式）"""
    
    def __init__(self, model_path=None, use_gpu=True):
        """
        初始化检测器
        
        Args:
            model_path: 微调后的模型路径（可选）
            use_gpu: 是否使用GPU加速
        """
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        print(f"使用设备: {self.device}")
        
        # 加载模型
        self.model = BERTTextClassifier()
        self.model.to(self.device)
        self.model.eval()  # 设置为评估模式
        
        # 保存tokenizer引用（从BERTTextClassifier中获取）
        self.tokenizer = self.model.tokenizer
        
        # 如果有微调模型，加载权重
        if model_path and os.path.exists(model_path):
            print(f"加载微调模型: {model_path}")
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            print("微调模型加载成功")
        else:
            print("使用预训练模型（未微调），建议后续进行领域适配训练")
    
    def detect(self, text: str) -> float:
        """
        检测文本是否为AI生成
        
        Args:
            text: 待检测文本
            
        Returns:
            float: AI生成概率 (0-1)，越高越可能是AI生成
        """
        if not text or len(text.strip()) < 10:
            return 0.0
        
        try:
            # 文本预处理
            inputs = self.tokenizer(
                text,
                max_length=512,  # BERT最大长度
                truncation=True,
                padding='max_length',
                return_tensors='pt'
            )
            
            input_ids = inputs['input_ids'].to(self.device)
            attention_mask = inputs['attention_mask'].to(self.device)
            
            # 推理
            with torch.no_grad():
                logits = self.model(input_ids, attention_mask)
                probabilities = torch.softmax(logits, dim=1)
                
                # 获取AI生成的概率（类别1）
                ai_probability = probabilities[0][1].item()
            
            return max(0.0, min(1.0, ai_probability))
            
        except Exception as e:
            print(f"BERT模型推理失败: {str(e)}")
            # 回退到启发式方法
            return self._heuristic_predict(text)
    
    def _heuristic_predict(self, text: str) -> float:
        """
        启发式检测方法（备用方案）
        """
        score = 0.0
        
        # AI常用词汇
        ai_indicators = [
            "根据我的理解", "作为AI助手", "我需要指出",
            "值得注意的是", "综上所述", "总的来说",
            "首先", "其次", "最后", "然而", "此外"
        ]
        
        ai_word_count = sum(1 for word in ai_indicators if word in text)
        if ai_word_count > 3:
            score += 0.3
        elif ai_word_count > 1:
            score += 0.15
        
        # 段落结构
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 3:
            score += 0.2
        
        # 句子长度方差
        sentences = [s.strip() for s in text.replace('。', '.').replace('！', '!').replace('？', '?').split('.') if s.strip()]
        if len(sentences) > 3:
            lengths = [len(s) for s in sentences]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            
            if variance < 100:
                score += 0.2
        
        # 主观性词汇
        subjective_words = ["我认为", "我觉得", "可能", "也许", "大概"]
        has_subjective = any(word in text for word in subjective_words)
        if not has_subjective:
            score += 0.15
        
        return min(score, 1.0)


# 全局单例
_detector = None

def get_detector(use_gpu=True):
    """获取检测器单例"""
    global _detector
    if _detector is None:
        model_path = os.path.join(os.path.dirname(__file__), "models", "bert_text_detector.pth")
        _detector = AIGCTextDetector(model_path=model_path, use_gpu=use_gpu)
    return _detector

def text_ai_score(text: str, use_gpu=True) -> float:
    """
    检测文本是否为AI生成
    
    Args:
        text: 待检测文本
        use_gpu: 是否使用GPU
        
    Returns:
        float: AI生成概率 (0-1)
    """
    detector = get_detector(use_gpu=use_gpu)
    return detector.detect(text)


if __name__ == "__main__":
    # 测试
    test_texts = [
        "随着人工智能技术的快速发展，AI生成内容已经广泛应用于各个领域。然而，这也带来了内容真实性和可信度的挑战。",
        "我觉得今天天气真好，想去公园散步。你觉得呢？",
        "根据我的理解，这个问题需要从多个角度来分析。首先，我们需要考虑技术层面的因素。其次，还要关注用户体验。最后，综合各方面因素得出结论。"
    ]
    
    print("=" * 60)
    print("BERT文本检测器测试")
    print("=" * 60)
    
    for i, text in enumerate(test_texts, 1):
        score = text_ai_score(text)
        print(f"\n测试 {i}:")
        print(f"文本: {text[:50]}...")
        print(f"AI生成概率: {score:.4f}")
        print(f"判断: {'疑似AI生成' if score > 0.5 else '疑似人类创作'}")
