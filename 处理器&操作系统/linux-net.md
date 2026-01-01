

# 网卡接收流程

![1409507-14f988865bf2c794.jpg.png](https://upload-images.jianshu.io/upload_images/9243349-e271410dd1ddbaef.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

网卡设备由net_device定义，驱动程序通过net_device向内核注册网卡的操作函数。网络数据包由网卡驱动封装成`sk_buf`的结构交给内核处理。

网络子设备初始化调用链：`start_kernel`->`rest_init`->`kernel_init`->`kernel_init_freeable`->`do_basic_setup`->`do_initcalls`->`do_initcalls`->`net_dev_init`。

+ softnet_data:

  每个cpu都有一个收包队列

`struct napi_struct` 是内核处理软中断的入口，每个`net_device`都对应一个`napi_struct`，驱动在硬中断中将自己的`napi_struct`挂载到CPU的收包队列`softnet_data`。内核在软中断中轮询该队列，并执行`napi_sturct`中的回调函数`int(*poll)(struct napi_struct *, int);`，在`poll`函数中，驱动将网卡数据转换成`skb_buff`形式，最终发往协议栈。也就是说，协议栈对数据包的处理，使用的是软中断的时间片。如果协议栈处理耗费了过多的CPU时间的化，会直接影响到设备的网络性能。



网络子系统初始化：

```C
static int __init net_dev_init(void)
{
    int i, rc = -ENOMEM;

    BUG_ON(!dev_boot_phase);

    if (dev_proc_init())
        goto out;

    if (netdev_kobject_init())
        goto out;

    INIT_LIST_HEAD(&ptype_all);
    for (i = 0; i < PTYPE_HASH_SIZE; i++)
        INIT_LIST_HEAD(&ptype_base[i]);

    INIT_LIST_HEAD(&offload_base);

    if (register_pernet_subsys(&netdev_net_ops))
        goto out;

    /*
     *  Initialise the packet receive queues.
     */

    for_each_possible_cpu(i) {
        struct work_struct *flush = per_cpu_ptr(&flush_works, i);
      	// 每个CPU初始化了一个softnet_data来挂载需要处理设备的napi_struct
        struct softnet_data *sd = &per_cpu(softnet_data, i);

        INIT_WORK(flush, flush_backlog);

        skb_queue_head_init(&sd->input_pkt_queue);
        skb_queue_head_init(&sd->process_queue);
#ifdef CONFIG_XFRM_OFFLOAD
        skb_queue_head_init(&sd->xfrm_backlog);
#endif
        INIT_LIST_HEAD(&sd->poll_list);
        sd->output_queue_tailp = &sd->output_queue;
#ifdef CONFIG_RPS
        sd->csd.func = rps_trigger_softirq;
        sd->csd.info = sd;
        sd->cpu = i;
#endif

        sd->backlog.poll = process_backlog;
        sd->backlog.weight = weight_p;
    }

    dev_boot_phase = 0;

    /* The loopback device is special if any other network devices
     * is present in a network namespace the loopback device must
     * be present. Since we now dynamically allocate and free the
     * loopback device ensure this invariant is maintained by
     * keeping the loopback device as the first device on the
     * list of network devices.  Ensuring the loopback devices
     * is the first device that appears and the last network device
     * that disappears.
     */
    if (register_pernet_device(&loopback_net_ops))
        goto out;

    if (register_pernet_device(&default_device_ops))
        goto out;
		// 注册软中断
    open_softirq(NET_TX_SOFTIRQ, net_tx_action);
    open_softirq(NET_RX_SOFTIRQ, net_rx_action);

    rc = cpuhp_setup_state_nocalls(CPUHP_NET_DEV_DEAD, "net/dev:dead",
                       NULL, dev_cpu_dead);
    WARN_ON(rc < 0);
    rc = 0;
out:
    return rc;
}
```

网络子系统初始化的时候，

 1. <font color=red size=3> 为每个cpu初始化一个softnet_data</font>
    `struct softnet_data *sd = &per_cpu(softnet_data, i);`

 2. 注册2个软中断：

    ` open_softirq(NET_TX_SOFTIRQ, net_tx_action);`  `open_softirq(NET_RX_SOFTIRQ, net_rx_action);`

`net_dev_init`执行完后，我们内核就有了处理数据包的能力，只要驱动能向`softnet_data`挂载需要收包设备的`napi_struct`。内核子线程`ksoftirqd`便会做后续的处理。接下来就是网卡驱动的初始化了。

网卡初始化：

```c
static struct pci_driver e1000_driver = {
    .name     = e1000_driver_name,
    .id_table = e1000_pci_tbl,
    .probe    = e1000_probe, //内核探测回调函数
    .remove   = e1000_remove,
#ifdef CONFIG_PM
    /* Power Management Hooks */
    .suspend  = e1000_suspend,
    .resume   = e1000_resume,
#endif
    .shutdown = e1000_shutdown,
    .err_handler = &e1000_err_handler
};
```

​		最关键的内核探测回调函数`e1000_probe`，算是网卡设备的初始化函数。<font color=#ff1111 size=3>每个网络设备都对应一个`net_dev`</font>,

```rust

static int e1000_probe(struct pci_dev *pdev, const struct pci_device_id *ent)
{
    struct net_device *netdev; //每个网络设备对应一个net_device
    netdev = alloc_etherdev(sizeof(struct e1000_adapter));//申请net_device设备
    netdev->netdev_ops = &e1000_netdev_ops; //注册操作设备的回调函数
    e1000_set_ethtool_ops(netdev);
    netdev->watchdog_timeo = 5 * HZ;
  	// e1000_clean为软中断调用的函数
    netif_napi_add(netdev, &adapter->napi, e1000_clean, 64);//软中断里会调用poll钩子函数
    strncpy(netdev->name, pci_name(pdev), sizeof(netdev->name) - 1);
    err = register_netdev(netdev);
}
```

硬件中断

```C
/**
 * e1000_intr - Interrupt Handler
 * @irq: interrupt number
 * @data: pointer to a network interface device structure
 **/
static irqreturn_t e1000_intr(int irq, void *data)
{
    struct net_device *netdev = data;
    struct e1000_adapter *adapter = netdev_priv(netdev);
    struct e1000_hw *hw = &adapter->hw;
    u32 icr = er32(ICR);

    /* disable interrupts, without the synchronize_irq bit */
    ew32(IMC, ~0);
    E1000_WRITE_FLUSH();
		// 调用napi_schedule_prep(&adapter->napi)
    if (likely(napi_schedule_prep(&adapter->napi))) {
        adapter->total_tx_bytes = 0;
        adapter->total_tx_packets = 0;
        adapter->total_rx_bytes = 0;
        adapter->total_rx_packets = 0;
        __napi_schedule(&adapter->napi);
    } else {
        /* this really should not happen! if it does it is basically a
         * bug, but not a hard error, so enable ints and continue
         */
        if (!test_bit(__E1000_DOWN, &adapter->flags))
            e1000_irq_enable(adapter);
    }

    return IRQ_HANDLED;
}
```

测试网卡设备的`napi`是否正在被CPU使用。没有就调用`__napi_schedule`将自己的`napi`挂载到CPU的`softnet_data`上。这样软中断的内核线程就能轮询到这个软中断。

```c
/**
 * __napi_schedule - schedule for receive
 * @n: entry to schedule
 *
 * The entry's receive function will be scheduled to run.
 * Consider using __napi_schedule_irqoff() if hard irqs are masked.
 */
void __napi_schedule(struct napi_struct *n)
{
    unsigned long flags;
		// 保存中断
    local_irq_save(flags);
    // 把当前设备的napi挂载到poll list中
    ____napi_schedule(this_cpu_ptr(&softnet_data), n);
    local_irq_restore(flags);
}

/* Called with irq disabled */
static inline void ____napi_schedule(struct softnet_data *sd,
                     struct napi_struct *napi)
{
    list_add_tail(&napi->poll_list, &sd->poll_list);
    //触发软中断
    __raise_softirq_irqoff(NET_RX_SOFTIRQ); //设置软中断标志位NET_RX_SOFTIRQ
}
```

软中断处理：

```c
static void net_rx_action(struct softirq_action *h)
{
	struct softnet_data *sd = &__get_cpu_var(softnet_data);
	unsigned long time_limit = jiffies + 2;
	int budget = netdev_budget;
	void *have;

	local_irq_disable();
	// 循环poll 列表
	while (!list_empty(&sd->poll_list)) {
		struct napi_struct *n;
		int work, weight;

		/* If softirq window is exhuasted then punt.
		 * Allow this to run for 2 jiffies since which will allow
		 * an average latency of 1.5/HZ.
		 */
		if (unlikely(budget <= 0 || time_after_eq(jiffies, time_limit)))
			goto softnet_break;

		local_irq_enable();

		/* Even though interrupts have been re-enabled, this
		 * access is safe because interrupts can only add new
		 * entries to the tail of this list, and only ->poll()
		 * calls can remove this head entry from the list.
		 */
		n = list_first_entry(&sd->poll_list, struct napi_struct, poll_list);

		have = netpoll_poll_lock(n);

		weight = n->weight;

		/* This NAPI_STATE_SCHED test is for avoiding a race
		 * with netpoll's poll_napi().  Only the entity which
		 * obtains the lock and sees NAPI_STATE_SCHED set will
		 * actually make the ->poll() call.  Therefore we avoid
		 * accidentally calling ->poll() when NAPI is not scheduled.
		 */
		work = 0;
		if (test_bit(NAPI_STATE_SCHED, &n->state)) {
      // 在这回调驱动的poll函数，这个函数在napi中，调用我们驱动初始化时注册的poll函数
      // 在e1000网卡中就是e1000_clean函数。
			work = n->poll(n, weight);
			trace_napi_poll(n);
		}

		WARN_ON_ONCE(work > weight);

		budget -= work;

		local_irq_disable();

		/* Drivers must not modify the NAPI state if they
		 * consume the entire weight.  In such cases this code
		 * still "owns" the NAPI instance and therefore can
		 * move the instance around on the list at-will.
		 */
		if (unlikely(work == weight)) {
			if (unlikely(napi_disable_pending(n))) {
				local_irq_enable();
				napi_complete(n);
				local_irq_disable();
			} else {
				if (n->gro_list) {
					/* flush too old packets
					 * If HZ < 1000, flush all packets.
					 */
					local_irq_enable();
					napi_gro_flush(n, HZ >= 1000);
					local_irq_disable();
				}
				list_move_tail(&n->poll_list, &sd->poll_list);
			}
		}

		netpoll_poll_unlock(have);
	}
out:
	net_rps_action_and_irq_enable(sd);

#ifdef CONFIG_NET_DMA
	/*
	 * There may not be any more sk_buffs coming right now, so push
	 * any pending DMA copies to hardware
	 */
	dma_issue_pending_all();
#endif

	return;

softnet_break:
	sd->time_squeeze++;
	__raise_softirq_irqoff(NET_RX_SOFTIRQ);
	goto out;
}
```

处理poll函数 `/drivers/net/ethernet/intel/e1000`

```c
/**
 * e1000_clean - NAPI Rx polling callback
 * @adapter: board private structure
 **/
static int e1000_clean(struct napi_struct *napi, int budget)
{
    struct e1000_adapter *adapter = container_of(napi, struct e1000_adapter,
                             napi);
    int tx_clean_complete = 0, work_done = 0;
    tx_clean_complete = e1000_clean_tx_irq(adapter, &adapter->tx_ring[0]);
		//将数据发给协议栈来处理。
    adapter->clean_rx(adapter, &adapter->rx_ring[0], &work_done, budget);
    if (!tx_clean_complete)
        work_done = budget;
    /* If budget not fully consumed, exit the polling mode */
    if (work_done < budget) {
        if (likely(adapter->itr_setting & 3))
            e1000_set_itr(adapter);
        napi_complete_done(napi, work_done);
        if (!test_bit(__E1000_DOWN, &adapter->flags))
            e1000_irq_enable(adapter);
    }
    return work_done;
}
```

```c
/**
 * e1000_clean_jumbo_rx_irq - Send received data up the network stack; legacy
 * @adapter: board private structure
 * @rx_ring: ring to clean
 * @work_done: amount of napi work completed this call
 * @work_to_do: max amount of work allowed for this call to do
 *
 * the return value indicates whether actual cleaning was done, there
 * is no guarantee that everything was cleaned
 */
// 发送收到的数据给内核网络协议栈
static bool e1000_clean_jumbo_rx_irq(struct e1000_adapter *adapter,
				     struct e1000_rx_ring *rx_ring,
				     int *work_done, int work_to_do)
```

这个函数太长，我就保留了`e1000_receive_skb`函数的调用，它调用了`napi_gro_receive`，这个函数同样是NAPI提供的函数，我们的`skb`从这里调用到`netif_receive_skb`协议栈的入口函数。调用路径是`napi_gro_receive`->`napi_frags_finish`->`netif_receive_skb_internal`->`__netif_receive_skb`。

`napi_gro_receive`:驱动通过`poll`注册，内核调用的函数。通过这函数的的调用，`skb`将会传给协议栈的入口函数`__netif_receive_skb`。`dev_gro_receive`函数用于对数据包的合并，他将合并`napi_struct.gro_list`链表上的`skb`

```c
gro_result_t napi_gro_receive(struct napi_struct *napi, struct sk_buff *skb)
{
    skb_mark_napi_id(skb, napi);
    trace_napi_gro_receive_entry(skb);

    skb_gro_reset_offset(skb);

    return napi_skb_finish(dev_gro_receive(napi, skb), skb);
}
```

<font color=red size=4> `IRQ`->`__napi_schedule`->`进入软中断`->`net_rx_action`->`napi_poll`->`驱动注册的poll`->`napi_gro_receive`。</font>

![linux-net.png](https://upload-images.jianshu.io/upload_images/9243349-accd24acba2d8139.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)



1. 网络子系统初始化，softnet_data 挂载到cpu
2. 网卡初始化 driver->netdevice->napi_struct 定义poll函数，就是软中断处理函数
3. 第一次收到数据触发软中断创建nap_struct放入softnet_data, 然后cpu napi_gro_receive



内核接收流程：

![](https://img-blog.csdn.net/20130826185002859?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvcnVzc2VsbF90YW8=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

# 网卡发送流程



## 内核发送流程

![](https://img-blog.csdn.net/20130718162926640?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvcnVzc2VsbF90YW8=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

# accept 等系统调用





# 网卡ring buf详解

## 网卡处理数据包流程

网卡处理网络数据流程图：

![img](https://oscimg.oschina.net/oscnet/57a1a21610c26615bf2508835615e5636b7.png)

图片来自参考链接1

上图中虚线步骤的解释：

1. DMA 将 NIC 接收的数据包逐个写入 sk_buff ，一个数据包可能占用多个 sk_buff , sk_buff 读写顺序遵循FIFO（先入先出）原则。
2. DMA 读完数据之后，NIC 会通过 NIC Interrupt Handler 触发 IRQ （中断请求）。
3. NIC driver 注册 poll 函数。
4. poll 函数对数据进行检查，例如将几个 sk_buff 合并，因为可能同一个数据可能被分散放在多个 sk_buff 中。
5. poll 函数将 sk_buff 交付上层网络栈处理。

完整流程：

1. 系统启动时 NIC (network interface card) 进行初始化，系统分配内存空间给 Ring Buffer 。
2. 初始状态下，Ring Buffer 队列每个槽中存放的 Packet Descriptor 指向 sk_buff ，状态均为 ready。
3. DMA 将 NIC 接收的数据包逐个写入 sk_buff ，一个数据包可能占用多个 sk_buff ，sk_buff 读写顺序遵循FIFO（先入先出）原则。
4. 被写入数据的 sk_buff 变为 used 状态。
5. DMA 读完数据之后，NIC 会通过 NIC Interrupt Handler 触发 IRQ （中断请求）。
6. NIC driver 注册 poll 函数。
7. poll 函数对数据进行检查，例如将几个 sk_buff 合并，因为可能同一个数据可能被分散放在多个 sk_buff 中。
8. poll 函数将 sk_buff 交付上层网络栈处理。
9. poll 函数清理 sk_buff，清理 Ring Buffer 上的 Descriptor 将其指向新分配的 sk_buff 并将状态设置为 ready。

## 多 CPU 下的 Ring Buffer 处理

因为分配给 Ring Buffer 的空间是有限的，当收到的数据包速率大于单个 CPU 处理速度的时候 Ring Buffer 可能被占满，占满之后再来的新数据包会被自动丢弃。

如果在多核 CPU 的服务器上，网卡内部会有多个 Ring Buffer，NIC 负责将传进来的数据分配给不同的 Ring Buffer，同时触发的 IRQ 也可以分配到多个 CPU 上，这样存在多个 Ring Buffer 的情况下 Ring Buffer 缓存的数据也同时被多个 CPU 处理，就能提高数据的并行处理能力。

当然，要实现“NIC 负责将传进来的数据分配给不同的 Ring Buffer”，NIC 网卡必须支持 Receive Side Scaling(RSS) 或者叫做 multiqueue 的功能。RSS 除了会影响到 NIC 将 IRQ 发到哪个 CPU 之外，不会影响别的逻辑了。数据处理过程跟之前描述的是一样的。

## Ring Buffer 相关命令

在生产实践中，因 Ring Buffer 写满导致丢包的情况很多。当环境中的业务流量过大且出现网卡丢包的时候，考虑到 Ring Buffer 写满是一个很好的思路。

总结下 Ring Buffer 相关的命令：

###  网卡收到的数据包统计

```
[root@server-20.140.beishu.polex.io ~ ]$ ethtool -S em1 | more
NIC statistics:
     rx_packets: 35874336743
     tx_packets: 35163830212
     rx_bytes: 6337524253985
     tx_bytes: 3686383656436
     rx_broadcast: 15392577
     tx_broadcast: 873436
     rx_multicast: 45849160
     tx_multicast: 1784024
```

RX 就是收到数据，TX 是发出数据。



### 带有 drop 字样的统计和 fifo_errors 的统计

```shell
[root@server-20.140.beishu.polex.io ~ ]$ ethtool -S em1 | grep -iE "error|drop"
rx_crc_errors: 0
rx_missed_errors: 0
tx_aborted_errors: 0
tx_carrier_errors: 0
tx_window_errors: 0
rx_long_length_errors: 0
rx_short_length_errors: 0
rx_align_errors: 0
dropped_smbus: 0
rx_errors: 0
tx_errors: 0
tx_dropped: 0
rx_length_errors: 0
rx_over_errors: 0
rx_frame_errors: 0
rx_fifo_errors: 79270
tx_fifo_errors: 0
tx_heartbeat_errors: 0
rx_queue_0_drops: 16669
rx_queue_1_drops: 21522
rx_queue_2_drops: 0
rx_queue_3_drops: 5678
rx_queue_4_drops: 5730
rx_queue_5_drops: 14011
rx_queue_6_drops: 15240
rx_queue_7_drops: 420
```

发送队列和接收队列 drop 的数据包数量显示在这里。并且所有 queue_drops 加起来等于 rx_fifo_errors。所以总体上能**通过 rx_fifo_errors 看到 Ring Buffer 上是否有丢包**。如果有的话一方面是看是否需要调整一下每个队列数据的分配，或者是否要加大 Ring Buffer 的大小。

### 查询 Ring Buffer 大小

[root@server-20.140.beishu.polex.io ~ ]$ ethtool -g em1
Ring parameters for em1:
Pre-set maximums:
RX: 4096
RX Mini: 0
RX Jumbo: 0
TX: 4096
Current hardware settings:
RX: 256
RX Mini: 0
RX Jumbo: 0
TX: 256

RX 和 TX 最大是 4096，当前值为 256 。队列越大丢包的可能越小，但数据延迟会增加。

### 调整 Ring Buffer 队列数量

```
[root@server-20.140.beishu.polex.io ~ ]$ ethtool -l em1
Channel parameters for em1:
Pre-set maximums:
RX:        0
TX:        0
Other:        1
Combined:    8
Current hardware settings:
RX:        0
TX:        0
Other:        1
Combined:    8
```

Combined = 8，说明当前 NIC 网卡会使用 8 个进程处理网络数据。

更改 eth0 网卡 Combined 的值：

```
ethtool -L eth0 combined 8
```

需要注意的是，ethtool 的设置操作可能都要重启一下才能生效。

### 调整 Ring Buffer 队列大小

查看当前 Ring Buffer 大小：

```
[root@server-20.140.beishu.polex.io ~ ]$ ethtool -g em1
Ring parameters for em1:
Pre-set maximums:
RX:        4096
RX Mini:    0
RX Jumbo:    0
TX:        4096
Current hardware settings:
RX:        256
RX Mini:    0
RX Jumbo:    0
TX:        256
```

看到 RX 和 TX 最大是 4096，当前值为 256。队列越大丢包的可能越小，但数据延迟会增加.

设置 RX 和 TX 队列大小：

```shell
ethtool -G em1 rx 4096
ethtool -G em1 tx 4096
```

### 调整 Ring Buffer 队列的权重

NIC 如果支持 mutiqueue 的话 NIC 会根据一个 Hash 函数对收到的数据包进行分发。能调整不同队列的权重，用于分配数据。

```
[root@server-20.140.beishu.polex.io ~ ]$ ethtool -x em1
RX flow hash indirection table for em1 with 8 RX ring(s):
    0:      0     0     0     0     0     0     0     0
    8:      0     0     0     0     0     0     0     0
   16:      1     1     1     1     1     1     1     1
   24:      1     1     1     1     1     1     1     1
   32:      2     2     2     2     2     2     2     2
   40:      2     2     2     2     2     2     2     2
   48:      3     3     3     3     3     3     3     3
   56:      3     3     3     3     3     3     3     3
   64:      4     4     4     4     4     4     4     4
   72:      4     4     4     4     4     4     4     4
   80:      5     5     5     5     5     5     5     5
   88:      5     5     5     5     5     5     5     5
   96:      6     6     6     6     6     6     6     6
  104:      6     6     6     6     6     6     6     6
  112:      7     7     7     7     7     7     7     7
  120:      7     7     7     7     7     7     7     7
RSS hash key:
Operation not supported
```

我的 NIC 一共有 8 个队列，一共有 128 个不同的 Hash 值，上面就是列出了每个 Hash 值对应的队列是什么。最左侧 0 8 16 是为了能让你快速的找到某个具体的 Hash 值。比如 Hash 值是 76 的话我们能立即找到 72 那一行：”72: 4 4 4 4 4 4 4 4”，从左到右第一个是 72 数第 5 个就是 76 这个 Hash 值对应的队列是 4 。

设置 8 个队列的权重。加起来不能超过 128 。128 是 indirection table 大小，每个 NIC 可能不一样。



### 更改 Ring Buffer Hash Field

分配数据包的时候是按照数据包内的某个字段来进行的，这个字段能进行调整。

```
[root@server-20.140.beishu.polex.io ~ ]$ ethtool -n em1 rx-flow-hash tcp4
TCP over IPV4 flows use these fields for computing Hash flow key:
IP SA
IP DA
L4 bytes 0 & 1 [TCP/UDP src port]
L4 bytes 2 & 3 [TCP/UDP dst port]
```

也可以设置 Hash 字段：查看 tcp4 的 Hash 字段。

```
ethtool -N em1 rx-flow-hash udp4 sdfn
```

sdfn 需要查看 ethtool 看其含义，还有很多别的配置值。

### IRQ 统计

`/proc/interrupts` 能看到每个 CPU 的 IRQ 统计。一般就是看看 NIC 有没有支持 multiqueue 以及 NAPI 的 IRQ 合并机制是否生效。看看 IRQ 是不是增长的很快。