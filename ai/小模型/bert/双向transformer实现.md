# BERT模型的双向编码详解与代码实现

## 1. 双向编码概念

### 1.1 什么是双向编码
双向编码是指模型在处理文本时能够同时考虑**左侧（上文）和右侧（下文）**的信息。这与传统的单向语言模型（如GPT）形成对比，单向模型只能根据上文预测下文，无法利用下文信息。

### 1.2 BERT的双向性
BERT的双向性通过**掩码语言模型（Masked Language Model, MLM）**任务实现。在预训练阶段：
- 随机掩盖输入序列中的部分token（15%）
- 模型需要基于**所有非掩盖位置**的信息来预测被掩盖的token
- 每个位置的预测都可以利用整个序列的上下文信息

### 1.3 与Transformer的区别

| 方面 | Transformer | BERT |
|------|------------|------|
| **架构** | 编码器-解码器结构 | 仅编码器结构 |
| **注意力机制** | 编码器：双向注意力<br>解码器：掩码自注意力（单向） | 完全双向自注意力 |
| **训练任务** | 机器翻译等序列到序列任务 | MLM + NSP（掩码语言模型+下一句预测） |
| **方向性** | 编码器双向，解码器单向 | 完全双向 |
| **应用** | 序列生成、翻译 | 语言理解、分类、问答 |

## 2. 双向编码的PyTorch实现

### 2.1 基础组件实现

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MultiHeadAttention(nn.Module):
    """多头自注意力机制 - 实现双向编码的核心"""
    def __init__(self, d_model=512, num_heads=8, dropout=0.1):
        super().__init__()
        assert d_model % num_heads == 0
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        # 线性变换层
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, query, key, value, mask=None):
        """
        参数:
            query, key, value: [batch_size, seq_len, d_model]
            mask: [batch_size, 1, 1, seq_len] 或 [batch_size, 1, seq_len, seq_len]
        返回:
            output: [batch_size, seq_len, d_model]
            attention_weights: [batch_size, num_heads, seq_len, seq_len]
        """
        batch_size = query.size(0)
        
        # 线性变换并分割多头
        Q = self.W_q(query).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        K = self.W_k(key).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        V = self.W_v(value).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        
        # 计算注意力分数（双向编码的关键）
        # Q: [batch_size, num_heads, seq_len, d_k]
        # K: [batch_size, num_heads, seq_len, d_k]
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        # 应用掩码（如果需要）
        if mask is not None:
            # 注意：在双向编码中，mask主要用于padding，不是用于限制方向性
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        # 计算注意力权重
        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # 应用注意力到value
        context = torch.matmul(attention_weights, V)
        
        # 合并多头
        context = context.transpose(1, 2).contiguous().view(
            batch_size, -1, self.d_model
        )
        
        # 输出变换
        output = self.W_o(context)
        
        return output, attention_weights

class TransformerEncoderLayer(nn.Module):
    """Transformer编码器层 - 实现双向编码"""
    def __init__(self, d_model=512, num_heads=8, d_ff=2048, dropout=0.1):
        super().__init__()
        self.self_attn = MultiHeadAttention(d_model, num_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        # 前馈网络
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
        )
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, mask=None):
        """
        参数:
            x: [batch_size, seq_len, d_model]
            mask: [batch_size, 1, 1, seq_len]
        """
        # 自注意力（双向编码的核心）
        attn_output, attn_weights = self.self_attn(x, x, x, mask)
        
        # 残差连接和层归一化
        x = self.norm1(x + self.dropout(attn_output))
        
        # 前馈网络
        ffn_output = self.ffn(x)
        
        # 残差连接和层归一化
        output = self.norm2(x + self.dropout(ffn_output))
        
        return output, attn_weights

class PositionalEncoding(nn.Module):
    """位置编码"""
    def __init__(self, d_model, max_len=512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                           (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe.unsqueeze(0))
        
    def forward(self, x):
        return x + self.pe[:, :x.size(1)]

class BERTEmbedding(nn.Module):
    """BERT的嵌入层：词嵌入 + 位置嵌入 + 段落嵌入"""
    def __init__(self, vocab_size, d_model=512, max_len=512, n_segments=2):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.position_embedding = nn.Embedding(max_len, d_model)
        self.segment_embedding = nn.Embedding(n_segments, d_model)
        
        self.norm = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, input_ids, segment_ids=None):
        """
        参数:
            input_ids: [batch_size, seq_len]
            segment_ids: [batch_size, seq_len] 段落标识
        """
        batch_size, seq_len = input_ids.size()
        
        # 创建位置索引
        position_ids = torch.arange(seq_len, device=input_ids.device).unsqueeze(0).expand(batch_size, -1)
        
        # 计算各种嵌入
        token_emb = self.token_embedding(input_ids)
        position_emb = self.position_embedding(position_ids)
        
        embeddings = token_emb + position_emb
        
        # 添加段落嵌入（如果有）
        if segment_ids is not None:
            segment_emb = self.segment_embedding(segment_ids)
            embeddings += segment_emb
        
        embeddings = self.norm(embeddings)
        embeddings = self.dropout(embeddings)
        
        return embeddings
```

### 2.2 完整的双向编码器实现

```python
class BidirectionalTransformerEncoder(nn.Module):
    """双向Transformer编码器（类似BERT结构）"""
    def __init__(self, vocab_size, d_model=512, num_layers=6, 
                 num_heads=8, d_ff=2048, max_len=512, dropout=0.1):
        super().__init__()
        self.d_model = d_model
        
        # 嵌入层
        self.embedding = BERTEmbedding(vocab_size, d_model, max_len)
        
        # 多层编码器
        self.layers = nn.ModuleList([
            TransformerEncoderLayer(d_model, num_heads, d_ff, dropout)
            for _ in range(num_layers)
        ])
        
        # 池化层（用于获取句子表示）
        self.pooler = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.Tanh()
        )
        
    def create_padding_mask(self, input_ids):
        """
        创建填充掩码
        参数:
            input_ids: [batch_size, seq_len]
        返回:
            mask: [batch_size, 1, 1, seq_len]
        """
        mask = (input_ids != 0).unsqueeze(1).unsqueeze(2)
        return mask.float()
    
    def forward(self, input_ids, segment_ids=None, return_all_layers=False):
        """
        前向传播 - 实现双向编码
        参数:
            input_ids: [batch_size, seq_len]
            segment_ids: [batch_size, seq_len]
            return_all_layers: 是否返回所有层的输出
        返回:
            序列表示和可选的注意力权重
        """
        # 创建padding mask
        mask = self.create_padding_mask(input_ids)
        
        # 获取嵌入表示
        x = self.embedding(input_ids, segment_ids)
        
        all_layer_outputs = []
        all_attention_weights = []
        
        # 通过多层编码器
        for layer in self.layers:
            x, attn_weights = layer(x, mask)
            
            if return_all_layers:
                all_layer_outputs.append(x)
                all_attention_weights.append(attn_weights)
        
        # 获取[CLS]位置的表示（用于分类任务）
        pooled_output = self.pooler(x[:, 0])  # 假设第一个token是[CLS]
        
        if return_all_layers:
            return {
                'last_hidden_state': x,
                'pooled_output': pooled_output,
                'all_hidden_states': all_layer_outputs,
                'all_attentions': all_attention_weights
            }
        else:
            return x, pooled_output

class BERTForMaskedLM(nn.Module):
    """用于掩码语言模型的BERT"""
    def __init__(self, vocab_size, d_model=512, num_layers=6, 
                 num_heads=8, max_len=512):
        super().__init__()
        
        # 双向编码器
        self.encoder = BidirectionalTransformerEncoder(
            vocab_size, d_model, num_layers, num_heads, 
            d_ff=d_model*4, max_len=max_len
        )
        
        # MLM头
        self.mlm_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
            nn.Linear(d_model, vocab_size)
        )
        
    def forward(self, input_ids, segment_ids=None, masked_positions=None):
        """
        参数:
            input_ids: [batch_size, seq_len]
            masked_positions: [batch_size, n_masks] 需要预测的位置
        """
        # 获取编码器输出
        hidden_states, _ = self.encoder(input_ids, segment_ids)
        
        # 预测被掩盖的token
        if masked_positions is not None:
            # 获取被掩盖位置的表示
            batch_size = hidden_states.size(0)
            seq_len = hidden_states.size(1)
            
            # 收集被掩盖位置的向量
            flat_positions = masked_positions.view(-1)
            batch_indices = torch.arange(batch_size, device=input_ids.device).unsqueeze(1)
            batch_indices = batch_indices.repeat(1, masked_positions.size(1)).view(-1)
            
            masked_vectors = hidden_states[batch_indices, flat_positions]
            
            # 重塑形状
            masked_vectors = masked_vectors.view(batch_size, -1, hidden_states.size(-1))
            
            # 预测被掩盖的token
            mlm_logits = self.mlm_head(masked_vectors)
            
            return mlm_logits, hidden_states
        else:
            # 如果不指定掩盖位置，预测所有位置
            mlm_logits = self.mlm_head(hidden_states)
            return mlm_logits, hidden_states
```

### 2.3 训练示例：掩码语言模型

```python
def mask_tokens(input_ids, mask_token_id, vocab_size, mask_prob=0.15):
    """
    模拟BERT的掩码过程
    """
    labels = input_ids.clone()
    probability_matrix = torch.full(labels.shape, mask_prob)
    
    # 特殊token不掩盖
    special_tokens_mask = (input_ids == 0)  # 假设0是[PAD]
    probability_matrix.masked_fill_(special_tokens_mask, value=0.0)
    
    # 随机选择要掩盖的位置
    masked_indices = torch.bernoulli(probability_matrix).bool()
    labels[~masked_indices] = -100  # 损失函数忽略非掩盖位置
    
    # 80%用[MASK]替换，10%随机替换，10%保持不变
    indices_replaced = torch.bernoulli(torch.full(labels.shape, 0.8)).bool() & masked_indices
    input_ids[indices_replaced] = mask_token_id
    
    indices_random = torch.bernoulli(torch.full(labels.shape, 0.5)).bool() & masked_indices & ~indices_replaced
    random_words = torch.randint(vocab_size, labels.shape, dtype=torch.long)
    input_ids[indices_random] = random_words[indices_random]
    
    return input_ids, labels, masked_indices

def train_masked_language_model():
    """训练掩码语言模型示例"""
    # 超参数
    vocab_size = 30522  # BERT的词汇表大小
    batch_size = 32
    seq_len = 128
    d_model = 768
    mask_token_id = 103  # [MASK]的token id
    
    # 创建模型
    model = BERTForMaskedLM(vocab_size, d_model=d_model, num_layers=12, num_heads=12)
    
    # 优化器
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    criterion = nn.CrossEntropyLoss(ignore_index=-100)
    
    # 模拟训练循环
    for epoch in range(10):
        for batch in range(100):  # 假设有100个batch
            # 模拟输入数据
            input_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
            
            # 应用掩码
            masked_inputs, labels, masked_positions = mask_tokens(
                input_ids.clone(), mask_token_id, vocab_size
            )
            
            # 获取被掩盖位置的非零索引
            masked_indices = masked_positions.nonzero(as_tuple=True)
            if len(masked_indices[0]) > 0:
                # 重塑masked_positions用于模型输入
                batch_positions = masked_indices[0]
                seq_positions = masked_indices[1]
                batch_seq_positions = torch.stack([batch_positions, seq_positions], dim=1)
                masked_pos_tensor = batch_seq_positions[:, 1].view(batch_size, -1)
                
                # 前向传播
                mlm_logits, _ = model(masked_inputs, masked_positions=masked_pos_tensor)
                
                # 计算损失
                loss = criterion(
                    mlm_logits.view(-1, vocab_size),
                    labels[masked_positions].view(-1)
                )
                
                # 反向传播
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                if batch % 10 == 0:
                    print(f"Epoch {epoch}, Batch {batch}, Loss: {loss.item():.4f}")

def demonstrate_bidirectional_encoding():
    """展示双向编码的效果"""
    vocab_size = 10000
    d_model = 512
    seq_len = 10
    
    # 创建模型
    model = BidirectionalTransformerEncoder(vocab_size, d_model=d_model, num_layers=4)
    
    # 创建示例输入
    input_ids = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
    
    # 前向传播
    hidden_states, pooled_output = model(input_ids)
    
    print("输入序列:", input_ids[0].tolist())
    print("输出形状:", hidden_states.shape)  # [1, 10, 512]
    print("池化输出形状:", pooled_output.shape)  # [1, 512]
    
    # 展示注意力机制的双向性
    print("\n双向编码的体现：")
    print("每个位置的表示都包含了整个序列的信息")
    print("第5个位置的表示包含了位置1-10的信息")
    print("这是通过自注意力机制实现的，每个位置都能关注到序列中的所有位置")

if __name__ == "__main__":
    # 运行演示
    demonstrate_bidirectional_encoding()
    
    # 如果要训练MLM，可以取消注释下面的行
    # train_masked_language_model()
```

## 3. 关键点总结

1. **双向性实现**：通过Transformer的自注意力机制，每个位置都能直接访问序列中的所有其他位置。

2. **与单向模型的区别**：
   - 单向（如GPT）：只能看到左侧上下文，用于生成任务
   - 双向（如BERT）：能看到整个上下文，用于理解任务

3. **掩码语言模型**：BERT的双向性是通过MLM预训练任务实现的，模型需要根据上下文预测被掩盖的token。

4. **实际应用**：双向编码使BERT在多项NLP任务中表现出色，特别是在需要理解上下文的任务中（如问答、情感分析等）。

这个实现展示了BERT双向编码的核心原理，虽然简化了原始BERT的一些细节，但抓住了双向编码的本质特征。