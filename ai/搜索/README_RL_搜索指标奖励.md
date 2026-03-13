# MacBERT + RL Query Rewrite - 使用 NDCG、MRR 和用户反馈作为奖励

## 📚 更新内容总结

### ✅ 已完成的修改

#### 1. **新增 SearchMetricReward 类**
实现了基于搜索评估指标的奖励计算器，包括：

- **NDCG 计算**（三种模式）
  - 标准 NDCG（需要理想排序）
  - 基于用户反馈的 NDCG（从点击行为推断相关性）
  - 启发式 NDCG（基于结果质量估计）

- **MRR 计算**
  - 基于用户点击确定第一个相关文档
  - 启发式方法（基于内容完整性）

- **用户反馈奖励**
  - 点击数量和比例
  - 满意点击
  - 停留时间分析
  - 查询重构惩罚

#### 2. **更新 RewardFunction 类**
```python
class RewardFunction:
    def calculate_reward(self, original_query, rewritten_query, 
                        search_results=None,  # 新增
                        user_feedback=None,   # 新增
                        ideal_ranking=None):  # 新增
        """
        计算综合奖励
        
        新参数:
            search_results: 搜索结果列表 [{doc_id, title, content, ...}]
            user_feedback: 用户反馈 {
                clicked_docs: [...],
                satisfied_clicks: [...],
                dwell_time: {...},
                reformulated: bool
            }
            ideal_ranking: 理想的相关文档排序
        """
```

#### 3. **更新 PPOTrainer.train_epoch() 方法**
```python
def train_epoch(self, data_loader, epoch, search_engine_fn=None):
    """
    新增参数:
        search_engine_fn: 搜索引擎函数 (query) -> [search_results]
    
    主要变化:
    1. 调用搜索引擎获取改写 query 的搜索结果
    2. 获取或模拟用户反馈
    3. 使用新的奖励函数计算 NDCG、MRR、Feedback
    4. 统计并输出各项指标的详细信息
    """
```

#### 4. **新增 _get_user_feedback() 方法**
```python
def _get_user_feedback(self, original_query, rewritten_query, search_results):
    """
    获取或模拟用户反馈
    
    模拟规则:
    - 排名越靠前，点击概率越高
    - 高质量文档更可能获得长停留和满意点击
    - 无点击时可能触发查询重构
    """
```

#### 5. **更新 TwoStageTrainer.stage2_reinforcement_learning()**
```python
def stage2_reinforcement_learning(self, pretrained_model_path, train_data, 
                                 val_data, search_engine_fn=None):
    """
    新增参数:
        search_engine_fn: 搜索引擎函数
    
    主要变化:
    1. 初始化 SearchMetricReward
    2. 使用新的 RewardFunction
    3. 将 search_engine_fn 传递给 PPOTrainer
    """
```

### 📊 奖励计算公式

**综合奖励**:
```python
reward = 0.4 * NDCG@10 + 0.3 * MRR + 0.3 * Feedback
```

**NDCG 计算**:
```python
if ideal_ranking exists:
    ndcg = standard_ndcg(search_results, ideal_ranking)
elif user_feedback exists:
    ndcg = feedback_based_ndcg(search_results, user_feedback)
else:
    ndcg = heuristic_ndcg(search_results)
```

**用户反馈奖励**:
```python
feedback = (
    0.3 * click_reward +       # min(1.0, num_clicks/3)
    0.4 * satisfaction_reward + # min(1.0, num_satisfied/2)
    0.2 * dwell_time_reward +   # avg_dwell > 60s → 1.0
    0.1 * reformulation_penalty # reformulated → -0.5
)
```

### 🔧 使用方法

#### 基础训练
```python
from macbert_rl_query_rewrite_train import TwoStageTrainer

trainer = TwoStageTrainer(model_name="hfl/chinese-macbert-base")

# 第一阶段：监督学习
pretrained_path = trainer.stage1_supervised_learning(train_data, val_data)

# 第二阶段：强化学习（使用 NDCG+MRR+Feedback 奖励）
def mock_search(query):
    # 模拟或真实的搜索引擎
    return search_api.search(query)

rl_model = trainer.stage2_reinforcement_learning(
    pretrained_model_path=pretrained_path,
    train_data=train_data,
    val_data=val_data,
    search_engine_fn=mock_search
)
```

#### 自定义权重
```python
class CustomReward(RewardFunction):
    def calculate_reward(self, original, rewritten, search_results, 
                        user_feedback=None, ideal_ranking=None):
        rewards = self.search_metric_fn.calculate_reward(
            original, rewritten, search_results, 
            user_feedback, ideal_ranking
        )
        
        # 自定义权重
        return (
            0.5 * rewards['ndcg'] +      # 更重视 NDCG
            0.3 * rewards['mrr'] +
            0.2 * rewards['feedback']
        )
```

### 📈 训练输出示例

```
PPO Epoch 1/5: 100%|██████████| 100/100 [00:15<00:00, 6.42it/s]
Reward Stats - NDCG: 0.7234, MRR: 0.6521, Feedback: 0.5843, Total: 0.6612
RL Epoch 1/5 - Loss: 0.1234, Reward: 0.6612

保存最佳 RL 模型，奖励：0.6612
```

### 🎯 实际应用场景

#### 场景 1: 有标注数据
```python
ideal_ranking = ["doc1", "doc2", "doc3"]  # 专家标注
reward = reward_fn.calculate_reward(
    original, rewritten, 
    search_results,
    ideal_ranking=ideal_ranking  # 使用标准 NDCG
)
```

#### 场景 2: 在线学习
```python
# 从日志数据库获取真实用户反馈
user_feedback = db.get_feedback(session_id, query)
reward = reward_fn.calculate_reward(
    original, rewritten,
    search_results,
    user_feedback=user_feedback  # 使用真实反馈
)
```

#### 场景 3: 离线评估
```python
# 没有用户反馈，使用启发式估计
reward = reward_fn.calculate_reward(
    original, rewritten,
    search_results
    # 自动使用启发式 NDCG
)
```

### 📁 文件清单

1. **macbert_rl_query_rewrite_train.py** - 主训练代码（已更新）
   - `SearchMetricReward` - 新增类
   - `RewardFunction` - 更新
   - `PPOTrainer.train_epoch()` - 更新
   - `PPOTrainer._get_user_feedback()` - 新增
   - `TwoStageTrainer.stage2_reinforcement_learning()` - 更新

2. **基于搜索指标的 RL 奖励函数设计.md** - 详细理论说明

3. **rl_search_reward_example.py** - 完整使用示例

4. **MacBERT+RL 实现指南.md** - 整体架构说明（已有）

### ✨ 核心优势

1. **直接优化业务指标** - NDCG 和 MRR 是搜索系统的核心 KPI
2. **以用户为中心** - 考虑真实的用户行为反馈
3. **端到端优化** - 从最终搜索效果反向指导 query 改写
4. **可解释性强** - 使用业界标准 IR 指标
5. **灵活可扩展** - 支持自定义权重和多任务学习

### 🚀 下一步

1. **集成真实搜索引擎** - 替换 mock_search 为生产环境 API
2. **收集用户反馈日志** - 建立用户行为数据库
3. **A/B 测试** - 对比 SL 模型和 RL 模型的线上效果
4. **持续优化** - 根据实际效果调整奖励权重

开始训练：
```bash
python macbert_rl_query_rewrite_train.py
```
