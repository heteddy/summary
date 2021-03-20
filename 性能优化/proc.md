

Linux系统上的/proc目录是一种文件系统，即proc文件系统。与其它常见的文件系统不同的是，**/proc是一种伪文件系统（也即虚拟文件系统），存储的是当前内核运行状态的一系列特殊文件，用户可以通过这些文件查看有关系统硬件及当前正在运行进程的信息，甚至可以通过更改其中某些文件来改变内核的运行状态。**

基于/proc文件系统如上所述的特殊性，其内的文件也常被称作虚拟文件，并具有一些独特的特点。例如，其中有些文件虽然使用查看命令查看时会返回大量信息，但文件本身的大小却会显示为0字节。此外，这些特殊文件中大多数文件的时间及日期属性通常为当前系统时间和日期，这跟它们随时会被刷新（存储于RAM中）有关。

为了查看及使用上的方便，这些文件通常会按照相关性进行分类存储于不同的目录甚至子目录中，如/proc/scsi目录中存储的就是当前系统上所有SCSI设备的相关信息，/proc/N中存储的则是系统当前正在运行的进程的相关信息，其中N为正在运行的进程（可以想象得到，在某进程结束后其相关目录则会消失）。

大多数虚拟文件可以使用文件查看命令如cat、more或者less进行查看，有些文件信息表述的内容可以一目了然，但也有文件的信息却不怎么具有可读性。不过，这些可读性较差的文件在使用一些命令如apm、free、lspci或top查看时却可以有着不错的表现。



```bash
[root@education_01 /proc/888]# ll
total 0
dr-xr-xr-x 2 teddy teddy 0 Feb 26 01:54 attr
-rw-r--r-- 1 root  root  0 Mar 17 10:52 autogroup
-r-------- 1 root  root  0 Mar 17 10:52 auxv
-r--r--r-- 1 root  root  0 Mar 17 10:52 cgroup
--w------- 1 root  root  0 Mar 17 10:52 clear_refs
-r--r--r-- 1 root  root  0 Feb 18 11:27 cmdline
-rw-r--r-- 1 root  root  0 Mar 17 10:52 comm
-rw-r--r-- 1 root  root  0 Mar 17 10:52 coredump_filter
-r--r--r-- 1 root  root  0 Mar 17 10:52 cpuset
lrwxrwxrwx 1 root  root  0 Feb 18 11:28 cwd -> /data/essencareer/jingzhi-corp/backend
-r-------- 1 root  root  0 Mar 17 10:52 environ
lrwxrwxrwx 1 root  root  0 Feb 18 11:27 exe -> /usr/local/python3/bin/uwsgi
dr-x------ 2 root  root  0 Feb 18 11:27 fd
dr-x------ 2 root  root  0 Mar 17 10:52 fdinfo
-rw-r--r-- 1 root  root  0 Mar 17 10:52 gid_map
-r-------- 1 root  root  0 Mar 15 17:53 io
-r--r--r-- 1 root  root  0 Mar 17 10:52 limits
-rw-r--r-- 1 root  root  0 Mar 17 10:52 loginuid
dr-x------ 2 root  root  0 Mar 17 10:52 map_files
-r--r--r-- 1 root  root  0 Feb 18 11:28 maps
-rw------- 1 root  root  0 Mar 17 10:52 mem
-r--r--r-- 1 root  root  0 Mar 17 10:52 mountinfo
-r--r--r-- 1 root  root  0 Mar 17 10:52 mounts
-r-------- 1 root  root  0 Mar 17 10:52 mountstats
dr-xr-xr-x 5 teddy teddy 0 Mar 17 10:52 net
dr-x--x--x 2 root  root  0 Feb 18 11:28 ns
-r--r--r-- 1 root  root  0 Mar 17 10:52 numa_maps
-rw-r--r-- 1 root  root  0 Mar 17 10:52 oom_adj
-r--r--r-- 1 root  root  0 Mar 17 10:52 oom_score
-rw-r--r-- 1 root  root  0 Mar 17 10:52 oom_score_adj
-r--r--r-- 1 root  root  0 Mar 17 10:52 pagemap
-r-------- 1 root  root  0 Mar 17 10:52 patch_state
-r--r--r-- 1 root  root  0 Mar 17 10:52 personality
-rw-r--r-- 1 root  root  0 Mar 17 10:52 projid_map
lrwxrwxrwx 1 root  root  0 Feb 18 11:28 root -> /
-rw-r--r-- 1 root  root  0 Mar 17 10:52 sched
-r--r--r-- 1 root  root  0 Mar 17 10:52 schedstat
-r--r--r-- 1 root  root  0 Mar 17 10:52 sessionid
-rw-r--r-- 1 root  root  0 Mar 17 10:52 setgroups
-r--r--r-- 1 root  root  0 Mar 17 10:52 smaps
-r--r--r-- 1 root  root  0 Mar 17 10:52 stack
-r--r--r-- 1 root  root  0 Feb 18 11:27 stat
-r--r--r-- 1 root  root  0 Mar 17 10:52 statm
-r--r--r-- 1 root  root  0 Feb 18 11:27 status
-r--r--r-- 1 root  root  0 Mar 17 10:52 syscall
dr-xr-xr-x 3 teddy teddy 0 Mar 17 10:52 task
-r--r--r-- 1 root  root  0 Mar 17 10:52 timers
-rw-r--r-- 1 root  root  0 Mar 17 10:52 uid_map
-r--r--r-- 1 root  root  0 Mar 17 10:52 wchan
[root@education_01 /proc/888]#
```

>   cmdline — 启动当前进程的完整命令，但僵尸进程目录中的此文件不包含任何信息；

```
[root@education_01 /proc/888]# cat cmdline
/usr/local/python3/bin/uwsgi--ini/data/essencareer/jingzhi-corp/doc/conf/uwsgi/eduwsgi.ini
```

>   cwd 命令运行的路径

```
[root@education_01 /proc/888]# ll cwd
lrwxrwxrwx 1 root root 0 Feb 18 11:28 cwd -> /data/essencareer/jingzhi-corp/backend
```

>   environ — 当前进程的环境变量列表，彼此间用空字符（NULL）隔开；变量用大写字母表示，其值用小写字母表示；

>   exe — 指向启动当前进程的可执行文件（完整路径）的符号链接，通过/proc/N/exe可以启动当前进程的一个拷贝；

>   fd — 这是个目录，包含当前进程打开的每一个文件的文件描述符（file descriptor），这些文件描述符是指向实际文件的一个符号链接；

>   maps — 当前进程关联到的每个可执行文件和库文件在内存中的映射区域及其访问权限所组成的列表；

>   root — 指向当前进程运行根目录的符号链接

>   task — 目录文件，包含由当前进程所运行的每一个线程的相关信息，每个线程的相关信息文件均保存在一个由线程号（tid）命名的目录中，这类似于其内容类似于每个进程目录中的内容；（内核2.6版本以后支持此功能）

>   /proc/modules 当前装入内核的所有模块名称列表，可以由lsmod命令使用，也可以直接查看

>   /proc/pci