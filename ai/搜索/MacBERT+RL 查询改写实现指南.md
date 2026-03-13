# MacBERT + 强化学习 Query Rewrite 实现指南

## 概述

本项目实现了基于 **MacBERT + 强化学习（PPO）** 的两阶段搜索 query 改写系统：

- **第一阶段**：监督学习预训练，学习基本的改写能力
- **第二阶段**：强化学习微调，优化改写质量

## 核心架构

### 1. 模型结构

```python
class MacBERTForRLQueryRewrite:
    - BERT 编码器：提取输入语义表示
    - 策略头 (Policy Head)：输出动作概率分布
    - 价值头 (Value Head)：评估状态价值
```

### 2. 损失计算位置

#### 第一阶段（监督学习）

在 `MacBERTForQueryRewrite.forward()` 中计算交叉熵损失：

```python
def forward(self, input_ids, attention_mask, labels):
    sequence_output = self.bert(input_ids, attention_mask)
    logits = self.classifier(sequence_output)
    
    if labels is not None:
        loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
        logits_flat = logits.view(-1, vocab_size)
        labels_flat = labels.view(-1)
        loss = loss_fct(logits_flat, labels_flat)
    
    return loss, logits
```

**损失函数**：标准的交叉熵损失
$$L = -\sum_{t} \log P(y_t | x_t)$$

#### 第二阶段（强化学习 - PPO）

在 `PPOTrainer.train_epoch()` 中计算 PPO 损失，包含三个部分：

##### 1. 策略损失（Policy Loss）

```python
# 重要性采样比率
ratio = torch.exp(new_log_probs - old_log_probs)

# PPO clipped loss
surr1 = ratio * advantages
surr2 = torch.clamp(ratio, 1-clip_epsilon, 1+clip_epsilon) * advantages
policy_loss = -torch.min(surr1, surr2)
```

**PPO 目标函数**：
$$L^{CLIP}(\theta) = \mathbb{E}[\min(r_t(\theta) \cdot A_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon) \cdot A_t)]$$

其中：
- $r_t(\theta) = \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{old}}(a_t|s_t)}$ 是重要性采样比率
- $A_t$ 是优势函数
- $\epsilon$ 是 clip 参数（默认 0.2）

##### 2. 价值损失（Value Loss）

```python
value_loss = F.mse_loss(new_values, returns)
```

**价值函数损失**：
$$L^{VF} = \frac{1}{2} ||V_\phi(s) - V^{target}(s)||^2$$

##### 3. 熵正则化（Entropy Regularization）

```python
probs = F.softmax(policy_logits, dim=-1)
entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1)
entropy_loss = entropy.mean()
```

**熵奖励**（鼓励探索）：
$$H(\pi) = -\sum_a \pi(a|s) \log \pi(a|s)$$

##### 4. 总损失

```python
loss = policy_loss.mean() + value_coef * value_loss - entropy_coef * entropy_loss
```

**总目标函数**：
$$L^{TOTAL} = L^{CLIP} + c_1 \cdot L^{VF} - c_2 \cdot H$$

其中：
- $c_1 = 0.5$ （价值系数）
- $c_2 = 0.01$ （熵系数）

### 3. 奖励函数设计

在 `RewardFunction` 类中实现了多维度奖励：

```python
def calculate_reward(self, original_query, rewritten_query, target_query):
    # 1. 语义相似度奖励（权重 0.4）
    semantic_reward = self.semantic_similarity_reward(...)
    
    # 2. 长度合理性奖励（权重 0.2）
    length_reward = self.length_reward(...)
    
    # 3. 流畅度奖励（权重 0.2）
    fluency_reward = self.fluency_reward(...)
    
    # 4. 目标相似度奖励（权重 0.2）
    target_reward = self.target_similarity_reward(...)
    
    # 加权求和
    total_reward = 0.4*semantic + 0.2*length + 0.2*fluency + 0.2*target
```

**综合奖励函数**：
$$R = 0.4 \cdot R_{semantic} + 0.2 \cdot R_{length} + 0.2 \cdot R_{fluency} + 0.2 \cdot R_{target}$$

### 4. 优势函数计算（GAE）

使用 **Generalized Advantage Estimation (GAE)**：

```python
def compute_returns_and_advantages(self, rewards, values, dones):
    last_gae_lambda = 0
    
    for t in reversed(range(seq_len)):
        # TD error: δ_t = r_t + γV(s_{t+1}) - V(s_t)
        delta = rewards[t] + gamma * next_value * (1-dones[t]) - values[t]
        
        # GAE: A_t = δ_t + γλδ_{t+1} + ...
        last_gae_lambda = delta + gamma * lambda_ * (1-dones[t]) * last_gae_lambda
        advantages[t] = last_gae_lambda
    
    return returns, advantages
```

**GAE 公式**：
$$A_t^{GAE(\gamma,\lambda)} = \sum_{l=0}^{\infty} (\gamma\lambda)^l \delta_{t+l}$$

其中：
- $\gamma = 0.99$ （折扣因子）
- $\lambda = 0.95$ （GAE 平滑参数）
- $\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$ （TD error）

## 训练流程

### 第一阶段：监督学习

```python
# 创建数据集
train_dataset = QueryRewriteDataset(data_list=train_data, strategy="align_with_insert")

# 创建模型
model = MacBERTForQueryRewrite("hfl/chinese-macbert-base")

# 训练
trainer = Trainer(model, train_dataset, val_dataset, args)
trainer.train()  # 最小化交叉熵损失
```

**优化目标**：
$$\min_\theta \sum_{(x,y) \in D} -\log P_\theta(y|x)$$

### 第二阶段：强化学习（PPO）

```python
# 加载预训练模型
model = MacBERTForRLQueryRewrite("hfl/chinese-macbert-base")
model.bert.load_state_dict(pretrained_weights)

# 创建 PPO 训练器
rl_trainer = PPOTrainer(model, reward_fn, args)

# PPO 训练循环
for epoch in range(rl_epochs):
    # 1. 采样动作
    actions, log_probs, values = model.sample_actions(input_ids)
    
    # 2. 计算奖励
    rewards = [reward_fn(original, rewritten) for ...]
    
    # 3. 计算优势
    returns, advantages = compute_returns_and_advantages(rewards, values)
    
    # 4. PPO 更新（多次）
    for _ in range(ppo_epochs):
        new_log_probs, new_values = model(input_ids, actions)
        
        ratio = exp(new_log_probs - old_log_probs)
        policy_loss = -min(ratio * advantages, clip(ratio) * advantages)
        value_loss = MSE(new_values, returns)
        entropy_loss = entropy(policy_logits)
        
        loss = policy_loss + 0.5 * value_loss - 0.01 * entropy_loss
        
        loss.backward()
        optimizer.step()
```

**PPO 算法伪代码**：

```
初始化策略参数 θ_0, 价值函数参数 ϕ_0
for k = 0, 1, 2, ... do:
    采集 N 条轨迹 {(s_t, a_t, r_t)}
    计算优势函数 Â_t (使用 GAE)
    
    for epoch = 1 to K do:
        对于每个样本：
            计算比率 r_t(θ) = π_θ(a_t|s_t) / π_θ_old(a_t|s_t)
            计算策略损失 L^CLIP(θ)
            计算价值损失 L^VF(ϕ)
            计算熵正则 H(π)
            总损失 L = L^CLIP + c1*L^VF - c2*H
        
        更新 θ 和 ϕ (使用梯度下降)
    
    更新旧策略 π_θ_old ← π_θ
```

## 关键参数配置

```python
class Args:
    # 第一阶段
    sl_learning_rate = 5e-5      # 监督学习学习率
    sl_epochs = 10               # 监督学习轮数
    
    # 第二阶段
    policy_lr = 3e-5             # 策略头学习率
    value_lr = 1e-4              # 价值头学习率
    bert_lr = 1e-5               # BERT 编码器学习率
    rl_epochs = 5                # RL 训练轮数
    
    # PPO 参数
    clip_epsilon = 0.2           # PPO clip 范围
    gamma = 0.99                 # 折扣因子
    gae_lambda = 0.95            # GAE λ参数
    ppo_epochs = 4               # 每个 batch 的 PPO 更新次数
    temperature = 1.0            # 采样温度
    value_coef = 0.5             # 价值损失系数
    entropy_coef = 0.01          # 熵正则系数
```

## 使用示例

### 训练模型

```bash
python macbert_rl_query_rewrite_train.py
```

### 推理预测

```python
# 加载模型
model = MacBERTForRLQueryRewrite("hfl/chinese-macbert-base")
model.load_state_dict(torch.load("query_rewrite_rl/pytorch_model.bin"))

# 预测
input_ids = tokenizer.encode(query, return_tensors="pt")
actions, confidence = model.predict_greedy(input_ids)
rewritten_query = tokenizer.decode(actions[0])
```

## 与纯监督学习的区别

| 特性 | 监督学习 | 强化学习 |
|------|---------|---------|
| **目标** | 拟合标注数据 | 最大化累积奖励 |
| **损失** | 交叉熵 | PPO 损失（策略 + 价值 + 熵） |
| **数据** | 需要 (original, target) 对 | 只需要 original 和 reward |
| **灵活性** | 受限于标注 | 可定义任意 reward 函数 |
| **优化** | 逐 token 准确 | 序列级别整体优化 |

## 总结

**第二阶段强化学习的核心步骤**：

1. **采样**：从当前策略采样动作序列
2. **评估**：计算奖励和优势函数（GAE）
3. **裁剪**：限制策略更新幅度（PPO clip）
4. **优化**：联合优化策略和价值网络
5. **探索**：通过熵正则保持探索能力

这种设计使得模型能够：
- ✅ 超越标注数据的限制
- ✅ 直接优化业务指标（通过 reward 设计）
- ✅ 更稳定的训练过程（PPO 的 clipped 更新）
- ✅ 更好的泛化能力（熵正则鼓励多样性）
