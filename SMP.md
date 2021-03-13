# SMP

为了扩展单核 CPU 的性能，现在的服务器架构多采用多核 CPU 架构。一个比较经典的 CPU 架构就是**对称多处理**（Symmetric Multi-Processing，SMP）架构。与之相对应的就是**非对称多处理**（Asym-metrical Mulit-Processing）结构。

这个**对称**是什么意思？即处理器与处理器的关系，在**对称多处理架构**中，处理器之间是相同等级的，所有处理器都可以访问相同的资源。与之相应的，**非对称多处理架构**，各处理器之间形成简单的主从设备关系，访问有限的资源。

一个 SMP CPU 架构如下所示：



![img](https://pic4.zhimg.com/80/v2-eec88d0bc5021f23d175168396792a67_1440w.jpg)



现代的 CPU 一般会有多个**核心**（Core），我们这里是两个。每个核心有各自的 **L1 Cache**，多个核心共享 **L2 和 L3 Cache**。CPU 通过**前端总线**（FSB）访问主内存。多个 CPU 对于内存访问是基于缓存行的，多个 CPU 对于内存的访问符合**缓存一致性协议**(Cache coherency protocol)。SMP 架构中，系统中所有资源都是共享的，由于多个 CPU 对于同一个前端总线的竞争，导致扩展能力有限。在超过 64 个 CPU 以上的机器中，这个问题会愈发严重。在大型服务器中，主流架构一般是 NUMA（Non-Uniform Memory Access，非一致存储访问）。



# SMP和NUMA 

## 通用的多核CPU架构

![img](https://pic2.zhimg.com/80/v2-44129f0798b4e604eb49a611faff5e0d_1440w.jpg)

在多核 CPU 中，每个核都有自己的私有缓存，这样才能达到最佳的性能，如果所有的核都共用同一个缓存，缓存的吞吐跟不上。所以现在CPU都有 L1，L2，L3三级缓存，L1和L2缓属于同一个CPU核，L3则是所有CPU核心所共享。L1、L2、L3的越离CPU核心越近，速度也越快，当然价格也越高，所以容量就越小。一般来讲，L1 的读取速率为 4 个CPU[时钟](https://link.zhihu.com/?target=http%3A//www.elecfans.com/tags/%E6%97%B6%E9%92%9F/)周期 L2 为 11 L3 为 39 内存为107 个CPU时钟周期。L1的大小一般为32KB，L2大小为256KB,L3为MB级别的。服务器可以达到24MB.

## 多处理器的架构

![img](https://pic2.zhimg.com/80/v2-fb75f86244a599e085f74c2c3a4ab571_1440w.jpg)

SMP架构 随着更多的处理器被添加到SMP系统中，总线的竞争将会越来越大，系统的性能也必将随之大打折扣

![img](https://pic3.zhimg.com/80/v2-03cacc8040302f1075cf4e49cb9e593a_1440w.jpg)

NUMA架构 NUMA架构在逻辑上也遵从对称多处理（SMP）架构，在NUMA架构，CPU访问和他自己同一Chip的内存速度比访问其他Chip的内存要快3倍左右，Linux内核默认使用CPU亲和的内存分配策略，使内存页尽可能的和调用线程处在同一个Core/Chip，所有这些都使得NUMA架构成了高性能的流行解决方案。

## CPU缓存行与伪共享的问题

缓存行是CPU Cache中的最小缓存单位，目前主流的CPU Cache的缓存行大小都是64B。如果我们需要缓存一个256字节的数据，这个一级缓存所能存放的缓存个数就是256/64 = 4个。

如果有的变量不足64Bytes，这时候有可能有多个变量共享缓存行。

当多线程修改互相独立的变量时，如果这些变量共享同一个缓存行，就会互相影响，这就是伪共享，缓存行上的写竞争是运行在SMP系统中并行线程实现可伸缩性最重要的限制因素。

![img](https://pic1.zhimg.com/80/v2-429693d7eb333a75e0f34c6330532360_1440w.jpg)图片来源网络

如上图在core1上的线程要更新变量X，同时core2上的线程要更新变量Y。但是，不巧的是这两个变量在同一个缓存行中。每个线程都要去竞争缓存行的所有权来更新变量。如果core1获得了所有权，缓存子系统将会使core2中对应的缓存行失效。如果core2获得了所有权然后执行更新操作，core1就要使自己对应的缓存行失效。这样需要多次经过L3缓存，影响了性能。

后续专门阐述如何解决伪共享的问题。

## 4 CPU缓存一致性问题

为了提高CPU的处理效率，cpu不会直接和内存交换数据，都会先经过缓存(L1,L2,L3),在什么写回内存并确定，考虑到以下场景：core1 读取了一个变量x，以及x和它相邻的字节被读入core1 的高速缓存，core2 也同样读取了变量x，讲x和相邻的字节存入core2的高速缓存。这样 core1 ， core2 的高速缓存拥有同样的数据。core1 修改了那个变量x，修改后，变量被放回 CPU1 的高速缓存行。但是该信息并没有被写回主内存 ，core2 访问该变量x，但由于 CPU1 并未将数据写入 RAM ，导致了数据不同步。

为了解决这个问题，设计者制定了一些规则，这就是缓存一致性协议MESI。

MESI 是缓存协议4个状态的首字母：

![img](https://pic3.zhimg.com/80/v2-b9d00b5f3ff3787a5ca0a1af7c5b23b2_1440w.jpg)

图片来源网络

后续详细讲解MESI协议。



# 查看cpu信息

>   虚拟文件展示的是可用CPU硬件的配置。

```shell
more /proc/cpuinfo
```

cpufreq-info

>    cpufreq-info命令(**cpufrequtils**包的一部分)从内核/硬件中收集并报告CPU频率信息。这条命令展示了CPU当前运行的硬件频率，包括CPU所允许的最小/最大频率、CPUfreq策略/统计数据等等。来看下CPU #0上的信息：

```
cpufreq-info -c 0
```

dmidecode

>   dmidecode命令直接从BIOS的DMI（桌面管理接口）数据收集关于系统硬件的具体信息。CPU信息报告包括CPU供应商、版本、CPU标志寄存器、最大/当前的时钟速度、(启用的)核心总数、L1/L2/L3缓存配置等等。

lscpu

>   lscpu命令用一个更加用户友好的格式统计了 /etc/cpuinfo 的内容，比如CPU、核心、套接字、NUMA节点的数量（线上/线下）。

```
[root@education_01 ~]# lscpu
Architecture:          x86_64
CPU op-mode(s):        32-bit, 64-bit
Byte Order:            Little Endian
CPU(s):                4
On-line CPU(s) list:   0-3
Thread(s) per core:    1
Core(s) per socket:    4
座：                 1
NUMA 节点：         1
厂商 ID：           GenuineIntel
CPU 系列：          6
型号：              79
型号名称：        Intel(R) Xeon(R) CPU E5-26xx v4
步进：              1
CPU MHz：             2394.446
BogoMIPS：            4788.89
超管理器厂商：  KVM
虚拟化类型：     完全
L1d 缓存：          32K
L1i 缓存：          32K
L2 缓存：           4096K
NUMA 节点0 CPU：    0-3
```

lshw

>   yum install lshw
>
>   **lshw**命令是一个综合性硬件查询工具。不同于其它工具，lshw需要root特权才能运行，因为它是在BIOS系统里查询DMI（桌面管理接口）信息。它能报告总核心数和可用核心数，但是会遗漏掉一些信息比如L1/L2/L3缓存配置。GTK版本的lshw-gtk也是可用的。
>
>   可以显示physical id

```
[root@education_01 /etc]# lshw -h
Hardware Lister (lshw) - B.02.18
usage: lshw [-format] [-options ...]
       lshw -version

	-version        print program version (B.02.18)

format can be
	-html           output hardware tree as HTML
	-xml            output hardware tree as XML
	-json           output hardware tree as a JSON object
	-short          output hardware paths
	-businfo        output bus information

options can be
	-dump filename  displays output and dump collected information into a file (SQLite database)
	-class CLASS    only show a certain class of hardware
	-C CLASS        same as '-class CLASS'
	-c CLASS        same as '-class CLASS'
	-disable TEST   disable a test (like pci, isapnp, cpuid, etc. )
	-enable TEST    enable a test (like pci, isapnp, cpuid, etc. )
	-quiet          don't display status
	-sanitize       sanitize output (remove sensitive information like serial numbers, etc.)
	-numeric        output numeric IDs (for PCI, USB, etc.)
	-notime         exclude volatile attributes (timestamps) from output

[root@education_01 /etc]# lshw -class processor
  *-cpu:0
       description: CPU
       product: Intel(R) Xeon(R) CPU E5-26xx v4
       vendor: Intel Corp.
       vendor_id: GenuineIntel
       physical id: 401
       bus info: cpu@0
       version: 6.79.1
       slot: CPU 1
       size: 2GHz
       capacity: 2GHz
       width: 64 bits
       capabilities: fpu fpu_exception wp vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx x86-64 constant_tsc rep_good nopl eagerfpu pni pclmulqdq ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch bmi1 avx2 bmi2 rdseed adx xsaveopt
       configuration: microcode=0
  *-cpu:1
       description: CPU
       vendor: Bochs
       physical id: 402
       bus info: cpu@1
       slot: CPU 2
       size: 2GHz
       capacity: 2GHz
  *-cpu:2
       description: CPU
       vendor: Bochs
       physical id: 403
       bus info: cpu@2
       slot: CPU 3
       size: 2GHz
       capacity: 2GHz
  *-cpu:3
       description: CPU
       vendor: Bochs
       physical id: 404
       bus info: cpu@3
       slot: CPU 4
       size: 2GHz
       capacity: 2GHz
```

lstopo

>   lstopo命令 (包括在 hwloc 包中) 以可视化的方式组成 CPU、缓存、内存和I/O设备的拓扑结构。这个命令用来识别处理器结构和系统的NUMA拓扑结构。
>
>   L1i  指令缓存
>
>   L1d  数据缓存
>
>   yum install hwloc-libs hwloc-gui
>
>   显示物理索引
>   lstopo -p
>
>   显示逻辑索引
>   lstopo -l
>
>   命令行显示
>   lstopo -no-graphics
>
>   lstopo --of png > computer.png



```
[root@education_01 /etc]# lstopo -p
Machine (7821MB)
  Package P#0
    L2 (4096KB) + L1d (32KB) + L1i (32KB) + Core P#0 + PU P#0
    L2 (4096KB) + L1d (32KB) + L1i (32KB) + Core P#1 + PU P#1
    L2 (4096KB) + L1d (32KB) + L1i (32KB) + Core P#2 + PU P#2
    L2 (4096KB) + L1d (32KB) + L1i (32KB) + Core P#3 + PU P#3
  HostBridge P#0
    PCI 8086:7010
      Block(Removable Media Device) "sr0"
    PCI 1013:00b8
      GPU "card0"
      GPU "controlD64"
    PCI 1af4:1000
    2 x { PCI 1af4:1001 }
[root@education_01 /etc]# lstopo -l
Machine (7821MB)
  Package L#0
    L2 L#0 (4096KB) + L1d L#0 (32KB) + L1i L#0 (32KB) + Core L#0 + PU L#0 (P#0)
    L2 L#1 (4096KB) + L1d L#1 (32KB) + L1i L#1 (32KB) + Core L#1 + PU L#1 (P#1)
    L2 L#2 (4096KB) + L1d L#2 (32KB) + L1i L#2 (32KB) + Core L#2 + PU L#2 (P#2)
    L2 L#3 (4096KB) + L1d L#3 (32KB) + L1i L#3 (32KB) + Core L#3 + PU L#3 (P#3)
  HostBridge L#0
    PCI 8086:7010
      Block(Removable Media Device) L#0 "sr0"
    PCI 1013:00b8
      GPU L#1 "card0"
      GPU L#2 "controlD64"
    PCI 1af4:1000
    2 x { PCI 1af4:1001 }
[root@education_01 /etc]#
```

>   Hwloc-ls

```
[root@education_01 ~]# hwloc-ls
Machine (7821MB)
  Package L#0
    L2 L#0 (4096KB) + L1d L#0 (32KB) + L1i L#0 (32KB) + Core L#0 + PU L#0 (P#0)
    L2 L#1 (4096KB) + L1d L#1 (32KB) + L1i L#1 (32KB) + Core L#1 + PU L#1 (P#1)
    L2 L#2 (4096KB) + L1d L#2 (32KB) + L1i L#2 (32KB) + Core L#2 + PU L#2 (P#2)
    L2 L#3 (4096KB) + L1d L#3 (32KB) + L1i L#3 (32KB) + Core L#3 + PU L#3 (P#3)
  HostBridge L#0
    PCI 8086:7010
      Block(Removable Media Device) L#0 "sr0"
    PCI 1013:00b8
      GPU L#1 "card0"
      GPU L#2 "controlD64"
    PCI 1af4:1000
    2 x { PCI 1af4:1001 }
```

numactl

numactl -H



```
yum -y install numactl numastat
```

**numastat**

```
[root@education_01 ~]# numastat
                           node0
numa_hit               987680327
numa_miss                      0
numa_foreign                   0
interleave_hit             15151
local_node             987680327
other_node                     0
[root@education_01 ~]# numactl -H
available: 1 nodes (0)
node 0 cpus: 0 1 2 3
node 0 size: 8191 MB
node 0 free: 246 MB
node distances:
node   0
  0:  10
```

NUMA 全称 Non-Uniform Memory Access，译为“非一致性内存访问”。这种构架下，不同的内存器件和CPU核心从属不同的 Node，每个 Node 都有自己的集成内存控制器（IMC，Integrated Memory Controller）。

在 Node 内部，架构类似SMP，使用 IMC Bus 进行不同核心间的通信；不同的 Node 间通过QPI（Quick Path Interconnect）进行通信，如下图所示：

![](https://pic4.zhimg.com/80/v2-ee9a115806bae6341fc724707e4058cf_1440w.jpg)

NUMA

一般来说，一个内存插槽对应一个 Node。需要注意的一个特点是，QPI的延迟要高于IMC Bus，也就是说CPU访问内存有了远近（remote/local）之别，而且实验分析来看，这个**差别非常明显**。

在Linux中，对于NUMA有以下几个需要注意的地方：

-   默认情况下，内核不会将内存页面从一个 NUMA Node 迁移到另外一个 NUMA Node；
-   但是有现成的工具可以实现将冷页面迁移到远程（Remote）的节点：NUMA Balancing；
-   关于不同 NUMA Node 上内存页面迁移的规则，社区中有依然有不少争论。

对于初次了解NUMA的人来说，了解到这里就足够了，本文的细节探讨也止步于此，如果想进一步深挖，可以参考开源小站[这篇文章](https://link.zhihu.com/?target=https%3A//links.jianshu.com/go%3Fto%3Dhttp%3A%2F%2Fwww.litrin.net%2F2017%2F10%2F31%2F%25E6%25B7%25B1%25E6%258C%2596numa%2F)。



通过 numactl -C 0-15 top 命令即是将进程“top”绑定到0~15 CPU core上执行。

## TLB

TLB是translation lookaside buffer的简称。首先，我们知道MMU的作用是把虚拟地址转换成物理地址。虚拟地址和物理地址的映射关系存储在页表中，而现在页表又是分级的。64位系统一般都是3~5级。常见的配置是4级页表，就以4级页表为例说明。分别是PGD、PUD、PMD、PTE四级页表。在硬件上会有一个叫做页表基地址寄存器，它存储PGD页表的首地址。MMU就是根据页表基地址寄存器从PGD页表一路查到PTE，最终找到物理地址(PTE页表中存储物理地址)。这就像在地图上显示你的家在哪一样，我为了找到你家的地址，先确定你是中国，再确定你是某个省，继续往下某个市，最后找到你家是一样的原理。一级一级找下去。这个过程你也看到了，非常繁琐。如果第一次查到你家的具体位置，我如果记下来你的姓名和你家的地址。下次查找时，是不是只需要跟我说你的姓名是什么，我就直接能够告诉你地址，而不需要一级一级查找。四级页表查找过程需要四次内存访问。延时可想而知，非常影响性能



# cpu特权级别

Intel的CPU将特权级别分为4个级别：RING0,RING1,RING2,RING3。

 linux的内核是一个有机的整体。每一个用户进程运行时都好像有一份内核的拷贝，每当用户进程使用系统调用时，都自动地将运行模式从用户级转为内核级，此时进程在内核的地址空间中运行。

  当一个任务（进程）执行系统调用而陷入内核代码中执行时，我们就称进程处于内核运行态（或简称为内核态）。此时处理器处于特权级最高的（0级）内核代码中执行。当进程处于内核态时，执行的内核代码会使用当前进程的内核栈。每个进程都有自己的内核栈。当进程在执行用户自己的代码时，则称其处于用户运行态（用户态）。即此时处理器在特权级最低的（3级）用户代码中运行。当正在执行用户程序而突然被中断程序中断时，此时用户程序也可以象征性地称为处于进程的内核态。因为中断处理程序将使用当前进程的内核栈。这与处于内核态的进程的状态有些类似。

  内核态与用户态是操作系统的两种运行级别,跟intel cpu没有必然的联系, 如上所提到的intel cpu提供Ring0-Ring3四种级别的运行模式，Ring0级别最高，Ring3最低。Linux使用了Ring3级别运行用户态，Ring0作为 内核态，没有使用Ring1和Ring2。Ring3状态不能访问Ring0的地址空间，包括代码和数据。Linux进程的4GB地址空间，3G-4G部 分大家是共享的，是内核态的地址空间，这里存放在整个内核的代码和所有的内核模块，以及内核所维护的数据。用户运行一个程序，该程序所创建的进程开始是运 行在用户态的，如果要执行文件操作，网络数据发送等操作，必须通过write，send等系统调用，这些系统调用会调用内核中的代码来完成操作，这时，必 须切换到Ring0，然后进入3GB-4GB中的内核地址空间去执行这些代码完成操作，完成后，切换回Ring3，回到用户态。这样，用户态的程序就不能 随意操作内核地址空间，具有一定的安全保护作用。

   处理器总处于以下状态中的一种：

1、内核态，运行于进程上下文，内核代表进程运行于内核空间；

2、内核态，运行于中断上下文，内核代表硬件运行于内核空间；

3、用户态，运行于用户空间。

 

从用户空间到内核空间有两种触发手段：

1.用户空间的应用程序，通过系统调用，进入内核空间。这个时候用户空间的进程要传递很多变量、参数的值给内核，内核态运行的时候也要保存用户进程的一些寄存器值、变量等。所谓的“进程上下文”，可以看作是用户进程传递给内核的这些参数以及内核要保存的那一整套的变量和寄存器值和当时的环境等。

2.硬件通过触发信号，导致内核调用中断处理程序，进入内核空间。这个过程中，硬件的一些变量和参数也要传递给内核，内核通过这些参数进行中断处理。所谓的“中断上下文”，其实也可以看作就是硬件传递过来的这些参数和内核需要保存的一些其他环境（主要是当前被打断执行的进程环境）。

 

# cache

查看cache

```shell
cd /sys/devices/system/cpu/cpu0/cache
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index0]# cat level
1
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index0]# cat type
Data
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index0]# cat size
32K
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index0]# cd ../index1/
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index1]# cat level
1
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index1]# cat type
Instruction
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index1]# cat size
32K
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index2]# cat type
Unified
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index2]# cat size
4096K
[root@education_01 /sys/devices/system/cpu/cpu0/cache/index2]# cat level
2

```





>   为什么L1i和L1d

由于Pentium采用了双路执行的超标量结构，有2条并行整数流水线，需要对数据和指令进行双重的访问，为了使得这些访问互不干涉，于是出现了8K数据Cache和8K指令Cache，即L1分指令Cache和数据Cache, 并且可以同时读写，



# 多cpu架构





https://zhuanlan.zhihu.com/p/31875174

