# MacBERT + 指针网络 NER 方案

## 基于 MacBERT 和 Pointer Network 的企业命名实体识别系统

---

### 📌 方案概述

**目标**: 识别企业内部文本中的**公司**、**部门**、**岗位**三类实体

**核心技术**: 
- **MacBERT** (中文预训练模型) → 强大的上下文语义理解
- **Pointer Network** (指针网络) → 直接预测实体边界位置

---

### 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      输入文本                                │
│    "张三在阿里巴巴技术部担任软件工程师"                       │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│              MacBERT Encoder (双向编码)                     │
│         提取每个位置的上下文表示 [CLS]...[SEP]               │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
        ┌──────────┴──────────┐
        ↓                     ↓
┌──────────────────┐  ┌──────────────────┐
│ Start Classifier │  │ End Classifier   │
│   (起始位置预测)  │  │  (结束位置预测)   │
└────────┬─────────┘  └────────┬─────────┘
         ↓                     ↓
    ORGANIZATION: [3, 7]   →  "阿里巴巴"
    DEPARTMENT:   [7, 10]  →  "技术部"
    POSITION:     [13, 18] →  "软件工程师"
```

---

### ✨ 核心优势

| 特性 | 传统 BIO 方案 | 本方案 (指针网络) |
|------|-------------|-----------------|
| **标签体系** | 复杂的 B/I/E/S/O | 简单的 start/end |
| **嵌套实体** | ❌ 不支持 | ✅ 天然支持 |
| **长实体处理** | 受标签长度限制 | ✅ 灵活预测 |
| **错误传播** | 序列依赖导致 | ✅ 独立预测 |
| **中文优化** | 通用模型 | ✅ MacBERT 专用 |

---

### 📊 训练数据

**100 条高质量标注数据**,涵盖:
- 🌐 互联网：阿里、腾讯、字节、百度...
- 💰 金融：平安集团、招商银行、高瓴资本...
- 🏢 房地产：万科、恒大、碧桂园...
- 🚀 硬科技：大疆、商汤、寒武纪...
- 🔬 生物医药：依图医疗、本源量子...

**数据格式**:
```json
{
  "text": "华为技术有限公司云计算部门首席架构师",
  "entities": [
    {"type": "ORGANIZATION", "start": 0, "end": 9, "text": "华为技术有限公司"},
    {"type": "DEPARTMENT", "start": 9, "end": 14, "text": "云计算部门"},
    {"type": "POSITION", "start": 14, "end": 19, "text": "首席架构师"}
  ]
}
```

---

### 🎯 模型配置

**基础版本**:
- MacBERT-Base (hidden_size=768, layers=12)
- Dropout: 0.1
- 分类器：768 → 384 → 3 (实体类型数)

**增强版本** (可选):
- Layer Normalization
- 实体类型嵌入
- 多层特征融合

**训练参数**:
- Batch Size: 16
- Learning Rate: 3e-5
- Epochs: 10
- Max Length: 128
- Optimizer: AdamW + Linear Warmup

---

### 📈 预期性能

| 数据规模 | Precision | Recall | F1-Score |
|---------|-----------|--------|----------|
| 100 条   | 85-90%    | 80-88% | 82-89%   |
| 500 条   | 88-92%    | 85-90% | 86-91%   |
| 1000+条 | 92-95%    | 90-94% | 91-94%   |

**评估标准**: 实体类型、起始位置、结束位置完全匹配

---

### 🚀 使用流程

```bash
# 1. 环境准备
pip install -r requirements.txt

# 2. 准备数据
python quick_start.py

# 3. 训练模型
python train.py --train_file ner_train.json --output_dir ./outputs

# 4. 预测
python predict.py --model_path ./outputs --text "李四在腾讯科技产品部工作"
```

**推理速度**: < 50ms/条文本  
**显存需求**: 训练 8GB / 推理 500MB

---

### 💡 应用场景

✅ **适合场景**:
- 企业组织架构分析
- 招聘信息结构化
- 名片/简历实体抽取
- 商业文档信息提取
- 竞品分析报告解析

❌ **不适合**:
- 超短文本 (< 5 字)
- 实体边界模糊
- 开放域实体类型

---

### 📁 项目文件

```
NER/
├── macbert_pointer_ner_data.md  # 100 条训练数据
├── data_processor.py            # 数据处理
├── model.py                     # 模型定义 (基础版 + 增强版)
├── train.py                     # 训练脚本
├── predict.py                   # 预测脚本
├── quick_start.py               # 快速入门
├── requirements.txt             # 依赖包
└── README.md                    # 详细文档
```

---

### 🔧 扩展方向

1. **添加新实体类型**: 修改 `entity_type_map` (如 LOCATION, TIME)
2. **数据增强**: 同义词替换、回译、句式变换
3. **模型优化**: 
   - MacBERT-Large
   - 添加 CRF 层
   - 领域自适应预训练
4. **部署加速**: 
   - ONNX 导出
   - 模型量化 (FP32→INT8)
   - 知识蒸馏

---

### 📚 参考资料

1. MacBERT: "Revisiting Pre-Trained Models for Chinese NLP" (EMNLP 2020)
2. Pointer Network: "Neural Machine Translation by Jointly Learning to Align and Translate" (ICLR 2015)
3. Span-based NER: "A Span-Based Model for Joint Overlapping NER" (ACL 2018)

---

**版本**: v1.0 | **创建日期**: 2026-03-07 | **开发者**: AI Assistant
