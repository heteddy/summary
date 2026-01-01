https://www.cnblogs.com/xiao987334176/p/9930517.html

https://www.cnblogs.com/guoxiangyue/p/11772717.html

# 安装

```
docker pull prom/node-exporter
docker pull prom/prometheus
docker pull grafana/grafana
```

## 启动node-exporter

```shell
docker run -d -p 9100:9100 \
  -v "/proc:/host/proc:ro" \
  -v "/sys:/host/sys:ro" \
  -v "/:/rootfs:ro" \
  --net="host" \
  --restart=on-failure:5 \
  prom/node-exporter
```

```shell
root@ubuntu:~# netstat -anpt
Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1147/sshd       
tcp        0     36 192.168.200.151:22       192.168.91.1:63648      ESTABLISHED 2969/0          
tcp        0      0 192.168.200.151:22       192.168.91.1:63340      ESTABLISHED 1321/1          
tcp6       0      0 :::9100                 :::*                    LISTEN      3070/node_exporter
```

```shell
http://192.168.200.151:9100/metrics
```

## 启动prometheus

```
mkdir /data/prometheus
cd /data/prometheus/
vim prometheus.yml
```

```yml
global:
  scrape_interval:     60s
  evaluation_interval: 60s
 
scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']
        labels:
          instance: prometheus
 
  - job_name: linux
    static_configs:
      - targets: ['192.168.200.151:9100'] # 本机地址
        labels:
          instance: localhost
```

```shell
docker run  -d \
  -p 9090:9090 \
  -v /data/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml  \
  --restart=always \
  prom/prometheus
```

```shell
root@ubuntu:/opt/prometheus# netstat -anpt
Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1147/sshd       
tcp        0     36 192.168.200.151:22       192.168.91.1:63648      ESTABLISHED 2969/0          
tcp        0      0 192.168.200.151:22       192.168.91.1:63340      ESTABLISHED 1321/1          
tcp6       0      0 :::9100                 :::*                    LISTEN      3070/node_exporter
tcp6       0      0 :::22                   :::*                    LISTEN      1147/sshd       
tcp6       0      0 :::9090                 :::*                    LISTEN      3336/docker-proxy
```

访问url：

```
http://192.168.200.151:9090/graph
```

```
http://192.168.200.151:9090/targets
```

## 启动grafana

```
mkdir /data/grafana-storage
```

```
chmod 777 -R /data/grafana-storage
```

```shell
docker run -d \
  -p 3000:3000 \
  --name=grafana \
  -v /data/grafana-storage:/var/lib/grafana \
  --restart=always \
  grafana/grafana
```

```shell
root@ubuntu:/opt/prometheus# netstat -anpt
Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      1147/sshd       
tcp        0     36 192.168.200.151:22       192.168.91.1:63648      ESTABLISHED 2969/0          
tcp        0      0 192.168.200.151:22       192.168.91.1:63340      ESTABLISHED 1321/1          
tcp6       0      0 :::9100                 :::*                    LISTEN      3070/node_exporter
tcp6       0      0 :::22                   :::*                    LISTEN      1147/sshd       
tcp6       0      0 :::3000                 :::*                    LISTEN      3494/docker-proxy
tcp6       0      0 :::9090                 :::*                    LISTEN      3336/docker-proxy
tcp6       0      0 192.168.200.151:9100     172.17.0.2:55108        ESTABLISHED 3070/node_exporter
```

```
http://192.168.200.151:3000/
```

# Prometheus Metrics Type 简介

Prometheus Metrics 是整个监控系统的核心，所有的监控指标数据都由其记录。Prometheus 中，所有 Metrics 皆为时序数据，并以名字作区分，即每个指标收集到的样本数据包含至少三个维度的信息：名字、时刻和数值。

而 Prometheus Metrics 有四种基本的 type：

- Counter：只增不减的单变量
- Gauge：可增可减的单变量
- Histogram：多桶统计的多变量
- Summary：聚合统计的多变量


此外，Prometheus Metrics 中有一种将样本数据以标签（Label）为维度作切分的数据类型，称为向量（Vector）。四种基本类型也都有其 Vector 类型：

- CounterVec
- GaugeVec
- HistogramVec
- SummaryVec

Vector 相当于一组同名同类型的 Metrics，以 Label 做区分。Label 可以有多个，Prometheus 实际会为每个 Label 组合创建一个 Metric。Vector 类型记录数据时需先打 Label 才能调用 Metrics 的方法记录数据。

如对于 HTTP 请求延迟这一指标，由于 HTTP 请求可在多个地域的服务器处理，且具有不同的方法，于是，可定义名为 http_request_latency_seconds 的 SummaryVec，标签有region和method，以此表示不同地域服务器的不同请求方法的请求延迟。

以下将对每个类型做详细的介绍。

#### Counter

定义：是单调递增的计数器，重启时重置为0，其余时候只能增加。

方法：

```
type Counter interface {
Metric
Collector

// 自增1
Inc()
// 把给定值加入到计数器中，若值小于 0 会 panic
Add(float64)
} 
```


常测量对象：

- 请求的数量
- 任务完成的数量
- 函数调用次数
- 错误发生次数
- ……



#### Gauge

定义：表示一个可增可减的数字变量，初值为0

方法：

```
type Gauge interface {
Metric
Collector
Set(float64)    // 直接设置成给定值
Inc()   // 自增1
Dec()   // 自减1
Add(float64)     // 增加给定值，可为负
Sub(float64)    // 减少给定值，可为负
// SetToCurrentTime 将 Gauge 设置成当前的 Unix 时间戳
SetToCurrentTime()
} 
```


常测量对象：

- 温度
- 内存用量
- 并发请求数
- ……



#### Histogram

定义：Histogram 会对观测数据取样，然后将观测数据放入有数值上界的桶中，并记录各桶中数据的个数，所有数据的个数和数据数值总和。

方法：

```
type Histogram interface {
Metric
Collector

// Observe 将一个观测到的样本数据加入 Histogram 中，并更新相关信息
Observe(float64)
} 
```


常测量对象：

- 请求时延
- 回复长度
- ……各种有样本数据


具体实现：Histogram 会根据观测的样本生成如下数据：

inf 表无穷值，a1，a2，……是单调递增的数值序列。

- [basename]_count：数据的个数，类型为 counter
- [basename]_sum：数据的加和，类型为 counter
- [basename]_bucket{le=a1}：处于 [-inf,a1] 的数值个数
- [basename]_bucket{le=a2}：处于 [-inf,a2] 的数值个数
- ……
- [basename]_bucket{le=<+inf>}：处于 [-inf,+inf] 的数值个数，Prometheus 默认额外生成，无需用户定义


Histogram 可以计算样本数据的百分位数，其计算原理为：通过找特定的百分位数值在哪个桶中，然后再通过插值得到结果。比如目前有两个桶，分别存储了 [-inf, 1] 和 [-inf, 2] 的数据。然后现在有 20% 的数据在 [-inf, 1] 的桶，100% 的数据在 [-inf, 2] 的桶。那么，50% 分位数就应该在 [1, 2] 的区间中，且处于 (50%-20%) / (100%-20%) = 30% / 80% = 37.5% 的位置处。Prometheus 计算时假设区间中数据是均匀分布，因此直接通过线性插值可以得到 (2-1)*3/8+1 = 1.375。

#### Summary

定义：Summary 与 Histogram 类似，会对观测数据进行取样，得到数据的个数和总和。此外，还会取一个滑动窗口，计算窗口内样本数据的分位数。

方法：

```
type Summary interface {
Metric
Collector

// Observe 将一个观测到的样本数据加入 Summary 中，并更新相关信息
Observe(float64)
} 
```


常测量对象：

- 请求时延
- 回复长度
- ……各种有样本数据


具体实现：Summary 完全是在 client 端聚合数据，每次调用 obeserve 会计算出如下数据：

- [basename]_count：数据的个数，类型为 counter
- [basename]_sum：数据的加和，类型为 counter
- [basename]{quantile=0.5}：滑动窗口内 50% 分位数值
- [basename]{quantile=0.9}：滑动窗口内 90% 分位数值
- [basename]{quantile=0.99}：滑动窗口内 99% 分位数值
- ……


实际分位数值可根据需求制定，且是对每一个 Label 组合做聚合。

#### Histogram 和 Summary 简单对比

可以看出，Histogram 和 Summary 类型测量的对象是比较接近的，但根据其实现方式和其本身的特点，在性能耗费、适用场景等方面具有一定差别，本文总结如下：

[![1.png](http://dockone.io/uploads/article/20200510/2cd8a25e99b946049ce7dd6e3407fcd4.png)](http://dockone.io/uploads/article/20200510/2cd8a25e99b946049ce7dd6e3407fcd4.png)



### 3、Metrics 设计的最佳实践

#### 如何确定需要测量的对象

在具体设计 Metrics 之前，首先需要明确需要测量的对象。需要测量的对象应该依据具体的问题背景、需求和需监控的系统本身来确定。

思路 1：从需求出发

Google 针对大量分布式监控的经验总结出<font color="red">四个监控的黄金指标</font>，这四个指标对于一般性的监控测量对象都具有较好的参考意义。这四个指标分别为：

- <font color="red">延迟：服务请求的时间。</font>
- <font color="red">通讯量：监控当前系统的流量，用于衡量服务的容量需求。</font>
- <font color="red">错误：监控当前系统所有发生的错误请求，衡量当前系统错误发生的速率。</font>
- <font color="red">饱和度：衡量当前服务的饱和度。主要强调最能影响服务状态的受限制的资源。例如，如果系统主要受内存影响，那就主要关注系统的内存状态。</font>



而笔者认为，以上四种指标，其实是为了满足四个监控需求：

- 反映用户体验，衡量系统核心性能。如：在线系统的时延，作业计算系统的作业完成时间等。
- 反映系统的服务量。如：请求数，发出和接收的网络包大小等。
- 帮助发现和定位故障和问题。如：错误计数、调用失败率等。
- 反映系统的饱和度和负载。如：系统占用的内存、作业队列的长度等。


除了以上常规需求，还可根据具体的问题场景，为了排除和发现以前出现过或可能出现的问题，确定相应的测量对象。比如，系统需要经常调用的一个库的接口可能耗时较长，或偶有失败，可制定 Metrics 以测量这个接口的时延和失败数。

思路 2：从需监控的系统出发

另一方面，为了满足相应的需求，不同系统需要观测的测量对象也是不同的。在 官方文档 的最佳实践中，将需要监控的应用分为了三类：

- 线上服务系统（Online-serving systems）：需对请求做即时的响应，请求发起者会等待响应。如 web 服务器。
- 线下计算系统（Offline processing）：请求发起者不会等待响应，请求的作业通常会耗时较长。如批处理计算框架 Spark 等。
- 批处理作业（Batch jobs）：这类应用通常为一次性的，不会一直运行，运行完成后便会结束运行。如数据分析的 MapReduce 作业。


对于每一类应用其通常情况下测量的对象是不太一样的。其总结如下：

- 线上服务系统：主要有请求、出错的数量，请求的时延等。
- 线下计算系统：最后开始处理作业的时间，目前正在处理作业的数量，发出了多少 items， 作业队列的长度等。
- 批处理作业：最后成功执行的时刻，每个主要 stage 的执行时间，总的耗时，处理的记录数量等。


除了系统本身，有时还需监控子系统：

- 使用的库（Libraries）: 调用次数，成功数，出错数，调用的时延。
- 日志（Logging）：计数每一条写入的日志，从而可找到每条日志发生的频率和时间。
- Failures: 错误计数。
- 线程池：排队的请求数，正在使用的线程数，总线程数，耗时，正在处理的任务数等。
- 缓存：请求数，命中数，总时延等。
- ……


最后的测量对象的确定应结合以上两点思路确定。

#### 如何选用 Vector

选用 Vec 的原则：

- 数据类型类似但资源类型、收集地点等不同
- Vec 内数据单位统一


例子：

- 不同资源对象的请求延迟
- 不同地域服务器的请求延迟
- 不同 http 请求错误的计数
- ……


此外，官方文档 中建议，对于一个资源对象的不同操作，如 Read/Write、Send/Receive， 应采用不同的 Metric 去记录，而不要放在一个 Metric 里。原因是监控时一般不会对这两者做聚合，而是分别去观测。

不过对于 request 的测量，通常是以 Label 做区分不同的 action。

#### 如何确定 Label

根据上文，常见 Label 的选择有：

- resource
- region
- type
- ……


确定 Label 的一个重要原则是：同一维度 Label 的数据是可平均和可加和的，也即单位要统一。如风扇的风速和电压就不能放在一个 Label 里。

此外，不建议下列做法：

```
my_metric{label=a} 1
my_metric{label=b} 6
my_metric{label=total} 7
```


即在 Label 中同时统计了分和总的数据，建议采用 PromQL 在服务器端聚合得到总和的结果。或者用另外的 Metric 去测量总的数据。

#### 如何命名 Metrics 和 Label

好的命名能够见名知义，因此命名也是良好设计的一环。

Metric 的命名：

- 需要符合 pattern: [a-zA-Z:][a-zA-Z0-9:]*
- 应该包含一个单词作为前缀，表明这个 Metric 所属的域。如：
  - prometheus_notifications_total
  - process_cpu_seconds_total
  - ipamd_request_latency
- 应该包含一个单位的单位作为后缀，表明这个 Metric 的单位。如：
  - http_request_duration_seconds
  - node_memory_usage_bytes
  - http_requests_total (for a unit-less accumulating count)
- 逻辑上与被测量的变量含义相同。
- 尽量使用基本单位，如 seconds，bytes。而不是 Milliseconds, megabytes。


Label 的命名：

依据选择的维度命名，如：

- region: shenzhen/guangzhou/beijing
- owner: user1/user2/user3
- stage: extract/transform/load