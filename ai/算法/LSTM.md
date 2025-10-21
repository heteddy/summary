LSTM 是RNN的升级



# 原理

循环神经网络的展开, 链式传递;

## 解决的问题:

用当前的话语预测未来的话, 用先前的信息预测当前的任务,可以学习先前的信息

- RNN的长期依赖问题，短期记忆可以，长期不行

  - 例如: 我来自中国,我是*** (中国人)

- 避免长期依赖的问题
- 

## LSTM 结构

## LSTM 核心思想

细胞状态，传送带，门选择通过的方法，通过的方法 sigmod层 点乘

有三个门，

1. 遗忘门  ft（sigmod  点乘  向量）  什么样的信息被丢弃 比如 代词
2. 输入门  it sigmod 点乘 向量 tanh
3. 输出门：ot 记忆





BP算法

[误差反向传播](https://zhida.zhihu.com/search?content_id=113813177&content_type=Article&match_order=1&q=%E8%AF%AF%E5%B7%AE%E5%8F%8D%E5%90%91%E4%BC%A0%E6%92%AD&zhida_source=entity)（Back-propagation, BP）算法的出现是神经网络发展的重大突破，也是现在众多深度学习训练方法的基础。该方法会计算神经网络中[损失函数](https://zhida.zhihu.com/search?content_id=113813177&content_type=Article&match_order=1&q=%E6%8D%9F%E5%A4%B1%E5%87%BD%E6%95%B0&zhida_source=entity)对各参数的[梯度](https://zhida.zhihu.com/search?content_id=113813177&content_type=Article&match_order=1&q=%E6%A2%AF%E5%BA%A6&zhida_source=entity)，配合优化方法更新参数，降低损失函数。





问题：

梯度消失

每个cell都有4个全连接层 mlp，计算费时



改进：

peephole lstm

GRU  门控循环单元

