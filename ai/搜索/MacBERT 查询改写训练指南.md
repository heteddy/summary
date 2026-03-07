# MacBERT 查询改写训练指南

## 概述

本项目实现了基于 **MacBERT** 模型的查询改写系统，采用**基于分类的生成方法**（方案 B），将序列生成问题转化为序列标注问题。

## 核心原理

### 方法特点
- **模型架构**: 使用 MacBERT（encoder-only）作为基础模型
- **任务转化**: 将 query改写转化为序列标注任务
- **预测方式**: 对输入序列的每个位置进行词表级别的分类，选择概率最高的词作为改写结果

### 技术优势
1. ✅ 利用 MacBERT强大的中文语义理解能力
2. ✅ 双向上下文建模，充分利用语境信息
3. ✅ 训练效率高，可直接使用交叉熵损失
4. ✅ 支持自定义对齐策略，灵活处理长度变化

## 快速开始

### 1. 环境安装

```bash
pip install torch transformers tqdm
```

### 2. 准备训练数据

训练数据格式为 `(原始查询，目标查询)` 的列表：

```python
train_data = [
    ("寿改", "寿险改革"),
    ("拧毛巾", "清洗毛巾"),
    ("vpn 到期了怎么办", "vpn 申请链接"),
    ("电脑登录不了", "电脑无法登录"),
    # ... 更多数据
]
```

或者使用 JSON 文件格式：

```json
[
  {
    "original_query": "寿改",
    "target_query": "寿险改革"
  },
  {
    "original_query": "拧毛巾",
    "target_query": "清洗毛巾"
  }
]
```

### 3. 运行训练

#### 方式 A: 使用示例数据快速测试

```bash
python macbert_query_rewrite_train.py
```

这会使用内置的示例数据进行训练，适合快速验证流程。

#### 方式 B: 使用自定义数据训练

创建 `train_model.py`:

```python
from macbert_query_rewrite_train import (
    QueryRewriteDataset, 
    MacBERTForQueryRewrite, 
    Trainer,
    Args
)

# 加载自定义数据
with open('your_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 划分数据集
split_idx = int(len(data) * 0.8)
train_list = data[:split_idx]
val_list = data[split_idx:]

# 创建数据集
train_dataset = QueryRewriteDataset(
    data_list=train_list,
    model_name="hfl/chinese-macbert-base",
    max_length=128
)

val_dataset = QueryRewriteDataset(
    data_list=val_list,
    model_name="hfl/chinese-macbert-base",
    max_length=128
)

# 创建模型
model = MacBERTForQueryRewrite("hfl/chinese-macbert-base")

# 配置训练参数
args = Args()
args.batch_size = 16
args.epochs = 20
args.learning_rate = 3e-5
args.output_dir = "./my_query_rewrite_model"

# 开始训练
trainer = Trainer(model, train_dataset, val_dataset, args)
trainer.train()
```

### 4. 使用训练好的模型进行预测

```python
from macbert_query_rewrite_train import Predictor

# 加载模型
predictor = Predictor("./my_query_rewrite_model")

# 预测
query = "电脑登录不了"
rewritten, confidence = predictor.predict(query)

print(f"原句：{query}")
print(f"改写：{rewritten}")
print(f"置信度：{confidence:.4f}")
```

## 代码结构说明

### 核心组件

#### 1. QueryRewriteDataBuilder - 数据构建器
负责将原始查询和目标查询转换为训练所需的格式：
- 分词
- 序列对齐（使用编辑距离算法）
- 构建 labels

#### 2. QueryRewriteDataset - 数据集类
PyTorch Dataset，用于加载和处理训练数据。

#### 3. MacBERTForQueryRewrite - 模型类
基于 MacBERT的查询改写模型：
- 使用 BertModel 作为编码器
- 添加线性分类层进行词表预测
- 支持训练和推理两种模式

#### 4. Trainer - 训练器
封装完整的训练流程：
- 自动管理训练循环
- 验证和评估
- 学习率调度
- 最佳模型保存

#### 5. Predictor - 预测器
简化的推理接口，用于生产环境部署。

## 关键技术点

### 1. 序列对齐策略

使用 `difflib.SequenceMatcher` 进行序列比对：

```python
matcher = SequenceMatcher(None, source_tokens, target_tokens)
alignments = matcher.get_opcodes()

for tag, i1, i2, j1, j2 in alignments:
    if tag == 'equal':
        # 相同部分直接对齐
    elif tag == 'replace':
        # 替换操作建立对应关系
    elif tag == 'delete':
        # 删除操作
    elif tag == 'insert':
        # 插入操作（需要特殊处理）
```

### 2. Labels 构建

- **有效位置**: 使用目标词在词表中的索引
- **特殊位置** (CLS, SEP, PAD): 设置为 `-100`（不参与 loss 计算）
- **被删除的位置**: 保持原词或使用特定策略

### 3. 损失函数

使用带忽略索引的交叉熵损失：

```python
loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
loss = loss_fct(logits_flat, labels_flat)
```

这样只有有效的 token 位置会参与梯度计算。

## 训练技巧与调参建议

### 超参数推荐

| 参数 | 小数据集 (<1k) | 中等数据集 (1k-10k) | 大数据集 (>10k) |
|------|---------------|-------------------|----------------|
| batch_size | 8-16 | 16-32 | 32-64 |
| learning_rate | 3e-5 | 2e-5 - 3e-5 | 1e-5 - 2e-5 |
| epochs | 20-30 | 10-20 | 5-10 |
| max_length | 64-128 | 128 | 128-256 |

### 数据增强策略

1. **同义词替换**: 生成更多的训练样本
2. **回译**: 通过翻译增加数据多样性
3. **模板生成**: 基于规则生成相似 query

### 常见问题解决

#### Q1: 训练损失下降但验证损失上升
**原因**: 过拟合  
**解决方案**:
- 减少 epochs
- 增加 dropout
- 使用早停策略（early stopping）
- 增加训练数据

#### Q2: 改写结果质量不高
**可能原因**:
- 训练数据不足
- 对齐策略不合理
- 模型容量不够

**改进方案**:
- 收集更多高质量的配对数据
- 优化序列对齐算法
- 尝试更大的模型（如 macbert-large）

#### Q3: 推理速度较慢
**优化方案**:
- 使用 GPU 推理
- 减小 max_length
- 批量推理（batch prediction）
- 模型量化或蒸馏

## 性能评估

### 离线评估指标

```python
def evaluate_rewriting(original, predicted, reference):
    """
    评估改写质量
    
    Args:
        original: 原始查询
        predicted: 模型改写的查询
        reference: 人工标注的标准改写
    
    Returns:
        metrics: 评估指标字典
    """
    from nltk.translate.bleu_score import sentence_bleu
    
    # BLEU分数
    bleu = sentence_bleu([reference.split()], predicted.split())
    
    # 编辑距离
    from Levenshtein import distance
    edit_dist = distance(predicted, reference)
    
    return {
        "bleu": bleu,
        "edit_distance": edit_dist
    }
```

### 在线评估指标

- **点击率 (CTR)**: 改写后搜索结果的点击情况
- **零结果率**: 改写后无搜索结果的比例
- **用户满意度**: 用户对搜索结果的反馈

## 扩展与优化

### 1. 多阶段训练

```python
# 第一阶段：在大规模通用数据上预训练
# 第二阶段：在领域特定数据上微调
# 第三阶段：强化学习优化（可选）
```

### 2. 集成强化学习

结合搜索反馈作为奖励信号，进一步优化模型性能（参考文档中的 RL 方案）。

### 3. 多任务学习

同时训练多个相关任务：
- Query改写
- Query 分类
- 语义匹配

## 参考资料

- [MacBERT 论文](https://arxiv.org/abs/2004.13922)
- [HuggingFace Transformers 文档](https://huggingface.co/docs/transformers)
- [神经机器翻译模型query改写.md](./神经机器翻译模型query改写.md)

## 许可证

本项目代码基于 MIT 许可证开源。

## 联系方式

如有问题请提 Issue 或联系开发者。
