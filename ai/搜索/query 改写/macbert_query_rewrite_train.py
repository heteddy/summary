# MacBERT 查询改写训练代码 - 基于分类的生成方法
"""
使用 MacBERT 作为基础模型，将查询改写任务转化为序列标注问题
对输入 query 的每个位置进行词表级别的分类，选择概率最高的词作为改写结果
"""

import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertModel, AdamW, get_linear_schedule_with_warmup
from difflib import SequenceMatcher
from tqdm import tqdm
import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QueryRewriteDataBuilder:
    """查询改写训练数据构建器 - 增强版"""
    
    def __init__(self, model_name="hfl/chinese-macbert-base", strategy="align_with_insert"):
        """
        初始化数据构建器
        
        Args:
            model_name: MacBERT 模型名称或路径
            strategy: 长度处理策略
                - "keep_original": 保持原长，忽略插入
                - "align_with_insert": 对齐并添加插入标记
                - "edit_operation": 编辑操作标签法
                - "span_level": Span 级别改写（新增）
        """
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.strategy = strategy
        logger.info(f"加载分词器：{model_name}, 策略：{strategy}")
        
        # 特殊标记（用于插入操作）
        self.insert_token = "<INS>"
        self.keep_token = "<KEEP>"
        self.delete_token = "<DEL>"
        
        # Span 级别特殊标记
        self.span_start_token = "[SPAN_START]"
        self.span_end_token = "[SPAN_END]"
        self.span_pad_token = "[SPAN_PAD]"
        
        # 检查是否需要添加特殊标记到词表
        self._add_special_tokens_if_needed()
    
    def _add_special_tokens_if_needed(self):
        """添加特殊标记到词表（如果需要）"""
        special_tokens = [
            self.insert_token, 
            self.keep_token, 
            self.delete_token,
            self.span_start_token,
            self.span_end_token,
            self.span_pad_token
        ]
        added_count = 0
        
        for token in special_tokens:
            if token not in self.tokenizer.get_vocab():
                added_count += 1
        
        if added_count > 0:
            self.tokenizer.add_tokens(special_tokens)
            logger.info(f"添加了 {added_count} 个特殊标记到词表")
    
    def align_sequences_advanced(self, source_tokens, target_tokens):
        """
        高级序列比对 - 支持插入、删除、替换的完整对齐
        
        Args:
            source_tokens: 原始 query 的分词列表
            target_tokens: 目标 query 的分词列表
            
        Returns:
            aligned_source: 对齐后的源序列（可能包含<INS>标记）
            aligned_target: 对齐后的目标序列
            operations: 操作列表 [(op_type, src_idx, tgt_idx), ...]
        """
        matcher = SequenceMatcher(None, source_tokens, target_tokens)
        aligned_source = []
        aligned_target = []
        operations = []
        
        src_pos = 0
        tgt_pos = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # 相同部分，直接复制
                for k in range(i2 - i1):
                    aligned_source.append(source_tokens[i1 + k])
                    aligned_target.append(target_tokens[j1 + k])
                    operations.append(('KEEP', src_pos + k, tgt_pos + k))
                src_pos += (i2 - i1)
                tgt_pos += (j2 - j1)
                
            elif tag == 'replace':
                # 替换操作
                src_len = i2 - i1
                tgt_len = j2 - j1
                
                # 逐位置替换（取最小长度）
                min_len = min(src_len, tgt_len)
                for k in range(min_len):
                    aligned_source.append(source_tokens[i1 + k])
                    aligned_target.append(target_tokens[j1 + k])
                    operations.append(('REPLACE', src_pos + k, tgt_pos + k))
                
                # 处理长度不匹配
                if src_len > tgt_len:
                    # 源序列更长，多余的源位置标记为 DELETE
                    for k in range(min_len, src_len):
                        aligned_source.append(source_tokens[i1 + k])
                        aligned_target.append(self.delete_token)
                        operations.append(('DELETE', src_pos + k, -1))
                elif tgt_len > src_len:
                    # 目标序列更长，需要 INSERT
                    for k in range(min_len, tgt_len):
                        aligned_source.append(self.insert_token)
                        aligned_target.append(target_tokens[j1 + k])
                        operations.append(('INSERT', -1, tgt_pos + k))
                
                src_pos += src_len
                tgt_pos += tgt_len
                
            elif tag == 'delete':
                # 删除操作
                for k in range(i2 - i1):
                    aligned_source.append(source_tokens[i1 + k])
                    aligned_target.append(self.delete_token)
                    operations.append(('DELETE', src_pos + k, -1))
                src_pos += (i2 - i1)
                
            elif tag == 'insert':
                # 插入操作
                for k in range(j2 - j1):
                    aligned_source.append(self.insert_token)
                    aligned_target.append(target_tokens[j1 + k])
                    operations.append(('INSERT', -1, tgt_pos + k))
                tgt_pos += (j2 - j1)
        
        return aligned_source, aligned_target, operations
    
    def detect_spans_from_alignment(self, operations, orig_tokens, tgt_tokens):
        """
        从对齐结果中检测需要改写的 spans
        
        Args:
            operations: 对齐操作列表
            orig_tokens: 原始 tokens
            tgt_tokens: 目标 tokens
            
        Returns:
            spans: Span 列表，每个 span 包含 {start, end, rewrite_text}
        """
        spans = []
        current_span = None
        
        for i, (op_type, src_idx, tgt_idx) in enumerate(operations):
            if src_idx == -1:
                continue  # 插入操作，不处理
            
            if op_type in ['REPLACE', 'DELETE']:
                # 开始或继续一个 span
                if current_span is None:
                    current_span = {
                        'start': src_idx,
                        'end': src_idx + 1,
                        'rewrite_tokens': []
                    }
                
                # 扩展当前 span
                if op_type == 'REPLACE' and tgt_idx != -1 and tgt_idx < len(tgt_tokens):
                    current_span['rewrite_tokens'].append(tgt_tokens[tgt_idx])
                elif op_type == 'DELETE':
                    pass  # 删除操作，不添加改写内容
                
                # 检查是否是连续的
                next_op = operations[i + 1] if i + 1 < len(operations) else None
                if next_op is None or next_op[0] not in ['REPLACE', 'DELETE'] or next_op[1] != src_idx + 1:
                    # 结束当前 span
                    if current_span:
                        spans.append(current_span)
                        current_span = None
            
            elif op_type == 'KEEP':
                # KEEP 操作会中断 span
                if current_span:
                    spans.append(current_span)
                    current_span = None
        
        # 处理最后一个 span
        if current_span:
            spans.append(current_span)
        
        return spans
    
    def build_sample_span_level(self, original_query, target_query, max_length=256):
        """
        方法 3: Span 级别改写
        将查询改写任务转化为 Span 检测 + Span 改写的两阶段任务
        
        数据格式：
        - 输入：原始查询 + Span 标记
        - 输出：Span 位置 + 改写内容
        
        Args:
            original_query: 原始查询
            target_query: 目标查询
            max_length: 最大序列长度
            
        Returns:
            sample: 训练样本（包含两种格式的数据）
        """
        # 分词
        orig_tokens = self.tokenizer.tokenize(original_query)
        tgt_tokens = self.tokenizer.tokenize(target_query)
        
        # 截断（预留空间给特殊标记）
        reserved_length = max_length - 10  # 预留空间
        if len(orig_tokens) > reserved_length:
            orig_tokens = orig_tokens[:reserved_length]
        if len(tgt_tokens) > reserved_length:
            tgt_tokens = tgt_tokens[:reserved_length]
        
        # 获取对齐关系
        _, _, operations = self.align_sequences_advanced(orig_tokens, tgt_tokens)
        
        # 检测需要改写的 spans
        spans = self.detect_spans_from_alignment(operations, orig_tokens, tgt_tokens)
        
        # ========== 格式 1: BIO 标注（用于 Span 检测）==========
        # B-SPAN: span 开始，I-SPAN: span 中间，O: 不在 span 中
        bio_labels = ['O'] * len(orig_tokens)
        
        for span in spans:
            start = span['start']
            end = span['end']
            
            if start < len(bio_labels):
                bio_labels[start] = 'B-SPAN'
                for i in range(start + 1, min(end, len(bio_labels))):
                    bio_labels[i] = 'I-SPAN'
        
        # 转换为数字标签
        bio_label_map = {'O': 0, 'B-SPAN': 1, 'I-SPAN': 2}
        bio_label_ids = [bio_label_map[label] for label in bio_labels]
        
        # 构建 input_ids（原始序列）
        input_ids = [self.tokenizer.cls_token_id] + \
                   self.tokenizer.convert_tokens_to_ids(orig_tokens) + \
                   [self.tokenizer.sep_token_id]
        
        # BIO labels（CLS 和 SEP 位置设为 -100）
        bio_labels_full = [-100] + bio_label_ids + [-100]
        
        attention_mask = [1] * len(input_ids)
        
        # Padding
        padding_length = max_length - len(input_ids)
        if padding_length > 0:
            input_ids += [self.tokenizer.pad_token_id] * padding_length
            attention_mask += [0] * padding_length
            bio_labels_full += [-100] * padding_length
        
        # ========== 格式 2: Span 改写数据（用于 Seq2Seq 模型）==========
        span_rewrite_data = []
        
        for span in spans:
            start = span['start']
            end = span['end']
            rewrite_tokens = span['rewrite_tokens']
            
            # 提取 span 原文
            span_original = orig_tokens[start:end]
            span_original_text = self.tokenizer.convert_tokens_to_string(span_original)
            
            # 提取改写文本
            span_rewrite_text = self.tokenizer.convert_tokens_to_string(rewrite_tokens)
            
            # 构建上下文（span 前后的内容）
            context_before = orig_tokens[:start]
            context_after = orig_tokens[end:]
            
            span_rewrite_data.append({
                'span_id': f"{start}_{end}",
                'span_original': span_original_text,
                'span_rewrite': span_rewrite_text,
                'context_before': self.tokenizer.convert_tokens_to_string(context_before),
                'context_after': self.tokenizer.convert_tokens_to_string(context_after),
                'position': {'start': start, 'end': end}
            })
        
        # ========== 格式 3: 增强的输入表示（带 Span 标记）==========
        # 在原始序列中标记出需要改写的 span
        enhanced_tokens = []
        for i, token in enumerate(orig_tokens):
            # 检查是否在某个 span 的开始位置
            is_span_start = any(s['start'] == i for s in spans)
            is_span_end = any(s['end'] == i for s in spans)
            
            if is_span_start:
                enhanced_tokens.append(self.span_start_token)
            
            enhanced_tokens.append(token)
            
            if is_span_end:
                enhanced_tokens.append(self.span_end_token)
        
        # 如果最后一个 token 在 span 中，添加结束标记
        if spans and max(s['end'] for s in spans) == len(orig_tokens):
            enhanced_tokens.append(self.span_end_token)
        
        enhanced_input_ids = [self.tokenizer.cls_token_id] + \
                            self.tokenizer.convert_tokens_to_ids(enhanced_tokens) + \
                            [self.tokenizer.sep_token_id]
        
        enhanced_attention_mask = [1] * len(enhanced_input_ids)
        
        # Padding for enhanced
        enhanced_padding = max_length - len(enhanced_input_ids)
        if enhanced_padding > 0:
            enhanced_input_ids += [self.tokenizer.pad_token_id] * enhanced_padding
            enhanced_attention_mask += [0] * enhanced_padding
        
        return {
            "original_query": original_query,
            "target_query": target_query,
            # 格式 1: BIO 标注数据
            "input_ids": input_ids,
            "bio_labels": bio_labels_full,
            "attention_mask": attention_mask,
            # 格式 2: Span 改写数据
            "spans": span_rewrite_data,
            # 格式 3: 增强输入
            "enhanced_input_ids": enhanced_input_ids,
            "enhanced_attention_mask": enhanced_attention_mask,
            # 元数据
            "method": "span_level",
            "num_spans": len(spans),
            "orig_tokens": orig_tokens,
            "tgt_tokens": tgt_tokens
        }
    
    def build_sample_edit_operation(self, original_query, target_query, max_length=128):
        """
        方法 1: 编辑操作标签法
        每个位置预测一个编辑操作（KEEP/DELETE/REPLACE_X）
        
        Args:
            original_query: 原始查询
            target_query: 目标查询
            max_length: 最大序列长度
            
        Returns:
            sample: 训练样本
        """
        # 分词
        orig_tokens = self.tokenizer.tokenize(original_query)
        tgt_tokens = self.tokenizer.tokenize(target_query)
        
        # 截断
        if len(orig_tokens) > max_length - 2:
            orig_tokens = orig_tokens[:max_length-2]
        if len(tgt_tokens) > max_length - 2:
            tgt_tokens = tgt_tokens[:max_length-2]
        
        # 获取对齐关系
        _, _, operations = self.align_sequences_advanced(orig_tokens, tgt_tokens)
        
        # 构建编辑操作标签
        # 标签体系：
        # 0: KEEP (保持原词)
        # 1: DELETE (删除)
        # 2+: REPLACE_i (替换为词表中第 i 个词)
        labels = []
        op_to_label = {}
        
        for op_type, src_idx, tgt_idx in operations:
            if src_idx == -1:
                continue  # 插入操作不对应源位置
            
            if op_type == 'KEEP':
                label = 0  # KEEP
            elif op_type == 'DELETE':
                label = 1  # DELETE
            elif op_type == 'REPLACE':
                # 获取目标词的索引
                if tgt_idx < len(tgt_tokens):
                    tgt_token_id = self.tokenizer.convert_tokens_to_ids([tgt_tokens[tgt_idx]])[0]
                    # 映射到标签空间（从 2 开始）
                    label = tgt_token_id + 2
                else:
                    label = 0  # 默认 KEEP
            
            labels.append(label)
        
        # 转换为 input_ids
        input_ids = [self.tokenizer.cls_token_id] + \
                   self.tokenizer.convert_tokens_to_ids(orig_tokens) + \
                   [self.tokenizer.sep_token_id]
        
        # Labels: CLS 和 SEP 位置设为 -100
        labels = [-100] + labels + [-100]
        attention_mask = [1] * len(input_ids)
        
        # Padding
        padding_length = max_length - len(input_ids)
        if padding_length > 0:
            input_ids += [self.tokenizer.pad_token_id] * padding_length
            attention_mask += [0] * padding_length
            labels += [-100] * padding_length
        
        return {
            "original_query": original_query,
            "target_query": target_query,
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": attention_mask,
            "method": "edit_operation"
        }
    
    def build_sample_align_with_insert(self, original_query, target_query, max_length=128):
        """
        方法 2: 带插入标记的对齐
        在源序列中添加<INS>标记来表示需要插入的位置
        
        Args:
            original_query: 原始查询
            target_query: 目标查询
            max_length: 最大序列长度
            
        Returns:
            sample: 训练样本
        """
        # 分词
        orig_tokens = self.tokenizer.tokenize(original_query)
        tgt_tokens = self.tokenizer.tokenize(target_query)
        
        # 高级对齐（支持插入标记）
        aligned_source, aligned_target, _ = self.align_sequences_advanced(
            orig_tokens, tgt_tokens
        )
        
        # 截断（如果对齐后的序列过长）
        if len(aligned_source) > max_length - 2:
            # 优先保留非插入位置
            keep_indices = [i for i, t in enumerate(aligned_source) if t != self.insert_token]
            if len(keep_indices) <= max_length - 2:
                # 只删除插入标记
                aligned_source = [aligned_source[i] for i in keep_indices]
                aligned_target = [aligned_target[i] for i in keep_indices]
            else:
                # 仍然过长，整体截断
                aligned_source = aligned_source[:max_length-2]
                aligned_target = aligned_target[:max_length-2]
        
        # 转换为 IDs
        input_ids = [self.tokenizer.cls_token_id] + \
                   self.tokenizer.convert_tokens_to_ids(aligned_source) + \
                   [self.tokenizer.sep_token_id]
        
        # 构建 labels（目标序列的 IDs）
        labels = [-100]  # CLS 位置
        for token in aligned_target:
            if token == self.delete_token:
                labels.append(-100)  # 删除的 token 不计算 loss
            else:
                token_id = self.tokenizer.convert_tokens_to_ids([token])[0]
                labels.append(token_id)
        labels.append(-100)  # SEP 位置
        
        attention_mask = [1] * len(input_ids)
        
        # Padding
        padding_length = max_length - len(input_ids)
        if padding_length > 0:
            input_ids += [self.tokenizer.pad_token_id] * padding_length
            attention_mask += [0] * padding_length
            labels += [-100] * padding_length
        
        return {
            "original_query": original_query,
            "target_query": target_query,
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": attention_mask,
            "aligned_source": aligned_source,
            "aligned_target": aligned_target,
            "method": "align_with_insert"
        }
    
    def build_sample(self, original_query, target_query, max_length=128):
        """
        构建单个训练样本 - 根据策略选择方法
        
        Args:
            original_query: 原始查询
            target_query: 目标查询
            max_length: 最大序列长度
            
        Returns:
            sample: 训练样本
        """
        if self.strategy == "edit_operation":
            return self.build_sample_edit_operation(
                original_query, target_query, max_length
            )
        elif self.strategy == "span_level":
            return self.build_sample_span_level(
                original_query, target_query, max_length
            )
        elif self.strategy == "align_with_insert":
            return self.build_sample_align_with_insert(
                original_query, target_query, max_length
            )
        else:
            # 默认方法（原始方法，可能有长度问题）
            return self._build_sample_basic(
                original_query, target_query, max_length
            )
    
    def _build_sample_basic(self, original_query, target_query, max_length=128):
        """原始方法（保留向后兼容）"""
        # 分词
        orig_tokens = self.tokenizer.tokenize(original_query)
        tgt_tokens = self.tokenizer.tokenize(target_query)
        
        # 转换为词表索引
        orig_ids = self.tokenizer.convert_tokens_to_ids(orig_tokens)
        tgt_ids = self.tokenizer.convert_tokens_to_ids(tgt_tokens)
        
        # 截断过长的序列
        if len(orig_ids) > max_length - 2:  # 预留 CLS 和 SEP
            orig_ids = orig_ids[:max_length-2]
            orig_tokens = orig_tokens[:max_length-2]
        
        if len(tgt_ids) > max_length - 2:
            tgt_ids = tgt_ids[:max_length-2]
            tgt_tokens = tgt_tokens[:max_length-2]
        
        # 添加特殊 token [CLS] + tokens + [SEP]
        input_ids = [self.tokenizer.cls_token_id] + orig_ids + [self.tokenizer.sep_token_id]
        attention_mask = [1] * len(input_ids)
        
        # 构建 labels
        labels = [-100]  # CLS token 不计算 loss
        
        # 获取对齐关系
        alignments = self.align_sequences(orig_tokens, tgt_tokens)
        
        # 创建目标位置映射
        tgt_position_map = {}
        for src_idx, tgt_idx in alignments:
            if tgt_idx != -1:
                tgt_position_map[src_idx] = tgt_idx
        
        # 为每个原始位置分配目标 label
        for i in range(len(orig_ids)):
            if i in tgt_position_map:
                # 有对应的目标词
                labels.append(tgt_ids[tgt_position_map[i]])
            else:
                # 该位置被删除或没有对应目标，保持原词
                labels.append(orig_ids[i])
        
        labels.append(-100)  # SEP token 不计算 loss
        
        # padding 到统一长度
        padding_length = max_length - len(input_ids)
        if padding_length > 0:
            input_ids += [self.tokenizer.pad_token_id] * padding_length
            attention_mask += [0] * padding_length
            labels += [-100] * padding_length
        
        return {
            "original_query": original_query,
            "target_query": target_query,
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": attention_mask,
            "orig_tokens": orig_tokens,
            "tgt_tokens": tgt_tokens
        }


class QueryRewriteDataset(Dataset):
    """查询改写数据集 - 增强版"""
    
    def __init__(self, data_path=None, data_list=None, model_name="hfl/chinese-macbert-base", 
                 max_length=128, strategy="align_with_insert"):
        """
        初始化数据集
        
        Args:
            data_path: JSON 格式的数据文件路径
            data_list: 数据列表 [(original, target), ...]
            model_name: 模型名称
            max_length: 最大序列长度
            strategy: 长度处理策略
                - "keep_original": 保持原长
                - "align_with_insert": 对齐并添加插入标记
                - "edit_operation": 编辑操作标签法
                - "span_level": Span 级别改写（新增）
        """
        self.builder = QueryRewriteDataBuilder(model_name, strategy=strategy)
        self.max_length = max_length
        self.strategy = strategy
        self.samples = []
        
        if data_path:
            logger.info(f"从文件加载数据：{data_path}")
            with open(data_path, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
        
        if data_list:
            logger.info(f"处理 {len(data_list)} 条训练数据（策略：{strategy}）")
            for item in tqdm(data_list, desc="构建数据集"):
                if isinstance(item, dict):
                    sample = self.builder.build_sample(
                        item['original_query'],
                        item['target_query'],
                        self.max_length
                    )
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    sample = self.builder.build_sample(item[0], item[1], self.max_length)
                else:
                    continue
                self.samples.append(sample)
        
        logger.info(f"数据集大小：{len(self.samples)}")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # 根据策略返回不同的数据格式
        if self.strategy == "span_level":
            # Span 级别需要返回多种数据
            return {
                "input_ids": torch.tensor(sample["input_ids"], dtype=torch.long),
                "bio_labels": torch.tensor(sample["bio_labels"], dtype=torch.long),
                "attention_mask": torch.tensor(sample["attention_mask"], dtype=torch.long),
                "enhanced_input_ids": torch.tensor(sample["enhanced_input_ids"], dtype=torch.long),
                "enhanced_attention_mask": torch.tensor(sample["enhanced_attention_mask"], dtype=torch.long),
                "spans": sample["spans"],  # 保持为列表
                "original_query": sample["original_query"],
                "target_query": sample["target_query"]
            }
        else:
            # 其他策略使用标准格式
            return {
                "input_ids": torch.tensor(sample["input_ids"], dtype=torch.long),
                "labels": torch.tensor(sample["labels"], dtype=torch.long),
                "attention_mask": torch.tensor(sample["attention_mask"], dtype=torch.long),
                "original_query": sample["original_query"],
                "target_query": sample["target_query"]
            }


class MacBERTForQueryRewrite(nn.Module):
    """基于 MacBERT的查询改写模型"""
    
    def __init__(self, model_name="hfl/chinese-macbert-base"):
        """
        初始化模型
        
        Args:
            model_name: MacBERT 模型名称或路径
        """
        super(MacBERTForQueryRewrite, self).__init__()
        self.bert = BertModel.from_pretrained(model_name)
        self.config = self.bert.config
        self.vocab_size = self.config.vocab_size
        
        # 输出层：将 BERT 的输出映射到词表空间
        self.classifier = nn.Linear(self.config.hidden_size, self.vocab_size)
        
        logger.info(f"加载 MacBERT 模型：{model_name}")
        logger.info(f"词表大小：{self.vocab_size}")
    
    def forward(self, input_ids, attention_mask=None, labels=None):
        """
        前向传播
        
        Args:
            input_ids: 输入 token IDs [batch_size, seq_len]
            attention_mask: 注意力掩码 [batch_size, seq_len]
            labels: 标签 [batch_size, seq_len]
            
        Returns:
            loss: 如果提供了 labels，返回损失
            logits: 预测分数 [batch_size, seq_len, vocab_size]
        """
        # BERT 编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        sequence_output = outputs.last_hidden_state
        
        # 预测每个位置的词
        logits = self.classifier(sequence_output)
        
        loss = None
        if labels is not None:
            # 计算交叉熵损失，忽略 label=-100 的位置
            loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
            
            # reshape 用于计算 loss
            batch_size, seq_len, vocab_size = logits.shape
            logits_flat = logits.view(-1, vocab_size)
            labels_flat = labels.view(-1)
            
            loss = loss_fct(logits_flat, labels_flat)
        
        return loss, logits
    
    def predict(self, input_ids, attention_mask=None):
        """
        预测改写结果
        
        Args:
            input_ids: 输入 token IDs
            attention_mask: 注意力掩码
            
        Returns:
            predicted_ids: 预测的 token IDs
            confidence: 置信度
        """
        self.eval()
        with torch.no_grad():
            _, logits = self.forward(input_ids, attention_mask)
            
            # 获取每个位置概率最高的词
            probs = torch.softmax(logits, dim=-1)
            confidence, predicted_ids = torch.max(probs, dim=-1)
        
        return predicted_ids, confidence


class MacBERTForSpanDetection(nn.Module):
    """
    Span 级别改写 - Span 检测模型
    
    用于识别查询中需要改写的文本片段（两阶段方法的第一阶段）
    """
    
    def __init__(self, model_name="hfl/chinese-macbert-base"):
        """
        初始化 Span 检测模型
        
        Args:
            model_name: MacBERT 模型名称或路径
        """
        super(MacBERTForSpanDetection, self).__init__()
        self.bert = BertModel.from_pretrained(model_name)
        self.config = self.bert.config
        
        # BIO 标注：O, B-SPAN, I-SPAN (3 类)
        self.num_labels = 3
        self.classifier = nn.Linear(self.config.hidden_size, self.num_labels)
        
        logger.info(f"加载 MacBERT Span 检测模型：{model_name}")
        logger.info(f"标签数量：{self.num_labels}")
    
    def forward(self, input_ids, attention_mask=None, bio_labels=None):
        """
        前向传播
        
        Args:
            input_ids: 输入 token IDs [batch_size, seq_len]
            attention_mask: 注意力掩码 [batch_size, seq_len]
            bio_labels: BIO 标签 [batch_size, seq_len]
            
        Returns:
            loss: 如果提供了 labels，返回损失
            logits: 预测分数 [batch_size, seq_len, num_labels]
        """
        # BERT 编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        sequence_output = outputs.last_hidden_state
        
        # 预测每个位置的 BIO 标签
        logits = self.classifier(sequence_output)
        
        loss = None
        if bio_labels is not None:
            # 计算交叉熵损失，忽略 label=-100 的位置
            loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
            
            # reshape 用于计算 loss
            batch_size, seq_len, num_labels = logits.shape
            logits_flat = logits.view(-1, num_labels)
            labels_flat = bio_labels.view(-1)
            
            loss = loss_fct(logits_flat, labels_flat)
        
        return loss, logits
    
    def detect_spans(self, input_ids, attention_mask=None):
        """
        检测需要改写的 spans
        
        Args:
            input_ids: 输入 token IDs
            attention_mask: 注意力掩码
            
        Returns:
            spans: 检测到的 spans 列表 [(start, end), ...]
            confidence: 置信度
        """
        self.eval()
        with torch.no_grad():
            _, logits = self.forward(input_ids, attention_mask)
            
            # 获取预测的 BIO 标签
            probs = torch.softmax(logits, dim=-1)
            confidence, predictions = torch.max(probs, dim=-1)
            
            # 解析 BIO 序列为 spans
            predictions = predictions[0].cpu().numpy()
            confidence = confidence[0].cpu().numpy()
            
            spans = []
            current_span = None
            
            for i, pred in enumerate(predictions):
                if pred == 1:  # B-SPAN
                    if current_span:
                        spans.append(current_span)
                    current_span = {'start': i, 'end': i + 1}
                elif pred == 2:  # I-SPAN
                    if current_span:
                        current_span['end'] = i + 1
                else:  # O
                    if current_span:
                        spans.append(current_span)
                        current_span = None
            
            # 处理最后一个 span
            if current_span:
                spans.append(current_span)
            
            avg_confidence = confidence.mean()
            
            return spans, avg_confidence


class MacBERTForSpanRewrite(nn.Module):
    """
    Span 级别改写 - Span 改写模型
    
    对检测到的 span 进行改写（两阶段方法的第二阶段）
    使用 Encoder-Decoder 架构
    """
    
    def __init__(self, encoder_name="hfl/chinese-macbert-base", 
                 decoder_name="gpt2"):
        """
        初始化 Span 改写模型
        
        Args:
            encoder_name: 编码器模型名称
            decoder_name: 解码器模型名称
        """
        super(MacBERTForSpanRewrite, self).__init__()
        
        from transformers import EncoderDecoderModel, GPT2Tokenizer
        
        # 创建 Encoder-Decoder 模型
        self.model = EncoderDecoderModel.from_encoder_decoder_pretrained(
            encoder_name,
            decoder_name
        )
        
        self.encoder_tokenizer = BertTokenizer.from_pretrained(encoder_name)
        self.decoder_tokenizer = GPT2Tokenizer.from_pretrained(decoder_name)
        
        # 设置 pad token
        if self.decoder_tokenizer.pad_token is None:
            self.decoder_tokenizer.pad_token = self.decoder_tokenizer.eos_token
        
        self.model.config.decoder_start_token_id = self.decoder_tokenizer.bos_token_id
        self.model.config.eos_token_id = self.decoder_tokenizer.eos_token_id
        self.model.config.pad_token_id = self.decoder_tokenizer.pad_token_id
        
        logger.info(f"加载 Span 改写模型：Encoder={encoder_name}, Decoder={decoder_name}")
    
    def forward(self, input_ids, attention_mask=None, decoder_input_ids=None, 
                decoder_labels=None):
        """
        前向传播
        
        Args:
            input_ids: 编码器输入 [batch_size, seq_len]
            attention_mask: 注意力掩码
            decoder_input_ids: 解码器输入
            decoder_labels: 解码器标签
            
        Returns:
            loss: 如果提供了 labels，返回损失
            logits: 解码器输出
        """
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            decoder_input_ids=decoder_input_ids,
            labels=decoder_labels
        )
        
        return outputs.loss, outputs.logits
    
    def rewrite_span(self, span_text, context_before="", context_after="", 
                     max_length=50):
        """
        改写单个 span
        
        Args:
            span_text: 需要改写的 span 文本
            context_before: 上文
            context_after: 下文
            max_length: 最大生成长度
            
        Returns:
            rewritten_text: 改写后的文本
        """
        self.eval()
        
        # 构建输入：上下文 + span
        input_text = f"{context_before} [SPAN] {span_text} [SPAN_END] {context_after}"
        
        # 分词
        inputs = self.encoder_tokenizer(
            input_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length
        )
        
        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_length=max_length,
                num_beams=4,
                early_stopping=True
            )
        
        # 解码
        rewritten_text = self.decoder_tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        return rewritten_text


class Trainer:
    """训练器 - 增强版（支持 Span 级别）"""
    
    def __init__(self, model, train_dataset, val_dataset, args):
        """
        初始化训练器
        
        Args:
            model: 模型
            train_dataset: 训练数据集
            val_dataset: 验证数据集
            args: 训练参数
        """
        self.model = model
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.args = args
        self.strategy = getattr(train_dataset, 'strategy', 'standard')
        
        # 设备配置
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        logger.info(f"使用设备：{self.device}")
        
        # 数据加载器
        self.train_loader = DataLoader(
            train_dataset, 
            batch_size=args.batch_size, 
            shuffle=True,
            num_workers=0
        )
        self.val_loader = DataLoader(
            val_dataset, 
            batch_size=args.batch_size,
            num_workers=0
        )
        
        # 优化器
        self.optimizer = AdamW(
            model.parameters(), 
            lr=args.learning_rate,
            weight_decay=args.weight_decay
        )
        
        # 学习率调度器
        total_steps = len(self.train_loader) * args.epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=int(total_steps * 0.1),
            num_training_steps=total_steps
        )
        
        # 最佳模型保存路径
        self.best_model_path = args.output_dir
        os.makedirs(self.best_model_path, exist_ok=True)
        
        logger.info(f"训练策略：{self.strategy}")
    
    def train_epoch_span_level(self, epoch):
        """训练一个 epoch（Span 级别专用）"""
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        progress_bar = tqdm(self.train_loader, desc=f"Epoch {epoch+1}/{self.args.epochs}")
        
        for batch in progress_bar:
            # 准备数据（Span 级别格式）
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            bio_labels = batch["bio_labels"].to(self.device)
            
            # 前向传播（Span 检测）
            self.optimizer.zero_grad()
            loss, _ = self.model(input_ids, attention_mask, bio_labels)
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.args.max_grad_norm)
            
            # 更新参数
            self.optimizer.step()
            self.scheduler.step()
            
            # 记录损失
            total_loss += loss.item()
            num_batches += 1
            
            # 更新进度条
            progress_bar.set_postfix({"loss": loss.item()})
        
        avg_loss = total_loss / max(num_batches, 1)
        return avg_loss
    
    def train_epoch(self, epoch):
        """训练一个 epoch"""
        # 如果是 Span 级别，使用专门的训练方法
        if self.strategy == "span_level":
            return self.train_epoch_span_level(epoch)
        
        # 否则使用标准训练方法
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        progress_bar = tqdm(self.train_loader, desc=f"Epoch {epoch+1}/{self.args.epochs}")
        
        for batch in progress_bar:
            # 准备数据
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch.get("labels")
            
            if labels is not None:
                labels = labels.to(self.device)
            
            # 前向传播
            self.optimizer.zero_grad()
            
            # 根据模型类型调用不同的 forward
            if isinstance(self.model, MacBERTForSpanDetection):
                loss, _ = self.model(input_ids, attention_mask, bio_labels=labels)
            else:
                loss, _ = self.model(input_ids, attention_mask, labels)
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.args.max_grad_norm)
            
            # 更新参数
            self.optimizer.step()
            self.scheduler.step()
            
            # 记录损失
            total_loss += loss.item()
            num_batches += 1
            
            # 更新进度条
            progress_bar.set_postfix({"loss": loss.item()})
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def evaluate_span_level(self, epoch):
        """评估模型（Span 级别专用）"""
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        with torch.no_grad():
            for batch in tqdm(self.val_loader, desc=f"Validation {epoch+1}"):
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                bio_labels = batch["bio_labels"].to(self.device)
                
                loss, _ = self.model(input_ids, attention_mask, bio_labels)
                total_loss += loss.item()
                num_batches += 1
        
        avg_loss = total_loss / max(num_batches, 1)
        return avg_loss
    
    def evaluate(self, epoch):
        """评估模型"""
        if self.strategy == "span_level":
            return self.evaluate_span_level(epoch)
        
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        with torch.no_grad():
            for batch in tqdm(self.val_loader, desc=f"Validation {epoch+1}"):
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch.get("labels")
                
                if labels is not None:
                    labels = labels.to(self.device)
                
                if isinstance(self.model, MacBERTForSpanDetection):
                    loss, _ = self.model(input_ids, attention_mask, bio_labels=labels)
                else:
                    loss, _ = self.model(input_ids, attention_mask, labels)
                
                total_loss += loss.item()
                num_batches += 1
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def train(self):
        """开始训练"""
        logger.info("开始训练...")
        best_val_loss = float('inf')
        
        for epoch in range(self.args.epochs):
            # 训练
            train_loss = self.train_epoch(epoch)
            logger.info(f"Epoch {epoch+1}/{self.args.epochs} - Train Loss: {train_loss:.4f}")
            
            # 验证
            val_loss = self.evaluate(epoch)
            logger.info(f"Epoch {epoch+1}/{self.args.epochs} - Val Loss: {val_loss:.4f}")
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model(self.best_model_path)
                logger.info(f"保存最佳模型到 {self.best_model_path}")
        
        logger.info(f"训练完成！最佳验证损失：{best_val_loss:.4f}")
    
    def save_model(self, output_dir):
        """保存模型"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存模型权重
        model_to_save = self.model.module if hasattr(self.model, 'module') else self.model
        torch.save(model_to_save.state_dict(), os.path.join(output_dir, "pytorch_model.bin"))
        
        # 保存配置文件
        if hasattr(model_to_save, 'bert'):
            model_to_save.bert.config.to_json_file(os.path.join(output_dir, "config.json"))
        elif hasattr(model_to_save, 'model'):
            model_to_save.model.config.to_json_file(os.path.join(output_dir, "config.json"))
        
        # 保存 tokenizer
        if hasattr(self.train_dataset.builder, 'tokenizer'):
            self.train_dataset.builder.tokenizer.save_pretrained(output_dir)
        
        logger.info(f"模型已保存到 {output_dir}")


class Predictor:
    """预测器"""
    
    def __init__(self, model_path, model_name="hfl/chinese-macbert-base"):
        """
        初始化预测器
        
        Args:
            model_path: 模型路径
            model_name: 模型名称
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.model = MacBERTForQueryRewrite(model_name)
        self.model.load_state_dict(torch.load(os.path.join(model_path, "pytorch_model.bin"), map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"加载模型成功：{model_path}")
    
    def predict(self, query, max_length=128):
        """
        预测改写结果
        
        Args:
            query: 原始查询
            max_length: 最大序列长度
            
        Returns:
            rewritten_query: 改写后的查询
            confidence: 平均置信度
        """
        # 分词
        tokens = self.tokenizer.tokenize(query)
        if len(tokens) > max_length - 2:
            tokens = tokens[:max_length-2]
        
        # 转换为 IDs
        input_ids = [self.tokenizer.cls_token_id] + \
                   self.tokenizer.convert_tokens_to_ids(tokens) + \
                   [self.tokenizer.sep_token_id]
        attention_mask = [1] * len(input_ids)
        
        # Padding
        padding_length = max_length - len(input_ids)
        if padding_length > 0:
            input_ids += [self.tokenizer.pad_token_id] * padding_length
            attention_mask += [0] * padding_length
        
        # 转换为 tensor
        input_ids = torch.tensor([input_ids]).to(self.device)
        attention_mask = torch.tensor([attention_mask]).to(self.device)
        
        # 预测
        with torch.no_grad():
            predicted_ids, confidence = self.model.predict(input_ids, attention_mask)
        
        # 解码预测结果
        predicted_tokens = self.tokenizer.convert_ids_to_tokens(predicted_ids[0])
        
        # 去除特殊 token 和 padding
        final_tokens = []
        for token in predicted_tokens:
            if token in [self.tokenizer.cls_token, self.tokenizer.sep_token, self.tokenizer.pad_token]:
                continue
            final_tokens.append(token)
        
        # 拼接为最终结果
        rewritten_query = self.tokenizer.convert_tokens_to_string(final_tokens)
        avg_confidence = confidence[0].mean().item()
        
        return rewritten_query, avg_confidence


def create_sample_data():
    """创建示例训练数据"""
    data = [
        ("寿改", "寿险改革"),
        ("拧毛巾", "清洗毛巾"),
        ("vpn 到期了怎么办", "vpn 申请链接"),
        ("电脑登录不了", "电脑无法登录"),
        ("密码忘记了", "密码找回"),
        ("怎么转账", "转账方法"),
        ("余额不足", "充值"),
        ("客服在哪", "联系客服"),
        ("订单取消", "取消订单"),
        ("退款进度", "退款查询"),
    ]
    return data


def main():
    """主函数"""
    # 训练参数
    class Args:
        batch_size = 8
        epochs = 10
        learning_rate = 5e-5
        weight_decay = 0.01
        max_grad_norm = 1.0
        output_dir = "./query_rewrite_model"
        max_length = 128
        strategy = "align_with_insert"  # 新增策略参数
    
    args = Args()
    
    # 创建示例数据
    logger.info("创建训练数据...")
    train_data = create_sample_data()
    
    # 划分训练集和验证集（8:2）
    split_idx = int(len(train_data) * 0.8)
    train_list = train_data[:split_idx]
    val_list = train_data[split_idx:]
    
    # 创建数据集
    train_dataset = QueryRewriteDataset(
        data_list=train_list,
        model_name="hfl/chinese-macbert-base",
        max_length=args.max_length,
        strategy=args.strategy
    )
    
    val_dataset = QueryRewriteDataset(
        data_list=val_list,
        model_name="hfl/chinese-macbert-base",
        max_length=args.max_length,
        strategy=args.strategy
    )
    
    # 创建模型
    model = MacBERTForQueryRewrite("hfl/chinese-macbert-base")
    
    # 创建训练器
    trainer = Trainer(model, train_dataset, val_dataset, args)
    
    # 开始训练
    trainer.train()
    
    # 测试预测
    logger.info("\n测试预测...")
    predictor = Predictor(args.output_dir)
    
    test_queries = ["电脑登录不了", "密码忘记了", "怎么转账"]
    for query in test_queries:
        rewritten, confidence = predictor.predict(query)
        logger.info(f"原句：{query} -> 改写：{rewritten} (置信度：{confidence:.4f})")


if __name__ == "__main__":
    main()
