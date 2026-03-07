"""
MacBERT + 指针网络 NER 训练脚本

用于训练基于 MacBERT 和 Pointer Network 的命名实体识别模型
"""

import os
import json
import torch
import argparse
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, AdamW, get_linear_schedule_with_warmup
from tqdm import tqdm
import numpy as np

from model import create_model
from data_processor import NERDataProcessor, split_dataset


class NERDataset(Dataset):
    """NER 数据集"""
    
    def __init__(self, data, processor, max_length=128):
        """
        初始化数据集
        
        Args:
            data: 数据列表
            processor: 数据处理器
            max_length: 最大序列长度
        """
        self.data = data
        self.processor = processor
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item['text']
        entities = item['entities']
        
        inputs, start_labels, end_labels = self.processor.tokenize_and_align(text, entities)
        
        return {
            'input_ids': inputs['input_ids'].squeeze(0),
            'attention_mask': inputs['attention_mask'].squeeze(0),
            'token_type_ids': inputs['token_type_ids'].squeeze(0),
            'start_labels': start_labels,
            'end_labels': end_labels,
        }


def collate_fn(batch):
    """
    批处理函数
    
    Args:
        batch: 批次数据
    
    Returns:
        batch_data: 批处理后的数据
    """
    input_ids = torch.stack([item['input_ids'] for item in batch])
    attention_mask = torch.stack([item['attention_mask'] for item in batch])
    token_type_ids = torch.stack([item['token_type_ids'] for item in batch])
    start_labels = torch.stack([item['start_labels'] for item in batch])
    end_labels = torch.stack([item['end_labels'] for item in batch])
    
    return {
        'input_ids': input_ids,
        'attention_mask': attention_mask,
        'token_type_ids': token_type_ids,
        'start_labels': start_labels,
        'end_labels': end_labels,
    }


def evaluate(model, dataloader, device, entity_types=3):
    """
    评估模型
    
    Args:
        model: 模型
        dataloader: 数据加载器
        device: 设备
        entity_types: 实体类型数量
    
    Returns:
        precision, recall, f1
    """
    model.eval()
    
    true_positives = 0
    predicted_positives = 0
    actual_positives = 0
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Evaluating'):
            # 移动数据到 GPU
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            start_labels = batch['start_labels'].to(device)
            end_labels = batch['end_labels'].to(device)
            
            # 前向传播
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )
            
            start_logits = outputs['start_logits']
            end_logits = outputs['end_logits']
            
            # 获取预测结果
            start_preds = torch.argmax(start_logits, dim=-1)
            end_preds = torch.argmax(end_logits, dim=-1)
            
            # 获取真实标签
            start_true = torch.argmax(start_labels, dim=1)
            end_true = torch.argmax(end_labels, dim=1)
            
            # 统计 true positives, predicted positives, actual positives
            for i in range(input_ids.size(0)):
                for entity_type in range(entity_types):
                    # 找到预测的实体
                    pred_start_positions = (start_preds[i, entity_type, :] > 0).nonzero().squeeze(-1)
                    pred_end_positions = (end_preds[i, entity_type, :] > 0).nonzero().squeeze(-1)
                    
                    # 找到真实的实体
                    true_start_positions = (start_true[i, entity_type, :] > 0).nonzero().squeeze(-1)
                    true_end_positions = (end_true[i, entity_type, :] > 0).nonzero().squeeze(-1)
                    
                    # 计算匹配数
                    for start_pos in pred_start_positions:
                        for end_pos in pred_end_positions:
                            if end_pos >= start_pos:
                                # 检查是否匹配真实实体
                                is_match = False
                                for true_start in true_start_positions:
                                    for true_end in true_end_positions:
                                        if start_pos == true_start and end_pos == true_end:
                                            is_match = True
                                            break
                                    if is_match:
                                        break
                                
                                if is_match:
                                    true_positives += 1
                                predicted_positives += 1
                    
                    actual_positives += len(true_start_positions) * len(true_end_positions)
    
    # 计算指标
    precision = true_positives / (predicted_positives + 1e-10)
    recall = true_positives / (actual_positives + 1e-10)
    f1 = 2 * precision * recall / (precision + recall + 1e-10)
    
    return precision, recall, f1


def train(args):
    """
    训练模型
    
    Args:
        args: 参数
    """
    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')
    
    # 加载数据
    print('Loading data...')
    processor = NERDataProcessor(
        tokenizer_path=args.model_name,
        max_length=args.max_length
    )
    
    # 加载训练数据
    if os.path.exists(args.train_file):
        with open(args.train_file, 'r', encoding='utf-8') as f:
            train_data = json.load(f)
    else:
        # 如果没有训练文件，从完整数据集中划分
        with open('macbert_pointer_ner_data.md', 'r', encoding='utf-8') as f:
            # 注意：这里需要解析 markdown 文件提取 JSON 数据
            # 简化处理，假设已经有分离的 JSON 文件
            all_data = json.load(f)
            train_data, dev_data, test_data = split_dataset(all_data)
    
    # 加载验证数据
    if os.path.exists(args.dev_file):
        with open(args.dev_file, 'r', encoding='utf-8') as f:
            dev_data = json.load(f)
    else:
        dev_data = None
    
    # 创建数据集和数据加载器
    train_dataset = NERDataset(train_data, processor, args.max_length)
    train_dataloader = DataLoader(
        train_dataset, 
        batch_size=args.batch_size, 
        shuffle=True,
        collate_fn=collate_fn
    )
    
    if dev_data:
        dev_dataset = NERDataset(dev_data, processor, args.max_length)
        dev_dataloader = DataLoader(
            dev_dataset, 
            batch_size=args.batch_size, 
            shuffle=False,
            collate_fn=collate_fn
        )
    
    # 创建模型
    print('Creating model...')
    model = create_model(
        model_name=args.model_name,
        num_entity_types=processor.num_entity_types,
        advanced=args.advanced
    )
    model.to(device)
    
    # 优化器和调度器
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            'weight_decay': args.weight_decay,
        },
        {
            'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            'weight_decay': 0.0,
        },
    ]
    
    optimizer = AdamW(
        optimizer_grouped_parameters, 
        lr=args.learning_rate, 
        eps=args.adam_epsilon
    )
    
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=args.warmup_steps,
        num_training_steps=len(train_dataloader) * args.num_epochs
    )
    
    # 训练循环
    print('Starting training...')
    best_f1 = 0.0
    
    for epoch in range(args.num_epochs):
        print(f'\nEpoch {epoch + 1}/{args.num_epochs}')
        
        # 训练
        model.train()
        total_loss = 0.0
        
        pbar = tqdm(train_dataloader, desc='Training')
        for batch in pbar:
            # 移动数据到 GPU
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            start_labels = batch['start_labels'].to(device)
            end_labels = batch['end_labels'].to(device)
            
            # 前向传播
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                start_labels=start_labels,
                end_labels=end_labels,
            )
            
            loss = outputs['loss']
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            
            # 更新参数
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            
            total_loss += loss.item()
            pbar.set_postfix({'loss': loss.item()})
        
        avg_train_loss = total_loss / len(train_dataloader)
        print(f'Average training loss: {avg_train_loss:.4f}')
        
        # 验证
        if dev_dataloader:
            precision, recall, f1 = evaluate(model, dev_dataloader, device, processor.num_entity_types)
            print(f'Validation - Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}')
            
            # 保存最佳模型
            if f1 > best_f1:
                best_f1 = f1
                print(f'Saving best model with F1={f1:.4f}...')
                model.save_pretrained(args.output_dir)
                processor.tokenizer.save_pretrained(args.output_dir)
    
    print(f'\nTraining completed! Best F1: {best_f1:.4f}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MacBERT + Pointer Network NER Training')
    
    # 数据参数
    parser.add_argument('--train_file', type=str, default='ner_train.json', help='训练数据文件')
    parser.add_argument('--dev_file', type=str, default='ner_dev.json', help='验证数据文件')
    parser.add_argument('--max_length', type=int, default=128, help='最大序列长度')
    
    # 模型参数
    parser.add_argument('--model_name', type=str, default='hfl/chinese-macbert-base', help='MacBERT 模型名称或路径')
    parser.add_argument('--advanced', action='store_true', help='是否使用增强版模型')
    
    # 训练参数
    parser.add_argument('--batch_size', type=int, default=16, help='批次大小')
    parser.add_argument('--num_epochs', type=int, default=10, help='训练轮数')
    parser.add_argument('--learning_rate', type=float, default=3e-5, help='学习率')
    parser.add_argument('--weight_decay', type=float, default=0.01, help='权重衰减')
    parser.add_argument('--adam_epsilon', type=float, default=1e-8, help='Adam 优化器 epsilon')
    parser.add_argument('--warmup_steps', type=int, default=100, help='预热步数')
    parser.add_argument('--max_grad_norm', type=float, default=1.0, help='最大梯度范数')
    
    # 输出参数
    parser.add_argument('--output_dir', type=str, default='./outputs', help='输出目录')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 开始训练
    train(args)
