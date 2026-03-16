# 基于搜索指标的 RL Query Rewrite - 完整使用示例

## 文件结构

```
搜索/
├── macbert_rl_query_rewrite_train.py    # 主训练代码（已更新）
├── 基于搜索指标的 RL 奖励函数设计.md     # 理论说明
└── rl_search_reward_example.py          # 使用示例（新增）
```

## 使用示例代码

### 示例 1: 基础训练流程

```python
"""
示例 1: 完整的两阶段训练流程
使用 NDCG + MRR + 用户反馈作为奖励
"""

from macbert_rl_query_rewrite_train import (
    TwoStageTrainer, 
    SearchMetricReward,
    RewardFunction,
    create_sample_data
)

# 1. 创建训练数据
train_data = [
    ("电脑登录不了", "电脑无法登录"),
    ("密码忘记了", "密码找回"),
    ("怎么转账", "转账方法"),
    ("余额不足", "充值"),
    ("客服在哪", "联系客服"),
]

# 划分数据集
train_list = train_data[:4]
val_list = train_data[4:]

# 2. 创建训练器
trainer = TwoStageTrainer(
    model_name="hfl/chinese-macbert-base"
)

# 3. 第一阶段：监督学习预训练
pretrained_path = trainer.stage1_supervised_learning(train_list, val_list)

# 4. 第二阶段：强化学习微调
# 定义搜索引擎函数（模拟或真实）
def mock_search_engine(query):
    """
    模拟搜索引擎
    
    在实际应用中，这里调用真实的搜索 API
    """
    # 模拟搜索结果
    return [
        {
            'doc_id': f'doc_{i}',
            'title': f'相关结果{i}',
            'content': f'这是关于{query}的详细内容...',
            'relevance': max(0, 5 - i)  # 模拟相关性评分
        }
        for i in range(10)
    ]

# 进行 RL 训练
rl_model = trainer.stage2_reinforcement_learning(
    pretrained_model_path=pretrained_path,
    train_data=train_list,
    val_data=val_list,
    search_engine_fn=mock_search_engine  # 传入搜索引擎
)

# 5. 保存最终模型
trainer._save_rl_model(trainer.rl_trainer, "./final_rl_model")
```

### 示例 2: 自定义搜索引擎集成

```python
"""
示例 2: 集成真实的搜索引擎
"""

import requests
from typing import List, Dict

class RealSearchEngine:
    """真实搜索引擎的封装"""
    
    def __init__(self, search_api_url: str, api_key: str):
        self.search_api_url = search_api_url
        self.api_key = api_key
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        执行搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            search_results: 搜索结果列表
        """
        # 调用搜索 API
        response = requests.get(
            self.search_api_url,
            params={
                'q': query,
                'k': top_k,
                'api_key': self.api_key
            }
        )
        
        results = response.json()
        
        # 转换为标准格式
        formatted_results = []
        for item in results.get('results', []):
            formatted_results.append({
                'doc_id': item['id'],
                'title': item['title'],
                'content': item.get('content', ''),
                'snippet': item.get('snippet', ''),
                'url': item.get('url', '')
            })
        
        return formatted_results


# 使用真实搜索引擎进行训练
search_engine = RealSearchEngine(
    search_api_url="http://your-search-api.com/search",
    api_key="your-api-key"
)

# 包装为训练代码可用的格式
def search_fn(query):
    return search_engine.search(query)

# 开始训练
rl_model = trainer.stage2_reinforcement_learning(
    pretrained_model_path="./sl_model",
    train_data=train_list,
    val_data=val_list,
    search_engine_fn=search_fn
)
```

### 示例 3: 使用真实用户反馈日志

```python
"""
示例 3: 从日志数据库获取用户反馈
"""

import sqlite3
from datetime import datetime, timedelta

class UserFeedbackCollector:
    """用户反馈收集器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
    
    def get_feedback(self, session_id: str, query: str) -> Dict:
        """
        获取用户反馈
        
        Args:
            session_id: 会话 ID
            query: 查询文本
            
        Returns:
            feedback: 用户反馈信息
        """
        cursor = self.conn.cursor()
        
        # 1. 获取点击记录
        cursor.execute("""
            SELECT doc_id, dwell_time, is_satisfied
            FROM click_logs
            WHERE session_id = ? AND query = ?
            ORDER BY position
        """, (session_id, query))
        
        clicked_docs = []
        satisfied_clicks = []
        dwell_times = {}
        
        for row in cursor.fetchall():
            doc_id, dwell_time, is_satisfied = row
            clicked_docs.append(doc_id)
            dwell_times[doc_id] = dwell_time
            
            if is_satisfied:
                satisfied_clicks.append(doc_id)
        
        # 2. 检查是否重新查询
        cursor.execute("""
            SELECT COUNT(*)
            FROM query_logs
            WHERE session_id = ?
            AND timestamp > (
                SELECT timestamp FROM query_logs
                WHERE session_id = ? AND query = ?
                LIMIT 1
            )
        """, (session_id, session_id, query))
        
        reformulated = cursor.fetchone()[0] > 0
        
        return {
            'clicked_docs': clicked_docs,
            'satisfied_clicks': satisfied_clicks,
            'dwell_time': dwell_times,
            'reformulated': reformulated
        }
    
    def close(self):
        self.conn.close()


# 集成到训练中
feedback_collector = UserFeedbackCollector("user_logs.db")

def search_with_feedback(query):
    """搜索并获取用户反馈"""
    # 1. 执行搜索
    search_results = search_engine.search(query)
    
    # 2. 在实际场景中，这里会从实时日志中获取反馈
    # 对于离线训练，可以使用历史平均或模拟
    # 这里简化处理
    user_feedback = None  # 离线训练时可能没有实时反馈
    
    return search_results, user_feedback

# 训练
rl_model = trainer.stage2_reinforcement_learning(
    pretrained_model_path="./sl_model",
    train_data=train_list,
    val_data=val_list,
    search_engine_fn=lambda q: search_with_feedback(q)[0]
)
```

### 示例 4: 自定义奖励权重

```python
"""
示例 4: 调整奖励函数的权重
"""

class CustomizedRewardFunction(RewardFunction):
    """自定义权重的奖励函数"""
    
    def __init__(self, ndcg_weight=0.5, mrr_weight=0.3, feedback_weight=0.2):
        super().__init__()
        self.ndcg_weight = ndcg_weight
        self.mrr_weight = mrr_weight
        self.feedback_weight = feedback_weight
    
    def calculate_reward(self, original_query, rewritten_query, 
                        search_results, user_feedback=None, 
                        ideal_ranking=None):
        """自定义权重的奖励计算"""
        
        # 计算各项指标
        ndcg = self.search_metric_fn.calculate_ndcg(
            search_results, ideal_ranking, user_feedback
        )
        
        mrr = self.search_metric_fn.calculate_mrr(
            search_results, user_feedback
        )
        
        feedback = self.search_metric_fn.calculate_feedback_reward(
            user_feedback
        )
        
        # 使用自定义权重
        total_reward = (
            self.ndcg_weight * ndcg +
            self.mrr_weight * mrr +
            self.feedback_weight * feedback
        )
        
        return {
            'ndcg': ndcg,
            'mrr': mrr,
            'feedback': feedback,
            'total': total_reward
        }


# 使用自定义权重进行训练
custom_reward_fn = CustomizedRewardFunction(
    ndcg_weight=0.5,    # 更重视 NDCG
    mrr_weight=0.3,
    feedback_weight=0.2
)

# 在训练器中使用
rl_trainer = PPOTrainer(
    model=model,
    reward_fn=custom_reward_fn,
    args=args
)
```

### 示例 5: 多任务学习场景

```python
"""
示例 5: 同时优化多个目标
"""

class MultiTaskReward(RewardFunction):
    """多任务奖励函数"""
    
    def calculate_reward(self, original_query, rewritten_query, 
                        search_results, user_feedback=None,
                        ideal_ranking=None):
        """
        多任务奖励：同时考虑搜索质量、多样性、新颖性
        """
        rewards = {}
        
        # 1. 搜索质量指标
        quality_reward = super().calculate_reward(
            original_query, rewritten_query,
            search_results, user_feedback, ideal_ranking
        )
        rewards['quality'] = quality_reward
        
        # 2. 多样性奖励（结果的多样性）
        diversity_reward = self.calculate_diversity(search_results)
        rewards['diversity'] = diversity_reward
        
        # 3. 新颖性奖励（与原始查询的差异）
        novelty_reward = self.calculate_novelty(original_query, rewritten_query)
        rewards['novelty'] = novelty_reward
        
        # 综合奖励
        total_reward = (
            0.6 * quality_reward +  # 质量为主
            0.2 * diversity_reward + # 多样性为辅
            0.2 * novelty_reward     # 鼓励创新改写
        )
        
        rewards['total'] = total_reward
        
        return rewards
    
    def calculate_diversity(self, search_results):
        """计算结果多样性"""
        if len(search_results) == 0:
            return 0.0
        
        # 简单的多样性度量：不同类别的数量
        categories = set()
        for result in search_results:
            category = result.get('category', 'unknown')
            categories.add(category)
        
        diversity_score = len(categories) / min(10, len(search_results))
        return diversity_score
    
    def calculate_novelty(self, original, rewritten):
        """计算改写的新颖性"""
        from difflib import SequenceMatcher
        
        similarity = SequenceMatcher(None, original, rewritten).ratio()
        
        # 适度的差异最好（完全相同或完全不同都不好）
        if 0.3 <= 1 - similarity <= 0.7:
            return 1.0
        elif similarity > 0.9:
            return 0.5  # 过于保守
        else:
            return 0.3  # 差异过大
    
    def _calculate_simple_reward(self, original: str, rewritten: str) -> float:
        """简化奖励（回退方案）"""
        return self.calculate_novelty(original, rewritten)


# 使用多任务奖励
multi_task_reward = MultiTaskReward()

rl_model = trainer.stage2_reinforcement_learning(
    pretrained_model_path="./sl_model",
    train_data=train_list,
    val_data=val_list,
    search_engine_fn=mock_search_engine
)
```

### 示例 6: 在线 A/B 测试

```python
"""
示例 6: 在线评估和 A/B 测试
"""

class OnlineEvaluator:
    """在线评估器"""
    
    def __init__(self, rl_model_path, control_model_path):
        # 加载实验组模型（RL 微调）
        self.treatment_model = MacBERTForRLQueryRewrite()
        self.treatment_model.load_state_dict(
            torch.load(rl_model_path)
        )
        
        # 加载对照组模型（仅 SL）
        self.control_model = MacBERTForQueryRewrite()
        self.control_model.load_state_dict(
            torch.load(control_model_path)
        )
        
        self.metrics = {
            'treatment': {'ndcg': [], 'mrr': [], 'ctr': []},
            'control': {'ndcg': [], 'mrr': [], 'ctr': []}
        }
    
    def run_ab_test(self, queries, search_engine, feedback_collector):
        """
        运行 A/B 测试
        
        Args:
            queries: 测试查询列表
            search_engine: 搜索引擎
            feedback_collector: 反馈收集器
        """
        for query in queries:
            # 随机分配到实验组或对照组
            import random
            group = random.choice(['treatment', 'control'])
            
            if group == 'treatment':
                # 使用 RL 模型改写
                rewritten = self.rewrite_query(query, self.treatment_model)
            else:
                # 使用 SL 模型改写
                rewritten = self.rewrite_query(query, self.control_model)
            
            # 执行搜索
            results = search_engine.search(rewritten)
            
            # 收集反馈
            feedback = feedback_collector.get_feedback(
                session_id=get_session_id(),
                query=rewritten
            )
            
            # 计算指标
            reward_fn = SearchMetricReward()
            ndcg = reward_fn.calculate_ndcg(results, user_feedback=feedback)
            mrr = reward_fn.calculate_mrr(results, user_feedback=feedback)
            ctr = len(feedback['clicked_docs']) / len(results) if results else 0
            
            # 记录
            self.metrics[group]['ndcg'].append(ndcg)
            self.metrics[group]['mrr'].append(mrr)
            self.metrics[group]['ctr'].append(ctr)
        
        return self.analyze_results()
    
    def analyze_results(self):
        """分析 A/B 测试结果"""
        import numpy as np
        
        results = {}
        for metric in ['ndcg', 'mrr', 'ctr']:
            treatment_mean = np.mean(self.metrics['treatment'][metric])
            control_mean = np.mean(self.metrics['control'][metric])
            
            improvement = (treatment_mean - control_mean) / control_mean
            
            results[metric] = {
                'treatment': treatment_mean,
                'control': control_mean,
                'improvement': f"{improvement:.2%}"
            }
        
        return results


# 运行 A/B 测试
evaluator = OnlineEvaluator(
    rl_model_path="./rl_model/pytorch_model.bin",
    control_model_path="./sl_model/pytorch_model.bin"
)

ab_results = evaluator.run_ab_test(
    queries=test_queries,
    search_engine=search_engine,
    feedback_collector=feedback_collector
)

print("A/B Test Results:")
for metric, data in ab_results.items():
    print(f"{metric.upper()}: Treatment={data['treatment']:.4f}, "
          f"Control={data['control']:.4f}, "
          f"Improvement={data['improvement']}")
```

## 总结

这些示例展示了如何：

1. ✅ **基础训练** - 使用 NDCG+MRR+ 反馈奖励
2. ✅ **集成真实搜索引擎** - 调用生产环境的搜索 API
3. ✅ **使用用户反馈日志** - 从数据库获取真实行为
4. ✅ **自定义权重** - 调整各指标的优先级
5. ✅ **多任务学习** - 同时优化质量、多样性、新颖性
6. ✅ **在线 A/B 测试** - 评估 RL 模型的实际效果

根据你的具体场景选择合适的配置！
