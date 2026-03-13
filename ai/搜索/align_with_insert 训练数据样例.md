# align_with_insert 方式训练数据样例与预测示例

## 概述

基于 **对齐 + 插入标记（align_with_insert）** 方式的完整训练数据样例和预测结果示例。

**核心思想**: 在源序列中添加 `<INS>` 标记来表示需要插入的位置，将长度不一致的问题转化为等长序列的预测问题。

---

## 一、训练数据样例

### 样例 1: 简单替换（长度不变）

**原始查询**: "电脑登录不了"  
**目标查询**: "电脑无法登录"

```json
{
  "original_query": "电脑登录不了",
  "target_query": "电脑无法登录",
  "method": "align_with_insert",
  
  // 分词结果
  "orig_tokens": ["电", "脑", "登", "录", "不", "了"],
  "tgt_tokens": ["电", "脑", "无", "法", "登", "录"],
  
  // 对齐结果
  "aligned_source": ["电", "脑", "登", "录", "不", "了"],
  "aligned_target": ["电", "脑", "无", "法", "登", "录"],
  
  // 操作类型
  "operations": [
    ("KEEP", 0, 0),
    ("KEEP", 1, 1),
    ("REPLACE", 2, 2),
    ("REPLACE", 3, 3),
    ("DELETE", 4, -1),
    ("DELETE", 5, -1)
  ],
  
  // 模型输入
  "input_ids": [101, 2345, 6789, 1234, 5678, 9012, 3456, 102],
  "labels": [-100, 2345, 6789, 4567, 8901, 1234, 5678, -100],
  "attention_mask": [1, 1, 1, 1, 1, 1, 1, 1]
}
```

**说明**:
- `input_ids`: [CLS] + 原始 tokens + [SEP]
- `labels`: 
  - CLS 和 SEP 位置为 -100（不参与 loss）
  - 删除的位置（"不", "了"）对应的 target 是 `<DEL>`，也设为 -100
  - 其他位置使用目标词的词表索引

---

### 样例 2: 插入操作（长度增加）⭐

**原始查询**: "vpn 到期"  
**目标查询**: "vpn 续费申请"

```json
{
  "original_query": "vpn 到期",
  "target_query": "vpn 续费申请",
  "method": "align_with_insert",
  
  // 分词结果
  "orig_tokens": ["vpn", "到", "期"],
  "tgt_tokens": ["vpn", "续", "费", "申", "请"],
  
  // 对齐结果（关键：添加了<INS>标记）
  "aligned_source": ["vpn", "<INS>", "<INS>", "到", "期"],
  "aligned_target": ["vpn", "续", "费", "申", "请"],
  
  // 操作类型
  "operations": [
    ("KEEP", 0, 0),
    ("INSERT", -1, 1),
    ("INSERT", -1, 2),
    ("REPLACE", 1, 3),
    ("REPLACE", 2, 4)
  ],
  
  // 模型输入
  "input_ids": [
    101,     // [CLS]
    100,     // vpn
    5001,    // <INS> (特殊标记)
    5001,    // <INS>
    2345,    // 到
    6789,    // 期
    102      // [SEP]
  ],
  "labels": [
    -100,    // [CLS] - 忽略
    100,     // vpn - 保持
    4567,    // 续 - 对应<INS>位置
    8901,    // 费 - 对应<INS>位置
    2345,    // 申 - 替换"到"
    6789,    // 请 - 替换"期"
    -100     // [SEP] - 忽略
  ],
  "attention_mask": [1, 1, 1, 1, 1, 1, 1]
}
```

**关键点**:
1. 源序列中添加了 2 个 `<INS>` 标记
2. `<INS>` 位置的 label 是要插入的词（"续", "费"）
3. 现在输入和输出长度一致（都是 7 个 token）

---

### 样例 3: 删除操作（长度减少）

**原始查询**: "寿改怎么办"  
**目标查询**: "寿险改革"

```json
{
  "original_query": "寿改怎么办",
  "target_query": "寿险改革",
  "method": "align_with_insert",
  
  // 分词结果
  "orig_tokens": ["寿", "改", "怎", "么", "办"],
  "tgt_tokens": ["寿", "险", "改", "革"],
  
  // 对齐结果
  "aligned_source": ["寿", "改", "怎", "么", "办"],
  "aligned_target": ["寿", "险", "改", "革", "<DEL>"],
  
  // 操作类型
  "operations": [
    ("KEEP", 0, 0),
    ("REPLACE", 1, 1),
    ("REPLACE", 2, 2),
    ("REPLACE", 3, 3),
    ("DELETE", 4, -1)
  ],
  
  // 模型输入
  "input_ids": [101, 8901, 2345, 3456, 7890, 1234, 102],
  "labels": [
    -100,    // [CLS]
    8901,    // 寿 - KEEP
    4567,    // 险 - REPLACE
    2345,    // 改 - REPLACE
    6789,    // 革 - REPLACE
    -100,    // <DEL> - 忽略
    -100     // [SEP]
  ],
  "attention_mask": [1, 1, 1, 1, 1, 1, 1]
}
```

---

### 样例 4: 复杂混合操作

**原始查询**: "拧毛巾怎么清洗"  
**目标查询**: "清洗毛巾的方法"

```json
{
  "original_query": "拧毛巾怎么清洗",
  "target_query": "清洗毛巾的方法",
  "method": "align_with_insert",
  
  // 分词结果
  "orig_tokens": ["拧", "毛", "巾", "怎", "么", "清", "洗"],
  "tgt_tokens": ["清", "洗", "毛", "巾", "的", "方", "法"],
  
  // 对齐结果
  "aligned_source": [
    "拧", "<INS>", "<INS>", "毛", "巾", 
    "<INS>", "怎", "么", "清", "洗"
  ],
  "aligned_target": [
    "清", "洗", "毛", "巾", "的", 
    "方", "法", "<DEL>", "<DEL>", "<DEL>"
  ],
  
  // 操作类型
  "operations": [
    ("REPLACE", 0, 0),      // 拧 -> 清
    ("INSERT", -1, 1),      // 插入"洗"
    ("KEEP", 1, 2),         // 毛 -> 毛
    ("KEEP", 2, 3),         // 巾 -> 巾
    ("INSERT", -1, 4),      // 插入"的"
    ("REPLACE", 3, 5),      // 怎 -> 方
    ("REPLACE", 4, 6),      // 么 -> 法
    ("DELETE", 5, -1),      // 清 -> 删除
    ("DELETE", 6, -1)       // 洗 -> 删除
  ],
  
  // 模型输入（简化表示）
  "input_ids": [
    [CLS], "拧", "<INS>", "<INS>", "毛", "巾", 
    "<INS>", "怎", "么", "清", "洗", [SEP]
  ],
  "labels": [
    -100,   // [CLS]
    清_id，  // 替换"拧"
    洗_id，  // 插入"洗"
    毛_id，  // 保持"毛"
    巾_id，  // 保持"巾"
    的_id，  // 插入"的"
    方_id，  // 替换"怎"
    法_id，  // 替换"么"
    -100,   // "清"被删除
    -100,   // "洗"被删除
    -100    // [SEP]
  ]
}
```

---

## 二、完整训练数据集示例

```python
# train_data.json
[
  {
    "original_query": "vpn 到期",
    "target_query": "vpn 续费申请"
  },
  {
    "original_query": "电脑登录不了",
    "target_query": "电脑无法登录"
  },
  {
    "original_query": "密码忘记了",
    "target_query": "密码找回"
  },
  {
    "original_query": "怎么转账",
    "target_query": "转账方法"
  },
  {
    "original_query": "余额不足",
    "target_query": "充值"
  },
  {
    "original_query": "客服在哪",
    "target_query": "联系客服"
  },
  {
    "original_query": "订单取消",
    "target_query": "取消订单"
  },
  {
    "original_query": "退款进度",
    "target_query": "退款查询"
  },
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

---

## 三、预测结果样例

### 预测流程

```python
from macbert_query_rewrite_train import Predictor

# 加载模型
predictor = Predictor("./query_rewrite_model_align_with_insert")

# 预测
query = "vpn 到期"
rewritten, confidence = predictor.predict(query)

print(f"原句：{query}")
print(f"改写：{rewritten}")
print(f"置信度：{confidence:.4f}")
```

---

### 预测样例 1: 成功插入

**输入**: "vpn 到期"

**模型内部处理过程**:

```python
# Step 1: 分词
tokens = ["vpn", "到", "期"]

# Step 2: 模型预测（逐 token）
# 输入：[CLS] vpn 到 期 [SEP]
# 预测每个位置的目标词

# Step 3: 解码
predicted_tokens = ["vpn", "续", "费", "申请"]

# Step 4: 拼接
rewritten = "vpn 续费申请"
```

**输出**:
```json
{
  "original_query": "vpn 到期",
  "rewritten_query": "vpn 续费申请",
  "confidence": 0.9234,
  "token_predictions": [
    {"position": 0, "original": "vpn", "predicted": "vpn", "op": "KEEP"},
    {"position": 1, "original": "到", "predicted": "续", "op": "REPLACE"},
    {"position": 2, "original": "期", "predicted": "费", "op": "REPLACE"},
    {"inserted_after_pos_0": "申请", "op": "INSERT"}
  ]
}
```

---

### 预测样例 2: 成功替换

**输入**: "电脑登录不了"

**输出**:
```json
{
  "original_query": "电脑登录不了",
  "rewritten_query": "电脑无法登录",
  "confidence": 0.8956,
  "token_predictions": [
    {"position": 0, "original": "电", "predicted": "电", "op": "KEEP"},
    {"position": 1, "original": "脑", "predicted": "脑", "op": "KEEP"},
    {"position": 2, "original": "登", "predicted": "无", "op": "REPLACE"},
    {"position": 3, "original": "录", "predicted": "法", "op": "REPLACE"},
    {"position": 4, "original": "不", "predicted": "登", "op": "REPLACE"},
    {"position": 5, "original": "了", "predicted": "录", "op": "REPLACE"}
  ]
}
```

---

### 预测样例 3: 部分成功（有误差）

**输入**: "拧毛巾"

**期望输出**: "清洗毛巾"  
**实际输出**: "洗毛巾"

```json
{
  "original_query": "拧毛巾",
  "rewritten_query": "洗毛巾",  // 缺少"清"
  "expected_query": "清洗毛巾",
  "confidence": 0.7234,
  "analysis": {
    "error_type": "missing_insertion",
    "description": "模型未能正确预测第一个<INS>位置的'清'字",
    "possible_cause": "训练数据中类似模式较少"
  }
}
```

---

### 预测样例 4: 过度改写

**输入**: "余额不足"

**期望输出**: "充值"  
**实际输出**: "余额不足请充值"

```json
{
  "original_query": "余额不足",
  "rewritten_query": "余额不足请充值",  // 过于冗长
  "expected_query": "充值",
  "confidence": 0.6543,
  "analysis": {
    "error_type": "over_generation",
    "description": "模型插入了过多内容",
    "possible_cause": "对<INS>标记的理解不够准确"
  }
}
```

---

## 四、可视化对齐过程

### 可视化工具代码

```python
def visualize_alignment(original, target, aligned_source, aligned_target):
    """可视化对齐结果"""
    
    print("=" * 60)
    print(f"原始查询：{original}")
    print(f"目标查询：{target}")
    print("=" * 60)
    
    # 并排显示对齐
    print("\n对齐结果:")
    print(f"{'源序列':<20} | {'目标序列':<20}")
    print("-" * 45)
    
    for src, tgt in zip(aligned_source, aligned_target):
        op = "→" if src != tgt else "="
        print(f"{src:<10} {op:>2} {tgt:<10}")
    
    print("=" * 60)

# 使用示例
visualize_alignment(
    "vpn 到期",
    "vpn 续费申请",
    ["vpn", "<INS>", "<INS>", "到期"],
    ["vpn", "续", "费", "申请"]
)
```

**输出**:
```
============================================================
原始查询：vpn 到期
目标查询：vpn 续费申请
============================================================

对齐结果:
源序列                 | 目标序列               
---------------------------------------------
vpn        → vpn       
<INS>      → 续        
<INS>      → 费        
到期       → 申请      

============================================================
```

---

## 五、常见问题与调试

### Q1: 如何检查数据构建是否正确？

```python
from macbert_query_rewrite_train import QueryRewriteDataBuilder

builder = QueryRewriteDataBuilder(
    model_name="hfl/chinese-macbert-base",
    strategy="align_with_insert"
)

# 构建单个样本
sample = builder.build_sample("vpn 到期", "vpn 续费申请")

# 检查关键字段
print("Original tokens:", sample['orig_tokens'])
print("Target tokens:", sample['tgt_tokens'])
print("Aligned source:", sample['aligned_source'])
print("Aligned target:", sample['aligned_target'])
print("Input IDs length:", len(sample['input_ids']))
print("Labels length:", len(sample['labels']))
```

---

### Q2: 如何处理连续的插入操作？

**问题**: 当需要连续插入多个词时（如插入"续费申请"4 个字），模型可能难以学习。

**解决方案**:
1. 在训练数据中增加类似模式的样本
2. 使用更长的 max_length
3. 考虑使用 span-level 方法

---

### Q3: 特殊标记 `<INS>` 的 ID 是多少？

```python
tokenizer = BertTokenizer.from_pretrained("hfl/chinese-macbert-base")
tokenizer.add_tokens(["<INS>", "<DEL>"])

print("<INS> token ID:", tokenizer.convert_tokens_to_ids(["<INS>"])[0])
print("<DEL> token ID:", tokenizer.convert_tokens_to_ids(["<DEL>"])[0])
```

---

## 六、性能优化建议

### 1. 批处理预测

```python
def batch_predict(predictor, queries, batch_size=16):
    """批量预测"""
    results = []
    
    for i in range(0, len(queries), batch_size):
        batch_queries = queries[i:i+batch_size]
        batch_results = predictor.batch_predict(batch_queries)
        results.extend(batch_results)
    
    return results
```

### 2. 缓存常用查询

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def predict_cached(query):
    return predictor.predict(query)
```

### 3. 置信度阈值过滤

```python
rewritten, confidence = predictor.predict(query)

if confidence < 0.7:
    # 低置信度，使用备选方案
    rewritten = fallback_strategy(query)
```

---

## 七、总结

### align_with_insert 方式的优势

✅ **优点**:
1. 直观易懂，符合人类直觉
2. 将不等长序列转化为等长序列
3. 可以同时处理插入、删除、替换
4. 模型架构无需修改

❌ **缺点**:
1. 需要扩展词表（添加特殊标记）
2. 推理时可能需要多轮迭代
3. 连续插入较多时效果下降

### 适用场景

| 场景特征 | 推荐使用 |
|---------|---------|
| 少量插入（1-2 个词） | ✅ 非常适合 |
| 主要是替换操作 | ✅ 适合 |
| 大量连续插入 | ⚠️ 考虑 span-level |
| 实时性要求高 | ✅ 适合（单次前向传播） |

---

## 八、运行示例

```bash
# 1. 准备训练数据
python prepare_data.py --strategy align_with_insert

# 2. 训练模型
python macbert_query_rewrite_train.py \
  --data_path train_data.json \
  --strategy align_with_insert \
  --output_dir ./model_align_insert

# 3. 测试预测
python test_prediction.py \
  --model_path ./model_align_insert \
  --test_queries "vpn 到期" "电脑登录不了"
```

**预期输出**:
```
原句：vpn 到期 -> 改写：vpn 续费申请 (置信度：0.9234)
原句：电脑登录不了 -> 改写：电脑无法登录 (置信度：0.8956)
```
