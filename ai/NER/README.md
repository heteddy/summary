# MacBERT + 指针网络 NER

基于 MacBERT 和 Pointer Network 的命名实体识别模型，专门用于识别企业内部的公司、部门、岗位三类实体。

## 目录结构

```
NER/
├── macbert_pointer_ner_data.md    # 训练数据说明和示例
├── data_processor.py              # 数据处理脚本
├── model.py                       # 模型定义
├── train.py                       # 训练脚本
├── predict.py                     # 预测脚本
├── requirements.txt               # 依赖包
└── README.md                      # 使用说明
```

## 环境要求

- Python 3.7+
- PyTorch 1.8+
- Transformers 4.0+

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 准备数据

训练数据格式为 JSON，示例:

```json
{
  "text": "张三在阿里巴巴技术部担任软件工程师",
  "entities": [
    {"type": "ORGANIZATION", "start": 3, "end": 7, "text": "阿里巴巴"},
    {"type": "DEPARTMENT", "start": 7, "end": 10, "text": "技术部"},
    {"type": "POSITION", "start": 13, "end": 18, "text": "软件工程师"}
  ]
}
```

完整训练数据见 `macbert_pointer_ner_data.md` 文件。

### 2. 划分数据集

```python
from data_processor import NERDataProcessor, split_dataset, save_data

processor = NERDataProcessor()
data = processor.load_data('macbert_pointer_ner_data.json')

train_data, dev_data, test_data = split_dataset(data)

save_data(train_data, 'ner_train.json')
save_data(dev_data, 'ner_dev.json')
save_data(test_data, 'ner_test.json')
```

### 3. 训练模型

```bash
python train.py \
  --train_file ner_train.json \
  --dev_file ner_dev.json \
  --model_name hfl/chinese-macbert-base \
  --batch_size 16 \
  --num_epochs 10 \
  --learning_rate 3e-5 \
  --output_dir ./outputs
```

**参数说明**:
- `--train_file`: 训练数据文件路径
- `--dev_file`: 验证数据文件路径
- `--model_name`: MacBERT 模型名称或路径 (默认：hfl/chinese-macbert-base)
- `--batch_size`: 批次大小 (默认：16)
- `--num_epochs`: 训练轮数 (默认：10)
- `--learning_rate`: 学习率 (默认：3e-5)
- `--max_length`: 最大序列长度 (默认：128)
- `--advanced`: 是否使用增强版模型
- `--output_dir`: 模型输出目录

### 4. 预测

#### 单个文本预测

```bash
python predict.py \
  --model_path ./outputs \
  --text "李四在腾讯科技产品部担任高级产品经理"
```

#### 批量预测

```bash
python predict.py \
  --model_path ./outputs \
  --file input.txt \
  --output predictions.json
```

#### 交互模式

```bash
python predict.py --model_path ./outputs
```

然后输入文本进行预测。

## 实体类型

模型支持三种实体类型:

1. **ORGANIZATION** (公司): 企业、子公司、集团名称
   - 示例：阿里巴巴、腾讯科技、华为技术有限公司

2. **DEPARTMENT** (部门): 内部组织机构
   - 示例：技术部、人力资源部、财务部、研发中心

3. **POSITION** (岗位): 职位、头衔
   - 示例：软件工程师、产品经理、总监、经理

## 模型架构

### MacBERT + 指针网络

```
输入文本 
  ↓
MacBERT Encoder
  ↓
Context Representations
  ↓
┌──────────────────┬──────────────────┐
│Start Classifier  │End Classifier    │
└──────────────────┴──────────────────┘
  ↓                ↓
Start Positions  End Positions
```

### 核心特点

1. **双向编码**: MacBERT 提供强大的上下文表示能力
2. **指针网络**: 直接预测实体的起始和结束位置，无需 BIO/BIOES tagging
3. **支持嵌套实体**: 天然支持嵌套和多实体识别
4. **端到端训练**: 简化训练流程

## 性能指标

评估指标:
- Precision (精确率)
- Recall (召回率)
- F1-Score

一个实体被认为正确当且仅当其实体类型、起始位置和结束位置都完全匹配。

## 数据增强

可以使用以下策略扩充训练数据:

1. **同义词替换**: 使用同义词替换实体中的词语
2. **句式变换**: 改变句子结构
3. **实体组合**: 随机组合不同的公司、部门、岗位

示例代码见 `data_processor.py`。

## 推理优化

### 1. 阈值调整

```python
predictor = NERPredictor('./outputs')
entities = predictor.predict(text, threshold=0.7)  # 提高阈值减少误报
```

### 2. 批处理

```python
texts = ["文本 1", "文本 2", "文本 3"]
all_entities = predictor.predict_batch(texts, batch_size=32)
```

### 3. GPU 加速

确保安装了 CUDA 版本的 PyTorch:

```bash
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu113
```

## 常见问题

### Q1: 如何处理长文本？

模型默认最大长度为 128，可以通过 `--max_length` 参数调整。对于更长的文本，建议使用滑动窗口或分段处理。

### Q2: 如何添加新的实体类型？

1. 修改 `data_processor.py` 中的 `entity_type_map`
2. 重新训练模型
3. 更新 `num_entity_types` 参数

### Q3: 模型效果不好怎么办？

- 增加训练数据量
- 调整学习率和批次大小
- 增加训练轮数
- 使用增强版模型 (`--advanced`)
- 检查数据标注质量

### Q4: 如何处理未登录词 (OOV)?

MacBERT 使用字级别的分词，对中文 OOV 有较好的鲁棒性。如果遇到特殊词汇，可以考虑:
- 在训练数据中增加相关样本
- 使用领域特定的预训练模型

## 参考资料

1. **MacBERT**: "Revisiting Pre-Trained Models for Chinese Natural Language Processing"
2. **Pointer Network**: "Neural Machine Translation by Jointly Learning to Align and Translate"
3. **Span-based NER**: "A Span-Based Model for Joint Overlapping Named Entity Recognition"

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue 或联系开发者。
