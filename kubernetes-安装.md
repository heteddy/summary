# 修改host（可选）

## 修改/etc/hostname

``` shell
localhost.localdomain #替换主机名
```

把它修改成想要的名字比如master

保存退出

## 修改/etc/hosts文件(可选)

``` shell
127.0.0.1  localhost localhost.localdomain localhost4 localhost4.localdomain4
::1     localhost localhost.localdomain localhost6 localhost6.localdomain6
192.168.80.10  master  #  添加的内容
192.168.80.11  slave  #  添加的内容
```

# 关闭防火墙

```shell
systemctl stop firewalld && systemctl disable firewalld
```

# 禁用SELINUX

```shell
# 临时禁用
setenforce 0

# 永久禁用 
vim /etc/selinux/config    # 或者修改/etc/sysconfig/selinux
SELINUX=disabled
```

# 修改k8s.conf文件

```shell
cat <<EOF >  /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
sysctl --system
```

# 修改k8s.conf文件

```shell
cat <<EOF >  /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
sysctl --system
```

# 关闭swap

```shell
# 临时关闭
swapoff -a
```

## 永久关闭swap

修改 /etc/fstab 文件，注释掉 SWAP 的自动挂载（永久关闭swap，重启后生效）

```shell
# 注释掉以下字段
/dev/mapper/cl-swap     swap                    swap    defaults        0 0
```

# docker 安装

## 卸载老版本的Docker

如果有没有老版本Docker，则不需要这步

```
yum remove docker \
           docker-common \
           docker-selinux \
           docker-engine
```

## 使用yum进行安装

每个节点均要安装，目前官网建议安装19.03版本的docker，[官网链接](https://yq.aliyun.com/go/articleRenderRedirect?url=https%3A%2F%2Fkubernetes.io%2Fdocs%2Fsetup%2Findependent%2Finstall-kubeadm%2F)

```shell
# step 1: 安装必要的一些系统工具
sudo yum install -y yum-utils device-mapper-persistent-data lvm2
# Step 2: 添加软件源信息
sudo yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
# Step 3: 更新并安装 Docker-CE
sudo yum makecache fast
sudo yum -y install docker-ce docker-ce-selinux
# 注意：
# 官方软件源默认启用了最新的软件，您可以通过编辑软件源的方式获取各个版本的软件包。例如官方并没有将测试版本的软件源置为可用，你可以通过以下方式开启。同理可以开启各种测试版本等。
# vim /etc/yum.repos.d/docker-ce.repo
#   将 [docker-ce-test] 下方的 enabled=0 修改为 enabled=1
#
# 安装指定版本的Docker-CE:
# Step 3.1: 查找Docker-CE的版本:
# yum list docker-ce.x86_64 --showduplicates | sort -r
#   Loading mirror speeds from cached hostfile
#   Loaded plugins: branch, fastestmirror, langpacks
#   docker-ce.x86_64            17.03.1.ce-1.el7.centos            docker-ce-stable
#   docker-ce.x86_64            17.03.1.ce-1.el7.centos            @docker-ce-stable
#   docker-ce.x86_64            17.03.0.ce-1.el7.centos            docker-ce-stable
#   Available Packages
# Step 3.2 : 安装指定版本的Docker-CE: (VERSION 例如上面的 17.03.0.ce.1-1.el7.centos)
sudo yum -y --setopt=obsoletes=0 install docker-ce-[VERSION] \
docker-ce-selinux-[VERSION]

# Step 4: 开启Docker服务
sudo systemctl enable docker && systemctl start docker
```

# 安装kubeadm，kubelet，kubectl

## 修改yum安装源

```bash
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF
```

## 安装kubeadm、kubelet、kubectl

各节点均需安装kubeadm、kubelet，kubectl仅kube-master节点需安装（作为worker节点，kubectl无法使用，可以不装）

```bash
yum install -y kubelet kubeadm kubectl --disableexcludes=kubernetes
systemctl enable --now kubelet
```

## 配置自动补全命令

```bash
#安装bash自动补全插件
yum install bash-completion -y
#设置kubectl与kubeadm命令补全，下次login生效
kubectl completion bash >/etc/bash_completion.d/kubectl
kubeadm completion bash > /etc/bash_completion.d/kubeadm
```

## 预拉取kubernetes镜像

由于国内网络因素，kubernetes镜像需要从mirrors站点或通过dockerhub用户推送的镜像拉取

```bash
#查看指定k8s版本需要哪些镜像
kubeadm config images list --kubernetes-version v1.18.6
```

![截屏2020-08-07 09.49.37.png](https://upload-images.jianshu.io/upload_images/9243349-d82be5e60342da09.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

