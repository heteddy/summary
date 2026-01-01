# 传统的位置编码

1. 绝对位置编码
2. 可学习的绝对位置编码



# 传统位置编码的问题

1. 外推性差

   如果模型训练时最⼤序列⻓度是 8192，那么它从未⻅过位置 8193 的编码。当需要处理更⻓

   的序列时，模型表现会急剧下降。

2. 相对位置不直接，需要计算



旋转位置编码提出2021年

> 让向量在复平⾯上旋转，⽤旋转⻆度编码位置，⽤⻆度差编码距离。



<a href=".images/%E6%B7%B1%E5%85%A5%E7%90%86%E8%A7%A3%20RoPE%EF%BC%88Rotary%20Position%20Embedding%EF%BC%89%E6%97%8B%E8%BD%AC%E4%BD%8D%E7%BD%AE%E7%BC%96%E7%A0%81%20-%20%E7%9F%A5%E4%B9%8E.pdf" download data-size="7134995">深入理解 RoPE（Rotary Position Embedding）旋转位置编码 - 知乎.pdf</a>

