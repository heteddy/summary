# 基于 NDCG、MRR 和用户反馈的强化学习 Query Rewrite

## 概述

第二阶段的强化学习使用**搜索评估指标**作为奖励信号，包括：

1. **NDCG (Normalized Discounted Cumulative Gain)** - 衡量排序质量
2. **MRR (Mean Reciprocal Rank)** - 衡量第一个相关结果的排名
3. **用户反馈** - 点击、停留时间、满意度等

## 奖励函数设计

### 综合奖励公式

```python
reward = 0.4 * NDCG + 0.3 * MRR + 0.3 * Feedback
```

### 1. NDCG 计算

NDCG 衡量搜索结果的排序质量，考虑了相关性的分级和位置折扣。

#### 三种计算模式：

**模式 1: 标准 NDCG（需要理想排序）**
```python
# 如果有标注的理想排序
ideal_ranking = ["doc1", "doc2", "doc3", ...]  # 按相关性排序
ndcg = calculate_ndcg(search_results, ideal_ranking)
```

**模式 2: 基于用户反馈的 NDCG**
```python
# 从用户行为推断相关性
relevance_inference_rules:
- 满意点击 + 长停留 (>60s) → relevance=5
- 满意点击 → relevance=4
- 普通点击 + 中等停留 (20-60s) → relevance=3
- 普通点击 + 短停留 (<20s) → relevance=2
- 未点击但靠前 → relevance=1
- 未点击 → relevance=0

dcg = Σ (2^rel_i - 1) / log2(i+1)
idcg = Σ (2^rel_ideal_i - 1) / log2(i+1)
ndcg = dcg / idcg
```

**模式 3: 启发式 NDCG**
```python
# 基于结果质量估计
scoring_factors:
- 标题和摘要完整性
- 文本长度
- 排名位置权重
```

### 2. MRR 计算

MRR 衡量第一个相关结果的排名位置。

```python
# 找到第一个相关文档的位置
for i, result in enumerate(search_results):
    if is_relevant(result):  # 基于点击或内容质量
        mrr = 1.0 / (i + 1)
        break
```

**相关性判断：**
- 有用户点击 → 相关
- 有满意点击 → 更相关
- 内容完整（标题 + 摘要）→ 可能相关

### 3. 用户反馈奖励

综合考虑多种用户行为信号：

```python
feedback_reward = (
    0.3 * click_reward +      # 点击数量和比例
    0.4 * satisfaction_reward + # 满意点击
    0.2 * dwell_time_reward +   # 平均停留时间
    0.1 * reformulation_penalty # 是否重新查询
)
```

**详细规则：**

| 指标 | 计算方法 | 权重 |
|------|---------|------|
| **点击奖励** | min(1.0, num_clicks/3) | 0.3 |
| **满意奖励** | min(1.0, num_satisfied/2) | 0.4 |
| **停留时间** | avg_dwell > 60s → 1.0<br>avg_dwell > 30s → 0.5<br>avg_dwell > 10s → 0.0<br>否则 → -0.5 | 0.2 |
| **查询重构** | reformulated=True → -0.5 | 0.1 |

## 代码实现

### 奖励函数类

```python
class SearchMetricReward:
    def calculate_reward(self, original_query, rewritten_query, 
                        search_results, user_feedback=None, 
                        ideal_ranking=None):
        """
        计算综合奖励
        
        Args:
            original_query: 原始查询
            rewritten_query: 改写后的查询
            search_results: 搜索结果列表 [{doc_id, title, content, ...}]
            user_feedback: 用户反馈 {
                clicked_docs: [doc_ids],
                satisfied_clicks: [doc_ids],
                dwell_time: {doc_id: seconds},
                reformulated: bool
            }
            ideal_ranking: 理想排序 [doc_ids]
            
        Returns:
            {
                'ndcg': float,
                'mrr': float,
                'feedback': float,
                'total': float
            }
        """
```

### PPO 训练循环

```python
def train_epoch(self, data_loader, epoch, search_engine_fn):
    for batch in data_loader:
        # 1. 采样动作（生成改写 query）
        actions, _, _ = model.sample_actions(input_ids)
        rewritten_queries = decode(actions)
        
        # 2. 执行搜索，获取结果
        search_results = search_engine_fn(rewritten_queries)
        
        # 3. 获取用户反馈（真实或模拟）
        user_feedback = get_user_feedback(original, rewritten, search_results)
        
        # 4. 计算奖励
        rewards = reward_fn.calculate_reward(
            original_query=original,
            rewritten_query=rewritten,
            search_results=search_results,
            user_feedback=user_feedback
        )
        
        # 5. PPO 更新
        loss = policy_loss + value_loss - entropy_loss
        loss.backward()
        optimizer.step()
```

## 实际应用场景

### 场景 1: 有标注数据（理想排序已知）

```python
# 训练数据包含理想排序
train_data = [
    {
        'original_query': '电脑登录',
        'target_query': '电脑无法登录',
        'ideal_ranking': ['doc1', 'doc2', 'doc3']  # 专家标注的相关文档
    },
    ...
]

# 使用标准 NDCG
reward = reward_fn.calculate_reward(
    original_query='电脑登录',
    rewritten_query='电脑无法登录',
    search_results=results,
    ideal_ranking=['doc1', 'doc2', 'doc3']
)
```

### 场景 2: 在线学习（使用真实用户反馈）

```python
# 部署到生产环境
def online_reward_calculation(query, rewritten):
    # 1. 使用改写的 query 搜索
    results = search_engine.search(rewritten)
    
    # 2. 收集用户行为日志
    user_feedback = {
        'clicked_docs': get_clicked_docs(session_id),
        'satisfied_clicks': get_satisfied_clicks(session_id),
        'dwell_time': get_dwell_times(session_id),
        'reformulated': did_reformulate(session_id)
    }
    
    # 3. 计算奖励
    reward = reward_fn.calculate_reward(
        original_query=query,
        rewritten_query=rewritten,
        search_results=results,
        user_feedback=user_feedback
    )
    
    return reward
```

### 场景 3: 离线评估（无用户反馈）

```python
# 使用启发式方法
reward = reward_fn.calculate_reward(
    original_query='vpn 到期',
    rewritten_query='vpn 续费',
    search_results=results
    # 没有 user_feedback 和 ideal_ranking
)
# 自动使用启发式 NDCG 和简化 MRR
```

## 训练配置

```python
class RLArgs:
    # 奖励相关参数
    ndcg_weight = 0.4          # NDCG 权重
    mrr_weight = 0.3           # MRR 权重
    feedback_weight = 0.3      # 用户反馈权重
    
    # NDCG 参数
    ndcg_k = 10                # NDCG@K
    
    # 用户反馈参数
    long_dwell_threshold = 60  # 长停留时间阈值（秒）
    medium_dwell_threshold = 20  # 中等停留时间阈值
    
    # PPO 参数
    clip_epsilon = 0.2
    gamma = 0.99
    gae_lambda = 0.95
```

## 评估指标

### 训练过程中的监控指标

```python
# 每个 epoch 输出
Reward Stats:
- NDCG: 0.7234    # 平均 NDCG 分数
- MRR: 0.6521     # 平均 MRR 分数
- Feedback: 0.5843 # 平均用户反馈分数
- Total: 0.6612   # 综合奖励
```

### 对比实验

比较不同奖励函数的效果：

```python
# 实验 1: 仅监督学习
sl_model.evaluate()

# 实验 2: SL + 简单 RL 奖励（字符相似度）
rl_simple_reward.evaluate()

# 实验 3: SL + 搜索指标奖励（NDCG+MRR+Feedback）⭐
rl_search_metric.evaluate()

# 预期结果：实验 3 > 实验 2 > 实验 1
```

## 优势分析

### 相比简单奖励函数的优势

| 特性 | 简单奖励 | 搜索指标奖励 |
|------|---------|-------------|
| **优化目标** | 文本相似度 | 搜索效果指标 |
| **与业务对齐** | 弱 | 强（直接优化 NDCG/MRR） |
| **用户导向** | 否 | 是（考虑用户反馈） |
| **可解释性** | 低 | 高（标准 IR 指标） |
| **泛化能力** | 有限 | 更好（学到搜索优化策略） |

### 数学形式化

**目标函数**：
$$\max_\theta \mathbb{E}_{\tau \sim \pi_\theta} \left[ \sum_{t=0}^{T} \gamma^t \cdot R(s_t, a_t) \right]$$

其中奖励函数：
$$R = 0.4 \cdot \text{NDCG}_K + 0.3 \cdot \text{MRR} + 0.3 \cdot \text{Feedback}$$

**NDCG 计算**：
$$\text{NDCG}_K = \frac{\text{DCG}_K}{\text{IDCG}_K} = \frac{\sum_{i=1}^{K} \frac{2^{rel_i} - 1}{\log_2(i+1)}}{\sum_{i=1}^{K} \frac{2^{rel^*_i} - 1}{\log_2(i+1)}}$$

**MRR 计算**：
$$\text{MRR} = \frac{1}{|\mathcal{Q}|} \sum_{q \in \mathcal{Q}} \frac{1}{\text{rank}_q}$$

**用户反馈**：
$$\text{Feedback} = \sum_{i} w_i \cdot f_i(\text{clicks}, \text{dwell}, \text{satisfaction})$$

## 总结

通过将**搜索评估指标（NDCG、MRR）**和**用户反馈信号**融入奖励函数，模型能够：

✅ **直接优化业务指标** - NDCG 和 MRR 是搜索系统的核心 KPI  
✅ **以用户为中心** - 考虑点击、停留时间、满意度等真实反馈  
✅ **端到端优化** - 从最终效果反向指导 query 改写  
✅ **可解释性强** - 使用业界标准指标，便于分析和调试  

这种设计使得强化学习的优化方向与搜索系统的整体目标高度一致！
