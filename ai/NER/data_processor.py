"""
MacBERT + 指针网络 NER 数据处理器

用于将标注好的 JSON 格式训练数据转换为模型可接受的输入格式
"""

import json
import torch
from typing import Dict, List, Tuple
from transformers import BertTokenizer


class NERDataProcessor:
    """NER 数据处理器"""
    
    def __init__(self, tokenizer_path: str = 'hfl/chinese-macbert-base', max_length: int = 128):
        """
        初始化数据处理器
        
        Args:
            tokenizer_path: MacBERT tokenizer 路径
            max_length: 最大序列长度
        """
        self.tokenizer = BertTokenizer.from_pretrained(tokenizer_path)
        self.max_length = max_length
        
        # 实体类型映射
        self.entity_type_map = {
            'ORGANIZATION': 0,
            'DEPARTMENT': 1,
            'POSITION': 2
        }
        self.num_entity_types = len(self.entity_type_map)
    
    def load_data(self, file_path: str) -> List[Dict]:
        """
        加载 JSON 格式的训练数据
        
        Args:
            file_path: JSON 文件路径
        
        Returns:
            数据列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    
    def tokenize_and_align(
        self, 
        text: str, 
        entities: List[Dict]
    ) -> Tuple[Dict, List[torch.Tensor], List[torch.Tensor]]:
        """
        对文本进行分词并对齐实体位置
        
        Args:
            text: 输入文本
            entities: 实体列表
        
        Returns:
            inputs: tokenizer 输出
            start_labels: 起始位置标签列表 (每个实体类型一个)
            end_labels: 结束位置标签列表 (每个实体类型一个)
        """
        # 使用 MacBERT tokenizer 分词
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        # 获取 token 数量 (不包括 padding)
        num_tokens = inputs['attention_mask'].sum().item()
        
        # 初始化标签 (每个实体类型一个 one-hot 向量)
        start_labels = []
        end_labels = []
        
        for entity_type in range(self.num_entity_types):
            start_label = torch.zeros(num_tokens, dtype=torch.long)
            end_label = torch.zeros(num_tokens, dtype=torch.long)
            start_labels.append(start_label)
            end_labels.append(end_label)
        
        # 填充实体位置标签
        for entity in entities:
            entity_type_idx = self.entity_type_map[entity['type']]
            original_start = entity['start']
            original_end = entity['end'] - 1  # 转换为包含结束位置
            
            # 将字符位置映射到 token 位置
            # 注意：这里简化处理，实际需要考虑中文分词和字符合并的情况
            token_start = original_start + 1  # +1 是因为 [CLS] 标记
            token_end = original_end + 1
            
            if token_start < num_tokens:
                start_labels[entity_type_idx][token_start] = 1
            if token_end < num_tokens:
                end_labels[entity_type_idx][token_end] = 1
        
        # 转换为 tensor
        start_labels = torch.stack(start_labels)  # (num_entity_types, seq_len)
        end_labels = torch.stack(end_labels)      # (num_entity_types, seq_len)
        
        return inputs, start_labels, end_labels
    
    def process_batch(
        self, 
        data: List[Dict]
    ) -> Tuple[Dict[str, torch.Tensor], torch.Tensor, torch.Tensor]:
        """
        批量处理数据
        
        Args:
            data: 数据列表
        
        Returns:
            batch_inputs: 批量的 tokenizer 输出
            batch_start_labels: 批量的起始位置标签 (batch_size, num_entity_types, seq_len)
            batch_end_labels: 批量的结束位置标签 (batch_size, num_entity_types, seq_len)
        """
        batch_inputs = None
        batch_start_labels = []
        batch_end_labels = []
        
        for item in data:
            text = item['text']
            entities = item['entities']
            
            inputs, start_labels, end_labels = self.tokenize_and_align(text, entities)
            
            if batch_inputs is None:
                batch_inputs = inputs
            else:
                for key in inputs:
                    batch_inputs[key] = torch.cat([batch_inputs[key], inputs[key]], dim=0)
            
            batch_start_labels.append(start_labels)
            batch_end_labels.append(end_labels)
        
        batch_start_labels = torch.stack(batch_start_labels)
        batch_end_labels = torch.stack(batch_end_labels)
        
        return batch_inputs, batch_start_labels, batch_end_labels
    
    def decode_entities(
        self, 
        inputs: Dict[str, torch.Tensor],
        start_preds: torch.Tensor,
        end_preds: torch.Tensor,
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        解码预测结果为实体
        
        Args:
            inputs: tokenizer 输入
            start_preds: 预测的起始位置概率 (batch_size, seq_len, num_entity_types)
            end_preds: 预测的结束位置概率 (batch_size, seq_len, num_entity_types)
            threshold: 置信度阈值
        
        Returns:
            entities: 预测的实体列表
        """
        entities = []
        
        # 反转实体类型映射
        idx_to_type = {v: k for k, v in self.entity_type_map.items()}
        
        batch_size = start_preds.size(0)
        
        for i in range(batch_size):
            for entity_type_idx in range(self.num_entity_types):
                # 获取当前实体类型的预测
                start_prob = start_preds[i, :, entity_type_idx]
                end_prob = end_preds[i, :, entity_type_idx]
                
                # 找到概率最高的 start 和 end 位置
                start_idx = torch.argmax(start_prob).item()
                end_idx = torch.argmax(end_prob).item()
                
                start_confidence = start_prob[start_idx].item()
                end_confidence = end_prob[end_idx].item()
                
                # 应用阈值
                if start_confidence > threshold and end_confidence > threshold and start_idx <= end_idx:
                    # 跳过特殊标记 ([CLS], [SEP])
                    if start_idx == 0 or end_idx >= inputs['attention_mask'][i].sum().item() - 1:
                        continue
                    
                    # 解码实体文本
                    # 注意：需要减去 [CLS] 的偏移
                    entity_text = self.tokenizer.decode(
                        inputs['input_ids'][i][start_idx:end_idx + 1],
                        skip_special_tokens=True
                    )
                    
                    entities.append({
                        'type': idx_to_type[entity_type_idx],
                        'start': start_idx - 1,  # 减去 [CLS] 的偏移
                        'end': end_idx,          # 已经是 exclusive
                        'text': entity_text,
                        'confidence': (start_confidence + end_confidence) / 2
                    })
        
        return entities


def split_dataset(data: List[Dict], train_ratio: float = 0.8, dev_ratio: float = 0.1) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    划分训练集、验证集和测试集
    
    Args:
        data: 完整数据集
        train_ratio: 训练集比例
        dev_ratio: 验证集比例
    
    Returns:
        train_data, dev_data, test_data
    """
    import random
    
    # 打乱数据
    random.shuffle(data)
    
    total_size = len(data)
    train_size = int(total_size * train_ratio)
    dev_size = int(total_size * dev_ratio)
    
    train_data = data[:train_size]
    dev_data = data[train_size:train_size + dev_size]
    test_data = data[train_size + dev_size:]
    
    return train_data, dev_data, test_data


def save_data(data: List[Dict], file_path: str):
    """
    保存数据到 JSON 文件
    
    Args:
        data: 数据列表
        file_path: 保存路径
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    # 示例用法
    processor = NERDataProcessor()
    
    # 加载数据
    data = processor.load_data('macbert_pointer_ner_data.json')
    
    # 划分数据集
    train_data, dev_data, test_data = split_dataset(data)
    
    # 保存划分后的数据集
    save_data(train_data, 'ner_train.json')
    save_data(dev_data, 'ner_dev.json')
    save_data(test_data, 'ner_test.json')
    
    print(f"训练集大小：{len(train_data)}")
    print(f"验证集大小：{len(dev_data)}")
    print(f"测试集大小：{len(test_data)}")
    
    # 测试数据处理
    sample = data[0]
    inputs, start_labels, end_labels = processor.tokenize_and_align(
        sample['text'], 
        sample['entities']
    )
    
    print(f"\n输入形状：{inputs['input_ids'].shape}")
    print(f"起始标签形状：{start_labels.shape}")
    print(f"结束标签形状：{end_labels.shape}")
