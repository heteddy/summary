

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



内核接收流程：

![](https://img-blog.csdn.net/20130826185002859?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvcnVzc2VsbF90YW8=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

# 网卡发送流程



## 内核发送流程

![](https://img-blog.csdn.net/20130718162926640?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvcnVzc2VsbF90YW8=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

# accept 等系统调用

