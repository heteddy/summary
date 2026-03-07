"""
MacBERT + 指针网络 NER 预测脚本

用于使用训练好的模型进行实体识别预测
"""

import torch
import json
from typing import List, Dict
from transformers import BertTokenizer
from model import create_model
from data_processor import NERDataProcessor


class NERPredictor:
    """NER 预测器"""
    
    def __init__(
        self, 
        model_path: str, 
        model_name: str = 'hfl/chinese-macbert-base',
        num_entity_types: int = 3,
        device: str = None
    ):
        """
        初始化预测器
        
        Args:
            model_path: 训练好的模型路径
            model_name: MacBERT 模型名称
            num_entity_types: 实体类型数量
            device: 设备 (cuda/cpu)
        """
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # 加载处理器
        self.processor = NERDataProcessor(tokenizer_path=model_name)
        
        # 加载模型
        self.model = create_model(
            model_name=model_name,
            num_entity_types=num_entity_types
        )
        
        # 加载训练好的权重
        self.model.load_state_dict(torch.load(f'{model_path}/pytorch_model.bin', map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        
        print(f'Model loaded from {model_path}')
        print(f'Using device: {self.device}')
    
    def predict(
        self, 
        text: str, 
        threshold: float = 0.5,
        return_probs: bool = False
    ) -> List[Dict]:
        """
        预测单个文本的实体
        
        Args:
            text: 输入文本
            threshold: 置信度阈值
            return_probs: 是否返回概率
        
        Returns:
            entities: 预测的实体列表
        """
        # 分词
        inputs = self.processor.tokenizer(
            text,
            truncation=True,
            max_length=self.processor.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        # 移动数据到设备
        input_ids = inputs['input_ids'].to(self.device)
        attention_mask = inputs['attention_mask'].to(self.device)
        
        # 推理
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )
            
            start_logits = outputs['start_logits']
            end_logits = outputs['end_logits']
            
            # 计算概率
            start_probs = torch.softmax(start_logits, dim=-1)
            end_probs = torch.softmax(end_logits, dim=-1)
        
        # 解码实体
        entities = self._decode_entities(
            inputs, 
            start_probs, 
            end_probs, 
            text,
            threshold,
            return_probs
        )
        
        return entities
    
    def _decode_entities(
        self,
        inputs,
        start_probs,
        end_probs,
        original_text,
        threshold,
        return_probs
    ):
        """
        解码预测结果为实体
        
        Args:
            inputs: tokenizer 输入
            start_probs: 起始位置概率
            end_probs: 结束位置概率
            original_text: 原始文本
            threshold: 置信度阈值
            return_probs: 是否返回概率
        
        Returns:
            entities: 实体列表
        """
        entities = []
        
        # 反转实体类型映射
        idx_to_type = {v: k for k, v in self.processor.entity_type_map.items()}
        
        batch_size = start_probs.size(0)
        
        for i in range(batch_size):
            seq_len = attention_mask[i].sum().item()
            
            for entity_type_idx in range(self.processor.num_entity_types):
                # 获取当前实体类型的预测
                start_prob = start_probs[i, :, entity_type_idx][:seq_len]
                end_prob = end_probs[i, :, entity_type_idx][:seq_len]
                
                # 找到所有可能的位置对
                start_positions = (start_prob > threshold).nonzero().squeeze(-1)
                end_positions = (end_prob > threshold).nonzero().squeeze(-1)
                
                if len(start_positions) == 0 or len(end_positions) == 0:
                    continue
                
                # 匹配 start 和 end 位置
                matched_spans = []
                for start_pos in start_positions:
                    # 找到最近的且 >= start_pos 的 end_pos
                    valid_end_positions = end_positions[end_positions >= start_pos]
                    
                    if len(valid_end_positions) > 0:
                        end_pos = valid_end_positions[0]
                        
                        # 检查是否已经匹配过
                        is_duplicate = False
                        for existing_span in matched_spans:
                            if existing_span[0] == start_pos and existing_span[1] == end_pos:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            confidence = (start_prob[start_pos].item() + end_prob[end_pos].item()) / 2
                            matched_spans.append((start_pos.item(), end_pos.item(), confidence))
                
                # 将 span 转换为实体
                for start_pos, end_pos, confidence in matched_spans:
                    # 跳过特殊标记
                    if start_pos == 0:  # [CLS]
                        continue
                    
                    # 解码文本
                    # 注意：需要处理 token 到字符的映射
                    token_ids = input_ids[i][start_pos:end_pos + 1]
                    entity_text = self.processor.tokenizer.decode(token_ids, skip_special_tokens=True)
                    
                    # 在原文本中查找实体位置
                    char_start = original_text.find(entity_text)
                    if char_start == -1:
                        # 如果找不到，使用近似匹配
                        char_start = 0
                        for i, char in enumerate(original_text):
                            if entity_text.startswith(char):
                                char_start = i
                                break
                    
                    char_end = char_start + len(entity_text)
                    
                    entity = {
                        'type': idx_to_type[entity_type_idx],
                        'start': char_start,
                        'end': char_end,
                        'text': entity_text,
                        'confidence': confidence,
                    }
                    
                    if return_probs:
                        entity['start_prob'] = start_prob[start_pos].item()
                        entity['end_prob'] = end_prob[end_pos].item()
                    
                    entities.append(entity)
        
        # 按位置和置信度排序
        entities.sort(key=lambda x: (x['start'], -x['confidence']))
        
        return entities
    
    def predict_batch(
        self, 
        texts: List[str], 
        threshold: float = 0.5,
        batch_size: int = 16
    ) -> List[List[Dict]]:
        """
        批量预测
        
        Args:
            texts: 文本列表
            threshold: 置信度阈值
            batch_size: 批次大小
        
        Returns:
            all_entities: 每个文本的实体列表
        """
        all_entities = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # 分词
            inputs = self.processor.tokenizer(
                batch_texts,
                truncation=True,
                max_length=self.processor.max_length,
                padding=True,
                return_tensors='pt'
            )
            
            # 移动数据到设备
            input_ids = inputs['input_ids'].to(self.device)
            attention_mask = inputs['attention_mask'].to(self.device)
            
            # 推理
            with torch.no_grad():
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                )
                
                start_logits = outputs['start_logits']
                end_logits = outputs['end_logits']
                
                start_probs = torch.softmax(start_logits, dim=-1)
                end_probs = torch.softmax(end_logits, dim=-1)
            
            # 解码实体
            for j, text in enumerate(batch_texts):
                batch_inputs = {
                    'input_ids': input_ids[j:j+1],
                    'attention_mask': attention_mask[j:j+1],
                }
                
                entities = self._decode_entities(
                    batch_inputs,
                    start_probs[j:j+1],
                    end_probs[j:j+1],
                    text,
                    threshold,
                    return_probs=False
                )
                
                all_entities.append(entities)
        
        return all_entities
    
    def visualize(self, text: str, entities: List[Dict]) -> str:
        """
        可视化实体标注结果
        
        Args:
            text: 原始文本
            entities: 实体列表
        
        Returns:
            colored_text: 带标记的文本
        """
        # 实体类型颜色映射
        color_map = {
            'ORGANIZATION': '\033[91m',  # 红色
            'DEPARTMENT': '\033[92m',     # 绿色
            'POSITION': '\033[94m',       # 蓝色
        }
        reset_color = '\033[0m'
        
        # 按起始位置排序
        entities_sorted = sorted(entities, key=lambda x: x['start'])
        
        # 构建带标记的文本
        result = []
        last_end = 0
        
        for entity in entities_sorted:
            # 添加实体前的文本
            result.append(text[last_end:entity['start']])
            
            # 添加带颜色的实体
            color = color_map.get(entity['type'], '')
            result.append(f'{color}[{entity["type"]}: {entity["text"]}]{reset_color}')
            
            last_end = entity['end']
        
        # 添加最后的文本
        result.append(text[last_end:])
        
        return ''.join(result)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MacBERT + Pointer Network NER Prediction')
    parser.add_argument('--model_path', type=str, default='./outputs', help='模型路径')
    parser.add_argument('--model_name', type=str, default='hfl/chinese-macbert-base', help='MacBERT 模型名称')
    parser.add_argument('--text', type=str, help='要预测的文本')
    parser.add_argument('--file', type=str, help='包含文本的文件')
    parser.add_argument('--threshold', type=float, default=0.5, help='置信度阈值')
    parser.add_argument('--output', type=str, help='输出文件路径')
    
    args = parser.parse_args()
    
    # 创建预测器
    predictor = NERPredictor(args.model_path, args.model_name)
    
    # 预测
    if args.text:
        entities = predictor.predict(args.text, args.threshold)
        print(f'\nInput: {args.text}')
        print(f'Entities: {json.dumps(entities, ensure_ascii=False, indent=2)}')
        
        # 可视化
        colored_text = predictor.visualize(args.text, entities)
        print(f'\nColored Text:\n{colored_text}')
    
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            texts = [line.strip() for line in f.readlines()]
        
        all_entities = predictor.predict_batch(texts, args.threshold)
        
        results = []
        for text, entities in zip(texts, all_entities):
            results.append({
                'text': text,
                'entities': entities
            })
        
        # 保存结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f'Results saved to {args.output}')
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    
    else:
        # 交互模式
        print('\nEnter text for NER prediction (type "quit" to exit):\n')
        while True:
            text = input('> ').strip()
            if text.lower() == 'quit':
                break
            
            entities = predictor.predict(text, args.threshold)
            print(f'\nEntities: {json.dumps(entities, ensure_ascii=False, indent=2)}')
            
            colored_text = predictor.visualize(text, entities)
            print(f'Colored Text:\n{colored_text}\n')


if __name__ == '__main__':
    main()
