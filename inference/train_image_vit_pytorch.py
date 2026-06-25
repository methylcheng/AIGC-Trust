"""
基于 PyTorch + Vision Transformer (ViT) 的 AIGC 图像检测模型训练
优势：
1. 全局自注意力机制，捕捉长距离依赖
2. PyTorch在WSL2中GPU支持成熟稳定
3. 对AI生成的结构性异常更敏感
4. 泛化能力强，适应多种AI生成器

架构：ViT-Base (使用ImageNet预训练权重)
- Patch大小: 16×16
- 隐藏层维度: 768
- 注意力头数: 12
- Transformer层数: 12
- 输入尺寸: 224×224
"""
import os
import numpy as np
import cv2
import math
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms, models
import time


# 设置设备（优先使用GPU）
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")


class PatchEmbedding(nn.Module):
    """图片分块嵌入层"""
    
    def __init__(self, img_size=224, patch_size=16, embed_dim=768):
        super(PatchEmbedding, self).__init__()
        
        self.num_patches = (img_size // patch_size) ** 2  # (224/16)^2 = 196
        
        # 使用卷积实现分块和线性映射
        self.proj = nn.Conv2d(
            in_channels=3,
            out_channels=embed_dim,
            kernel_size=patch_size,
            stride=patch_size
        )
        
        # 位置编码（可学习）
        self.pos_embedding = nn.Parameter(torch.randn(1, self.num_patches + 1, embed_dim))
        
        # CLS token（分类令牌）
        self.cls_token = nn.Parameter(torch.randn(1, 1, embed_dim))
    
    def forward(self, x):
        # x: (B, C, H, W) -> (B, 3, 224, 224)
        
        # 分块并投影: (B, embed_dim, num_patches_h, num_patches_w)
        x = self.proj(x)
        
        # 展平: (B, embed_dim, num_patches)
        B, C, H, W = x.shape
        x = x.reshape(B, C, -1)
        
        # 转置: (B, num_patches, embed_dim)
        x = x.transpose(1, 2)
        
        # 添加CLS token到序列开头
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        
        # 添加位置编码
        x = x + self.pos_embedding
        
        return x


class MultiHeadAttention(nn.Module):
    """多头自注意力机制"""
    
    def __init__(self, embed_dim=768, num_heads=12, qkv_bias=False):
        super(MultiHeadAttention, self).__init__()
        
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads  # 768/12 = 64
        
        # Q, K, V 线性变换
        self.qkv = nn.Linear(embed_dim, embed_dim * 3, bias=qkv_bias)
        
        # 输出投影
        self.proj = nn.Linear(embed_dim, embed_dim)
        
        self.scale = self.head_dim ** -0.5
    
    def forward(self, x):
        B, N, C = x.shape
        
        # 计算Q, K, V: (B, N, 3*C)
        qkv = self.qkv(x)
        
        # 重塑为多头: (B, N, 3, num_heads, head_dim)
        qkv = qkv.reshape(B, N, 3, self.num_heads, self.head_dim)
        
        # 转置为: (3, B, num_heads, N, head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        
        # 分离Q, K, V
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        # 计算注意力分数: (B, num_heads, N, N)
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        
        # 加权求和: (B, num_heads, N, head_dim)
        out = (attn @ v)
        
        # 转回原始形状: (B, N, C)
        out = out.transpose(1, 2).reshape(B, N, C)
        
        # 输出投影
        out = self.proj(out)
        
        return out


class MLP(nn.Module):
    """多层感知机（Transformer中的FFN）"""
    
    def __init__(self, in_features, hidden_features=None, out_features=None):
        super(MLP, self).__init__()
        
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_features, out_features)
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        x = self.fc2(x)
        return x


class TransformerBlock(nn.Module):
    """Transformer编码器块"""
    
    def __init__(self, embed_dim=768, num_heads=12, mlp_ratio=4.0, qkv_bias=False):
        super(TransformerBlock, self).__init__()
        
        # Layer Normalization
        self.norm1 = nn.LayerNorm(embed_dim, eps=1e-6)
        self.norm2 = nn.LayerNorm(embed_dim, eps=1e-6)
        
        # 多头自注意力
        self.attn = MultiHeadAttention(embed_dim, num_heads, qkv_bias)
        
        # MLP
        mlp_hidden_dim = int(embed_dim * mlp_ratio)  # 768 * 4 = 3072
        self.mlp = MLP(embed_dim, mlp_hidden_dim)
        
        # Dropout
        self.drop_path = nn.Dropout(p=0.1)
    
    def forward(self, x):
        # 残差连接 + LayerNorm + Attention
        x = x + self.drop_path(self.attn(self.norm1(x)))
        
        # 残差连接 + LayerNorm + MLP
        x = x + self.drop_path(self.mlp(self.norm2(x)))
        
        return x


class VisionTransformer(nn.Module):
    """
    Vision Transformer for AIGC Detection
    
    架构配置（ViT-Base）:
    - Patch大小: 16×16
    - 隐藏层: 768维
    - 注意力头: 12个
    - Transformer层: 12层
    - MLP比例: 4x
    """
    
    def __init__(self, 
                 img_size=224, 
                 patch_size=16, 
                 embed_dim=768, 
                 depth=12,
                 num_heads=12, 
                 mlp_ratio=4.0,
                 num_classes=2,
                 qkv_bias=False):
        super(VisionTransformer, self).__init__()
        
        # 分块嵌入
        self.patch_embed = PatchEmbedding(img_size, patch_size, embed_dim)
        
        # Transformer编码器块
        self.blocks = nn.Sequential(*[
            TransformerBlock(embed_dim, num_heads, mlp_ratio, qkv_bias)
            for _ in range(depth)
        ])
        
        # 最终LayerNorm
        self.norm = nn.LayerNorm(embed_dim, eps=1e-6)
        
        # 分类头（使用CLS token）
        self.head = nn.Linear(embed_dim, num_classes)
        
        # Dropout
        self.dropout = nn.Dropout(p=0.5)
    
    def forward(self, x):
        # 分块嵌入: (B, 3, 224, 224) -> (B, 197, 768)
        x = self.patch_embed(x)
        
        # Transformer编码
        x = self.blocks(x)
        
        # LayerNorm
        x = self.norm(x)
        
        # 取CLS token的输出: (B, 768)
        cls_token = x[:, 0]
        
        # Dropout
        cls_token = self.dropout(cls_token)
        
        # 分类: (B, num_classes)
        x = self.head(cls_token)
        
        return x


# ==================== 数据集类 ====================
class ArchiveDataset(Dataset):
    """Archive 多模型数据集加载器"""
    
    def __init__(self, base_dir, split='train', max_samples_per_model=None, transform=None):
        self.base_dir = base_dir
        self.image_paths = []
        self.labels = []
        self.transform = transform
        
        models = [
            'imagenet_ai_0419_biggan',
            'imagenet_ai_0419_vqdm',
            'imagenet_ai_0424_sdv5',
            'imagenet_ai_0424_wukong',
            'imagenet_ai_0508_adm',
            'imagenet_glide',
            'imagenet_midjourney'
        ]
        
        print(f"加载 {split} 数据集...")
        
        for model_name in models:
            model_path = os.path.join(base_dir, model_name, split)
            
            if not os.path.exists(model_path):
                continue
            
            # 加载真实图片 (label=0)
            nature_dir = os.path.join(model_path, 'nature')
            if os.path.exists(nature_dir):
                nature_files = sorted([f for f in os.listdir(nature_dir) 
                                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                
                # 处理特殊值 'auto_1_3' - 自动计算1/3数据量
                if max_samples_per_model == 'auto_1_3':
                    limit = max(1, len(nature_files) // 3)
                    nature_files = nature_files[:limit]
                elif max_samples_per_model:
                    nature_files = nature_files[:max_samples_per_model]
                
                for filename in nature_files:
                    self.image_paths.append(os.path.join(nature_dir, filename))
                    self.labels.append(0)
            
            # 加载 AI 生成图片 (label=1)
            ai_dir = os.path.join(model_path, 'ai')
            if os.path.exists(ai_dir):
                ai_files = sorted([f for f in os.listdir(ai_dir) 
                                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                
                # 处理特殊值 'auto_1_3' - 自动计算1/3数据量
                if max_samples_per_model == 'auto_1_3':
                    limit = max(1, len(ai_files) // 3)
                    ai_files = ai_files[:limit]
                elif max_samples_per_model:
                    ai_files = ai_files[:max_samples_per_model]
                
                for filename in ai_files:
                    self.image_paths.append(os.path.join(ai_dir, filename))
                    self.labels.append(1)
        
        print(f"  加载完成: {len(self.image_paths)} 张图片")
        print(f"     - 真实图片: {sum(1 for l in self.labels if l == 0):,} 张")
        print(f"     - AI生成图片: {sum(1 for l in self.labels if l == 1):,} 张")
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, index):
        img_path = self.image_paths[index]
        
        # 支持中文路径
        img_array = np.fromfile(img_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            img = np.zeros((224, 224, 3), dtype=np.uint8)
        
        # 调整尺寸到 224x224
        img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_LINEAR)
        
        # 转换为RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 数据增强（仅训练集）
        if self.transform:
            img = self.transform(img)
        
        label = self.labels[index]
        
        return img, label


def create_dataloader(base_dir, split='train', batch_size=32, max_samples_per_model=None, shuffle=True, use_balanced_sampler=False):
    """创建 PyTorch DataLoader
    
    Args:
        base_dir: 数据集根目录
        split: 'train' 或 'test'
        batch_size: 批次大小
        max_samples_per_model: 每个模型的最大样本数
        shuffle: 是否打乱数据
        use_balanced_sampler: 是否使用平衡采样器（解决类别不平衡）
    """
    
    # 定义数据增强（高精度模式 - 更强增强）
    if split == 'train':
        transform = transforms.Compose([
            transforms.ToTensor(),
            # ========== 强几何变换 ==========
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0), ratio=(0.9, 1.1)),  # 随机裁剪缩放
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=20),  # 增大旋转角度
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),  # 随机平移缩放
            # ========== 强色彩变换 ==========
            transforms.ColorJitter(
                brightness=0.3,    # 增强亮度扰动
                contrast=0.3,      # 增强对比度扰动
                saturation=0.3,    # 增强饱和度扰动
                hue=0.15           # 增强色调扰动
            ),
            transforms.RandomGrayscale(p=0.1),  # 随机灰度化
            # ========== ImageNet标准化（预训练模型必需）==========
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            # ========== 随机擦除（正则化）==========
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.15), value='random'),  # 启用随机擦除增强正则化
        ])
    else:
        # 测试集：只做基础预处理，不做增强
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    
    dataset = ArchiveDataset(base_dir, split=split, max_samples_per_model=max_samples_per_model, transform=transform)
    
    # 如果使用平衡采样器（仅训练集）
    sampler = None
    if use_balanced_sampler and split == 'train':
        # 计算类别权重
        labels = np.array(dataset.labels)
        class_counts = np.bincount(labels)
        class_weights = 1.0 / class_counts
        sample_weights = class_weights[labels]
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )
        print(f"  ✓ 启用平衡采样器 - 类别分布: {class_counts}")
        shuffle = False  # 使用sampler时不能shuffle
    
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        sampler=sampler,
        num_workers=2,  # Windows下使用2个worker并行加载数据
        pin_memory=True,  # 启用pinned memory加速CPU→GPU传输
        prefetch_factor=2,  # 预取2个batch，减少GPU等待时间
        persistent_workers=False  # Windows下不建议持久化worker
    )
    
    return dataloader, len(dataset)


def train_vit(epochs=30, batch_size=64, max_train_samples_per_model=None, max_test_samples_per_model=None, use_balanced_sampler=True):
    """
    训练 Vision Transformer 模型（高精度全量训练模式）
    
    训练策略：
    1. 使用适中的初始学习率 + Warmup
    2. 余弦退火调度（无重启，稳定收敛）
    3. 更多Epochs确保充分收敛
    4. 更强的正则化防止过拟合
    5. 使用全部数据进行训练
    6. 平衡采样解决类别不平衡问题
    7. 增大的batch size获得更稳定梯度
    """
    save_path = os.path.join(os.path.dirname(__file__), "models", "image_detector_vit.pth")
    
    print("=" * 70)
    print("开始训练 Vision Transformer AIGC检测模型 (PyTorch)")
    print("=" * 70)
    print("\n模型配置:")
    print("  - 架构: ViT-Base")
    print("  - Patch大小: 16×16")
    print("  - 隐藏层: 768维")
    print("  - 注意力头: 12个")
    print("  - Transformer层: 12层")
    print("  - 输入尺寸: 224×224")
    print("=" * 70)
    
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "archive")
    
    # 创建数据集
    print("\n【步骤 1/4】加载数据集...")
    train_loader, train_size = create_dataloader(
        base_dir, 
        split='train', 
        batch_size=batch_size, 
        max_samples_per_model=max_train_samples_per_model,
        use_balanced_sampler=use_balanced_sampler
    )
    
    val_loader, val_size = create_dataloader(
        base_dir, 
        split='val',  # 使用验证集（目录名为val）
        batch_size=batch_size, 
        max_samples_per_model=max_test_samples_per_model,
        shuffle=False,
        use_balanced_sampler=False  # 验证集不需要平衡采样
    )
    
    print(f"\n数据统计:")
    print(f"  训练集: {train_size:,} 张")
    print(f"  验证集: {val_size:,} 张")
    print(f"  Batch size: {batch_size}")
    print(f"  Epochs: {epochs}")
    
    # 创建ViT网络
    print("\n【步骤 2/4】构建 Vision Transformer 模型...")
    print("  使用 torchvision 预训练 ViT-Base (ImageNet权重)")
    
    # 使用 torchvision 的预训练 ViT
    vit_model = models.vit_b_16(weights=models.ViT_B_16_Weights.IMAGENET1K_V1)
    
    # 修改分类头为2分类
    num_features = vit_model.heads.head.in_features
    vit_model.heads.head = nn.Linear(num_features, 2)
    
    model = vit_model.to(device)
    
    # 打印参数统计
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  总参数量: {total_params:,}")
    print(f"  可训练参数: {trainable_params:,}")
    
    # 定义损失函数和优化器（超高精度配置）
    criterion = nn.CrossEntropyLoss(label_smoothing=0.15)  # 标签平滑，防止过拟合
    
    optimizer = torch.optim.AdamW(
        model.parameters(), 
        lr=0.0001,  # 标准学习率（配合Warmup）
        weight_decay=0.05,  # 适中的权重衰减（配合其他正则化手段）
        betas=(0.9, 0.999),  # AdamW动量参数
        eps=1e-8  # 数值稳定性
    )
    
    # ========== 学习率预热 + 余弦退火 ========== 
    warmup_epochs = 3  # 前3个epoch线性warmup
    total_steps = epochs * len(train_loader)
    warmup_steps = warmup_epochs * len(train_loader)
    
    def lr_lambda(current_step):
        if current_step < warmup_steps:
            # Linear warmup: 从0线性增长到1
            return float(current_step) / float(max(1, warmup_steps))
        else:
            # Cosine decay: 余弦退火到0
            progress = float(current_step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))
    
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    # ========== 混合精度训练（加速训练，节省显存）==========
    scaler = torch.amp.GradScaler('cuda') if torch.cuda.is_available() else None
    
    # 开始训练
    print(f"\n【步骤 3/4】开始训练 {epochs} 个 epoch...")
    print("-" * 70)
    print("提示: ViT训练初期Loss下降较慢，请耐心等待...")
    print("✨ 启用超高精度训练模式:")
    print(f"   - Batch Size: {batch_size} (增大以获得更稳定梯度)")
    print(f"   - 平衡采样: {'启用' if use_balanced_sampler else '禁用'}")
    print("   - 标签平滑 (Label Smoothing 0.15)")
    print("   - Linear Warmup + Cosine Decay")
    print("   - 强数据增强 (随机裁剪+翻转+旋转+色彩扰动+随机擦除)")
    print("   - 梯度裁剪 + 权重衰减 (0.05)")
    print("   - 混合精度训练 (AMP)")
    print("   - 早停机制 (patience=8)")
    print("   - 使用独立测试集验证")
    
    best_acc = 0.0
    patience = 5  # 早停耐心值（减少，适应快速训练）
    no_improve_count = 0  # 未改进计数
    
    # 打印初始模型预测分布(调试用)
    print("\n🔍 初始模型诊断:")
    model.eval()
    with torch.no_grad():
        sample_images, sample_labels = next(iter(train_loader))
        sample_images = sample_images.to(device)
        sample_outputs = model(sample_images)
        sample_preds = torch.argmax(sample_outputs, dim=1).cpu().numpy()
        print(f"   前10个样本标签: {sample_labels[:10].numpy()}")
        print(f"   前10个样本预测: {sample_preds[:10]}")
        print(f"   预测分布: class0={sum(sample_preds==0)}, class1={sum(sample_preds==1)}")
    model.train()
    
    for epoch in range(epochs):
        # 训练阶段
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        start_time = time.time()
        
        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = torch.tensor(labels).to(device)
            
            # ========== 混合精度训练（加速，节省显存）==========
            if scaler is not None:
                # 自动混合精度
                with torch.amp.autocast('cuda'):
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                
                # 反向传播（带梯度缩放）
                optimizer.zero_grad()
                scaler.scale(loss).backward()
                # 梯度裁剪，防止梯度爆炸
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                # 标准精度训练
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                # 反向传播
                optimizer.zero_grad()
                loss.backward()
                # 梯度裁剪，防止梯度爆炸
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
            
            # 更新学习率（LambdaLR自动管理）
            scheduler.step()
            
            # 统计
            running_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # 每50个batch打印一次详细统计
            if (batch_idx + 1) % 50 == 0:
                pred_dist = torch.bincount(predicted, minlength=2)
                label_dist = torch.bincount(labels, minlength=2)
                print(f"  Epoch [{epoch+1}/{epochs}] Batch [{batch_idx+1}/{len(train_loader)}] "
                      f"Loss: {loss.item():.4f} Acc: {100.*correct/total:.2f}%")
                print(f"    预测分布: [class0={pred_dist[0].item()}, class1={pred_dist[1].item()}] | "
                      f"标签分布: [class0={label_dist[0].item()}, class1={label_dist[1].item()}]")
        
        # 更新学习率（已在batch中更新，这里不需要再调用）
        # scheduler.step()  # 已移至batch循环内
        
        epoch_loss = running_loss / len(train_loader)
        epoch_acc = 100. * correct / total
        epoch_time = time.time() - start_time
        
        # 获取当前学习率
        current_lr = optimizer.param_groups[0]['lr']
        
        print(f"\nEpoch [{epoch+1}/{epochs}] Loss: {epoch_loss:.4f} Acc: {epoch_acc:.2f}% Time: {epoch_time:.1f}s LR: {current_lr:.6f}")
        
        # 验证阶段
        print("  验证中...")
        model.eval()
        val_correct = 0
        val_total = 0
        val_loss = 0.0
        
        # ========== 详细验证指标（Precision, Recall, F1）==========
        tp = fp = tn = fn = 0  # True Positive, False Positive, etc.
        
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)  # 直接使用labels，不需要torch.tensor转换
                
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
                # 计算混淆矩阵
                for pred, true in zip(predicted.cpu().numpy(), labels.cpu().numpy()):
                    if pred == 1 and true == 1:
                        tp += 1
                    elif pred == 1 and true == 0:
                        fp += 1
                    elif pred == 0 and true == 0:
                        tn += 1
                    else:  # pred == 0 and true == 1
                        fn += 1
        
        val_acc = 100. * val_correct / val_total
        val_avg_loss = val_loss / len(val_loader)
        
        # 计算Precision, Recall, F1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"  验证准确率: {val_acc:.2f}% | Loss: {val_avg_loss:.4f}")
        print(f"  Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1_score:.4f}")
        print(f"  TP={tp}, FP={fp}, TN={tn}, FN={fn}")
        
        # 保存最佳模型
        if val_acc > best_acc:
            best_acc = val_acc
            no_improve_count = 0  # 重置未改进计数
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            torch.save(model.state_dict(), save_path)
            print(f"  ✓ 保存最佳模型 (准确率: {best_acc:.2f}%, F1: {f1_score:.4f})")
        else:
            no_improve_count += 1
            print(f"  ⚠️  连续 {no_improve_count}/{patience} 个epoch未改进")
        
        # ========== 早停机制（Early Stopping）==========
        if no_improve_count >= patience:
            print(f"\n🛑 早停触发！连续{patience}个epoch未改进，停止训练。")
            print(f"   最佳验证准确率: {best_acc:.2f}%")
            break
        
        print("-" * 70)
    
    # 验证
    print("\n" + "=" * 70)
    print(f"训练完成！最佳验证准确率: {best_acc:.2f}%")
    print("=" * 70)
    
    print(f"\n模型已保存到: {save_path}")
    if os.path.exists(save_path):
        print(f"   文件大小: {os.path.getsize(save_path) / (1024*1024):.2f} MB")
    
    return best_acc


if __name__ == "__main__":
    # ========== 三分之一数据集训练配置 ==========
    print("=" * 70)
    print("🚀 ViT模型快速训练（1/3数据集）")
    print("=" * 70)
    print("\n💡 训练策略:")
    print("   - 使用1/3训练数据（加速训练）")
    print("   - 20个epoch快速迭代")
    print("   - Linear Warmup + Cosine Decay")
    print("   - 正则化 (weight_decay=0.05, label_smoothing=0.15, RandomErasing)")
    print("   - 早停机制 (patience=5)")
    print("   - 混合精度训练加速")
    print("   - 平衡采样解决类别不平衡")
    print("   - Batch Size: 64 (更稳定梯度估计)")
    print("=" * 70)
    
    accuracy = train_vit(
        epochs=20,                       # 减少epoch数，快速迭代
        batch_size=64,                   # 增大batch size获得更稳定梯度
        max_train_samples_per_model='auto_1_3',  # 自动计算1/3数据量
        max_test_samples_per_model=None,   # 使用全部测试数据
        use_balanced_sampler=True          # 启用平衡采样解决类别不平衡
    )
    print(f"\n最终验证准确率: {accuracy:.2f}%")
    
    print("\n" + "=" * 70)
    print("✅ 训练完成！")
    print("=" * 70)
