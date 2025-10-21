# NLP-Interview

[https://github.com/laddie132/NLP-Interview#nlp-interview](https://github.com/laddie132/NLP-Interview#nlp-interview)

NLP算法岗-面试知识点

[TOC]

> 前言
> 
> 推荐使用Typora打开，阅读效果更好。
> 
> 推荐参考书籍如下：
> 
> - 《统计学习方法（第2版）》- 李航
> - 《Deep Learning》- Ian Goodfellow等
> - 《机器学习》- 周志华
> - 《百面机器学习》- 诸葛越等

## 一、基础算法

[https://github.com/laddie132/NLP-Interview#一基础算法](https://github.com/laddie132/NLP-Interview#%E4%B8%80%E5%9F%BA%E7%A1%80%E7%AE%97%E6%B3%95)

- Hashmap、Trie树
- 二分查找及其变形
- 各大排序算法

  - 冒泡排序、选择排序、插入排序、快速排序、归并排序、堆排序、桶排序
  - 复杂度（最优、最差、平均），稳定性

- 链表

  - 快慢指针：判断环（起点和长度）、找中间值、删除倒数第n个节点
  - 链表的翻转

- BFS、DFS（前序、中序、后序）

  - 递归和非递归算法
  - 恢复二叉树：前序+中序，后序+中序

- 二叉搜索树（红黑树）
- 平衡二叉树、完全二叉树
- 动态规划（背包问题）
- 搜索算法（回溯、递归）
- 并查集（初始化、查询、合并）
- python的多线程、多进程

> 经典算法
> 
> - 快速幂、快速幂取余
> - 大数相加、大数相乘
> - 字符串匹配算法KMP
> - 最长公共子序列（LCS）
> - 最长上升子序列（LIS）
> - 最小编辑距离
> - 0-1背包问题、完全背包问题、有序背包问题
> - 最短路径Dijkstra算法
> - 用rand7构造rand10
> - 绳子三段构成三角形概率，任意三角形锐角、直角、钝角的概率
> - 蓄水池采样
> - 无序数组的top-k

## 二、机器学习

[https://github.com/laddie132/NLP-Interview#二机器学习](https://github.com/laddie132/NLP-Interview#%E4%BA%8C%E6%9C%BA%E5%99%A8%E5%AD%A6%E4%B9%A0)

- 数据归一化

  - min-max、高斯分布、L1归一化、L2归一化
  - 哪些模型不用归一化，为什么要归一化
  - 特征筛选、连续变量构造特征

- 生成模型与判别模型
- 线性回归、LR回归、感知机（之间的联系）

  - LR推导
  - LR实际使用会对连续特征离散化
  - LR和softmax损失函数求导
  - 为什么不用线性回归做分类

- 朴素贝叶斯

  - 连续变量怎么处理、拉普拉斯平滑

- SVM推导

  - 基本形式、合页损失、对偶形式、核函数
  - LR与SVM的区别与联系

- 最大熵模型
- 决策树：ID3、C4.5、CART
- GBDT、XGBoost与AdaBoost的区别与联系
- 随机森林
- ensemble模型方法：Bagging，Boosting，Stacking
- HMM、MEMM和CRF的区别与联系
- 主题模型

  - LSA、pLSA、LDA（潜在狄利克雷分布）

- 各种机器学习距离

  - 余弦距离和欧式距离的关系

- LDA线性判别分析
- 降维：PCA、SVD
- K近邻算法
- K-means聚类

  - 数学证明可收敛（与EM算法的关系）
  - 缺点及改进：K-means++等


## 三、优化算法

[https://github.com/laddie132/NLP-Interview#三优化算法](https://github.com/laddie132/NLP-Interview#%E4%B8%89%E4%BC%98%E5%8C%96%E7%AE%97%E6%B3%95)

- 经验风险最小化、结构风险最小化、期望风险最小化
- 各种损失函数（交叉熵、LR损失函数、均方误差、KL损失、Hinge损失）

  - 交叉熵的两种解释

    - 信息量、信息熵、相对熵（KL散度）

  - 均方误差是经验分布和高斯模型之间的交叉熵
  - 线性回归为什么用均方差损失

    - 假设误差服从均值为0的高斯分布


- 极大似然估计、贝叶斯估计、最大后验估计

  - 最大后验估计是结构化风险最小化

- EM算法（带隐变量的极大似然估计）
- 凸优化的标准形式

  - KKT条件与对偶问题、原始问题

- 一阶优化算法与二阶优化算法

  - 梯度下降、牛顿法、拟牛顿法
  - 牛顿法不适用深度学

    - 计算慢，Hessian矩阵不一定正定、陷入鞍点
    - 牛顿法中的正则化


- 梯度消失和梯度爆炸问题

  - 悬崖、梯度截断

- 常见优化算法

  - SGD、Mini-Batch SGD、动量法、牛顿动量法、AdaGrad、AdaDelta、Adam
  - Adam失效 （二阶动量震荡 -> Adamax，一阶动量->容易跳过局部最优，L2正则化->AdamW）

- 参数初始化方法

  - 不能全部初始化为相同值
  - 均匀分布、正态分布
  - Xavier初始化、Kaiming初始化
  - 偏置初始化为1的情况

- K折交叉验证
- PR曲线与ROC曲线（对不平衡数据不敏感）
- AUC公式

  - 两种计算，概率学解释（排序）

- 模型压缩、模型蒸馏

## 四、特殊技巧

[https://github.com/laddie132/NLP-Interview#四特殊技巧](https://github.com/laddie132/NLP-Interview#%E5%9B%9B%E7%89%B9%E6%AE%8A%E6%8A%80%E5%B7%A7)

- Batch Size大小会怎么影响收敛速度

  - 一阶优化、二阶优化

- Batch-Normalization，Layer-Normalization，Instance-Normalization

  - 在（N, H, W, C）哪个维度归一化

- BN、激活函数、Dropout的顺序
- 防止过拟合（模型和数据）

  - 偏差与方差的解释
  - 数据增强，提前终止，正则化，引入噪声，Dropout，Bagging，多任务学习
  - 正则化的三种解释
  - Dropout与Bagging，及求导

- 数据不平衡（模型和数据）

  - 上采样、下采样，数据扩充，修改损失函数加权，数据量大标签数据分为k类、分别和小标签数据训练，最后Ensemble投票，ROC曲线

- 数据增强的方式

  - 随机替换、随机插入、随机删除、随机交换，翻译中间语言->回译，生成对抗网络

- softmax上溢和下溢问题
- 数据采样方法

## 五、深度学习

[https://github.com/laddie132/NLP-Interview#五深度学习](https://github.com/laddie132/NLP-Interview#%E4%BA%94%E6%B7%B1%E5%BA%A6%E5%AD%A6%E4%B9%A0)

- 常见激活函数及其用法

  - sigmoid、tanh、relu、maxout
  - relu的优缺点 -> softplus、leaky relu、prelu、gelu

- BP梯度反向传递推导
- LSTM、GRU公式

  - RNN为什么存在梯度消失，LSTM怎么解决梯度消失

- CNN+Pooling原理

  - 稀疏交互、参数共享、等变表示
  - Pooling：一定的平移不变性和旋转不变性

- Attention解释及种类
- 记忆网络

> 常考题目
> 
> - 如何用多层感知机实现异或逻辑
> - 一个隐层需要多少节点能实现包含n元输入的任意布尔函数
> - 多个隐层实现包含n元输入的任意布尔函数，需要多少节点和网络层

## 六、NLP算法

[https://github.com/laddie132/NLP-Interview#六nlp算法](https://github.com/laddie132/NLP-Interview#%E5%85%ADnlp%E7%AE%97%E6%B3%95)

- 传统NLP方法

  - N-gram最大概率分词、HMM词性标注、PCFG句法分析和CYK算法

- 语言模型评价：困惑度
- LSTM-CRF模型（训练和测试）
- 词向量：one-hot、Word2Vec、GloVe、FastText

  - Word2Vec公式推导：cBow、Skip-Gram

    - 求导
    - 加速训练：层次softmax和负采样
    - 为什么没有正则化

  - Word2Vec，GloVe，FastText区别

- 句向量：Skip-Thought、Quick-Thought
- 文档向量：Doc2Vec、TF-IDF词袋模型、LSA潜在语义模型
- 预训练语言模型：Cove、ELMo、GPT、BERT

  - 数据、模型、计算

- Seq2seq、文本分类、机器阅读理解、任务型人机对话
- BeamSearch与维特比算法

  - 一个局部最优，N*K*V；一个全局最优，N*V*V


## 七、强化学习

[https://github.com/laddie132/NLP-Interview#七强化学习](https://github.com/laddie132/NLP-Interview#%E4%B8%83%E5%BC%BA%E5%8C%96%E5%AD%A6%E4%B9%A0)

- MDP：马尔科夫决策过程
- value-based和policy-based方法
- DP的方法：贝尔曼方程、策略迭代、值迭代
- TD的方法：Sarsa与Q-Learning

  - on policy与off policy

- DQN、Double DQN、Dueling DQN
- 经验池回放机制（优先队列）
- Policy Gradient方法：REINFORCE、Actor Critic框架

## 致谢

[https://github.com/laddie132/NLP-Interview#致谢](https://github.com/laddie132/NLP-Interview#%E8%87%B4%E8%B0%A2)

- 机器学习500问：[https://github.com/scutan90/DeepLearning-500-questions](https://github.com/scutan90/DeepLearning-500-questions)
- AI算法岗求职攻略：[https://github.com/amusi/AI-Job-Notes](https://github.com/amusi/AI-Job-Notes)
- 深度学习面试宝典：[https://github.com/amusi/Deep-Learning-Interview-Book](https://github.com/amusi/Deep-Learning-Interview-Book)
- 算法工程师面试：[https://github.com/PPshrimpGo/AIinterview](https://github.com/PPshrimpGo/AIinterview)

