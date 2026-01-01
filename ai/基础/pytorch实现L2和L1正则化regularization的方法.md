[https://blog.csdn.net/guyuealian/article/details/88426648](https://blog.csdn.net/guyuealian/article/details/88426648)

1.torch.optim优化器实现L2正则化

torch.optim集成了很多优化器，如SGD，Adadelta，Adam，Adagrad，RMSprop等，这些优化器自带的一个参数weight_decay，用于指定权值衰减率，相当于L2正则化中的λ参数，注意torch.optim集成的优化器只有L2正则化方法，你可以查看注释，参数weight_decay 的解析是：



> weight_decay (float, optional): weight decay (L2 penalty) (default: 0)



 使用torch.optim的优化器，可如下设置L2正则化



    optimizer = optim.Adam(model.parameters(),lr=learning_rate,weight_decay=0.01)

AI写代码

python

运行





但是这种方法存在几个问题，



（1）一般正则化，只是对模型的权重W参数进行惩罚，而偏置参数b是不进行惩罚的，而torch.optim的优化器weight_decay参数指定的权值衰减是对网络中的所有参数，包括权值w和偏置b同时进行惩罚。很多时候如果对b 进行L2正则化将会导致严重的欠拟合，因此这个时候一般只需要对权值w进行正则即可。（PS：这个我真不确定，源码解析是 weight decay (L2 penalty) ，但有些网友说这种方法会对参数偏置b也进行惩罚，可解惑的网友给个明确的答复）



（2）缺点：torch.optim的优化器固定实现L2正则化，不能实现L1正则化。如果需要L1正则化，可如下实现：







（3）根据正则化的公式，加入正则化后，loss会变原来大，比如weight_decay=1的loss为10，那么weight_decay=100时，loss输出应该也提高100倍左右。而采用torch.optim的优化器的方法，如果你依然采用loss_fun= nn.CrossEntropyLoss()进行计算loss，你会发现，不管你怎么改变weight_decay的大小，loss会跟之前没有加正则化的大小差不多。这是因为你的loss_fun损失函数没有把权重W的损失加上。



（4）采用torch.optim的优化器实现正则化的方法，是没问题的！只不过很容易让人产生误解，对鄙人而言，我更喜欢TensorFlow的正则化实现方法，只需要tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)，实现过程几乎跟正则化的公式对应的上。

————————————————

版权声明：本文为CSDN博主「AI吃大瓜」的原创文章，遵循CC 4.0 BY-SA版权协议，转载请附上原文出处链接及本声明。

原文链接：https://blog.csdn.net/guyuealian/article/details/88426648