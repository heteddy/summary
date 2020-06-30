[ TOC ]

# 什么时候使用
用于系统的物理解耦和逻辑解耦
## 场景
+ 削峰填谷
+ 数据驱动的任务依赖
+ 多个接收方，上游不关心多下游执行结果
+ upsteam 关注结果但时间很长

# 消息队列的推送
+ 推送 push
    * 优点
       - 实时性好
       - 中间件服务器做负载均衡
    * 缺点
       - 需要确认收到
+ 拉取 pull
  * 优点
    - 可以拉取多条
    - 服务端逻辑少
  * 缺点:
    1. 可能导致消息堆积
    1. 消费端主动轮训
    
# rabbitmq的push和pull
* 拉
这种方式Api比较简单，但是需要自己控制拉取节奏，
``` go
func (ch *Channel) Get(queue string, autoAck bool) (msg Delivery, ok bool, err error)
```
> Get synchronously receives a single Delivery from the head of a queue from the server to the client. In almost all cases, using Channel.Consume will be preferred.

> If there was a delivery waiting on the queue and that delivery was received, the second return value will be true. If there was no delivery waiting or an error occurred, the ok bool will be false.
* 推
``` go
func (ch *Channel) Consume(queue, consumer string, autoAck, exclusive, noLocal, noWait bool, args Table) (<-chan Delivery, error)
```
```go
c.deliveryChan, err = c.channel.Consume(c.queueName,
		c.tag,
		false,
		false,
		false,
		false,
		nil)
	if err != nil {
		c.RabbitMQClient.Close()
		return err
	}
	
	// important: 在一个goroutine中同时对msgs和notifyClose两个channel进行读取可能会导致死锁。
	// 因为msgs被关闭就会结束相应的goroutine，
	// 此时notifyClose因为没有接收者，而在amqp.channel关闭的过程中出现死锁。
	go c.handle(c.deliveryChan) //另外启动一个携程处理任务
```
# 消息不重复消费
在消息中添加唯一的消息ID；同时确保消息的幂等性；

# 消息不丢
消息发送的时候Producer要收到rabbitmq的Confirm消息；消费端收到消息后应该给rabbitmq发送ACK；

# 保证送达
1. 在保证消息不丢的前提下，在发送到rabbitmq之后写入数据库，当消息被consumer处理之后更新数据库中的状态；
1. 启动一个异步认为定时检查数据库中的任务，如果状态没有被更新就取出来重新发送到消息队列；
1. 在保证消息幂等性的前提下，可以保证消息被送达

# 消息顺序性
消息中只有一个接收者的情况下，可以保证消息的顺序消费

# 消息队列的延时以及过期失效问题
延时队列可以通过以下2种方式实现：
1. 死信队列
   * 死信产生：
      - 消息被拒绝(basic.reject / basic.nack)，并且requeue = false
      - 消息TTL过期
      - 队列达到最大长度

    * 死信说明
           DLX也是一个正常的Exchange，和一般的Exchange没有区别，它能在任                      何的队列上被指定，实际上就是设置某个队列的属性。当这个队列中有死信时，RabbitMQ就会自动的将这个消息重新发布到设置的Exchange上去，进而被路由到另一个队列。可以监听这个队列中的消息做相应的处理。

     * 延时消息
        基于上面的说明，发送一条消息到一个没有consumer的exchange 并设置ttl的过期时间为我们需要延时的时间比如30(秒),当ttl过期之后就会根据私信dlx.exchange路由到指定的queue中；然后再死信队列中的consumer复制消费这个消息

2. 使用插件 delayed_exchange
[rabbitmq-delayed-message-exchange](https://github.com/rabbitmq/rabbitmq-delayed-message-exchange)
    创建exchange的时候需要按照下图所示指定类型
    ``` go
    arg := make(map[string]interface{})
    arg["x-delayed-type"] = "topic"
	ex := mq.Exchange{
		Name: "delay-task2",
		Kind: "x-delayed-message",
		Args: arg,
	}
    ```
    发送message的时候指定消息的delay的时间
   ``` go
    table := make(map[string]interface{})
    table["x-delay"] = 3000  // 指定delay 3s
    err := p.Publish(ctx, d, "delay.order.abc", table);
   ```
  # 限流
  ``` go 
    // 限定prefetch count  prefetch_size, global
    //Qos controls how many messages or how many bytes the server will try to keep on the network for consumers before receiving delivery acks. The intent of Qos is to make sure the network buffers stay full between the server and client.
    if err := c.channel.Qos(1, 0, false); err != nil {
	}
c.deliveryChan, err = c.channel.Consume(c.queueName,
		c.tag,
		false, // 关闭auto ack
		false,
		false,
		false,
		nil)
	if err != nil {
		c.RabbitMQClient.Close()
		return err
	}
  ```
# 断线重连
单独启动一个协程，执行下面的操作
``` go
func (c *RabbitMQConsumer) reconnect() error {
	// 重新连接成功之后，重新执行consume；

	for {
		// 是否发生错误
		select {
		case err := <-c.connNotify:
			if err != nil {
				log.Println("rabbitmq consumer - connection NotifyClose: ", err)
			}
		case err := <-c.channelNotify:
			if err != nil {
				log.Println("rabbitmq consumer - channel NotifyClose: ", err)
			}
		case <-c.quit:
			return nil
		}
		// 连接未关闭
		if !c.conn.IsClosed() {
			var errConn, errChannel *amqp.Error
			for errChannel = range c.channelNotify {
				log.Println(errChannel)
			}
			for errConn = range c.connNotify {
				log.Println(errConn)
			}

			// 关闭 SubMsg common delivery
			if err := c.channel.Cancel(c.tag, true); err != nil {
				log.Println("rabbitmq consumer - channel cancel failed: ", err)
			}
			if err := c.channel.Close(); err != nil {

			}
			if err := c.conn.Close(); err != nil {
				log.Println("rabbitmq consumer - connection close failed: ", err)
			}
		} else {
			log.Println("conn is closed")
		}
		// IMPORTANT: 必须清空 Notify，否则死连接不会释放 如果还有error一起读完否则连接不能释放

	retry:
		for {
			select {
			case <-c.quit:
				return nil
			default:
				log.Println("rabbitmq consumer - reconnect")
				// 第二次重新连接
				if err := c.Init(); err != nil {
					// 等待；然后重试
					time.Sleep(time.Second * 10)
					log.Println("loop again continue")
					continue
				}
				break retry
			}
		}
	}
}
```
# 高可用
1. 主备
只有主节点提供读写；备用节点只是在主节点挂掉的情况下服务；并发量并不大的情况可以使用haproxy做主备；

2. 镜像模式
mirror镜像队列；保证rabbitmq数据的高可靠性，实现数据同步2-3个节点的数据同步；前端需要自己做负载均衡
![image.png](https://upload-images.jianshu.io/upload_images/9243349-0bfbcf47ea499145.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)
3. Federation
在broker之间传输消息的插件
[https://github.com/rabbitmq/rabbitmq-federation](https://github.com/rabbitmq/rabbitmq-federation)



![image.png](https://upload-images.jianshu.io/upload_images/9243349-172944eaf7da4d54.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)
如上图所示，Federation Exchanges,可以看成Downstream从Upstream主动拉取消息，但并不是拉取所有消息，必须是在Downstream上已经明确定义Bindings关系的Exchange，也就是有实际的物理Queue来接收消息，才会从Upstream拉取消息到Downstream。使用AMQP协议实施代理间通信，Downstream会将绑定关系组合在一起，绑定/解绑命令将会发送到Upstream交换机。因此，FederationExchange只接收具有订阅的消息。

# rabbitmq 思维导图
![rabbit mq.png](https://upload-images.jianshu.io/upload_images/9243349-047f75cafd6342c3.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)