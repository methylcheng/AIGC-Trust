"""
使用C-ReD数据集训练中文BERT文本检测模型
基于 PyTorch + Transformers
支持 GPU 加速训练
"""
import os
import sys
import csv
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm
import argparse

# 配置国内镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# C-ReD 数据集路径
DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "C-ReD-main", "benchmark data")
CATEGORIES = ["composition", "film review", "news", "paper", "question answer"]
HUMAN_KEYWORD = "human"


class TextDataset(Dataset):
    """文本数据集"""
    
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        # 编码文本
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


class BERTClassifier(nn.Module):
    """BERT分类器"""
    
    def __init__(self, model_name='bert-base-chinese', num_classes=2, dropout=0.3):
        super(BERTClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_classes)
        )
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]
        logits = self.classifier(cls_output)
        return logits


def load_dataset():
    """加载C-ReD数据集"""
    print(f"正在从 {DATASET_DIR} 加载 C-ReD 数据集...")
    
    texts = []
    labels = []
    file_count = 0
    sample_count = 0
    
    for category in CATEGORIES:
        cat_dir = os.path.join(DATASET_DIR, category)
        if not os.path.exists(cat_dir):
            print(f"  警告: 目录不存在 {cat_dir}")
            continue
        
        for filename in os.listdir(cat_dir):
            if not filename.endswith(".csv"):
                continue
            
            filepath = os.path.join(cat_dir, filename)
            is_human = HUMAN_KEYWORD in filename.lower()
            label = 0 if is_human else 1  # 0=人类, 1=AI
            
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    text = row.get("text", "")
                    if text and len(text) > 10:
                        texts.append(text)
                        labels.append(label)
                        count += 1
                
                file_count += 1
                sample_count += count
                source = "人类" if is_human else filename.split("_")[1].replace(".csv", "")
                print(f"  [{category}] {filename}: {count} 条 ({source})")
    
    print(f"\n数据集加载完成: {file_count} 个文件, {sample_count} 条样本")
    print(f"  人类文本: {labels.count(0)} 条")
    print(f"  AI生成文本: {labels.count(1)} 条")
    
    return texts, labels


def train_model(epochs=5, batch_size=16, learning_rate=2e-5, max_length=512, save_path=None):
    """训练模型"""
    if save_path is None:
        save_path = os.path.join(os.path.dirname(__file__), "models", "bert_text_detector.pth")
    
    print("=" * 60)
    print("开始训练 BERT 文本检测模型")
    print("=" * 60)
    
    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 加载数据
    texts, labels = load_dataset()
    
    # 打乱数据
    indices = np.random.permutation(len(texts))
    texts = [texts[i] for i in indices]
    labels = [labels[i] for i in indices]
    
    # 划分训练集和验证集 (90% / 10%)
    split = int(len(texts) * 0.9)
    train_texts, val_texts = texts[:split], texts[split:]
    train_labels, val_labels = labels[:split], labels[split:]
    
    print(f"\n训练集: {len(train_texts)} 条")
    print(f"验证集: {len(val_texts)} 条")
    
    # 加载tokenizer
    print("\n加载 tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained('bert-base-chinese')
    
    # 创建数据集
    train_dataset = TextDataset(train_texts, train_labels, tokenizer, max_length)
    val_dataset = TextDataset(val_texts, val_labels, tokenizer, max_length)
    
    # 创建DataLoader
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # 创建模型
    print("\n加载 BERT 模型...")
    model = BERTClassifier(model_name='bert-base-chinese')
    model.to(device)
    
    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    
    # 训练循环
    print(f"\n开始训练 {epochs} 个 epoch...")
    print("-" * 60)
    
    best_val_acc = 0.0
    
    for epoch in range(epochs):
        # 训练阶段
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        progress_bar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{epochs}')
        for batch in progress_bar:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            outputs = model(input_ids, attention_mask)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            correct += (predicted == labels).sum().item()
            total += labels.size(0)
            
            progress_bar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{correct/total:.4f}'
            })
        
        train_acc = correct / total
        avg_loss = total_loss / len(train_loader)
        
        # 验证阶段
        model.eval()
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                
                outputs = model(input_ids, attention_mask)
                _, predicted = torch.max(outputs, 1)
                val_correct += (predicted == labels).sum().item()
                val_total += labels.size(0)
        
        val_acc = val_correct / val_total
        
        print(f"\nEpoch {epoch+1}/{epochs}:")
        print(f"  训练损失: {avg_loss:.4f}")
        print(f"  训练准确率: {train_acc:.4f}")
        print(f"  验证准确率: {val_acc:.4f}")
        
        # 保存最佳模型
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
            }, save_path)
            print(f"  ✓ 保存最佳模型 (验证准确率: {val_acc:.4f})")
        
        print("-" * 60)
    
    print(f"\n训练完成！")
    print(f"最佳验证准确率: {best_val_acc:.4f}")
    print(f"模型已保存到: {save_path}")
    
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='训练BERT文本检测模型')
    parser.add_argument('--epochs', type=int, default=5, help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=16, help='批次大小')
    parser.add_argument('--lr', type=float, default=2e-5, help='学习率')
    parser.add_argument('--max_length', type=int, default=512, help='最大序列长度')
    
    args = parser.parse_args()
    
    train_model(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_length=args.max_length
    )
