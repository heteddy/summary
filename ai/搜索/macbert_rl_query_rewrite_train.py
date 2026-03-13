# MacBERT + 强化学习 查询改写训练代码
# 第一阶段：监督学习预训练
# 第二阶段：强化学习微调优化

import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertModel, AdamW, get_linear_schedule_with_warmup
from difflib import SequenceMatcher
from tqdm import tqdm
import os
import logging
from datetime import datetime
from typing import List, Tuple, Dict
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 奖励函数设计 ====================

class RewardFunction:
    """
    奖励函数计算器
    
    基于搜索评估指标：NDCG、MRR 和用户反馈
    """
    
    def __init__(self, search_metric_fn=None):
        """
        初始化奖励函数
        
        Args:
            search_metric_fn: 搜索指标计算器（SearchMetricReward 实例）
        """
        self.search_metric_fn = search_metric_fn or SearchMetricReward()
        
    def calculate_reward(self, original_query: str, rewritten_query: str, 
                        search_results: List[Dict] = None,  # type: ignore
                        user_feedback: Dict = None,  # type: ignore
                        ideal_ranking: List[str] = None) -> float:  # type: ignore
        """
        计算综合奖励分数
        
        Args:
            original_query: 原始查询
            rewritten_query: 改写后的查询
            search_results: 搜索结果列表（用于计算 NDCG 和 MRR）
            user_feedback: 用户反馈信息
            ideal_ranking: 理想的相关文档排序
            
        Returns:
            reward: 奖励分数 (-1 到 1)
        """
        # 如果没有提供搜索结果，使用简化的奖励计算
        if search_results is None:
            return self._calculate_simple_reward(original_query, rewritten_query)
        
        # 使用搜索指标计算奖励
        rewards = self.search_metric_fn.calculate_reward(
            original_query=original_query,
            rewritten_query=rewritten_query,
            search_results=search_results,
            user_feedback=user_feedback,
            ideal_ranking=ideal_ranking
        )
        
        # 返回总奖励
        return rewards['total']
    
    def _calculate_simple_reward(self, original: str, rewritten: str) -> float:
        """
        简化的奖励计算（当没有搜索结果时使用）
        
        基于基本的文本相似度指标
        """
        rewards = []
        
        # 1. 长度合理性
        length_reward = self.length_reward(original, rewritten)
        rewards.append(length_reward)
        
        # 2. 流畅度
        fluency_reward = self.fluency_reward(rewritten)
        rewards.append(fluency_reward)
        
        # 3. 简单的语义相似度（字符重叠）
        similarity = self._simple_similarity(original, rewritten)
        similarity_reward = 1.0 if similarity > 0.5 else 0.5 if similarity > 0.3 else 0.0
        rewards.append(similarity_reward)
        
        # 平均
        return sum(rewards) / len(rewards)
    
    def length_reward(self, original: str, rewritten: str, 
                     max_ratio: float = 2.0) -> float:
        """
        长度合理性奖励
        
        防止改写后的文本过长或过短
        """
        len_orig = len(original)
        len_rewrite = len(rewritten)
        
        if len_orig == 0:
            return 0.0
        
        ratio = len_rewrite / len_orig
        
        # 理想的长度比例在 0.5-2.0 之间
        if 0.5 <= ratio <= max_ratio:
            reward = 1.0
        elif ratio < 0.5:
            reward = -0.5 * (0.5 - ratio) / 0.5
        else:
            reward = -0.5 * (ratio - max_ratio) / max_ratio
        
        return reward
    
    def fluency_reward(self, text: str) -> float:
        """
        流畅度奖励
        
        基于语言模型困惑度或规则判断流畅度
        """
        # 简单规则：检查是否包含不合理的字符组合
        if not text or len(text.strip()) == 0:
            return -1.0
        
        # 检查是否有重复字符
        if len(text) > 10 and len(set(text)) / len(text) < 0.3:
            return -0.5
        
        # 检查是否以合理的方式结束
        if text[-1] in '.,!?;:':
            return 0.8
        
        return 1.0
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简单的字符级别相似度"""
        set1 = set(text1)
        set2 = set(text2)
        
        intersection = set1 & set2
        union = set1 | set2
        
        if len(union) == 0:
            return 0.0
        
        return len(intersection) / len(union)


# ==================== 基于搜索指标的奖励函数 ====================

class SearchMetricReward:
    """
    基于搜索评估指标的奖励函数
    
    使用 NDCG、MRR 和用户反馈来评估改写质量
    """
    
    def __init__(self, relevance_judgment_fn=None):
        """
        初始化搜索指标奖励函数
        
        Args:
            relevance_judgment_fn: 相关性判断函数 (query, doc) -> relevance_score
        """
        self.relevance_judgment_fn = relevance_judgment_fn
        
    def calculate_reward(self, original_query: str, rewritten_query: str, 
                        search_results: List[Dict], 
                        user_feedback: Dict = None,  # type: ignore
                        ideal_ranking: List[str] = None) -> Dict[str, float]:  # type: ignore
        """
        计算综合奖励分数
        
        Args:
            original_query: 原始查询
            rewritten_query: 改写后的查询
            search_results: 搜索结果列表，每个包含 {doc_id, title, content, ...}
            user_feedback: 用户反馈信息，包含：
                - clicked_docs: 点击的文档 ID 列表
                - dwell_time: 停留时间（秒）
                - satisfied_clicks: 满意点击的文档 ID 列表
                - reformulated: 是否重新构造查询（bool）
            ideal_ranking: 理想的相关文档排序（用于计算有监督的 NDCG）
            
        Returns:
            reward_dict: 包含各项奖励的字典
                {
                    'ndcg': float,
                    'mrr': float,
                    'feedback': float,
                    'total': float
                }
        """
        rewards = {}
        
        # 1. 计算 NDCG
        ndcg_score = self.calculate_ndcg(search_results, ideal_ranking, user_feedback)
        rewards['ndcg'] = ndcg_score
        
        # 2. 计算 MRR
        mrr_score = self.calculate_mrr(search_results, user_feedback)
        rewards['mrr'] = mrr_score
        
        # 3. 计算用户反馈奖励
        feedback_score = self.calculate_feedback_reward(user_feedback)
        rewards['feedback'] = feedback_score
        
        # 4. 综合奖励（加权平均）
        # NDCG 和 MRR 权重较高，用户反馈作为重要参考
        total_reward = (
            0.4 * ndcg_score + 
            0.3 * mrr_score + 
            0.3 * feedback_score
        )
        rewards['total'] = total_reward
        
        return rewards
    
    def calculate_ndcg(self, search_results: List[Dict], 
                      ideal_ranking: List[str] = None,  # type: ignore
                      user_feedback: Dict = None) -> float:  # type: ignore
        """
        计算 NDCG@K (Normalized Discounted Cumulative Gain)
        
        Args:
            search_results: 搜索结果列表
            ideal_ranking: 理想的相关文档 ID 列表
            user_feedback: 用户反馈
            
        Returns:
            ndcg_score: NDCG 分数 (0-1)
        """
        K = min(10, len(search_results))  # NDCG@10
        
        if len(search_results) == 0:
            return 0.0
        
        # ========== 方法 1: 如果有理想排序，使用标准的 NDCG ==========
        if ideal_ranking:
            return self._calculate_standard_ndcg(search_results, ideal_ranking, K)
        
        # ========== 方法 2: 如果没有理想排序，使用用户反馈估计相关性 ==========
        if user_feedback:
            return self._calculate_feedback_based_ndcg(search_results, user_feedback, K)
        
        # ========== 方法 3: 如果都没有，使用启发式方法估计 ==========
        return self._calculate_heuristic_ndcg(search_results, K)
    
    def _calculate_standard_ndcg(self, search_results: List[Dict], 
                                 ideal_ranking: List[str], K: int) -> float:
        """
        标准 NDCG 计算（需要理想排序）
        """
        # 构建 doc_id 到 relevance 的映射
        relevance_map = {}
        for i, doc_id in enumerate(ideal_ranking):
            # 位置越靠前，相关性越高
            # 位置 1: relevance=5, 位置 2: relevance=4, ..., 位置 5+: relevance=1
            relevance = max(1, 6 - i) if i < len(ideal_ranking) else 0
            relevance_map[doc_id] = relevance
        
        # 计算 DCG
        dcg = 0.0
        for i in range(min(K, len(search_results))):
            doc_id = search_results[i].get('doc_id')
            rel = relevance_map.get(doc_id, 0)
            dcg += (2**rel - 1) / np.log2(i + 2)
        
        # 计算 Ideal DCG
        idcg = 0.0
        for i in range(min(K, len(ideal_ranking))):
            doc_id = ideal_ranking[i]
            rel = relevance_map.get(doc_id, 0)
            idcg += (2**rel - 1) / np.log2(i + 2)
        
        # NDCG = DCG / IDCG
        if idcg == 0:
            return 0.0
        
        ndcg = dcg / idcg
        return ndcg
    
    def _calculate_feedback_based_ndcg(self, search_results: List[Dict], 
                                       user_feedback: Dict, K: int) -> float:
        """
        基于用户反馈的 NDCG 计算
        
        使用点击和停留时间来推断文档相关性
        """
        clicked_docs = set(user_feedback.get('clicked_docs', []))
        satisfied_clicks = set(user_feedback.get('satisfied_clicks', []))
        dwell_times = user_feedback.get('dwell_time', {})  # {doc_id: time}
        
        # 为每个文档分配相关性分数
        relevance_scores = []
        
        for i in range(min(K, len(search_results))):
            doc_id = search_results[i].get('doc_id')
            
            # 相关性判断规则：
            # 5: 满意点击且长停留 (>60s)
            # 4: 满意点击
            # 3: 普通点击且中等停留 (20-60s)
            # 2: 普通点击且短停留 (<20s)
            # 1: 未点击但排名靠前
            # 0: 未点击
            
            if doc_id in satisfied_clicks:
                dwell = dwell_times.get(doc_id, 0)
                rel = 5 if dwell > 60 else 4
            elif doc_id in clicked_docs:
                dwell = dwell_times.get(doc_id, 0)
                if dwell > 60:
                    rel = 4
                elif dwell > 20:
                    rel = 3
                else:
                    rel = 2
            else:
                # 未点击的文档，根据位置给一个基础分
                rel = max(0, 2 - i * 0.3)
            
            relevance_scores.append(rel)
        
        # 计算 DCG
        dcg = sum((2**rel - 1) / np.log2(i + 2) for i, rel in enumerate(relevance_scores))
        
        # 计算 Ideal DCG（将 relevance_scores 降序排列）
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg = sum((2**rel - 1) / np.log2(i + 2) for i, rel in enumerate(ideal_scores))
        
        if idcg == 0:
            return 0.0
        
        ndcg = dcg / idcg
        return ndcg
    
    def _calculate_heuristic_ndcg(self, search_results: List[Dict], K: int) -> float:
        """
        启发式 NDCG 计算
        
        基于搜索结果的质量进行估计
        """
        if len(search_results) == 0:
            return 0.0
        
        # 简单的启发式规则：
        # - 有标题和摘要的文档得分更高
        # - 长文本得分更高
        # - 排名靠前的文档权重更大
        
        relevance_scores = []
        for i, result in enumerate(search_results[:K]):
            score = 0
            
            # 基本信息完整性
            if result.get('title'):
                score += 1
            if result.get('content') or result.get('snippet'):
                score += 1
            
            # 文本长度
            content_len = len(result.get('content', '') or result.get('snippet', ''))
            if content_len > 500:
                score += 2
            elif content_len > 200:
                score += 1
            
            # 位置衰减
            position_weight = 1.0 / (i + 1)
            relevance_scores.append(score * position_weight)
        
        # 归一化到 [0, 1]
        if max(relevance_scores) == 0:
            return 0.0
        
        dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(relevance_scores))
        max_dcg = sum(sorted(relevance_scores, reverse=True)[i] / np.log2(i + 2) 
                     for i in range(len(relevance_scores)))
        
        if max_dcg == 0:
            return 0.0
        
        return dcg / max_dcg
    
    def calculate_mrr(self, search_results: List[Dict], 
                     user_feedback: Dict = None) -> float:  # type: ignore
        """
        计算 MRR (Mean Reciprocal Rank)
        
        Args:
            search_results: 搜索结果列表
            user_feedback: 用户反馈
            
        Returns:
            mrr_score: MRR 分数 (0-1)
        """
        if len(search_results) == 0:
            return 0.0
        
        # ========== 方法 1: 使用用户反馈确定第一个相关文档 ==========
        if user_feedback:
            clicked_docs = set(user_feedback.get('clicked_docs', []))
            satisfied_clicks = set(user_feedback.get('satisfied_clicks', []))
            
            # 优先查找满意点击的第一个位置
            for relevant_set in [satisfied_clicks, clicked_docs]:
                for i, result in enumerate(search_results):
                    doc_id = result.get('doc_id')
                    if doc_id in relevant_set:
                        return 1.0 / (i + 1)
        
        # ========== 方法 2: 使用启发式方法 ==========
        # 假设第一个有完整信息的文档是相关的
        for i, result in enumerate(search_results):
            if result.get('title') and (result.get('content') or result.get('snippet')):
                # 返回倒数排名
                return 1.0 / (i + 1)
        
        # 如果没有找到相关文档
        return 0.0
    
    def calculate_feedback_reward(self, user_feedback: Dict = None) -> float:
        """
        基于用户反馈的奖励
        
        Args:
            user_feedback: 用户反馈信息
            
        Returns:
            feedback_reward: 反馈奖励 (-1 到 1)
        """
        if not user_feedback:
            # 没有反馈时，给中性分数
            return 0.0
        
        reward_components = []
        weights = []
        
        # 1. 点击奖励
        clicked_docs = user_feedback.get('clicked_docs', [])
        if len(clicked_docs) > 0:
            click_reward = min(1.0, len(clicked_docs) / 3.0)  # 最多 3 个点击给满分
            reward_components.append(click_reward)
            weights.append(0.3)
        else:
            # 没有点击给负奖励
            reward_components.append(-0.5)
            weights.append(0.3)
        
        # 2. 满意点击奖励
        satisfied_clicks = user_feedback.get('satisfied_clicks', [])
        if len(satisfied_clicks) > 0:
            satisfaction_reward = min(1.0, len(satisfied_clicks) / 2.0)
            reward_components.append(satisfaction_reward)
            weights.append(0.4)
        else:
            reward_components.append(0.0)
            weights.append(0.4)
        
        # 3. 停留时间奖励
        dwell_times = user_feedback.get('dwell_time', {})
        if dwell_times:
            avg_dwell = sum(dwell_times.values()) / len(dwell_times)
            # 平均停留时间 > 30s 给正奖励
            if avg_dwell > 60:
                time_reward = 1.0
            elif avg_dwell > 30:
                time_reward = 0.5
            elif avg_dwell > 10:
                time_reward = 0.0
            else:
                time_reward = -0.5
            reward_components.append(time_reward)
            weights.append(0.2)
        else:
            reward_components.append(0.0)
            weights.append(0.2)
        
        # 4. 查询重构惩罚
        reformulated = user_feedback.get('reformulated', False)
        if reformulated:
            # 用户重新构造查询，说明不满意
            reward_components.append(-0.5)
            weights.append(0.1)
        else:
            reward_components.append(0.0)
            weights.append(0.1)
        
        # 加权求和
        total_reward = sum(r * w for r, w in zip(reward_components, weights))
        
        # 限制在 [-1, 1] 范围
        return max(-1.0, min(1.0, total_reward))


# ==================== 强化学习策略模型 ====================

class MacBERTForRLQueryRewrite(nn.Module):
    """
    基于 MacBERT 的强化学习查询改写模型
    
    使用策略梯度方法（Policy Gradient）
    将 query 改写视为序列决策问题
    """
    
    def __init__(self, model_name="hfl/chinese-macbert-base"):
        """
        初始化 RL 模型
        
        Args:
            model_name: MacBERT 模型名称
        """
        super(MacBERTForRLQueryRewrite, self).__init__()
        self.bert = BertModel.from_pretrained(model_name)
        self.config = self.bert.config
        self.vocab_size = self.config.vocab_size
        
        # 策略网络：输出每个位置选择每个词的概率分布
        self.policy_head = nn.Linear(self.config.hidden_size, self.vocab_size)
        
        # 价值网络：评估当前状态的价值（用于基线）
        self.value_head = nn.Linear(self.config.hidden_size, 1)
        
        logger.info(f"加载 MacBERT RL 模型：{model_name}")
        logger.info(f"策略头：Linear({self.config.hidden_size} -> {self.vocab_size})")
        logger.info(f"价值头：Linear({self.config.hidden_size} -> 1)")
    
    def forward(self, input_ids, attention_mask=None, actions=None):
        """
        前向传播
        
        Args:
            input_ids: 输入 token IDs [batch_size, seq_len]
            attention_mask: 注意力掩码 [batch_size, seq_len]
            actions: 采取的动作（预测的词 IDs）[batch_size, seq_len]
            
        Returns:
            policy_logits: 策略输出 [batch_size, seq_len, vocab_size]
            values: 价值估计 [batch_size, seq_len]
            log_probs: 动作的对数概率（如果提供了 actions）
        """
        # BERT 编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        sequence_output = outputs.last_hidden_state  # [batch, seq_len, hidden]
        
        # 策略头输出
        policy_logits = self.policy_head(sequence_output)
        
        # 价值头输出
        values = self.value_head(sequence_output).squeeze(-1)
        
        # 计算采取动作的对数概率
        log_probs = None
        if actions is not None:
            # 使用多项式分布计算对数概率
            log_probs = F.log_softmax(policy_logits, dim=-1)
            # 收集实际采取动作的概率
            log_probs = log_probs.gather(2, actions.unsqueeze(-1)).squeeze(-1)
        
        return policy_logits, values, log_probs
    
    def sample_actions(self, input_ids, attention_mask=None, temperature=1.0):
        """
        从策略分布中采样动作
        
        Args:
            input_ids: 输入 IDs
            attention_mask: 注意力掩码
            temperature: 温度参数（控制探索程度）
            
        Returns:
            actions: 采样的动作
            log_probs: 动作的对数概率
            values: 价值估计
        """
        self.eval()
        with torch.no_grad():
            policy_logits, values, _ = self.forward(input_ids, attention_mask)
            
            # 应用温度参数
            scaled_logits = policy_logits / temperature
            
            # 从多项式分布采样
            probs = F.softmax(scaled_logits, dim=-1)
            dist = torch.distributions.Categorical(probs)
            actions = dist.sample()
            
            # 计算对数概率
            log_probs = dist.log_prob(actions)
            
            # Mask padding 位置
            if attention_mask is not None:
                log_probs = log_probs * attention_mask
                values = values * attention_mask
        
        return actions, log_probs, values
    
    def predict_greedy(self, input_ids, attention_mask=None):
        """
        贪婪预测（选择概率最高的动作）
        
        Args:
            input_ids: 输入 IDs
            attention_mask: 注意力掩码
            
        Returns:
            actions: 预测的动作
            confidence: 置信度
        """
        self.eval()
        with torch.no_grad():
            policy_logits, values, _ = self.forward(input_ids, attention_mask)
            
            # 获取概率分布
            probs = F.softmax(policy_logits, dim=-1)
            
            # 选择概率最高的词
            confidence, actions = torch.max(probs, dim=-1)
        
        return actions, confidence


# ==================== PPO 算法实现 ====================

class PPOTrainer:
    """
    PPO (Proximal Policy Optimization) 训练器
    
    用于微调预训练的 query 改写模型
    """
    
    def __init__(self, model, reward_fn, args):
        """
        初始化 PPO 训练器
        
        Args:
            model: RL 模型
            reward_fn: 奖励函数
            args: 训练参数
        """
        self.model = model
        self.reward_fn = reward_fn
        self.args = args
        
        # 设备配置
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        logger.info(f"使用设备：{self.device}")
        
        # 优化器（分别设置策略和价值网络的 learning rate）
        self.optimizer = AdamW([
            {'params': model.policy_head.parameters(), 'lr': args.policy_lr},
            {'params': model.value_head.parameters(), 'lr': args.value_lr},
            {'params': model.bert.parameters(), 'lr': args.bert_lr}
        ])
        
        # PPO 参数
        self.clip_epsilon = args.clip_epsilon
        self.gamma = args.gamma  # 折扣因子
        self.lam = args.gae_lambda  # GAE 参数
        self.epochs_per_batch = args.ppo_epochs
        self.batch_size = args.batch_size
        
        logger.info(f"PPO 配置：clip={self.clip_epsilon}, gamma={self.gamma}, lambda={self.lam}")
    
    def compute_returns_and_advantages(self, rewards, values, dones):
        """
        计算回报和优势函数（使用 GAE）
        
        Args:
            rewards: 奖励序列 [batch, seq_len]
            values: 价值估计 [batch, seq_len]
            dones: 终止标记 [batch, seq_len]
            
        Returns:
            returns: 回报
            advantages: 优势函数
        """
        batch_size, seq_len = rewards.shape
        
        # 初始化
        returns = torch.zeros_like(rewards)
        advantages = torch.zeros_like(rewards)
        
        # 从后向前计算
        last_gae_lambda = 0
        
        for t in reversed(range(seq_len)):
            if t == seq_len - 1:
                next_value = 0
            else:
                next_value = values[:, t + 1]
            
            # TD error: δ_t = r_t + γV(s_{t+1}) - V(s_t)
            delta = rewards[:, t] + self.gamma * next_value * (1 - dones[:, t]) - values[:, t]
            
            # GAE: A_t = δ_t + γλδ_{t+1} + ...
            last_gae_lambda = delta + self.gamma * self.lam * (1 - dones[:, t]) * last_gae_lambda
            advantages[:, t] = last_gae_lambda
            
            # 回报 = 优势 + 价值
            returns[:, t] = advantages[:, t] + values[:, t]
        
        return returns, advantages
    
    def train_epoch(self, data_loader, epoch, search_engine_fn=None):
        """
        训练一个 epoch
        
        Args:
            data_loader: 数据加载器
            epoch: 当前 epoch
            search_engine_fn: 搜索引擎函数 (query) -> [search_results]
            
        Returns:
            avg_loss: 平均损失
            avg_reward: 平均奖励
        """
        self.model.train()
        total_loss = 0
        total_reward = 0
        num_batches = 0
        reward_stats = {'ndcg': 0, 'mrr': 0, 'feedback': 0, 'total': 0}
        
        progress_bar = tqdm(data_loader, desc=f"PPO Epoch {epoch+1}")
        
        for batch in progress_bar:
            # 准备数据
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            original_queries = batch["original_query"]
            target_queries = batch.get("target_query", [None] * len(original_queries))
            
            batch_size = input_ids.shape[0]
            seq_len = input_ids.shape[1]
            
            # ========== 步骤 1: 采样动作 ==========
            actions, old_log_probs, old_values = self.model.sample_actions(
                input_ids, attention_mask, temperature=self.args.temperature
            )
            
            # 解码采样的动作
            decoded_queries = self.decode_actions(input_ids, actions, attention_mask)
            
            # ========== 步骤 2: 获取搜索结果并计算奖励 ==========
            rewards = []
            batch_rewards = {'ndcg': [], 'mrr': [], 'feedback': []}
            
            for i in range(batch_size):
                orig_q = original_queries[i]
                rewrite_q = decoded_queries[i]
                
                # 如果有搜索引擎，获取真实的搜索结果
                if search_engine_fn:
                    try:
                        # 使用改写后的查询搜索
                        search_results = search_engine_fn(rewrite_q)
                        
                        # 模拟或获取用户反馈
                        user_feedback = self._get_user_feedback(
                            orig_q, rewrite_q, search_results
                        )
                        
                        # 计算详细的奖励（包含 NDCG、MRR、反馈）
                        reward_dict = self.reward_fn.calculate_reward(
                            original_query=orig_q,
                            rewritten_query=rewrite_q,
                            search_results=search_results,
                            user_feedback=user_feedback,
                            ideal_ranking=None  # 可以提供理想排序
                        )
                        
                        # 如果返回的是字典，提取总奖励
                        if isinstance(reward_dict, dict):
                            reward = reward_dict['total']
                            for key in ['ndcg', 'mrr', 'feedback']:
                                batch_rewards[key].append(reward_dict.get(key, 0))
                        else:
                            reward = reward_dict
                        
                    except Exception as e:
                        logger.warning(f"搜索失败：{e}, 使用简化奖励")
                        reward = self.reward_fn._calculate_simple_reward(orig_q, rewrite_q)
                else:
                    # 没有搜索引擎，使用简化奖励
                    reward = self.reward_fn._calculate_simple_reward(orig_q, rewrite_q)
                
                rewards.append(reward)
            
            rewards = torch.tensor(rewards, dtype=torch.float32).to(self.device)
            total_reward += rewards.mean().item()
            
            # 统计各项奖励
            for key in ['ndcg', 'mrr', 'feedback']:
                if batch_rewards[key]:
                    reward_stats[key] += float(sum(batch_rewards[key]) / len(batch_rewards[key]))
            reward_stats['total'] += float(rewards.mean().item())
            
            # 将标量奖励扩展到序列长度（简化的 dense reward）
            rewards_expanded = rewards.unsqueeze(1).expand(-1, seq_len)
            
            # 创建 dones 标记（所有位置都为 0，因为这是一个完整序列的奖励）
            dones = torch.zeros_like(attention_mask)
            
            # ========== 步骤 3: 计算回报和优势 ==========
            with torch.no_grad():
                returns, advantages = self.compute_returns_and_advantages(
                    rewards_expanded, old_values, dones
                )
                
                # 标准化优势函数
                advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            
            # ========== 步骤 4: PPO 更新 ==========
            for _ in range(self.epochs_per_batch):
                # 重新计算 log 概率
                _, _, new_log_probs = self.model.forward(input_ids, attention_mask, actions)
                
                # 重新计算价值
                _, new_values, _ = self.model.forward(input_ids, attention_mask)
                
                # 重要性采样比率：r_t(θ) = π_θ(a|s) / π_θ_old(a|s)
                ratio = torch.exp(new_log_probs - old_log_probs)
                
                # PPO  clipped loss
                surr1 = ratio * advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages
                policy_loss = -torch.min(surr1, surr2)
                
                # 价值损失
                value_loss = F.mse_loss(new_values, returns)
                
                # 熵正则化（鼓励探索）
                policy_logits, _, _ = self.model.forward(input_ids, attention_mask)
                probs = F.softmax(policy_logits, dim=-1)
                entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1)
                entropy_loss = entropy.mean()
                
                # 总损失
                loss = (
                    policy_loss.mean() + 
                    self.args.value_coef * value_loss - 
                    self.args.entropy_coef * entropy_loss
                )
                
                # 反向传播
                self.optimizer.zero_grad()
                loss.backward()
                
                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.args.max_grad_norm)
                
                # 更新参数
                self.optimizer.step()
                
                total_loss += loss.item()
                num_batches += 1
            
            # 更新进度条
            progress_bar.set_postfix({
                "loss": f"{loss.item():.4f}",
                "reward": f"{rewards.mean().item():.4f}"
            })
        
        avg_loss = total_loss / max(num_batches, 1)
        avg_reward = total_reward / len(data_loader)
        
        # 打印各项奖励的平均值
        for key in ['ndcg', 'mrr', 'feedback']:
            reward_stats[key] /= float(len(data_loader))
        reward_stats['total'] /= float(len(data_loader))
        
        logger.info(f"Reward Stats - NDCG: {reward_stats['ndcg']:.4f}, "
                   f"MRR: {reward_stats['mrr']:.4f}, "
                   f"Feedback: {reward_stats['feedback']:.4f}, "
                   f"Total: {reward_stats['total']:.4f}")
        
        return avg_loss, avg_reward
    
    def _get_user_feedback(self, original_query: str, rewritten_query: str, 
                          search_results: List[Dict]) -> Dict:
        """
        获取或模拟用户反馈
        
        在实际应用中，这里应该从日志中获取真实的用户反馈
        这里提供一个简单的模拟实现
        
        Args:
            original_query: 原始查询
            rewritten_query: 改写后的查询
            search_results: 搜索结果
            
        Returns:
            user_feedback: 用户反馈信息
        """
        # TODO: 在实际应用中，从日志数据库查询真实反馈
        # 这里提供模拟实现
        
        if len(search_results) == 0:
            return {}  # type: ignore
        
        # 模拟点击行为：假设前 3 个结果更可能被点击
        clicked_docs = []
        satisfied_clicks = []
        dwell_times = {}
        
        for i, result in enumerate(search_results[:5]):
            doc_id = result.get('doc_id')
            
            # 模拟点击概率（排名越靠前，点击概率越高）
            click_prob = 0.8 - i * 0.1
            
            if np.random.random() < click_prob:
                clicked_docs.append(doc_id)
                
                # 模拟停留时间（秒）
                # 假设质量高的文档停留时间长
                quality_score = np.random.random()
                if quality_score > 0.7:
                    dwell_time = np.random.uniform(60, 120)  # 长停留
                    satisfied_clicks.append(doc_id)
                elif quality_score > 0.4:
                    dwell_time = np.random.uniform(20, 60)   # 中等停留
                else:
                    dwell_time = np.random.uniform(5, 20)    # 短停留
                
                dwell_times[doc_id] = dwell_time
        
        # 模拟查询重构（如果用户不满意，可能会重新查询）
        reformulated = len(clicked_docs) == 0 or np.random.random() < 0.2
        
        return {
            'clicked_docs': clicked_docs,
            'satisfied_clicks': satisfied_clicks,
            'dwell_time': dwell_times,
            'reformulated': reformulated
        }
    
    def decode_actions(self, input_ids, actions, attention_mask):
        """
        解码动作为文本
        
        Args:
            input_ids: 原始输入 IDs
            actions: 预测的动作
            attention_mask: 注意力掩码
            
        Returns:
            queries: 解码后的查询列表
        """
        tokenizer = self.model.bert.tokenizer if hasattr(self.model.bert, 'tokenizer') else BertTokenizer.from_pretrained("hfl/chinese-macbert-base")
        
        queries = []
        for i in range(actions.shape[0]):
            # 获取非 padding 位置
            mask = attention_mask[i].bool()
            action_ids = actions[i][mask]
            
            # 转换为 tokens
            tokens = tokenizer.convert_ids_to_tokens(action_ids.tolist())
            
            # 过滤特殊 token
            special_tokens = [tokenizer.cls_token, tokenizer.sep_token, tokenizer.pad_token]
            tokens = [t for t in tokens if t not in special_tokens]
            
            # 转换为字符串
            query = tokenizer.convert_tokens_to_string(tokens)
            queries.append(query)
        
        return queries


# ==================== 两阶段训练流程 ====================

class TwoStageTrainer:
    """
    两阶段训练器
    
    第一阶段：监督学习预训练
    第二阶段：强化学习微调
    """
    
    def __init__(self, model_name="hfl/chinese-macbert-base", args=None):
        """
        初始化两阶段训练器
        
        Args:
            model_name: 模型名称
            args: 训练参数
        """
        self.model_name = model_name
        self.args = args or self._default_args()
        
        # 初始化 tokenizer
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        
        # 初始化奖励函数
        self.reward_fn = RewardFunction()
        
        logger.info("两阶段训练器初始化完成")
        logger.info(f"模型：{model_name}")
        logger.info(f"第一阶段：监督学习预训练")
        logger.info(f"第二阶段：PPO 强化学习微调")
    
    def _default_args(self):
        """默认训练参数"""
        class Args:
            # 通用参数
            batch_size = 8
            max_length = 128
            
            # 第一阶段参数
            sl_epochs = 10
            sl_learning_rate = 5e-5
            sl_output_dir = "./query_rewrite_sl"
            
            # 第二阶段参数
            rl_epochs = 5
            policy_lr = 3e-5
            value_lr = 1e-4
            bert_lr = 1e-5
            rl_output_dir = "./query_rewrite_rl"
            
            # PPO 参数
            clip_epsilon = 0.2
            gamma = 0.99
            gae_lambda = 0.95
            ppo_epochs = 4
            temperature = 1.0
            value_coef = 0.5
            entropy_coef = 0.01
            max_grad_norm = 1.0
            
        return Args()
    
    def stage1_supervised_learning(self, train_data, val_data):
        """
        第一阶段：监督学习预训练
        
        Args:
            train_data: 训练数据列表 [(original, target), ...]
            val_data: 验证数据列表
            
        Returns:
            pretrained_model_path: 预训练模型路径
        """
        logger.info("=" * 60)
        logger.info("第一阶段：监督学习预训练")
        logger.info("=" * 60)
        
        # 创建数据集
        train_dataset = QueryRewriteDataset(
            data_list=train_data,
            model_name=self.model_name,
            max_length=self.args.max_length,
            strategy="align_with_insert"
        )
        
        val_dataset = QueryRewriteDataset(
            data_list=val_data,
            model_name=self.model_name,
            max_length=self.args.max_length,
            strategy="align_with_insert"
        )
        
        # 创建模型
        model = MacBERTForQueryRewrite(self.model_name)
        
        # 创建训练器
        trainer = Trainer(
            model=model,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            args=self.args
        )
        
        # 开始训练
        trainer.train()
        
        # 保存预训练模型
        pretrained_path = os.path.join(self.args.sl_output_dir, "final_model")
        trainer.save_model(pretrained_path)
        
        logger.info(f"第一阶段完成，预训练模型保存到：{pretrained_path}")
        return pretrained_path
    
    def stage2_reinforcement_learning(self, pretrained_model_path, train_data, val_data, 
                                     search_engine_fn=None):
        """
        第二阶段：强化学习微调
        
        Args:
            pretrained_model_path: 预训练模型路径
            train_data: 训练数据
            val_data: 验证数据
            search_engine_fn: 搜索引擎函数 (query) -> [search_results]
            
        Returns:
            rl_model: 强化学习微调后的模型
        """
        logger.info("=" * 60)
        logger.info("第二阶段：强化学习微调 (PPO)")
        logger.info("=" * 60)
        
        # 加载预训练模型
        logger.info(f"加载预训练模型：{pretrained_model_path}")
        model = MacBERTForRLQueryRewrite(self.model_name)
        
        # 加载预训练权重
        if os.path.exists(os.path.join(pretrained_model_path, "pytorch_model.bin")):
            state_dict = torch.load(
                os.path.join(pretrained_model_path, "pytorch_model.bin"),
                map_location='cpu'
            )
            
            # 只加载 BERT 编码器的权重
            bert_state_dict = {k: v for k, v in state_dict.items() if k.startswith('bert.')}
            model.bert.load_state_dict(bert_state_dict, strict=False)
            logger.info("成功加载预训练 BERT 权重")
        
        # 初始化奖励函数（使用搜索指标）
        reward_fn = RewardFunction(search_metric_fn=SearchMetricReward())
        
        # 创建 RL 训练器
        rl_trainer = PPOTrainer(
            model=model,
            reward_fn=reward_fn,
            args=self.args
        )
        
        # 创建数据集（用于采样）
        train_dataset = QueryRewriteDataset(
            data_list=train_data,
            model_name=self.model_name,
            max_length=self.args.max_length,
            strategy="align_with_insert"
        )
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.args.batch_size,
            shuffle=True,
            num_workers=0
        )
        
        # 开始 RL 训练
        best_reward = -float('inf')
        
        for epoch in range(self.args.rl_epochs):
            logger.info(f"\nRL Epoch {epoch+1}/{self.args.rl_epochs}")
            
            # 训练（传入搜索引擎函数）
            avg_loss, avg_reward = rl_trainer.train_epoch(train_loader, epoch, search_engine_fn)
            
            logger.info(f"RL Epoch {epoch+1} - Loss: {avg_loss:.4f}, Reward: {avg_reward:.4f}")
            
            # 保存最佳模型
            if avg_reward > best_reward:
                best_reward = avg_reward
                self._save_rl_model(rl_trainer, self.args.rl_output_dir)
                logger.info(f"保存最佳 RL 模型，奖励：{best_reward:.4f}")
        
        logger.info(f"\n第二阶段完成！最佳奖励：{best_reward:.4f}")
        return rl_trainer.model
    
    def _save_rl_model(self, rl_trainer, output_dir):
        """保存 RL 模型"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存模型权重
        model_to_save = rl_trainer.model.module if hasattr(rl_trainer.model, 'module') else rl_trainer.model
        torch.save(
            model_to_save.state_dict(),
            os.path.join(output_dir, "pytorch_model.bin")
        )
        
        # 保存配置
        model_to_save.bert.config.to_json_file(os.path.join(output_dir, "config.json"))
        
        # 保存 tokenizer
        self.tokenizer.save_pretrained(output_dir)
        
        logger.info(f"RL 模型已保存到：{output_dir}")
    
    def train(self, train_data, val_data):
        """
        完整的两阶段训练流程
        
        Args:
            train_data: 训练数据
            val_data: 验证数据
        """
        # 第一阶段
        pretrained_path = self.stage1_supervised_learning(train_data, val_data)
        
        # 第二阶段
        rl_model = self.stage2_reinforcement_learning(pretrained_path, train_data, val_data)
        
        logger.info("\n" + "=" * 60)
        logger.info("两阶段训练全部完成！")
        logger.info(f"最终模型路径：{self.args.rl_output_dir}")
        logger.info("=" * 60)
        
        return rl_model


# ==================== 主函数 ====================

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
        ("如何修改手机号", "修改手机号"),
        ("账户被冻结", "解冻账户"),
        ("提现失败", "提现问题"),
        ("优惠券怎么用", "优惠券使用方法"),
        ("实名认证", "实名认证流程"),
    ]
    return data


def main():
    """主函数：演示两阶段训练"""
    logger.info("开始 MacBERT + RL Query Rewrite 训练")
    
    # 创建示例数据
    train_data = create_sample_data()
    
    # 划分训练集和验证集
    split_idx = int(len(train_data) * 0.8)
    train_list = train_data[:split_idx]
    val_list = train_data[split_idx:]
    
    # 创建两阶段训练器
    two_stage_trainer = TwoStageTrainer(
        model_name="hfl/chinese-macbert-base",
        args=None  # 使用默认参数
    )
    
    # 开始训练
    final_model = two_stage_trainer.train(train_list, val_list)
    
    # 测试模型
    logger.info("\n测试最终模型...")
    test_queries = ["电脑登录不了", "密码忘记了", "怎么转账"]
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    final_model.to(device)
    final_model.eval()
    
    with torch.no_grad():
        for query in test_queries:
            # 分词
            tokens = two_stage_trainer.tokenizer.tokenize(query)
            input_ids = [two_stage_trainer.tokenizer.cls_token_id] + \
                       two_stage_trainer.tokenizer.convert_tokens_to_ids(tokens) + \
                       [two_stage_trainer.tokenizer.sep_token_id]
            attention_mask = [1] * len(input_ids)
            
            # Padding
            padding_length = two_stage_trainer.args.max_length - len(input_ids)
            if padding_length > 0:
                input_ids += [two_stage_trainer.tokenizer.pad_token_id] * padding_length
                attention_mask += [0] * padding_length
            
            # 转换为 tensor
            input_ids = torch.tensor([input_ids]).to(device)
            attention_mask = torch.tensor([attention_mask]).to(device)
            
            # 预测
            actions, confidence = final_model.predict_greedy(input_ids, attention_mask)
            
            # 解码
            mask = attention_mask[0].bool()
            action_ids = actions[0][mask]
            tokens = two_stage_trainer.tokenizer.convert_ids_to_tokens(action_ids.tolist())
            special_tokens = [two_stage_trainer.tokenizer.cls_token, 
                            two_stage_trainer.tokenizer.sep_token, 
                            two_stage_trainer.tokenizer.pad_token]
            tokens = [t for t in tokens if t not in special_tokens]
            rewritten = two_stage_trainer.tokenizer.convert_tokens_to_string(tokens)
            
            logger.info(f"原句：{query} -> 改写：{rewritten} (置信度：{confidence[0].mean().item():.4f})")


if __name__ == "__main__":
    main()
