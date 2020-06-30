总体结构图

虚拟文件系统和文件系统簇以及`page cache`,`buffer cache`的关系；文件的通用块io，驱动程序，address_space。回写关系

# 虚拟文件系统vfs



## 选项

`void* mmap(void* addr, size_t len, int prot, int flag, int fd, off_t off)`

MAP_SHARED //与其它所有映射这个对象的进程共享映射空间。对共享区的写入，相当于输出到文件。直到msync()或者[munmap](https://baike.baidu.com/item/munmap)()被调用，文件实际上不会被更新。

MAP_PRIVATE //建立一个写入时拷贝的私有映射。内存区域的写入不会影响到原文件。这个标志和以上标志是互斥的，只能使用其中一个。

## mmap内存映射原理

mmap是一种内存映射文件的方法，即将一个文件或者其他对象映射到进程的地址空间，实现文件磁盘地址和进程虚拟地址空间中一段虚拟地址的一一对应关系；实现这样的映射关系后，进程就可以采用指针的方式读写操作这一块内存，而系统会自动回写脏页面到对应的文件磁盘上，即完成了对文件的操作而不必调用read，write等系统调用函数，相反，内核空间堆这段区域的修改也直接反应到用户空间，从而可以实现不同进程间的文件共享。

![1492538-65c592785f5e64a4.png](https://upload-images.jianshu.io/upload_images/9243349-b0c558e9f551b0fc.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

- 进程的虚拟地址空间，由多个虚拟内存区域构成。
- 虚拟内存区域是进程的虚拟地址空间中的一个同质区间，即具有同样特性的连续地址范围。
- text数据段，初始数据段，BSS数据段，堆，栈和内存映射都是一个独立的虚拟内存区域。
- 为内存映射服务的地址空间处于堆栈之外的空余部分。

**mmap内存映射的实现过程，可分为三个阶段**

进程启动映射过程，并在虚拟地址空间中为映射创建虚拟映射区域

- 进程在用户空间调用mmap函数
- 在当前进程的虚拟地址空间中，寻找一段空闲的满足要求的连续的虚拟地址
- 为此虚拟去分配一个vm_area_struct结构，并对该结构各个域进行初始化
- 将新建的vm_area_struct插入到进程的虚拟地址区域链表或树中

## vm_area_struct

vm_area_struct ：虚拟内存管理的最基本单元，描述的是一段连续的，具有相同访问属性的虚拟空间，该空间的大小为物理内存页面的整数倍。

linux内核实用 vm_area_struct 来表示一个独立的虚拟内存区域，由于每个不同质的虚拟内存区域功能和内部机制不同，因此一个进程实用多个vm_area_struct结构来分别表示不同类型的虚拟内存区域。各个vm_area_struct实用链表或者树形结构连接，方便进程快速访问。

![1492538-0cdca89bda99d8b6.png](https://upload-images.jianshu.io/upload_images/9243349-a33307285a6d2491.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

**task_struct:**进程控制模块；
**mm_struct：**进程所拥有的内存描述符；

## 调用内核空间的系统调用函数mmap（不同于用户空间），实现文件的物理地址和进程的虚拟地址的一一映射关系。

- 为映射分配了新的虚拟地址区域后，通过待映射的文件指针，在文件描述符表中找到对应的文件描述符，通过文件描述符，连接到内核“已打开文集”中该文件的文件结构体struct file，每个文件结构体维护着和这个已打开文件的相关信息。
- 通过该文件的文件结构体，连接到file_operations模块，调用 内核函数mmap，int mmap(struct file *filep,struct vm_area_struct *vma)
- 内核mmap函数通过虚拟文件系统inode模块定位到文件磁盘物理地址。
- 通过remap_pfn_range函数建立页表，即实现了文件地址和虚拟地址区域的映射，此时这片虚拟地址区域没有任何数据关联到主存中

## 进程发起对这片映射空间的访问，引发缺页异常，实现文件内容到物理内存的拷贝。

- 进程的读写操作访问虚拟地址空间的这一段映射地址，通过查询页表，发现这一段地址不在物理页面上，因为只是建立了地址映射，真正的磁盘数据还没有拷贝到内存中，因此引发缺页异常
- 缺页异常进行一系列判断，确定无非法操作后，内核发起请求调页过程
- 调页过程先在交换缓存空间中寻找需要访问的内存页，如果没有则调用nopage函数把所缺的页面从磁盘装入主存中
- 之后进程可对这片主存进行读或写操作，如果写操作改变了内容，一定时间后系统会自动回写脏页面到对应的磁盘地址，也就是完成了写入到文件的过程
- 修改过的脏页面不会立即更新到文件中，而是有一段时间的延迟，可以调用msync来强制同步，这样所写的内容就立即保存到文件里了。

## mmap

![图6](https://img-blog.csdn.net/20180428163208382?watermark/2/text/aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L0dESjAwMDE=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70)图6

![图7](https://img-blog.csdn.net/20180428163400198?watermark/2/text/aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L0dESjAwMDE=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70)图7

图6中的“只读”标志不是说映射的内容是只读的，这仅仅是内核为了节省物理内存而采用的对于物理内存的一种“欺骗手段”而已。如果两个进程只是读取文件中的内容，不做任何的改动，那么文件只在物理内存中保留一份；但是如果有一个进程，如render，要对文件中的内容做出改动，那么会触发缺页中断，内核采用<font color=red>写时复制技术</font>，为要改动的内容对应的页重新分配一个物理页框，将被改动的内容对应的物理页框中的数据复制到新分配的物理页框中，再进行改动。此时新分配的物理页框对于render而言是它自己“私有的”，别的进程是看不到的，也不会被同步到后备的存储中。但是如果是共享映射，所有的进程都是共享同一块页缓存的，此时被映射的文件的数据在内存中只保留一份。任何一个进程对映射区进行读或者写，都不会导致对页缓冲数据的复制。

mmap的系统调用函数原型为`void* mmap(void* addr, size_t len, int prot, int flag, int fd, off_t off)`。其中，flag指定了是私有映射还是共享映射，私有映射的写会引发缺页中断，然后复制对应的物理页框到新分配的页框中。prot指定了被映射的文件是可读、可写、可执行还是不可访问。如果prot指定的是可读，但是却对映射文件执行写操作，则此时却缺页中断会引起段错误，而不是进行写时复制。

**那么此时存在另一个问题就是当最后一个render进程退出之后，存储scene.dat的页缓存是不是会被马上释放掉？**当然不是！在一个进程中打开一个文件使用完之后该进程退出，然后在另一个进程中使用该文件这种情况通常是很常见的，页缓存的管理中必须考虑到这种情况。况且从页缓存中读取数据的时间是ns级别，但是从硬盘中读取数据的时间是ms级别，因此如果能够在使用数据的时候命中页缓存，那么对于系统的性能将非常有帮助。那么，问题来了，什么时候该文件对应的页缓存要被换出内存呢?就是系统中的内存紧张，必须要换出一部分物理页到硬盘中或者交换区中，以腾出更多的空间给即将要使用的数据的时候。所以只要系统中存在空闲的内存，那么页缓存就不会被换出，直到到达页缓存的上限为止。是否换出某一页缓存不是由某一个进程决定的，而是由操作系统在整个系统空间中的资源分配决定的。毕竟，从页缓存中读取数据要比从硬盘上读取数据要快的多了。

# 文件系统簇

## 分类

### 日志文件系统

#### 访问模式：

+ 回写（write back）：日志只记录对元数据的修改，实际数据的修改不记录日志
+ 顺序（ordered）模式：日志只记录对元数据的修改，写入元数据之前收集实际数据的修改，以组的形式写入。
+ 日志journal模式：实际数据和元数据都写入日志

### 网络文件系统



# page cache

## 页缓存的实现：

页缓存是以页为单位进行数据管理的，那么必须在内核中标识该物理页。其实每个真正存放数据的物理页帧都对应一个管理结构体，称之为struct page，其结构体如下。

```C

struct page  {
    unsigned long    flags;
    atomic_t    _count;
    atomic_t    _mapcount;
    unsigned long    private;
    struct address_space    *mapping;
    pgoff_t    index;
    struct list_head    lru;
    void*    virtual;
}
```

 flags:  描述page当前的状态和其他信息，如当前的page是否是脏页**PG_dirty**；是否是最新的已经同步到后备存储的页**PG_uptodate**; 是否处于lru链表上等；

+ _count：引用计数，标识内核中引用该page的次数，如果要操作该page，引用计数会+1，操作完成之后-1。当该值为0时，表示没有引用该page的位置，所以该page可以被解除映射，这在内存回收的时候是有用的；

+ _mapcount:  页表被映射的次数，也就是说page同时被多少个进程所共享，初始值为-1，如果只被一个进程的页表映射了，该值为0。

+ lru:当page被用户态使用或者是当做页缓存使用的时候，将该page连入zone中的lru链表，供内存回收使用；

+ _mapping有三种含义：

  a.如果mapping  =  0，说明该page属于交换缓存（swap cache); 当需要地址空间时会指定交换分区的地址空间swapper_space;

  b.如果mapping !=  0,  bit[0]  =  0,  说明该page属于页缓存或者文件映射，mapping指向文件的地址空间address_space；

  c.如果mapping !=  0,  bit[0]  !=0 说明该page为匿名映射，mapping指向struct  anon_vma对象

**页缓存就是将一个文件在内存中的所有物理页所组成的一种树形结构，我们称之为基数树，用于管理属于同一个文件在内存中的缓存内容。**

<font color=red size=4>address_space与inode是一一对应的关系</font>

一个文件在内存中对应的所有物理页组成了一棵基数树。而一个文件在内存中具有唯一的inode结构标识，inode结构中有该文件所属的设备及其标识符，因而，根据一个inode能够确定其对应的后备设备。<font color=red>为了将文件在物理内存中的页缓存和文件及其后备设备关联起来，linux内核引入了address_space结构体。可以说address_space结构体是将页缓存和文件系统关联起来的桥梁</font>，其组成如下：

```C
struct address_space {
    struct inode*    host;/*指向与该address_space相关联的inode节点*/
    struct radix_tree_root    page_tree;/*所有页形成的基数树根节点*/
    spinlock_t    tree_lock;/*保护page_tree的自旋锁*/
    unsigned int    i_map_writable;/*VM_SHARED的计数*/
    struct prio_tree_root    i_map;         
    struct list_head    i_map_nonlinear;
    spinlock_t    i_map_lock;/*保护i_map的自旋锁*/
    atomic_t    truncate_count;/*截断计数*/
    unsigned long    nrpages;/*页总数*/
    pgoff_t    writeback_index;/*回写的起始位置*/
    struct address_space_operation*    a_ops;/*操作表*/
    unsigned long    flags;/*gfp_mask掩码与错误标识*/
    struct backing_dev_info*    backing_dev_info;/*预读信息*/
    spinlock_t    private_lock;/*私有address_space锁*/
    struct list_head    private_list;/*私有address_space链表*/
    struct address_space*    assoc_mapping;/*相关的缓冲*/
}
```

struct prio_tree_root:与该地址空间相关联的所有进程的虚拟地址区间vm_area_struct所对应的整个进程地址空间mm_struct形成的优先查找树的根节点;vm_area_struct中如果有后备存储，则存在prio_tree_node结构体，通过该prio_tree_node和prio_tree_root结构体，构成了所有与该address_space相关联的进程的一棵优先查找树，便于查找所有与该address_space相关联的进程；

下面列出struct prio_tree_root和struct  prio_tree_node的结构体。

```c
struct  prio_tree_root {
    struct prio_tree_node*  prio_tree_root;
    unsigned short              index_bits;
};
struct prio_tree_node {
    struct prio_tree_node*  left;
    struct prio_tree_node*  right; 
    struct prio_tree_node*  parent;
    unsigned long                start;
    unsigned long                last;
};
      
```

   为了便于形成页缓存、文件和进程之间关系的清晰思路，文章画出一幅图，如图2所示。

![图 2 页缓存及其相关结构](https://img-blog.csdn.net/201804281624126?watermark/2/text/aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L0dESjAwMDE=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70)

从以上可以解释可以看出，address_space成为构建页缓存和文件、页缓存和共享该文件的所有进程之间的桥梁。

每个进程的地址空间使用mm_struct结构体标识，该结构体中包含一系列的由vm_area_struct结构体组成的连续地址空间链表。每个vm_area_struct中存在struct  file* vm_file用于指向该连续地址空间中所打开的文件，而vm_file通过struct file中的struct  path与struct  dentry相关联。  struct dentry中通过inode指针指向inode，inode与address_space一一对应，至此形成了页缓存与文件系统之间的关联；为了便于查找与某个文件相关联的所有进程，address_space中的prio_tree_root指向了所有与该页缓存相关联的进程所形成的优先查找树的根节点。关于这种关系的详细思路请参考图1，这里画出其简化图，如图3。

![图 3 页缓存、文件系统、进程地址空间简化关系图](https://img-blog.csdn.net/20180428162503141?watermark/2/text/aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L0dESjAwMDE=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70)
        这里需要说明的linux中文件系统的一点是，内核为每个进程在其地址空间中都维护了结构体struct* fd_array[]用于维护该进程地址空间中打开的文件的指针；同时内核为所有被打开的文件还维护了系统级的一个文件描述符表用以记录该系统打开的所有文件，供所有进程之间共享；每个被打开的文件都由一个对应的inode结构体表示，由系统级的文件描述符表指向。所以，进程通过自己地址空间中的打开文件描述符表可以找到系统级的文件描述符表，进而找到文件。

## 页缓存、内存、文件IO之间的关系

进程发起读请求的过程如下：

1. 进程调用库函数read()向内核发起读文件的请求；
2. 内核通过检查进程的文件描述符定位到虚拟文件系统已经打开的文件列表项，调用该文件系统对VFS的read()调用提供的接口；
3. <font color=red>通过文件表项链接到目录项模块，根据传入的文件路径在目录项中检索，找到该文件的inode；</font>
4. inode中，通过文件内容偏移量计算出要读取的页(通过radix tree)；
5. 通过该inode的i_mapping指针找到对应的address_space页缓存树---基数树，查找对应的页缓存节点；
   1. 如果页缓存节点命中，那么直接返回文件内容；
   2. 如果页缓存缺失，那么产生一个缺页异常，首先创建一个新的空的物理页框，通过该inode找到文件中该页的磁盘地址，读取相应的页填充该页缓存（DMA的方式将数据读取到页缓存），更新页表项；重新进行第5步的查找页缓存的过程；

<font color=red size=4>**所有的文件内容的读取（无论一开始是命中页缓存还是没有命中页缓存）最终都是直接来源于页缓存。** </font>

<font color=red size=4>**当将数据从磁盘复制到页缓存之后，还要将页缓存的数据通过CPU复制到read调用提供的缓冲区中，这就是普通文件IO需要的两次复制数据复制过程。**</font>

+ 第一次是通过DMA的方式将数据从磁盘复制到页缓存中，本次过程只需要CPU在一开始的时候让出总线、结束之后处理DMA中断即可，中间不需要CPU的直接干预，CPU可以去做别的事情；
+ 第二次是将数据从页缓存复制到进程自己的的地址空间对应的物理内存中，这个过程中需要CPU的全程干预，浪费CPU的时间和额外的物理内存空间。**

写操作也是一样的，待写入的buffer在用户空间，必须将其先拷贝到内核空间对应的主存中，再写回到磁盘中，也是需要两次数据拷贝。mmap的使用减少了数据从用户空间到页缓存的复制过程，提高了IO的效率，尤其是对于大文件而言；对于比较小的文件而言，由于mmap执行了更多的内核操作，因此其效率可能比普通的文件IO更差。

[bio](https://blog.csdn.net/hty46565/article/details/74783749)

### buffer_head

![bio](https://img-blog.csdn.net/20170708091846985?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvaHR5NDY1NjU=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

​	说明:

+ 70的b_bdev指向具体的块设备。

+ 66中的b_blocknr指向逻辑块号。我们就知道了块是哪个块。

+ 64的b_page指向缓冲区位于哪个页面之中。

+ 68的b_data指向页面中的缓冲区开始的位置。

+ 67的b_size显示了缓冲区的大小是多少。

  

  从这几个域我们就知道了磁盘与内存的映射关系了。在内存页中，数据起始于b_data，到b_data+b_size。
  其它还有一些域，如b_state显示了buffer的状态。b_count表示了这个buffer_head的被用次数，若被用了就需要给它进行原子加1操作，这样其它地方就不能再重复使用了。
  显然，只知道内存与磁盘数据的对应关系还不行，我们还需要知道在内存中的具体的区域，也就是需要知道数据的容器。这个容器就是结构体bio。

### bio

![](https://img-blog.csdn.net/20170708221123819?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvaHR5NDY1NjU=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

95行bi_io_vec指向了一个bio_vec结构体数组。这个bio_vec结构体是一个比较关键的东西。我们看一下这个结构体。

![](https://img-blog.csdn.net/20170708221834715?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQvaHR5NDY1NjU=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

此结构体中的page大家应该比较熟悉，这个内存中的一个页面。bv_offset表示页中数据的偏移量，bv_len表示这个数据的长度。这下我们应该明白了。bio结构体拥有bio_vec结构体数组，每个结构体包含了一个页面中的一些“片段”。而这“片段”就是之前buffer_head描述的磁盘与内存中对应的块的连续数据。换句话说，“片段”由连续的内存缓冲区组成。
现在再回过头来看bio结构体。

既然知道了bi_io_vec指向bio_vec结构体数组的首地址。那么肯定就得知道数组的长度与当前正操作的bio_vec的索引。
这就是72行bi_vcnt域和73行bi_idx域。bi_vcnt记录数组的数量，bi_idx记录当前bi_vec结构体的索引数。

至此，磁盘与内存的映射关系的结构体我们了解了，块在内存中的数据容器的结构体我们也了解了。


## 页缓存中的数据如何实现和后备存储之间的同步？

普通文件IO，都是将数据直接写在页缓存上，那么页缓存中的数据何时写回后备存储？怎么写回？

### 何时写回

​			1.  空闲内存的值低于一个指定的阈值的时候，内核必须将脏页写回到后备存储以释放内存。因为只有干净的内存页才可以回收。当脏页被写回之后就变为PG_uptodate标志，变为干净的页，内核就可以将其所占的内存回收；

2. 当脏页在内存中驻留的时间超过一个指定的阈值之后，内核必须将该脏页写回到后备存储，以确定脏页不会在内存中无限期的停留；

3. 当用户进程显式的调用fsync、fdatasync或者sync的时候，内核按照要求执行回写操作。

### 由谁写回

> 为每个存储设备创建单独的刷新线程

系统中存在一个管理线程和多个刷新线程（每个持久存储设备对应一个刷新线程）。管理线程监控设备上的脏页面情况，若设备一段时间内没有产生脏页面，就销毁设备上的刷新线程；若监测到设备上有脏页面需要回写且尚未为该设备创建刷新线程，那么创建刷新线程处理脏页面回写。而刷新线程的任务较为单调，只负责将设备中的脏页面回写至持久存储设备中。

刷新线程刷新设备上脏页面大致设计如下：

+ 每个设备保存脏文件链表，保存的是该设备上存储的脏文件的inode节点。所谓的回写文件脏页面即回写该inode链表上的某些文件的脏页面。
+ 系统中存在多个回写时机，
  + 第一是应用程序主动调用回写接口（fsync，fdatasync以及sync等），
  + 第二管理线程周期性地唤醒设备上的回写线程进行回写，
  + 第三是某些应用程序/内核任务发现内存不足时要回收部分缓存页面而事先进行脏页面回写，设计一个统一的框架来管理这些回写任务非常有必要。

### 回写数据结构

首先，必须为每个设备创建相关的脏inode链表以及刷新线程，这些信息必须都记录在设备信息中，因此，设备信息中必须增加额外的成员变量以记录这些信息。同时，对于刷新线程部分，我们除了记录刷新线程的task结构外，还必须记录与该刷新线程相关的一些控制信息，如为了实现周期性地回写，必须记录上次回写时间等，也可以将脏inode链表记录在该结构体之中。

其次，为了实现周期性回写和释放缓存而导致的回写，可为**每次回写构造一个任务，发起回写的本质是构造这样一个任务，回写的执行者只是执行这样的任务**，当然，发起者需要根据其回写的意图（如数据完整性回写、周期性任务回写、释放缓存页面而进行的回写）设置任务的参数，执行者根据任务的参数决定任务的处理过程，结构相当清晰。为了增加这样一个任务数据结构，必须在设备中添加一个任务队列，以记录调用者发起的所有任务。

```c
struct backing_dev_info
struct bdi_writeback //记录线程的上次刷新时间以及脏inode链表
struct wb_writeback_work
struct writeback_control
```

每个设备均对应这样一个结构体，该结构体最初是为了设备预读而设计的，但内核后来对其扩充，增加了设备回写相关的成员变量。与设备脏文件回写的相关成员如下列举：

```c
 struct backing_dev_info {
     struct list_head bdi_list;
     .........
     struct bdi_writeback wb; 
     spinlock_t wb_lock;   
     struct list_head work_list;
     .........
 };
```

系统提供***bdi_list\***将所有设备的bdi结构串联成链表，便于统一管理；***wb\***是该设备对应的回写线程的数据结构，会在下面仔细描述；***work_list\***是设备上所有任务的链表，发起回写的调用者只是构造一个回写任务挂入该链表即可；***wb_lock\***是保护任务链表的锁。

前面说过，每个设备均创建了一个写回线程，每个写回线程不仅需要记录创建的进程结构，还需要记录线程的上次刷新时间以及脏inode链表等，这就是 ***bdi_writeback***。

```c
 struct bdi_writeback {
     struct backing_dev_info *bdi; /* our parent bdi */
     unsigned int nr;
     unsigned long last_old_flush; /* last old data flush */
     unsigned long last_active; /* last time bdi thread was active */
     struct task_struct *task; /* writeback thread */
     struct timer_list wakeup_timer; /* used for delayed bdi thread wakeup */
     struct list_head b_dirty; /* dirty inodes */
     struct list_head b_io; /* parked for writeback */
     struct list_head b_more_io; /* parked for more writeback */
 };
```

成员bdi指向设备结构体，*last_old_flush*记录上次刷新的时间，这是用于周期性回写之用，*last_active*记录回写线程的上次活动时间，该成员可用于销毁长时间不活跃的回写线程。*task*是刷新线程的进程结构，*b_dirty*是脏inode链表，每当一个文件被弄脏时，都会将其inode添加至所在设备的b_dirty链表中，至于*b_io*和*b_more_io*链表的作用在后面将仔细描述吧。

**struct wb_writeback_work**

前面说过，回写的过程实质上就是发起者构造一个回写任务，交给回写执行者去处理。这个任务就详细描述了本次回写请求的具体参数，内核中每个回写任务的具体参数如下描述：

```c
 struct wb_writeback_work {
     long nr_pages;
     struct super_block *sb;
     enum writeback_sync_modes sync_mode;
     unsigned int for_kupdate:1;
     unsigned int range_cyclic:1;
     unsigned int for_background:1;
     struct list_head list; /* pending work list */
     struct completion *done; /* set if the caller waits */
 };
```

*nr_pages*表示调用者指示本次回写任务需要回写的脏页面数。*sb*表示调用者是否指定需要回写设备上属于哪个文件系统的脏页面，因为前面我们说过，每个设备可能会被划分成多个分区以支持多个文件系统，sb如果没有被赋值，则由回写线程决定回写哪个文件系统上的脏页面。*sync_mode*代表本次回写任务同步策略，**WB_SYNC_NONE**代表什么？**WB_SYNC_ALL**又代表什么？**for_kupdate**代表本回写任务是不是由于周期性回写而发起的，**range_cyclic**表示什么？**for_background**表示什么？**list**和**done**又分别代表了什么？

**struct writeback_control**

该结构可当做上面所描述回写任务的子任务，即系统会将每次回写任务拆分成多个子任务去处理，原因会在后面仔细说明。

# 回写

## bdi(backing device info) 备用存储设备相关信息

为每个设备创建了`bdi-default` `flush-x:y`用于脏数据的刷盘，`x`代表主设备号，`y`代表当前设备号。

`bdi-default` 和`flush-x:y`

## 注册bdi设备：

系统挂载设备时候，通过`add_disk`向系统添加磁盘设备，`bdi_register_dev(bdi, disk_devt(disk))`,这些bdi设备会以链表的形式组织在全局变量bdi_list下。bdi_list全局变量在文件 include/linux/backing-dev.h。

## writeback

**bdi_writeback**:该数据结构封装了writeback的内核线程以及需要操作的inode队列。

**wb_writeback_work**:该数据结构封装了writeback的工作任务。

`/proc/sys/vm/dirty_writeback_centisecs`  默认值是500，单位是10ms。唤醒执行一次函数sync_supers，用来 下刷系统super_blocks链表中所有的元数据块信息。

[<ffffffffa0019abb>] ? mpt2sas_base_get_smid_scsiio+0x6b/0xb0 [mpt2sas] [<ffffffffa001a6d7>] ? mpt2sas_base_get_msg_frame+0x57/0x60 [mpt2sas] [<ffffffffa00246fe>] ? _scsih_qcmd+0x17e/0x9b0 [mpt2sas] [<ffffffff81253de3>] ? ftrace_raw_event_id_block_rq+0x153/0x190 [<ffffffff81363591>] ? scsi_dispatch_cmd+0x101/0x360

[<ffffffff8136b08d>] ? scsi_request_fn+0x41d/0x790

[<ffffffff8107c981>] ? ftrace_raw_event_timer_cancel+0xa1/0xb0 [<ffffffff81255601>] ? __blk_run_queue+0x31/0x40 [<ffffffff8126e4f9>] ? cfq_insert_request+0x469/0x5b0 [<ffffffff8124f6d1>] ? elv_insert+0xd1/0x1a0

[<ffffffff8124f7ea>] ? __elv_add_request+0x4a/0x90 [<ffffffff81258903>] ? __make_request+0x103/0x5a0 [<ffffffff81254512>] ? ftrace_raw_event_id_block_bio+0xf2/0x100 [<ffffffff81256efe>] ? generic_make_request+0x25e/0x530 [<ffffffff8125728c>] ? submit_bio+0xbc/0x160

[<ffffffff811acd46>] ? submit_bh+0xf6/0x150
 [<ffffffffa01097a3>] ? ext4_mb_init_cache+0x883/0x9f0 [ext4] [<ffffffff8112b560>] ? __lru_cache_add+0x40/0x90 [<ffffffffa0109a2e>] ? ext4_mb_init_group+0x11e/0x210 [ext4] [<ffffffffa0109bed>] ? ext4_mb_good_group+0xcd/0x110 [ext4] [<ffffffffa010b38b>] ? ext4_mb_regular_allocator+0x19b/0x410 [ext4] [<ffffffffa010d25d>] ? ext4_mb_new_blocks+0x38d/0x560 [ext4] [<ffffffffa0100afe>] ? ext4_ext_find_extent+0x2be/0x320 [ext4] [<ffffffffa0103bb3>] ? ext4_ext_get_blocks+0x1113/0x1a10 [ext4] [<ffffffff810edb54>] ? rb_reserve_next_event+0xb4/0x370 [<ffffffff810edfc2>] ? ring_buffer_lock_reserve+0xa2/0x160 [<ffffffffa00dfd79>] ? ext4_get_blocks+0xf9/0x2a0 [ext4] [<ffffffff81012bd9>] ? read_tsc+0x9/0x20
 [<ffffffff8109cd39>] ? ktime_get_ts+0xa9/0xe0
 [<ffffffffa00e1c21>] ? mpage_da_map_and_submit+0xa1/0x450 [ext4] [<ffffffff81277ef5>] ? radix_tree_gang_lookup_tag_slot+0x95/0xe0 [<ffffffff81113bd0>] ? find_get_pages_tag+0x40/0x120 [<ffffffffa00e203d>] ? mpage_add_bh_to_extent+0x6d/0xf0 [ext4] [<ffffffffa00e238f>] ? write_cache_pages_da+0x2cf/0x470 [ext4] [<ffffffffa00e2802>] ? ext4_da_writepages+0x2d2/0x620 [ext4] [<ffffffff811299e1>] ? do_writepages+0x21/0x40
 [<ffffffff811a500d>] ? writeback_single_inode+0xdd/0x2c0 [<ffffffff811a544e>] ? writeback_sb_inodes+0xce/0x180 [<ffffffff811a55ab>] ? writeback_inodes_wb+0xab/0x1b0 [<ffffffff811a594b>] ? wb_writeback+0x29b/0x3f0
 [<ffffffff814fd9b0>] ? thread_return+0x4e/0x76e
 [<ffffffff8107eb42>] ? del_timer_sync+0x22/0x30
 [<ffffffff811a5c39>] ? wb_do_writeback+0x199/0x240 [<ffffffff811a5d43>] ? bdi_writeback_task+0x63/0x1b0 [<ffffffff81091f97>] ? bit_waitqueue+0x17/0xd0
 [<ffffffff81138640>] ? bdi_start_fn+0x0/0x100
 [<ffffffff811386c6>] ? bdi_start_fn+0x86/0x100
 [<ffffffff81138640>] ? bdi_start_fn+0x0/0x100
 [<ffffffff81091d66>] ? kthread+0x96/0xa0
 [<ffffffff8100c14a>] ? child_rip+0xa/0x20s

[<ffffffff81091cd0>] ? kthread+0x0/0xa0

[<ffffffff8100c140>] ? child_rip+0x0/0x20



从函数栈信息，我们可以看出flush-x:y内核线程执行流程为` bdi_start_fn()--> bdi_writeback_task()--> wb_do_writeback() -->wb_writeback()--> writeback_inodes_wb()--> writeback_sb_inodes() --> writeback_single_inode()--> do_writepages() --> ext4_da_writepages() --> ...`

# 读流程

```c
fsync(int fd)(位于fs/sync.c中)
--->do_fsync(fd, 0)（位于fs/sync.c中）
    --->vfs_fsync(file, datasync)（位于fs/sync.c中）
        --->vfs_fsync_range(file, 0, LLONG_MAX, datasync)（位于fs/sync.c中）
            --->filemap_write_and_wait_range(mapping,start, end)（位于mm/filemap.c中）
                --->__filemap_fdatawrite_range(mapping,lstart, lend,WB_SYNC_ALL)（位于mm/filemap.c中）
                    --->filemap_fdatawait_range(mapping,lstart,lend)（位于mm/filemap.c中）
                        --->ext2_fsync(struct file*file, int datasync)（针对ext2文件系统，位于fs/ext2/file.c）
                            --->generic_file_fsync(file, datasync)（位于fs/libfs.c中）
```

+ `sys_read`

  通过fd得到对应的file结构，然后调用`vfs_read`；

+ `vfs_read`：

  各种权限及文件锁的检查，然后调用file->f_op->read（若不存在则调用do_sync_read）。file->f_op是从对应的inode->i_fop而来，而inode->i_fop是由对应的文件系统类型在生成这个inode时赋予的。file->f_op->read很可能就等同于`do_sync_read`；

+ `do_sync_read`: 

  f_op->read是完成一次同步读，而f_op->aio_read完成一次异步读。do_sync_read则是利用f_op->aio_read这个异步读操作来完成同步读，也就是在发起一次异步读之后，如果返回值是-EIOCBQUEUED，则进程睡眠，直到读完成即可。但实际上对于磁盘文件的读，f_op->aio_read一般不会返回-EIOCBQUEUED，除非是设置了O_DIRECT标志aio_read，或者是对于一些特殊的文件系统（如nfs这样的网络文件系统）

+ f_op->aio_read

  这个函数通常是由generic_file_aio_read或者其封装来实现的；
  `generic_file_aio_read`。一次异步读可能包含多个读操作（对应于readv系统调用），对于其中的每一个，调用`do_generic_file_read`；

+ `do_generic_file_read`：

  主要流程是<font color=red size=4>**在radix树里面查找是否存在对应的page**</font>，且该页可用。是则从page里面读出所需的数据，然后返回，否则通过`file->f_mapping->a_ops->readpage`去读这个页。

+ `file->f_mapping->a_ops->readpage`  <font color=red size=3>( address_space）</font>

  返回后，说明读请求已经提交了。但是磁盘上的数据还不一定就已经读上来了，需要等待数据读完。等待的方法就是`lock_page`：在调用file->f_mapping->a_ops->readpage之前会给page置PG_locked标记。而数据读完后，会将该标记清除，这个后面会看到。而这里的<font color=red size=4>lock_page就是要等待`PG_locked`标记被清除</font>。）
  file->f_mapping是从对应inode->i_mapping而来，inode->i_mapping->a_ops是由对应的文件系统类型在生成这个inode时赋予的。而各个文件系统类型提供的a_ops->readpage函数一般是mpage_readpage函数的封装；

+ `mpage_readpage`

  调用do_mpage_readpage构造一个<font color=red>**`bio`**</font>，再调用mpage_bio_submit将其提交；

+ `do_mpage_readpage`

  根据page->index确定需要读的磁盘扇区号，然后构造一组bio。其中需要使用文件系统类型提供的get_block函数来对应需要读取的磁盘扇区号；

+ `mpage_bio_submit`

  设置bio的结束回调`bio->bi_end_io`为`mpage_end_io_read`，然后调用`submit_bio`提交这组bio；

+ submit_bio

  调用`generic_make_request`将bio提交到<font color=red size=4>磁盘驱动维护的请求队列</font>中；

+ generic_make_request

  一个包装函数，对于每一个bio，调用__generic_make_request;

+ `__generic_make_request`

  获取bio对应的块设备文件对应的磁盘对象的请求队列`bio->bi_bdev->bd_disk->queue`，调用`q->make_request_fn`将bio添加到队列；

+ q->make_request_fn

  设备驱动程序在其初始化时会初始化这个request_queue结构，并且设置`q->make_request_fn和q->request_fn`（这个下面就会用到）。前者用于将一个bio组装成request添加到request_queue，后者用于处理request_queue中的请求。一般情况下，设备驱动通过调用blk_init_queue来初始化request_queue，q->request_fn需要给定，而`q->make_request_fn`使用了默认的`__make_request`；

+ __make_request

  <font color=red size =4>**会根据不同的调度算法来决定如何添加bio**</font>，生成对应的request结构加入request_queue结构中，并且决定是否调用q->request_fn，或是在`kblockd_workqueue`任务队列里面添加一个任务，等`kblockd`内核线程来调用q->request_fn；

+ q->request_fn

  <font color=red size=3>**驱动程序定义的函数**</font>负责从request_queue里面取出request进行处理。从添加bio到request被取出，若干的请求已经被IO调度算法整理过了。驱动程序负责根据request结构里面的描述，将实际物理设备里面的数据读到内存中。当驱动程序完成一个request时，会调用`end_request`（或类似）函数，以结束这个request；

+ `end_request`

  完成request的收尾工作，并且会调用对应的bio的的结束方法bio->bi_end_io，即前面设置的`mpage_end_io_read`；

+ `mpage_end_io_read`

  如果page已更新则设置其up-to-date标记，并为page解锁，唤醒等待page解锁的进程。最后释放bio对象

[块存储：AIO的直接读流程注释](https://blog.csdn.net/yiyeguzhou100/article/details/106289024)

# 写流程

1. sys_write

   跟sys_read一样，对应的 vfs_write、do_sync_write、f_op->aio_write、generic_file_aio_write被顺序调用；

2. generic_file_aio_write

   调用__generic_file_aio_write_nolock来进行写的处理，将数据写到磁盘高速缓存中。写完成之后，判断如果文件打开时使用了O_SYNC标记，则再调用sync_page_range将写入到磁盘高速缓存中的数据同步到磁盘（只同步文件头信息）；

3. __generic_file_aio_write_nolock

   进行一些检查之后，调用generic_file_buffered_write；
   generic_file_buffered_write。调用generic_perform_write执行写，写完成之后，判断如果文件打开时使用了O_SYNC标记，则再调用generic_osync_inode将写入到磁盘高速缓存中的数据同步到磁盘（同步文件头信息和文件内容）；

4. generic_perform_write

   ​		一次异步写可能包含多个写操作（对应于writev系统调用），对于其中牵涉的每一个page，调用file->f_mapping->a_ops->write_begin<font color=red size=3>( address_space）</font>准备好需要写的磁盘高速缓存页面，然后将需要写的数据拷入其中，最后调用file->f_mapping->a_ops->write_end完成写；

   ​		file->f_mapping是从对应inode->i_mapping而来，inode->i_mapping->a_ops是由对应的文件系统类型在生成这个inode时赋予的。而各个文件系统类型提供的file->f_mapping->a_ops->write_begin函数一般是block_write_begin函数的封装、file->f_mapping->a_ops->write_end函数一般是generic_write_end函数的封装；

5. block_write_begin

   调用grab_cache_page_write_begin<font color=red size=4>**在radix树里面查找要被写的page**</font>，如果不存在则创建一个。调用__block_prepare_write为这个page准备一组buffer_head结构，用于描述组成这个page的数据块（利用其中的信息，可以生成对应的bio结构）

6. `__generic_write_end`

   调用block_write_end提交写请求，然后设置page的dirty标记；
   block_write_end。<font color=red size=4>调用`__block_commit_write`为page中的每一个buffer_head结构设置dirty标记；
   至此，write调用就要返回了</font>。如果文件打开时使用了O_SYNC标记，sync_page_range或generic_osync_inode将被调用。否则write就结束了，等待pdflush内核线程发现radix树上的脏页，并最终调用到do_writepages写回这些脏页

   


![20200527200122956.png](https://upload-images.jianshu.io/upload_images/9243349-94d4526b31ba7fbc.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

block_write_begin。

。调用block_write_end提交写请求，然后设置page的dirty标记；
block_write_end。<font color=red size=4>调用`__block_commit_write`为page中的每一个buffer_head结构设置dirty标记；
至此，write调用就要返回了</font>。如果文件打开时使用了O_SYNC标记，sync_page_range或generic_osync_inode将被调用。否则write就结束了，等待pdflush内核线程发现radix树上的脏页，并最终调用到do_writepages写回这些脏页;

`__sync_page_range`也是调用generic_osync_inode来实现的，而generic_osync_inode最终也会调用到do_writepages；
do_writepages。调用inode->i_mapping->a_ops->writepages，而后者一般是mpage_writepages函数的包装；
mpage_writepages。检查radix树中需要写回的page，对每一个page调用`__mpage_writepage`；

`__mpage_writepage`：这里也是构造bio，然后调用mpage_bio_submit来进行提交；
后面的流程跟read几乎就一样了……

![](https://img-blog.csdn.net/20170222091610211?watermark/2/text/aHR0cDovL2Jsb2cuY3Nkbi5uZXQveW91bmdlcl9jaGluYQ==/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70/gravity/SouthEast)

[块存储：AIO的直接写流程注释](https://blog.csdn.net/yiyeguzhou100/article/details/106389441)

[Linux read系统调用之 submit_bio()](https://blog.csdn.net/weixin_42205011/article/details/98731459)

[浅谈Linux内核IO体系之磁盘IO](https://zhuanlan.zhihu.com/p/96391501)

[[Linux-块设备驱动(详解)](https://www.cnblogs.com/lifexy/p/7661454.html)](https://www.cnblogs.com/lifexy/p/7661454.html)



下面这个写的非常好

[22.Linux-块设备驱动之框架详细分析(详解)](https://www.cnblogs.com/lifexy/p/7651667.html)





[块层介绍 第二篇: request层](https://mp.weixin.qq.com/s/5qHpq-NXbUEzp-m2tisJAw?scene=25#wechat_redirect)

