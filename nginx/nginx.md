

https://www.cnblogs.com/sxhlinux/p/6748191.html

# 基本操作

**Linux对信号SIGQUIT(3)，SIGABRT(6), SIGFPE(8)和SIGSEGV(11)的默认处理，都可以强制让进程产生coredump文件。如果进程代码对这些信号做了其它处理，就不会产生了。**

## reload 流程：

+ 向master进程发送hup信号

+ master进程校验配置语法

+ master进程打开新的监听端口

+ master进程根据配置启动worker进程

+ master进程向老的worker发送quit信号

+ 老的worker进程关闭监听句柄，处理完成当前连接结束进程

  

## 热升级

+ 重命名旧的nginx执行文件，拷贝新的nginx
+ kill -USR2 [旧的主进程id]       #通知旧的主进程将要进行升级
+ master进程修改pid文件名，加后缀.oldbin
+ master 进程使用新的nginx文件启动新的进程
+ 向老的master发送quit信号，关闭老的master
+ 回滚：向老的master发送sighup，新的发送sigquit

实现nginx热部署的前提：nginx是路径方式启动的：

     执行步骤：     
    
     1. mv /usr/local/nginx/sbin/nginx /usr/local/nginx/sbin/nginx.old    #备份原nginx执行文件
    
     2. cp [新的nginx文件] /usr/local/nginx/sbin    #拷贝新的执行文件  
    
     3. kill -USR2 [旧的主进程id]       #通知旧的主进程将要进行升级
    
     4. kill -WINCH [旧的主进程id]    #通知旧的主进程优雅地关闭它的worker 进程
    
     5. kill -QUIT [旧的主进程id]     #通知旧的主进程优雅的退出
    
     6. 更新配置文件，并重新加载  
NGX_HTTP_POST_READ_PHASE:
接收完请求头之后的第一个阶段，它位于uri重写之前，实际上很少有模块会注册在该阶段，默认的情况下，该阶段被跳过

NGX_HTTP_SERVER_REWRITE_PHASE:
server级别的uri重写阶段，也就是该阶段执行处于server块内，location块外的重写指令，在读取请求头的过程中nginx会根据host及端口找到对应的虚拟主机配置

NGX_HTTP_FIND_CONFIG_PHASE:
寻找location配置阶段，该阶段使用重写之后的uri来查找对应的location，值得注意的是该阶段可能会被执行多次，因为也可能有location级别的重写指令

NGX_HTTP_REWRITE_PHASE:
location级别的uri重写阶段，该阶段执行location基本的重写指令，也可能会被执行多次

NGX_HTTP_POST_REWRITE_PHASE:
location级别重写的后一阶段，用来检查上阶段是否有uri重写，并根据结果跳转到合适的阶段

NGX_HTTP_PREACCESS_PHASE:
访问权限控制的前一阶段，该阶段在权限控制阶段之前，一般也用于访问控制，比如限制访问频率，链接数等

NGX_HTTP_ACCESS_PHASE:
访问权限控制阶段，比如基于ip黑白名单的权限控制，基于用户名密码的权限控制等

NGX_HTTP_POST_ACCESS_PHASE:
问权限控制的后一阶段，该阶段根据权限控制阶段的执行结果进行相应处理

NGX_HTTP_TRY_FILES_PHASE:
try_files指令的处理阶段，如果没有配置try_files指令，则该阶段被跳过

NGX_HTTP_CONTENT_PHASE:
内容生成阶段，该阶段产生响应，并发送到客户端

NGX_HTTP_LOG_PHASE:
日志记录阶段，该阶段记录访问日志





init_by_lua            http
set_by_lua             server, server if, location, location if
rewrite_by_lua         http, server, location, location if
access_by_lua          http, server, location, location if
content_by_lua         location, location if
header_filter_by_lua   http, server, location, location if
body_filter_by_lua     http, server, location, location if
log_by_lua             http, server, location, location if
{
	set_by_lua: 流程分支处理判断变量初始化
	rewrite_by_lua: 转发、重定向、缓存等功能(例如特定请求代理到外网)
	access_by_lua: IP准入、接口权限等情况集中处理(例如配合iptable完成简单防火墙)
	content_by_lua: 内容生成
	header_filter_by_lua: 应答HTTP过滤处理(例如添加头部信息)
	body_filter_by_lua: 应答BODY过滤处理(例如完成应答内容统一成大写)
	log_by_lua: 会话完成后本地异步完成日志记录(日志可以记录在本地，还可以同步到其他机器)
}
