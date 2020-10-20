# 组成部分

## pod

状态：

+ pending

  还没有被调度，可以查看 kubectl describe pod

+ waiting

  没有正常拉去镜像

+ running

  运行状态

## Endpoint

## 异常调查

+ service 远程调试

  使用工具telepresence，将本地应用代理到集群的一个serivice上

  ![](https://intranetproxy.alipay.com/skylark/lark/0/2019/png/225439/1570503307524-cc111087-301f-4db3-9f29-b8f94345699a.png)

  1. 首先先将 Telepresence 的一个 Proxy 应用部署到远程的 K8s 集群里面。然后将远程单一个 deployment swap 到本地的一个 application，使用的命令就是 Telepresence-swap-deployment 然后以及远程的 DEPLOYMENT_NAME。通过这种方式就可以将本地一个 application 代理到远程的 service 之上、可以将应用在远程集群里面进行本地调试，这个有兴趣的同学可以到 GitHub 上面来看一下这个插件的使用的方式。

  2. 第二个是如果本地应用需要调用远程集群的服务时候，可以通过 port-forward 的方式将远程的应用调用到本地的端口之上。比如说现在远程的里面有一个 API server，这个 API server 提供了一些端口，本地在调试 Code 时候，想要直接调用这个 API server，那么这时，比较简单的一个方式就是通过 port-forward 的方式。

  

+ service 无法正常工作

  网络是否正常

  label配置问题，通过endpoint的方式查看

# 监控

## 分类

### 资源

### 性能

### 安全

### 事件

## metrics server

## kube-eventer





# 日志

## 分类

+ 主机内核日志

+ runtime的日志

  docker

+ 核心组件的日志

  apiserver，kube scheduler， etcd，ingress

+ 部署应用日志

# 网络模型

per pod per ip

对基本约束，可以做出这样一些解读：因为容器的网络发展复杂性就在于它其实是寄生在 Host 网络之上的。从这个角度讲，可以把容器网络方案大体分为 **Underlay/Overlay** 两大派别：

- Underlay 的标准是它与 Host 网络是同层的，从外在可见的一个特征就是它是不是使用了 Host 网络同样的网段、输入输出基础设备、容器的 IP 地址是不是需要与 Host 网络取得协同（来自同一个中心分配或统一划分）。这就是 Underlay；
- Overlay 不一样的地方就在于它并不需要从 Host 网络的 IPM 的管理的组件去申请IP，一般来说，它只需要跟 Host 网络不冲突，这个 IP 可以自由分配的

三个基本条件：

+ 所有的pod与其他的pod可以通信，无须NAT
+ Node<->pod 无须NAT
+ POD可见IP地址确为其他pod与其通信时所用，无须显示转换

四大目标：

+ 容器与容器间通信
+ pod与pod间通信
+ pod与service间通信
+ 外部与service通信

Netns 究竟实现了什么

network namespace

pod与netns的关系：



# service

为什么？

+ pod 生命周期短暂，地址变化

+ deployment等的pod需要统一访问的入口和负载均衡

+ 不同环境中部署同样的访问模式

  

![](https://intranetproxy.alipay.com/skylark/lark/0/2019/png/225439/1569203602310-c33ee9c4-a75f-4102-8c8e-4564821ed3d6.png)

 ![](https://intranetproxy.alipay.com/skylark/lark/0/2019/png/225439/1569393560637-b1571644-5393-4fbf-98a7-aa41ee7f7dc4.png)

在 service 创建之后，它会在集群里面创建一个虚拟的 IP 地址以及端口，在集群里，所有的 pod 和 node 都可以通过这样一个 IP 地址和端口去访问到这个 service。这个 service 会把它选择的 pod 及其 IP 地址都挂载到后端。这样通过 service 的 IP 地址访问时，就可以负载均衡到后端这些 pod 上面去。 

当 pod 的生命周期有变化时，比如说其中一个 pod 销毁，service 就会自动从后端摘除这个 pod。这样实现了：就算 pod 的生命周期有变化，它访问的端点是不会发生变化的。



![](https://intranetproxy.alipay.com/skylark/lark/0/2019/png/225439/1569393559709-e279c245-41c7-43c6-99cf-b23ee5f1f278.png)

# docker

![](https://img-blog.csdnimg.cn/20181108184239159.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L0NsZXZlckNvZGU=,size_16,color_FFFFFF,t_70)

## 联合文件系统（UnionFS）

联合文件系统（UnionFS）是一种分层、轻量级并且高性能的文件系统，它支持对文件系统的修改作为一次提交来一层层的叠加，同时可以将不同目录挂载到同一个虚拟文件系统下(unite several directories into asingle virtual filesystem)。

联合文件系统是 Docker 镜像的基础。镜像可以通过分层来进行继承，基于基础镜像（没有父镜像），可以制作各种具体的应用镜像。

另外，不同 Docker 容器就可以共享一些基础的文件系统层，同时再加上自己独有的改动层，大大提高了存储的效率。

Docker 中使用的 AUFS（AnotherUnionFS）就是一种联合文件系统。 AUFS 支持为每一个成员目录（类似 Git 的分支）设定只读（readonly）、读写（readwrite）和写出（whiteout-able）权限, 同时 AUFS 里有一个类似分层的概念, 对只读权限的分支可以逻辑上进行增量地修改(不影响只读部分的)。

Docker 目前支持的联合文件系统种类包括 AUFS, btrfs, vfs 和 DeviceMapper

## 控制组（cgroups）

控制组（cgroups）是 Linux 内核的一个特性，主要用来对共享资源进行隔离、限制、审计等。只有能控制分配到容器的资源，才能避免当多个容器同时运行时的对系统资源的竞争。

控制组技术最早是由 Google 的程序员 2006 年起提出，Linux 内核自 2.6.24 开始支持。

控制组可以提供对容器的内存、CPU、磁盘 IO 等资源的限制和审计管理。

## 名字空间（Namespaces）

名字空间是 Linux 内核一个强大的特性。每个容器都有自己单独的名字空间，运行在其中的应用都像是在独立的操作系统中运行一样。名字空间保证了容器之间彼此互不影响。

**1 pid 名字空间**
不同用户的进程就是通过 pid 名字空间隔离开的，且不同名字空间中可以有相同 pid。所有的 LXC 进程在Docker 中的父进程为Docker进程，每个 LXC 进程具有不同的名字空间。同时由于允许嵌套，因此可以很方便的实现嵌套的 Docker 容器。

**2 net 名字空间**
有了 pid 名字空间, 每个名字空间中的 pid 能够相互隔离，但是网络端口还是共享 host 的端口。网络隔离是通过 net 名字空间实现的， 每个 net 名字空间有独立的 网络设备, IP 地址, 路由表, /proc/net 目录。这样每个容器的网络就能隔离开来。Docker 默认采用 veth 的方式，将容器中的虚拟网卡同 host 上的一 个Docker网桥 docker0 连接在一起。

**3 ipc 名字空间**
容器中进程交互还是采用了 Linux 常见的进程间交互方法(interprocess communication – IPC), 包括信号量、消息队列和共享内存等。然而同 VM 不同的是，容器的进程间交互实际上还是 host 上具有相同 pid 名字空间中的进程间交互，因此需要在 IPC 资源申请时加入名字空间信息，每个 IPC 资源有一个唯一的 32位 id。

**4 mnt 名字空间**
类似 chroot，将一个进程放到一个特定的目录执行。mnt 名字空间允许不同名字空间的进程看到的文件结构不同，这样每个名字空间 中的进程所看到的文件目录就被隔离开了。同 chroot 不同，每个名字空间中的容器在 /proc/mounts 的信息只包含所在名字空间的 mount point。

**5 uts 名字空间**
UTS(“UNIX Time-sharing System”) 名字空间允许每个容器拥有独立的 hostname 和 domain name, 使其在网络上可以被视作一个独立的节点而非 主机上的一个进程。

**6 user 名字空间**
每个容器可以有不同的用户和组 id, 也就是说可以在容器内用容器内部的用户执行程序而非主机上的用户。