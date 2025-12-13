# Linear

"Linear" 表示神经网络的线性层，也称为`全连接层`或`密集层`。它接收输入并应用线性变换，将每个输入与对应的权重相乘并求和，然后加上偏置。该层没有激活函数。线性层常用于将输入数据映射到下一层的特征空间。

> 只包含线性运算，没有非线性激活函数

```python
# 以下是使用PyTorch库的示例代码：
import torch
import torch.nn as nn
# 定义线性层
linear_layer = nn.Linear(in_features=10, out_features=5)
# 创建输入
input_data = torch.randn(1, 10)  # 假设输入维度为10
# 应用线性变换
output = linear_layer(input_data)
print(output)
```

# FC 全连接

FC（全连接）： `FC` 表示全连接层，与 `Linear` 的含义相同。在神经网络中，全连接层是指每个神经元都与上一层的所有神经元相连接。每个连接都有一个权重，用于线性变换。

# FFN MLP

`FFN` 和 `MLP` 表示前馈神经网络和多层感知机，它们在概念上是相同的。前馈神经网络是一种最常见的神经网络结构，由多个全连接层组成，层与层之间是前向传播的。多层感知机是一种前馈神经网络的具体实现，其中至少有一个隐藏层。

```python
import torch
import torch.nn as nn

# 创建前馈神经网络模型
class FFN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(FFN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        return out

# 创建输入数据
input_data = torch.randn(1, 10)  # 假设输入维度为10

# 定义模型参数
input_size = 10
hidden_size = 64
output_size = 1

# 创建前馈神经网络模型实例
model = FFN(input_size, hidden_size, output_size)

# 前向传播
output = model(input_data)
print(output)
```

# 神经网络中的logits

在深度学习中，**Logits** 指的是神经网络最后一层（通常是全连接层）的**原始输出值**，它们尚未经过归一化处理，因此不具备概率意义。这些值可以是任意实数（正、负或极大/极小），代表模型对各类别的“倾向性”或“证据强度”。



##### **Logits 与概率的区别**

1. **Logits（未归一化）**：

   - 取值范围：任意实数。
   - 无概率意义。
   - 仅表示模型对某类别的“倾向性”。

2. **Softmax 输出（归一化后）**：

   - 取值范围：[0, 1]。
   - 满足概率分布的性质，所有值之和为 1。
   - 每个值表示模型预测该类别的概率。
