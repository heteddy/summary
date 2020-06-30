# tcp

![](https://coolshell.cn/wp-content/uploads/2009/09/tcp1.jpg)

![](https://coolshell.cn/wp-content/uploads/2009/09/tcp2.jpg)

![](https://images2017.cnblogs.com/blog/1260476/201711/1260476-20171116161802952-584681349.png)



## 三次握手(建立连接)

- 第一次：建立连接时，客户端发送SYN包(syn=j)到服务器，并进入SYN_SEND状态，等待服务器确认；
- 第二次：服务器收到SYN包，向客户端返回ACK（ack=j+1），同时自己也发送一个SYN包（syn=k），即SYN+ACK包，此时服务器进入SYN_RCVD状态；
- 第三次：客户端收到服务器的SYN＋ACK包，向服务器发送确认包ACK(ack=k+1)，此包发送完毕，客户端和服务器进入ESTABLISHED状态，完成三次握手。
- 完成三次握手，客户端与服务器开始传送数据，也就是ESTABLISHED状态。
- 三次握手保证了不会建立无效的连接，从而浪费资源。

## 四次挥手(断开连接)

- 第一次： TCP客户端发送一个FIN，用来关闭客户到服务器的数据传送。
- 第二次：服务器收到这个FIN，它发回一个ACK，确认序号为收到的序号加1。和SYN一样，一个FIN将占用一个序号。
- 第三次：服务器关闭客户端的连接，发送一个FIN给客户端。
- 第四次：客户端发回ACK报文确认，并将确认序号设置为收到序号加1。

## time_wait

> netstat -n | awk '/^tcp/ {++S[$NF]} END {for(a in S) print a, S[a]}' 

这么多状态不用都记住，只要了解到我上面提到的最常见的三种状态的意义就可以了。一般不到万不得已的情况也不会去查看网络状态，如果服务器出了异常，百分之八九十都是下面两种情况：

1.服务器保持了大量TIME_WAIT状态

2.服务器保持了大量CLOSE_WAIT状态

因为linux分配给一个用户的文件句柄是有限的（可以参考：http://blog.csdn.net/shootyou/article/details/6579139），而TIME_WAIT和CLOSE_WAIT两种状态如果一直被保持，那么意味着对应数目的通道就一直被占着，而且是“占着茅坑不使劲”，一旦达到句柄数上限，新的请求就无法被处理了

### 服务器保持了大量TIME_WAIT状态

这种情况比较常见，一些爬虫服务器或者WEB服务器（如果网管在安装的时候没有做内核参数优化的话）上经常会遇到这个问题，这个问题是怎么产生的呢？

从 上面的示意图可以看得出来，TIME_WAIT是主动关闭连接的一方保持的状态，对于爬虫服务器来说他本身就是“客户端”，在完成一个爬取任务之后，他就 会发起主动关闭连接，从而进入TIME_WAIT的状态，然后在保持这个状态2MSL（max segment lifetime）时间之后，彻底关闭回收资源。为什么要这么做？明明就已经主动关闭连接了为啥还要保持资源一段时间呢？这个是TCP/IP的设计者规定 的，主要出于以下两个方面的考虑：

1. 防止上一次连接中的包，迷路后重新出现，影响新连接（经过2MSL，上一次连接中所有的重复包都会消失）
2. 可靠的关闭TCP连接。在主动关闭方发送的最后一个 ack(fin) ，有可能丢失，这时被动方会重新发fin, 如果这时主动方处于 CLOSED 状态 ，就会响应 rst 而不是 ack。所以主动方要处于 TIME_WAIT 状态，而不能是 CLOSED 。另外这么设计TIME_WAIT 会定时的回收资源，并不会占用很大资源的，除非短时间内接受大量请求或者受到攻击。

> 1. 对于基于TCP的HTTP协议，关闭TCP连接的是Server端，这样，Server端会进入TIME_WAIT状态，可 想而知，对于访 问量大的Web Server，会存在大量的TIME_WAIT状态，假如server一秒钟接收1000个请求，那么就会积压 240*1000=240，000个 TIME_WAIT的记录，维护这些状态给Server带来负担。当然现代操作系统都会用快速的查找算法来管理这些 TIME_WAIT，所以对于新的 TCP连接请求，判断是否hit中一个TIME_WAIT不会太费时间，但是有这么多状态要维护总是不好。 
> 2. HTTP协议1.1版规定default行为是Keep-Alive，也就是会重用TCP连接传输多个 request/response，一个主要原因就是发现了这个问题。 

解决思路很简单，就是让服务器能够快速回收和重用那些TIME_WAIT的资源。

下面来看一下我们网管对/etc/sysctl.conf文件的修改：

```c++
#对于一个新建连接，内核要发送多少个 SYN 连接请求才决定放弃,不应该大于255，默认值是5，对应于180秒左右时间   
net.ipv4.tcp_syn_retries=2  
#net.ipv4.tcp_synack_retries=2  
#表示当keepalive起用的时候，TCP发送keepalive消息的频度。缺省是2小时，改为300秒  
net.ipv4.tcp_keepalive_time=1200  
net.ipv4.tcp_orphan_retries=3  
#表示如果套接字由本端要求关闭，这个参数决定了它保持在FIN-WAIT-2状态的时间  
net.ipv4.tcp_fin_timeout=30    
#表示SYN队列的长度，默认为1024，加大队列长度为8192，可以容纳更多等待连接的网络连接数。  
net.ipv4.tcp_max_syn_backlog = 4096  
#表示开启SYN Cookies。当出现SYN等待队列溢出时，启用cookies来处理，可防范少量SYN攻击，默认为0，表示关闭  
net.ipv4.tcp_syncookies = 1  
  
#表示开启重用。允许将TIME-WAIT sockets重新用于新的TCP连接，默认为0，表示关闭  
net.ipv4.tcp_tw_reuse = 1  
#表示开启TCP连接中TIME-WAIT sockets的快速回收，默认为0，表示关闭  
net.ipv4.tcp_tw_recycle = 1  // 这里可能导致问题
  
##减少超时前的探测次数   
net.ipv4.tcp_keepalive_probes=5   
##优化网络设备接收队列   
net.core.netdev_max_backlog=3000 
```

修改完之后执行/sbin/sysctl -p让参数生效。

 

这里头主要注意到的是net.ipv4.tcp_tw_reuse 

tcp_timestamps
net.ipv4.tcp_tw_recycle 
net.ipv4.tcp_fin_timeout 
net.ipv4.tcp_keepalive_*

这几个参数。

 

net.ipv4.tcp_tw_reuse和net.ipv4.tcp_tw_recycle的开启都是为了回收处于TIME_WAIT状态的资源。但是服务器并不需要打开因为可以控制time_wait的最大上限。

> tcp_max_tw_buckets = *262144* 

net.ipv4.tcp_fin_timeout这个时间可以减少在异常情况下服务器从FIN-WAIT-2转到TIME_WAIT的时间。

net.ipv4.tcp_keepalive_*一系列参数，是用来设置服务器检测连接存活的相关配置。

关于keepalive的用途可以参考：http://hi.baidu.com/tantea/blog/item/580b9d0218f981793812bb7b.html

### 服务器保持了大量CLOSE_WAIT状态

服务器A是一台爬虫服务器，它使用简单的HttpClient去请求资源服务器B上面的apache获取文件资源，正常情况下，如果请求成功，那么在抓取完 资源后，服务器A会主动发出关闭连接的请求，这个时候就是主动关闭连接，服务器A的连接状态我们可以看到是TIME_WAIT。

如果一旦发生异常呢？假设 请求的资源服务器B上并不存在，那么这个时候就会由服务器B发出关闭连接的请求，服务器A就是被动的关闭了连接，如果服务器A被动关闭连接之后程序员忘了 让HttpClient释放连接，那就会造成CLOSE_WAIT的状态了。

### 为什么不能把tcp_tw_recycle改成1
这个是通过血的教训换来的，先说改成1的后果是会导致一个路由器后面用户有人能连你服务器有人telnet不通。
原因是tcp_tw_recycle改成1后会启用tcp的tcp_timestamps功能，这个功能简单说就是所有的通信包是时间戳递增的，如果收到了同一个IP下时间戳小的包那就说明是个老数据包，就会丢弃这个功能。
而一个路由器下每台电脑的时候不是完全一致的，有的电脑的时间戳会小，导致这些电脑发出的通信包被直接丢弃了

## TCP滑动窗口

TCP引入了一些技术和设计来做 <font color=red size=4>网络流控</font>，Sliding Window是其中一个技术。 前面我们说过，**TCP头里有一个字段叫Window，又叫Advertised-Window，这个字段是接收端告诉发送端自己还有多少缓冲区可以接收数据**。**于是发送端就可以根据这个接收端的处理能力来发送数据，而不会导致接收端处理不过来**。 为了说明滑动窗口，我们需要先看一下TCP缓冲区的一些数据结构：

![img](https://coolshell.cn/wp-content/uploads/2014/05/sliding_window.jpg)

上图中，我们可以看到：

- 接收端LastByteRead指向了TCP缓冲区中读到的位置，NextByteExpected指向的地方是收到的连续包的最后一个位置，LastByteRcved指向的是收到的包的最后一个位置，我们可以看到中间有些数据还没有到达，所以有数据空白区。

- 发送端的LastByteAcked指向了被接收端Ack过的位置（表示成功发送确认），LastByteSent表示发出去了，但还没有收到成功确认的Ack，LastByteWritten指向的是上层应用正在写的地方。

于是：

- 接收端在给发送端回ACK中会汇报自己的AdvertisedWindow = MaxRcvBuffer – LastByteRcvd – 1;

- 而发送方会根据这个窗口来控制发送数据的大小，以保证接收方可以处理。

下面我们来看一下发送方的滑动窗口示意图：

![img](https://coolshell.cn/wp-content/uploads/2014/05/tcpswwindows.png)

（[图片来源](http://www.tcpipguide.com/free/t_TCPSlidingWindowAcknowledgmentSystemForDataTranspo-6.htm)）

上图中分成了四个部分，分别是：（其中那个黑模型就是滑动窗口）

1. 已收到ack确认的数据。
2. 发还没收到ack的。
3. 在窗口中还没有发出的（接收方还有空间）。
4. 窗口以外的数据（接收方没空间）

下面是个滑动后的示意图（收到36的ack，并发出了46-51的字节）：

![img](https://coolshell.cn/wp-content/uploads/2014/05/tcpswslide.png)

下面我们来看一个接受端控制发送端的图示：

![img](https://coolshell.cn/wp-content/uploads/2014/05/tcpswflow.png)

（[图片来源](http://www.tcpipguide.com/free/t_TCPWindowSizeAdjustmentandFlowControl-2.htm)）

### Zero Window

上图，我们可以看到一个处理缓慢的Server（接收端）是怎么把Client（发送端）的TCP Sliding Window给降成0的。此时，你一定会问，如果Window变成0了，TCP会怎么样？是不是发送端就不发数据了？是的，发送端就不发数据了，你可以想像成“Window Closed”，那你一定还会问，如果发送端不发数据了，接收方一会儿Window size 可用了，怎么通知发送端呢？

解决这个问题，TCP使用了Zero Window Probe技术，缩写为ZWP，也就是说，发送端在窗口变成0后，会发ZWP的包给接收方，让接收方来ack他的Window尺寸，一般这个值会设置成3次，第次大约30-60秒（不同的实现可能会不一样）。如果3次过后还是0的话，有的TCP实现就会发RST把链接断了。

**注意**：只要有等待的地方都可能出现DDoS攻击，Zero Window也不例外，一些攻击者会在和HTTP建好链发完GET请求后，就把Window设置为0，然后服务端就只能等待进行ZWP，于是攻击者会并发大量的这样的请求，把服务器端的资源耗尽。（关于这方面的攻击，大家可以移步看一下[Wikipedia的SockStress词条](http://en.wikipedia.org/wiki/Sockstress)）

另外，Wireshark中，你可以使用tcp.analysis.zero_window来过滤包，然后使用右键菜单里的follow TCP stream，你可以看到ZeroWindowProbe及ZeroWindowProbeAck的包。

### Silly Window Syndrome

Silly Window Syndrome翻译成中文就是“糊涂窗口综合症”。正如你上面看到的一样，如果我们的接收方太忙了，来不及取走Receive Windows里的数据，那么，就会导致发送方越来越小。到最后，如果接收方腾出几个字节并告诉发送方现在有几个字节的window，而我们的发送方会义无反顾地发送这几个字节。

要知道，我们的TCP+IP头有40个字节，为了几个字节，要达上这么大的开销，这太不经济了。

另外，你需要知道网络上有个MTU，对于以太网来说，MTU是1500字节，除去TCP+IP头的40个字节，真正的数据传输可以有1460，这就是所谓的MSS（Max Segment Size）注意，TCP的RFC定义这个MSS的默认值是536，这是因为 [RFC 791](http://tools.ietf.org/html/rfc791)里说了任何一个IP设备都得最少接收576尺寸的大小（实际上来说576是拨号的网络的MTU，而576减去IP头的20个字节就是536）。

**如果你的网络包可以塞满MTU，那么你可以用满整个带宽，如果不能，那么你就会浪费带宽**。（大于MTU的包有两种结局，一种是直接被丢了，另一种是会被重新分块打包发送） 你可以想像成一个MTU就相当于一个飞机的最多可以装的人，如果这飞机里满载的话，带宽最高，如果一个飞机只运一个人的话，无疑成本增加了，也而相当二。

所以，**Silly Windows Syndrome这个现像就像是你本来可以坐200人的飞机里只做了一两个人**。 要解决这个问题也不难，就是避免对小的window size做出响应，直到有足够大的window size再响应，这个思路可以同时实现在sender和receiver两端。

- 如果这个问题是由Receiver端引起的，那么就会使用 David D Clark’s 方案。在receiver端，如果收到的数据导致window size小于某个值，可以直接ack(0)回sender，这样就把window给关闭了，也阻止了sender再发数据过来，等到receiver端处理了一些数据后windows size 大于等于了MSS，或者，receiver buffer有一半为空，就可以把window打开让send 发送数据过来。

- 如果这个问题是由Sender端引起的，那么就会使用著名的 [Nagle’s algorithm](http://en.wikipedia.org/wiki/Nagle's_algorithm)。这个算法的思路也是延时处理，他有两个主要的条件：1）要等到 Window Size>=MSS 或是 Data Size >=MSS，2）收到之前发送数据的ack回包，他才会发数据，否则就是在攒数据。

另外，Nagle算法默认是打开的，所以，对于一些需要小包场景的程序——**比如像telnet或ssh这样的交互性比较强的程序，你需要关闭这个算法**。你可以在Socket设置TCP_NODELAY选项来关闭这个算法（关闭Nagle算法没有全局参数，需要根据每个应用自己的特点来关闭）

> setsockopt(sock_fd, IPPROTO_TCP, TCP_NODELAY, (**char** *)&value,sizeof(**int**));

另外，网上有些文章说TCP_CORK的socket option是也关闭Nagle算法，这不对。**TCP_CORK其实是更新激进的Nagle算法，完全禁止小包发送，而Nagle算法没有禁止小包发送，只是禁止了大量的小包发送**。最好不要两个选项都设置。

**tcp_tw_reuse**

**tcp_tw_recycle**



## 拥塞控制

拥塞控制分为四个部分：慢启动、拥塞避免、快速重传、快速恢复：

### 慢热启动算法 – Slow Start

慢启动的算法如下(cwnd全称Congestion Window 拥塞窗口)：

1. 连接建好的开始先初始化cwnd = 1，表明可以传一个MSS大小的数据。
2. 每当收到一个ACK，cwnd++; 呈线性上升
3. 每当过了一个RTT，cwnd = cwnd*2; 呈指数让升
4. 还有一个ssthresh（slow start threshold），是一个上限，当cwnd >= ssthresh时，就会进入“拥塞避免算法”（后面会说这个算法）

### 拥塞避免算法 – Congestion Avoidance

前面说过，还有一个ssthresh（slow start threshold），是一个上限，当cwnd >= ssthresh时，就会进入“拥塞避免算法”。一般来说ssthresh的值是65535，单位是字节，当cwnd达到这个值时后，算法如下：

1）收到一个ACK时，cwnd = cwnd + 1/cwnd

2）当每过一个RTT时，cwnd = cwnd + 1

这样就可以避免增长过快导致网络拥塞，慢慢的增加调整到网络的最佳值。很明显，是一个**线性上升**的算法。

### TCP重传机制

注意，接收端给发送端的Ack确认只会确认最后一个连续的包，比如，发送端发了1,2,3,4,5一共五份数据，接收端收到了1，2，于是回ack 3，然后收到了4（注意此时3没收到），此时的TCP会怎么办？我们要知道，因为正如前面所说的，**SeqNum和Ack是以字节数为单位，所以ack的时候，不能跳着确认，只能确认最大的连续收到的包**，不然，发送端就以为之前的都收到了。

#### 快速重传机制

于是，TCP引入了一种叫**Fast Retransmit** 的算法，**不以时间驱动，而以数据驱动重传**。也就是说，如果，包没有连续到达，就ack最后那个可能被丢了的包，<font color=red size=4>**如果发送方连续收到3次相同的ack，就重传。**</font>Fast Retransmit的好处是不用等timeout了再重传。

# https 连接建立

## 简单

![](https://images2017.cnblogs.com/blog/1260476/201711/1260476-20171116160813812-635766483.png)

- 在使用HTTPS是需要保证服务端配置正确了对应的安全证书
- 客户端发送请求到服务端
- 服务端返回公钥和证书到客户端
- 客户端接收后会验证证书的安全性,如果通过则会随机生成一个随机数,用公钥对其加密,发送到服务端
- 服务端接受到这个加密后的随机数后会用私钥对其解密得到真正的随机数,随后用这个随机数当做私钥对需要发送的数据进行对称加密
- 客户端在接收到加密后的数据使用私钥(即生成的随机值)对数据进行解密并且解析数据呈现结果给客户
- SSL加密建立

## 详细

![](https://pic1.zhimg.com/80/v2-d3b43a0ab493a761d7a3603b006316c8_1440w.jpg)

1. 客户端向服务端发送一个招呼报文（hello），包含自己支持的SSL版本，加密算法等信息。

2. 服务端回复一个招呼报文（hi）包含自己支持的SSL版本，加密算法等信息。

3. 服务端发送自己经过CA认证的公开密钥
   1. 服务端向CA认证机构发送自己的公开密钥（FPkey）
   2. CA认证机构使用自己的私有密钥给FPkey加上签名返回给服务端

5. 服务端发送结束招呼的报文，SSL第一次握手结束。

5. 客户端使用FPkey对自己的随机密码串（Ckey）进行加密并发送给服务端
   1. 客户端首先使用CA的公开密钥对FPkey的签名进行认证，确认密钥未被替换

8. 客户端发送提示报文，后续报文将用对称秘钥Ckey进行加密。

7. 客户端发送finished报文，表示该次发送结束

   1. 后续是否通信取决于客户端的finished报文能否被服务端成功解密

11. 服务端发送提示报文，表示他之后的报文也会用Ckey进行加密

12. 服务端发送finished报文。至此SSL握手结束，成功建立SSL连接。

10. 客户端开始发送http请求报文
    1. 建立Tcp连接，开始传输数据

15. 服务端发送http回复报文

16. 客户端发送断开连接报文，并断开Tcp连接

# http2

https://www.jianshu.com/p/e57ca4fec26f

## 核心概念

- `连接 Connection` ：1个TCP连接包含多个Stream。
- `数据流 Stream` ：一个双向通讯数据流，包含1条或多条 message。
- `消息 Message` ：对应HTTP/1 中的请求或者响应，包含一个或者多条 Frame
- `数据帧` ： 最小单位，以二进制压缩格式存放 HTTP/1 中的内容。

- 一个消息是由 Headers 帧和DATA 帧组成的。

  ![img](https:////upload-images.jianshu.io/upload_images/16844918-9f95a514360f47b3.png?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

  消息的组成

  流，消息，帧 之间的关系

  ![img](https:////upload-images.jianshu.io/upload_images/16844918-7604b27bb632e48e.png?imageMogr2/auto-orient/strip|imageView2/2/w/1160/format/webp)

  流，消息，帧 之间的关系

抓包可以看到 1号 Stream 流 传递了 一个 GET 请求。1号 Stream 流也进行了回复（HEADER+DATA）



![img](https:////upload-images.jianshu.io/upload_images/16844918-a248300a20967a49.png?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

http2抓包

在一条 Connection 中，不同的流可以穿插传递，但是同一条流的达到顺序必须是有序的，比如1号流，流内的 帧必须有序。
 这就是**传输中无序，接收时组装**。

![img](https:////upload-images.jianshu.io/upload_images/16844918-b13e6490eedb402c.png?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

多路复用



### 帧格式

**每个帧标准为9个字节** （可理解为帧头）

![img](https:////upload-images.jianshu.io/upload_images/16844918-6944e48c904981a9.png?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

帧格式


 帧中指明了其所属于哪一个 Stream流 （Stream Identifier）其占了31 位。
 由此可见，一个帧中最重要的就是 Stream Id 了。其余的内容为



- `Length` : 代表整个 frame 的长度，用一个 24 位无符号整数表示
- `Type` : 定义 frame 的类型。帧类型决定了帧主体的格式和语义，如果 type 为 unknown 应该忽略或抛弃。
- `Flags` :是为帧类型相关而预留的布尔标识。标识对于不同的帧类型赋予了不同的语义。
- `R`:  是一个保留的比特位。这个比特的语义没有定义，发送时它必须被设置为 (0x0), 接收时需要忽略。
- `Frame Payload` : 是主体内容，由帧类型决定

下图为wireshark中抓取的帧，上述的帧格式可以对比找到



![img](https:////upload-images.jianshu.io/upload_images/16844918-911158d7aaee5e74.png?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

wireshark中的帧

正是将每一个帧关联到流上。才实现了多路复用。这个多路复用指的是很多个流之间的帧随意穿插。比如客户端收到 1流的 1 帧，又收到了 2流的3帧，再收到了3流的4帧，1流的2帧，1流的3帧，3流的5帧。
 注意。相同的流之内，其帧必须是按顺序的。
 看一下下面的图。还是之前的抓包图



![img](https:////upload-images.jianshu.io/upload_images/16844918-5b6106dcce4e3796.png?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

http2抓包

有没有发现除了 0 帧之外，为什么没有偶数帧？1，3，5 。。。
 这就是因为 **由客户端发起的连接，必须是奇数流。服务端发起的必须是偶数流**
 一般服务端推送算作是服务端发起的连接，也就会出现偶数流了。

> 要想实现并发，其实就是建立多个流。因为单个流因为必须顺序发送，所以没有办法做到并发。

- 流状态管理的约束性规定
  - 新建立的流ID必须大于曾经建立过状态为opened 或者 reserved 的流ID。
  - 在新建立的流ID发送帧时，意味着更小ID为idle的流就必须置为closed了。
  - Stream ID 不能复用，长连接耗尽的ID，只能通过重新建立TCP连接了。

Stream ID 为 0 的帧 是 控制帧，如setting，window_update，ping等帧。

## Flow Control

HTTP/2 也支持流控，如果 sender 端发送数据太快，receiver 端可能因为太忙，或者压力太大，或者只想给特定的  stream 分配资源，receiver 端就可能不想处理这些数据。譬如，如果 client 给 server  请求了一个视频，但这时候用户暂停观看了，client 就可能告诉 server 别在发送数据了。

虽然 TCP 也有 flow control，但它仅仅只对一个连接有效果。HTTP/2 在一条连接上面会有多个  streams，有时候，我们仅仅只想对一些 stream 进行控制，所以 HTTP/2 单独提供了流控机制。Flow control  有如下特性：

- Flow control 是单向的。Receiver 可以选择给 stream 或者整个连接设置 window size。
- Flow control 是基于信任的。Receiver 只是会给 sender 建议它的初始连接和 stream 的 flow control window size。
- Flow control 不可能被禁止掉。当 HTTP/2 连接建立起来之后，client 和 server 会交换 SETTINGS frames，用来设置 flow control window size。
- Flow control 是 hop-by-hop，并不是 end-to-end 的，也就是我们可以用一个中间人来进行 flow control。

这里需要注意，HTTP/2 默认的 window size 是 64 KB，实际这个值太小了，在 TiKV 里面我们直接设置成 1 GB。