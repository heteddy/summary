# snowflake id

![snowflake](http://www.jiangxinlingdu.com/assets/images/2018/7849276-4d1955394baa3c6d.png)

UidGenerator是Java实现的, 基于[Snowflake](https://github.com/twitter/snowflake)算法的唯一ID生成器。UidGenerator以组件形式工作在应用项目中, 支持自定义workerId位数和初始化策略, 从而适用于[docker](https://www.docker.com/)等虚拟化环境下实例自动重启、漂移等场景。 在实现上, UidGenerator通过借用未来时间来解决sequence天然存在的并发限制; 采用RingBuffer来缓存已生成的UID, 并行化UID的生产和消费, 同时对CacheLine补齐，避免了由RingBuffer带来的硬件级「伪共享」问题. 最终单机QPS可达600万。

依赖版本：[Java8](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)及以上版本, [MySQL](https://dev.mysql.com/downloads/mysql/)(内置WorkerID分配器, 启动阶段通过DB进行分配; 如自定义实现, 则DB非必选依赖）

## Snowflake算法

[![Snowflake](https://github.com/baidu/uid-generator/raw/master/doc/snowflake.png)](https://github.com/baidu/uid-generator/blob/master/doc/snowflake.png)
Snowflake算法描述：指定机器 & 同一时刻 & 某一并发序列，是唯一的。据此可生成一个64 bits的唯一ID（long）。默认采用上图字节分配方式：

- sign(1bit)
  固定1bit符号标识，即生成的UID为正数。
- delta seconds (28 bits)
  当前时间，相对于时间基点"2016-05-20"的增量值，单位：秒，最多可支持约8.7年
- worker id (22 bits)
  机器id，最多可支持约420w次机器启动。内置实现为在启动时由数据库分配，默认分配策略为用后即弃，后续可提供复用策略。
- sequence (13 bits)
  每秒下的并发序列，13 bits可支持每秒8192个并发。

**以上参数均可通过Spring进行自定义**

## CachedUidGenerator

RingBuffer环形数组，数组每个元素成为一个slot。RingBuffer容量，默认为Snowflake算法中sequence最大值，且为2^N。可通过`boostPower`配置进行扩容，以提高RingBuffer 读写吞吐量。

Tail指针、Cursor指针用于环形数组上读写slot：

- Tail指针
  表示Producer生产的最大序号(此序号从0开始，持续递增)。Tail不能超过Cursor，即生产者不能覆盖未消费的slot。当Tail已赶上curosr，此时可通过`rejectedPutBufferHandler`指定PutRejectPolicy
- Cursor指针
  表示Consumer消费到的最小序号(序号序列与Producer序列相同)。Cursor不能超过Tail，即不能消费未生产的slot。当Cursor已赶上tail，此时可通过`rejectedTakeBufferHandler`指定TakeRejectPolicy

[![RingBuffer](https://github.com/baidu/uid-generator/raw/master/doc/ringbuffer.png)](https://github.com/baidu/uid-generator/blob/master/doc/ringbuffer.png)

CachedUidGenerator采用了双RingBuffer，Uid-RingBuffer用于存储Uid、Flag-RingBuffer用于存储Uid状态(是否可填充、是否可消费)

由于数组元素在内存中是连续分配的，可最大程度利用CPU cache以提升性能。但同时会带来「伪共享」FalseSharing问题，为此在Tail、Cursor指针、Flag-RingBuffer中采用了CacheLine 补齐方式。

[![FalseSharing](https://github.com/baidu/uid-generator/raw/master/doc/cacheline_padding.png)](https://github.com/baidu/uid-generator/blob/master/doc/cacheline_padding.png)

## RingBuffer填充时机

- 初始化预填充
  RingBuffer初始化时，预先填充满整个RingBuffer.
- 即时填充
  Take消费时，即时检查剩余可用slot量(`tail` - `cursor`)，如小于设定阈值，则补全空闲slots。阈值可通过`paddingFactor`来进行配置，请参考Quick Start中CachedUidGenerator配置
- 周期填充
  通过Schedule线程，定时补全空闲slots。可通过`scheduleInterval`配置，以应用定时填充功能，并指定Schedule时间间隔

![百度UID](http://www.jiangxinlingdu.com/assets/images/2018/7849276-35ba996d3f17ca43.png)

