### 目录

1. [摘要](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#summary)
2. 源码分析
   - [程序入口](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#main)
   - [uwsgi_setup()函数的主要代码](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#uwsgi-setup)
   - [uwsgi_start()函数的主要代码](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#uwsgi-start)
   - [uwsgi_run()函数的主要代码](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#uwsgi-run)
   - [simple_loop()函数的主要代码](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#simple-loop)
3. 值得关注的一些东西
   - [在C/C++中嵌入Python时，C/C++代码中开启的线程 与 Python代码中开启的线程的关系](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#thread)
   - [插件化开发](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#plugin)
   - [并发模型](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#concurrency)
4. [参考文档](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#references)

------

### 摘要[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]

- 本文在CentOS Linux release 7.3.1611 (Core)、uwsgi 2.0.15、Python 2.7.5下测试通过。
- 当使用uwsgi作为Python的WSGI Server的时候，本质上就是将Python解释器嵌入到uwsgi这个C程序中，所以在看本文之前，可以先简单的了解一下Python的C API，Python的C API就像Python一样的简洁，学习起来很方便

------

### 源码分析[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]

**1，程序入口[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
core/uwsgi.c：

```c
#ifdef UWSGI_AS_SHARED_LIBRARY
int uwsgi_init(int argc, char *argv[], char *envp[]) {
#else
int main(int argc, char *argv[], char *envp[]) {
#endif
    uwsgi_setup(argc, argv, envp);
    return uwsgi_run();
}
```

**2，uwsgi_setup()函数的主要代码[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
core/uwsgi.c：

```c
void uwsgi_setup(int argc, char *argv[], char *envp[]) {
    ....
    // !!! 初始化内嵌插件 !!!
    //initialize embedded plugins
    UWSGI_LOAD_EMBEDDED_PLUGINS
    ....
    uwsgi_start((void *) uwsgi.argv);
}
```

在执行`sudo python setup.py install`安装uwsgi的时候，可以看到:

> configured CFLAGS: ... -DUWSGI_LOAD_EMBEDDED_PLUGINS="ULEP(python);ULEP(gevent);ULEP(ping);ULEP(cache);ULEP(nagios);ULEP(rrdtool);ULEP(carbon);ULEP(rpc);ULEP(corerouter);ULEP(fastrouter);ULEP(http);ULEP(ugreen);ULEP(signal);ULEP(syslog);ULEP(rsyslog);ULEP(logsocket);ULEP(router_uwsgi);ULEP(router_redirect);ULEP(router_basicauth);ULEP(zergpool);ULEP(redislog);ULEP(mongodblog);ULEP(router_rewrite);ULEP(router_http);ULEP(logfile);ULEP(router_cache);ULEP(rawrouter);ULEP(router_static);ULEP(sslrouter);ULEP(spooler);ULEP(cheaper_busyness);ULEP(symcall);ULEP(transformation_tofile);ULEP(transformation_gzip);ULEP(transformation_chunked);ULEP(transformation_offload);ULEP(router_memcached);ULEP(router_redis);ULEP(router_hash);ULEP(router_expires);ULEP(router_metrics);ULEP(transformation_template);ULEP(stats_pusher_socket);"

接下来，在uwsgi.h头文件中，找到ULEP这个宏：

```c
#define ULEP(pname)\
    if (pname##_plugin.request) {\
    uwsgi.p[pname##_plugin.modifier1] = &pname##_plugin;\
    if (uwsgi.p[pname##_plugin.modifier1]->on_load) {\
        uwsgi.p[pname##_plugin.modifier1]->on_load();}\
    }\
    else {\
    if (uwsgi.gp_cnt >= MAX_GENERIC_PLUGINS) {\
        uwsgi_log("you have embedded too much generic plugins !!!\n");\
        exit(1);\
    }\
    uwsgi.gp[uwsgi.gp_cnt] = &pname##_plugin;\
    if (uwsgi.gp[uwsgi.gp_cnt]->on_load)\
        uwsgi.gp[uwsgi.gp_cnt]->on_load();\
    uwsgi.gp_cnt++;\
    }\
```

可以看到，所有具有request属性的插件，会被当作请求插件，保存到`uwsgi.p[]`数组中（注意：每个插件对象在数组中的索引值是其modifier1属性的值）；
其它的插件会被当作通用插件，保存到`uwsgi.gp[]`数组中。
同时，会调用所有插件的on_load钩子。
默认情况下，python是内嵌的请求插件。
**`uwsgi_setup`中最重要的工作就是把插件都装配好了**。

**3，uwsgi_start()函数的主要代码[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
`uwsgi_setup()`函数最后调用了`uwsgi_start()`，`uwsgi_start()`函数用于完成各种**初始化工作**：
core/uwsgi.c：

```c
int uwsgi_start(void *v_argv) {
    ...

    // ！！！初始化socket协议！！！
    // initialize socket protocols (do it after caching !!!)
    uwsgi_protocols_register();
    ...

    // ！！！ 绑定所有未绑定的socket ！！！
    uwsgi_bind_sockets();
    
    // put listening socket in non-blocking state and set the protocol
    uwsgi_set_sockets_protocols();
    ...
    
    // initialize request plugin only if workers or master are available
    if (uwsgi.sockets || uwsgi.master_process || uwsgi.no_server || uwsgi.command_mode || uwsgi.loop) {
        for (i = 0; i < 256; i++) {
            if (uwsgi.p[i]->init) {
                uwsgi.p[i]->init();
            }    
        }    
    }
    ...

    if (uwsgi.has_threads) {
        ...
        // again check for workers/sockets...
        if (uwsgi.sockets || uwsgi.master_process || uwsgi.no_server || uwsgi.command_mode || uwsgi.loop) {
            for (i = 0; i < 256; i++) {
                if (uwsgi.p[i]->enable_threads)
                    uwsgi.p[i]->enable_threads();
            }
        }
    }
    ...

    //init apps hook (if not lazy)
    if (!uwsgi.lazy && !uwsgi.lazy_apps) {
        uwsgi_init_all_apps();
    }
    ...


    if (!uwsgi.status.is_cheap) {
        if (uwsgi.cheaper && uwsgi.cheaper_count) {
            int nproc = uwsgi.cheaper_initial;
            if (!nproc)
                nproc = uwsgi.cheaper_count;
            for (i = 1; i <= uwsgi.numproc; i++) {
                if (i <= nproc) {
                    if (uwsgi_respawn_worker(i))
                        break;
                    uwsgi.respawn_delta = uwsgi_now();
                }    
                else {
                    uwsgi.workers[i].cheaped = 1; 
                }    
            }    
        } 
    ...
}
```

`uwsgi_start()`函数，主要做以下初始化工作：

- 调用`uwsgi_protocols_register()`，初始化socket协议。最终会把uwsgi支持的所有协议，保存到`uwsgi.protocols`链表中。在绑定完所有的socket之后，会将相应的回调设置给每个socket
- 在`uwsgi_bind_sockets()`函数中，对每个socket，调用了`bind_to_tcp(uwsgi_sock->name, uwsgi.listen_queue, tcp_port)`（core/socket.c），`bind_to_tcp()`函数在按需执行各种`setsockopt`之后，执行bind，listen
  **至此，master进程监听了所有的socket**。
- 调用所有请求插件的init钩子。默认情况下，python请求插件已经被装配了，接下来看，python插件的init方法都做了什么：
  plugins/python/python_plugin.c:

```c
struct uwsgi_plugin python_plugin = {
    .name = "python",
    .alias = "python",
    .modifier1 = 0,
    .init = uwsgi_python_init,
    .enable_threads = uwsgi_python_enable_threads,
    .init_apps = uwsgi_python_init_apps,
    ...
}
```

`uwsgi_python_init()`函数中，最主要的动作就是调用了Python的C API `Py_Initialize()`创建了Python的**虚拟机实例**，同时通过`PyThreadState_Get()`获取了主线程的ThreadState对象，并将其保存到全局变量`uwsgi_python up`的`main_thread`域中。
**至此，Python虚拟机实例就被创建了**

- 根据需要调用请求插件的enable_threads钩子。下面是`uwsgi_python_enable_threads()`的主要代码：

```c
void uwsgi_python_enable_threads() {
    ...

    // ！！！开启多线程支持，这条语句也会导致主进程的主线程获取到GIL，并且在该函数中，没有释放。Pyhton要求C代码在执行任何Python代码之前获取到GIL！！！
    PyEval_InitThreads();
    ...

    // ！！！将ThreadState对象保存到Thread Local中，
    // 在Python中每个线程对应一个ThreadState对象！！！
    pthread_setspecific(up.upt_gil_key, (void *) PyThreadState_Get());
    ...


    // ！！！将 获取和释放GIL的方法 保存到全局变量up的域中！！！
    up.gil_get = gil_real_get;
    up.gil_release = gil_real_release;
    ...
}
```

上面的流程中主要使用了Python的C API，更多细节可以移步[参考文档](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#references)。

- 在非lazy模式下（默认，可以通过uwsgi命令的`--lazy-apps`选项开启lazy模式，lazy模式是在worker进程中加载WSGI Application，而非lazy模式是在master进程中加载WSGI Application），`uwsgi_start()`函数还会调用请求插件的init_apps钩子。下面看python插件的init_apps钩子 `uwsgi_python_init_apps` 都做了什么：

```c
void uwsgi_python_init_apps() {
    // lazy ?
    if (uwsgi.mywid > 0) {
        UWSGI_GET_GIL; // 如果是延迟加载（也就是在子进程中加载），则获取GIL
    }
    ...

    // setup app loaders
    ...

    if (up.file_config != NULL) {
        init_uwsgi_app(LOADER_FILE, up.file_config, uwsgi.wsgi_req, up.main_thread, PYTHON_APP_TYPE_WSGI);
    }
    ...

    // lazy ?
    if (uwsgi.mywid > 0) {
        UWSGI_RELEASE_GIL;
    } 
}
```

下面看`init_uwsgi_app()`函数：
plugins/python/pyloader.c:

```c
int init_uwsgi_app(int loader, void *arg1, struct wsgi_request *wsgi_req, PyThreadState *interpreter, int app_type) {
    ...

    // !!! 创建uwsgi_app对象 !!!
    struct uwsgi_app *wi;
    ...

    // !!! 将该uwsgi_app对象保存到数组uwsgi.workers[uwsgi.mywid].apps !!!
    wi = &uwsgi_apps[id];
    ...

    // !!! 设置modifier1 !!!
    wi->modifier1 = python_plugin.modifier1;
    ...

    // !!! 加载WSGI Application !!!
    wi->callable = up.loaders[loader](arg1);
    ...

    // !!! 设置request 和 response handler !!!
    if (app_type == PYTHON_APP_TYPE_WSGI) {
        wi->request_subhandler = uwsgi_request_subhandler_wsgi;
        wi->response_subhandler = uwsgi_response_subhandler_wsgi;
        wi->argc = 2;
    }
    ...
}
```

**至此，WSGI application已经被导入了。**

- `uwsgi_start()`函数最后会fork出指定数量的worker进程，并对它们进行一些列的设置，其中包括为每一个线程（也被称为：core）设置一个wsgi_request对象

**至此，整个的初始化过程就完成了。**

**4，uwsgi_run()函数的主要代码[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
`uwsgi_start()`完成之后，就会进入到`uwsgi_run()`函数：
core/uwsgi.c：

```c
int uwsgi_run() {

    // !!! master进程进入master循环，master负责监控worker状态，在worker crash的时候，负责重新fork等工作!!!
    // !!! from now on, we could be in the master or in a worker !!!
    int i;

    if (getpid() == masterpid && uwsgi.master_process == 1) { 
#ifdef UWSGI_AS_SHARED_LIBRARY
        int ml_ret = master_loop(uwsgi.argv, uwsgi.environ);
        if (ml_ret == -1) {
            return 0;
        }    
#else
        (void) master_loop(uwsgi.argv, uwsgi.environ);
#endif
        //from now on the process is a real worker
    }    
    ...

    // !!!worker进入worker循环!!!
    uwsgi_worker_run();
    _exit(0);
}
```

我们不看master循环了，只看worker循环。不理解，为何这一个函数，能进入到多个无限循环的童鞋，可以移步[参考文档](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#references)，了解一下`fork`系统调用。
接下来进入到`uwsgi_worker_run()`函数：

```
void uwsgi_worker_run() {
    ...

    uwsgi_ignition();

    // never here
    exit(0);

}
```

然后进入到`uwsgi_ignition()`函数：

```c
void uwsgi_ignition() {
    ...

    else {
        if (uwsgi.async < 2) {
            simple_loop();
        }
        else {
            async_loop();
        }
    }

    // end of the process...
    end_me(0);
}
```

我们只看`simple_loop()`函数的源代码。

**5，simple_loop()函数的主要代码[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
core/loop.c：

```c
void simple_loop() {
    uwsgi_loop_cores_run(simple_loop_run);
}

void uwsgi_loop_cores_run(void *(*func) (void *)) {
    int i;
    for (i = 1; i < uwsgi.threads; i++) {
        long j = i;
        pthread_create(&uwsgi.workers[uwsgi.mywid].cores[i].thread_id, &uwsgi.threads_attr, func, (void *) j); 
    }
    long y = 0;
    func((void *) y); 
}
```

这段代码表明，uwsgi开启了`uwsgi.threads`（包括主线程）个**操作系统线程**，并发的运行`simple_loop_run()`函数：

```c
void *simple_loop_run(void *arg1) {
    ...

    // !!!在uwsgi_setup_thread_req()函数中调用了所有请求插件的init_thread钩子。!!!
    // !!!python插件的init_thread钩子 uwsgi_python_init_thread()函数，会为线程创建了一个ThreadState对象，并保存到Thread Local中，后续的GET_GIL 和 RELEASE_GIL都会用到这些ThreadState状态，这是C/C++多线程调用Python的约定!!!
    if (uwsgi.threads > 1) {
        uwsgi_setup_thread_req(core_id, wsgi_req);
    }
    ...

    // 下面的代码就是和操作系统平台相关的了，因为不同的平台实现了不同的IO多路复用机制，笔者主要就epoll进行说明
    // ！！！创建一个用于轮询的epoll描述符！！！
    // initialize the main event queue to monitor sockets
    int main_queue = event_queue_init();

    // !!!向epoll描述符中，添加事件!!!
    uwsgi_add_sockets_to_queue(main_queue, core_id);
    ...

    // ok we are ready, let's start managing requests and signals
    while (uwsgi.workers[uwsgi.mywid].manage_next_request) {

        // ！！！初始化wsgi_req对象！！！
        wsgi_req_setup(wsgi_req, core_id, NULL);

        // !!!该函数的详细说明在下面，点此跳转!!!
        if (wsgi_req_accept(main_queue, wsgi_req)) {
            continue;
        }   

        // !!!该函数的详细说明在下面，点此跳转!!!
        if (wsgi_req_recv(main_queue, wsgi_req)) {
            uwsgi_destroy_request(wsgi_req);
            continue;
        }   

        // !!!释放wsgi_req中的资源!!!
        uwsgi_close_request(wsgi_req);
    } 
    ...

}
```

下面是被`simple_loop_run()`函数所调用的一些（和epoll相关的）代码的细节：
core/event.c：

```c
int event_queue_init() {
    int epfd;


    epfd = epoll_create(256);

    if (epfd < 0) { 
        uwsgi_error("epoll_create()");
        return -1;
    }    

    return epfd;
}

int event_queue_add_fd_read(int eq, int fd) {

    uwsgi_log("== event_queue_add_fd_read ==\n");

    struct epoll_event ee;

    memset(&ee, 0, sizeof(struct epoll_event));
    ee.events = EPOLLIN;
    ee.data.fd = fd;

    if (epoll_ctl(eq, EPOLL_CTL_ADD, fd, &ee)) {
        uwsgi_error("epoll_ctl()");
        return -1;
    }    

    return 0;
}
```

core/util.c：

```c
// !!!accept请求!!!
// accept a request
int wsgi_req_accept(int queue, struct wsgi_request *wsgi_req) {
    ...

    // !!!序列化accept，防止惊群效应!!!
    thunder_lock;
    ...

    // !!!调用epoll_wait收集发生事件的一个文件描述符，并保存到interesting_fd!!!
    ret = event_queue_wait(queue, timeout, &interesting_fd);
    if (ret < 0) {
        thunder_unlock;
        return -1;
    }
    ...

    // 循环检测是哪个server socket发生了事件，然后accept请求，并设置wsgi_req对象
    while (uwsgi_sock) {
        if (interesting_fd == uwsgi_sock->fd || (uwsgi_sock->retry && uwsgi_sock->retry[wsgi_req->async_id]) || (uwsgi_sock->fd_threads && interesting_fd == uwsgi_sock->fd_threads[wsgi_req->async_id])) {
            wsgi_req->socket = uwsgi_sock;
            wsgi_req->fd = wsgi_req->socket->proto_accept(wsgi_req, interesting_fd);
            thunder_unlock;
            if (wsgi_req->fd < 0) {
                if (uwsgi.threads > 1)
                    pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, &ret);
                return -1;
            }

            if (!uwsgi_sock->edge_trigger) {
                uwsgi_post_accept(wsgi_req);
            }

            // !!! 返回0 表示成功accept了请求!!!
            return 0;
        }

        uwsgi_sock = uwsgi_sock->next;
    }
    ...
}
```

core/utils.c：

```c
// ！！！接收并处理请求！！！
// receive a new request
int wsgi_req_recv(int queue, struct wsgi_request *wsgi_req) {
    ...

    // 读取请求
    // edge triggered sockets get the whole request during accept() phase
    if (!wsgi_req->socket->edge_trigger) {
        for (;;) {
            int ret = wsgi_req->socket->proto(wsgi_req);
            if (ret == UWSGI_OK)
                break;
            if (ret == UWSGI_AGAIN) {
                ret = uwsgi_wait_read_req(wsgi_req);
                if (ret <= 0)
                    return -1;
                continue;
            }
            return -1;
        }
    }
    ...

    // 根据header头中的modifier1选择调用哪一个请求插件的request钩子
    wsgi_req->async_status = uwsgi.p[wsgi_req->uh->modifier1]->request(wsgi_req);

    return 0;
}
```

因为我们使用的是python请求插件，所以看一下python的request钩子`uwsgi_request_wsgi`函数：
plugins/python/python_plugin.c：

```c
int uwsgi_request_wsgi(struct wsgi_request *wsgi_req) {
    ...
    struct uwsgi_app *wi;

    // !!! 获取到uwsgi_app实例 !!!
    wi = &uwsgi_apps[wsgi_req->app_id];
    ...

    // !!!获取GIL!!!
    UWSGI_GET_GIL

    // no fear of race conditions for this counter as it is already protected by the GIL
    wi->requests++;

    // !!! 创建wsgi环境变量 !!!
    // create WSGI environ
    wsgi_req->async_environ = up.wsgi_env_create(wsgi_req, wi);

    // !!!构建调用WSGI应用程序所需要的参数，并且调用WSGI应用程序!!!
    wsgi_req->async_result = wi->request_subhandler(wsgi_req, wi);

    // !!!迭代WSGI应用程序的返回，并发送响应!!!
    while (wi->response_subhandler(wsgi_req) != UWSGI_OK) {
            if (uwsgi.async > 1) {
                UWSGI_RELEASE_GIL
                wsgi_req->async_force_again = 1;
                return UWSGI_AGAIN;
            }   
            else {
                wsgi_req->switches++;
            }   
        }  
    }
    ...

    // !!!释放GIL!!!
    UWSGI_RELEASE_GIL
    ....

}
```

综上，worker循环的大致流程就是：不断的accept连接 -> 读取请求 -> 处理请求 -> 发送响应。

###### 完毕！

------

### 值得关注的一些东西[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]

**1，在C/C++中嵌入Python时，C/C++代码中开启的线程 与 Python代码中开启的线程的关系[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
C/C++通过pthread库创建的线程是操作系统的原生线程，Python中创建的线程也是操作系统的原生线程，都是由操作系统来调度的。
Python中的线程每次被操作系统调度到的时候，需要先获取解释器实例的GIL。严格意义上说，Python中的多线程属于协同式多任务处理，在Python2中，线程不间断的执行100条字节码指令时，就会主动释放GIL，线程在等待I/O的时候，也会释放GIL。这是Python线程，在原生线程基础上的自身的特色。
当在C/C++中使用Python的C API的时候，只要遵循Python关于多线程的相应约定（GET GIL -> 将PyThreadState对象载入解释器 -> 执行Python代码 -> 清除PyThreadState对象 -> 释放GIL），那么C/C++创建的线程 和 Python本身创建的线程 本质都是一样的。

**2，插件化开发[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
uwsgi使用的是插件化的开发方式。启动时，加载相关的若干个插件（比如python请求插件），并对这些插件进行初始化；运行时，根据输入，调用相应的插件的钩子函数，来完成处理。uwsgi只需要完成**主流程**和通用功能，而将具体实现交给插件去做。这种可插拔的方式，是非常值得借鉴的。

**3，并发模型[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]**
uwsgi采用的是经典的 单master/多worker 并发模型。master负责信号处理，初始化，创建并管理worker进程，以及绑定监听sockets。worker的每个线程，处在这样的一个循环中：accept -> recv -> handle request -> send response。

------

### 参考文档[[TOC](http://timd.cn/uwsgi-source-code-analysis/?utm_source=tuicool&utm_medium=referral#toc)]

- [Python八荣八耻](https://www.cnblogs.com/dyx1024/archive/2012/05/03/2556674.html)
- [Linux进程管理——fork()和写时复制](https://www.cnblogs.com/wuchanming/p/4495479.html)
- [C++多线程调用python](http://www.cppblog.com/API/archive/2013/12/06/204618.html)