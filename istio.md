# 架构基础

kubernetes 提供平台基础设施层容器编排和调度能力

+ 服务部署和弹性伸缩  deployment
+ 服务拆分和服务发现： service

kubernetes 提供简单的负载均衡

+ 负载均衡：基于ipvs或者iptables的简单均衡机制

微服务治理独立：

+ 治理能力独立
+ 应用程序无感知
+ 服务通信的基础设施层

Istio 微服务治理功能

+ 连接
+ 安全
+ 控制
+ 观察 - 监控

istio的关键能力：

+ 流量管理

  - 负载均衡

  + 动态路由
  + 灰度发布
  + 故障注入

+ 策略执行

  + 限流
  + acl

+ 认证和安全

  + 认证
  + 鉴权

+ 可观察性

  + 调用链
  + 访问日志
  + 监控

## Istio 架构

数据面，控制面

+ Pilot-配置规则到proxy，元信息
+ Mixer
  + policy check - 访问控制，限流
  + telemetry - 监控，调用链分析
+ Citadel-访问安全，证书下发
+ galley

![架构](https://pic3.zhimg.com/80/v2-2b1f812684b16f6bd828da0db4f772d8_1440w.jpg)



### Pilot

![](https://pic1.zhimg.com/80/v2-ec5dd596ea07c159aa00e8280179a966_1440w.jpg)

数据访问工作在Envoy

![](https://pic1.zhimg.com/80/v2-9a6ff1c1e0e054a979e025b8ad51ab76_1440w.jpg)

![](https://pic1.zhimg.com/80/v2-be0cf946e1bae9d90209887b1ff3877f_1440w.jpg)





![](https://picb.zhimg.com/80/v2-d12bb0244052913d095829b2aeefdfb5_1440w.jpg)

# 组件

## 数据面

### Envoy

基于c++实现的L4/L7 proxy转发器

+ Listerners（LDS）
+ Routes （RDS）
+ Clusters （CDS）
+ Endpoints （EDS）

配置文件

```yml
listeners:
	name:listener_0
	address:
		socket_address: {address:0.0.0.0, port_value:10000}
		
		
		route_config:
			name: local_route
			virtual_hosts:
			-name:local_service
			routes:
				-match: {prefix:"/"}
				route:{cluster: service_envoy}
				
				
		clusters:  
			-name: service_envoy
			lb_policy: ROUND_ROBIN 
			hosts:[......] #  Endpoints
```

### 服务治理规则

#### gateway

外部服务的访问接入，发布内部端口服务，提供外部访问，

#### virtual service

服务的访问的路由控制，满足特定条件的请求流到哪里，过程中治理，包括请求重写，重试，故障注入等。

+ hosts
+ Gateways
+ HTTP
+ TCP
+ TLS

#### Destination Rule

路由处理之后,负载均衡，连接池，断路器，TLS等

#### ServiceEntry

外部服务接入到服务注册表中，让istio中自动发现的服务能访问和路由到这些手工加入的服务。

## 控制面

[深入理解Istio核心组件之Pilot](https://www.cnblogs.com/YaoDD/p/11391342.html)

### Pilot

用户定义的规则，k8s的规则；watch resource

service 包含了version的概念，可以将version导入到不同的路由，endpoint

#### 服务发现

1. Pilot实现若干服务发现的接口定义
2. Pilot的Controller list/watch kubeApiserver 的service，endpoint等资源并转换成标准格式
3. Envoy从pilot获取XDS,动态更新
4. 当服务访问时，Envoy在处理outbound请求时，根据配置的LB策略，选择一个服务实例

![](https://pic3.zhimg.com/80/v2-385bce187a15bc1b353d9d5a5df92664_1440w.jpg)

#### 服务配置管理

路由规则，从apiserver获取路由规则

1. 配置：管理员通过pilot配置治理规则
2. 下发：Envoy从pilot中获取治理规则
3. 执行：在流量访问的时候执行治理规则

下图是一个灰度发布的规则，把1%的规则发布到其中一个版本，分布式治理在consumer和producer，lb在consumer发起

![灰度发布的规则](https://pic1.zhimg.com/80/v2-9a6ff1c1e0e054a979e025b8ad51ab76_1440w.jpg)

### Mixer

#### 功能和设计

运行管理；控制，observe

metric，日志，调用链

Mixer处理不同的基础设置后端的灵活性是通过使用插件模型实现的，这种插件称为Adapter

Mixer通过他们与不同的基础设施后端连接，这些后端提供核心功能，提供日志，监控，配额，acl检查等。



解耦，中介，运维时配置

![](https://pic3.zhimg.com/80/v2-ba6814d46b29d35a0ed6c4844e43e79e_1440w.jpg)

#### 配置模型

handler： 

Instance：envoy 上报的 attributes生成instance

rule：配置的规则

#### 典型应用



#### policy

#### telemetry

+ logging
+ quota
+ auth

### citadel

安全管理配置中心



