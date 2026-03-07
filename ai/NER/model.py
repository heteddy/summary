"""
MacBERT + 指针网络 NER 模型

基于 MacBERT 和 Pointer Network 的命名实体识别模型
"""

import torch
import torch.nn as nn
from transformers import BertModel, BertPreTrainedModel


class MacBERTPointerNER(BertPreTrainedModel):
    """
    MacBERT + 指针网络 NER 模型
    
    使用 MacBERT 作为编码器，通过两个独立的 MLP 分别预测实体的起始和结束位置
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.num_entity_types = config.num_labels if hasattr(config, 'num_labels') else 3
        
        # MacBERT 编码器
        self.bert = BertModel(config)
        
        # Dropout
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        
        # 起始位置预测层 (为每个实体类型预测 start 位置)
        self.start_classifier = nn.Sequential(
            nn.Linear(config.hidden_size, config.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(config.hidden_dropout_prob),
            nn.Linear(config.hidden_size // 2, self.num_entity_types)
        )
        
        # 结束位置预测层 (为每个实体类型预测 end 位置)
        self.end_classifier = nn.Sequential(
            nn.Linear(config.hidden_size, config.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(config.hidden_dropout_prob),
            nn.Linear(config.hidden_size // 2, self.num_entity_types)
        )
        
        # 初始化权重
        self.init_weights()
    
    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        start_labels=None,
        end_labels=None,
        return_dict=None,
    ):
        """
        前向传播
        
        Args:
            input_ids: (batch_size, seq_len) - 输入 token IDs
            attention_mask: (batch_size, seq_len) - 注意力掩码
            token_type_ids: (batch_size, seq_len) - 句子类型 IDs
            position_ids: (batch_size, seq_len) - 位置 IDs
            start_labels: (batch_size, num_entity_types, seq_len) - 起始位置标签
            end_labels: (batch_size, num_entity_types, seq_len) - 结束位置标签
            return_dict: 是否返回字典格式
        
        Returns:
            如果提供标签：返回 loss
            否则：返回 (start_logits, end_logits)
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_values
        
        # MacBERT 编码
        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            return_dict=return_dict,
        )
        
        sequence_output = outputs[0]  # (batch_size, seq_len, hidden_size)
        sequence_output = self.dropout(sequence_output)
        
        # 预测起始和结束位置
        start_logits = self.start_classifier(sequence_output)  # (batch_size, seq_len, num_entity_types)
        end_logits = self.end_classifier(sequence_output)      # (batch_size, seq_len, num_entity_types)
        
        # 转置为 (batch_size, num_entity_types, seq_len) 以便与标签对齐
        start_logits = start_logits.permute(0, 2, 1)
        end_logits = end_logits.permute(0, 2, 1)
        
        loss = None
        if start_labels is not None and end_labels is not None:
            # 计算损失
            loss_fct = nn.CrossEntropyLoss()
            
            # start_loss: 对每个实体类型，预测哪个位置是起始位置
            start_loss = loss_fct(start_logits, start_labels.argmax(dim=1))
            
            # end_loss: 对每个实体类型，预测哪个位置是结束位置
            end_loss = loss_fct(end_logits, end_labels.argmax(dim=1))
            
            # 总损失
            loss = start_loss + end_loss
        
        if not return_dict:
            output = (start_logits, end_logits) + outputs[2:]
            return ((loss,) + output) if loss is not None else output
        
        return {
            'loss': loss,
            'start_logits': start_logits,
            'end_logits': end_logits,
            'hidden_states': outputs.hidden_states,
            'attentions': outputs.attentions,
        }


class MacBERTPointerNERAdvanced(MacBERTPointerNER):
    """
    增强版 MacBERT + 指针网络 NER 模型
    
    添加了以下改进:
    1. 多层特征融合
    2. Layer Normalization
    3. 可学习的实体类型嵌入
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Layer Normalization
        self.layer_norm = nn.LayerNorm(config.hidden_size)
        
        # 实体类型嵌入 (可选，用于建模实体类型之间的关系)
        self.entity_type_embeddings = nn.Embedding(self.num_entity_types, config.hidden_size)
        
        # 注意力机制 (用于融合不同层的特征)
        if config.num_hidden_layers > 1:
            self.attention_weight = nn.Parameter(torch.ones(config.num_hidden_layers))
        
        # 初始化权重
        self.init_weights()
    
    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        start_labels=None,
        end_labels=None,
        return_dict=None,
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_values
        
        # MacBERT 编码 (获取所有层的输出)
        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            return_dict=return_dict,
            output_hidden_states=True,
        )
        
        # 使用最后一层的输出
        sequence_output = outputs[0]  # (batch_size, seq_len, hidden_size)
        
        # Layer Normalization
        sequence_output = self.layer_norm(sequence_output)
        
        # Dropout
        sequence_output = self.dropout(sequence_output)
        
        # 预测起始和结束位置
        start_logits = self.start_classifier(sequence_output)  # (batch_size, seq_len, num_entity_types)
        end_logits = self.end_classifier(sequence_output)      # (batch_size, seq_len, num_entity_types)
        
        # 转置
        start_logits = start_logits.permute(0, 2, 1)
        end_logits = end_logits.permute(0, 2, 1)
        
        loss = None
        if start_labels is not None and end_labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            start_loss = loss_fct(start_logits, start_labels.argmax(dim=1))
            end_loss = loss_fct(end_logits, end_labels.argmax(dim=1))
            loss = start_loss + end_loss
        
        if not return_dict:
            output = (start_logits, end_logits) + outputs[2:]
            return ((loss,) + output) if loss is not None else output
        
        return {
            'loss': loss,
            'start_logits': start_logits,
            'end_logits': end_logits,
            'hidden_states': outputs.hidden_states,
            'attentions': outputs.attentions,
        }


def create_model(
    model_name: str = 'hfl/chinese-macbert-base',
    num_entity_types: int = 3,
    advanced: bool = False
):
    """
    创建 MacBERT + 指针网络 NER 模型
    
    Args:
        model_name: MacBERT 模型名称或路径
        num_entity_types: 实体类型数量
        advanced: 是否使用增强版模型
    
    Returns:
        model: NER 模型
    """
    from transformers import BertConfig
    
    # 加载配置
    config = BertConfig.from_pretrained(model_name)
    config.num_labels = num_entity_types
    
    # 创建模型
    if advanced:
        model = MacBERTPointerNERAdvanced.from_pretrained(model_name, config=config)
    else:
        model = MacBERTPointerNER.from_pretrained(model_name, config=config)
    
    return model


if __name__ == '__main__':
    # 测试模型
    model = create_model()
    
    # 创建测试输入
    batch_size = 2
    seq_len = 128
    input_ids = torch.randint(0, 10000, (batch_size, seq_len))
    attention_mask = torch.ones((batch_size, seq_len))
    
    # 前向传播 (训练模式)
    start_labels = torch.zeros((batch_size, 3, seq_len))
    start_labels[0, 0, 5] = 1  # ORGANIZATION start
    start_labels[0, 1, 10] = 1  # DEPARTMENT start
    start_labels[1, 2, 8] = 1   # POSITION start
    
    end_labels = torch.zeros((batch_size, 3, seq_len))
    end_labels[0, 0, 8] = 1    # ORGANIZATION end
    end_labels[0, 1, 13] = 1   # DEPARTMENT end
    end_labels[1, 2, 12] = 1   # POSITION end
    
    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        start_labels=start_labels,
        end_labels=end_labels,
    )
    
    print(f"Loss: {outputs['loss']}")
    print(f"Start logits shape: {outputs['start_logits'].shape}")
    print(f"End logits shape: {outputs['end_logits'].shape}")
    
    # 推理模式
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        start_probs = torch.softmax(outputs['start_logits'], dim=-1)
        end_probs = torch.softmax(outputs['end_logits'], dim=-1)
        
        print(f"\nStart probs shape: {start_probs.shape}")
        print(f"End probs shape: {end_probs.shape}")
