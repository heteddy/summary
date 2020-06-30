# slab分配器

相同类型的对象归为一类，每当要申请这样一个对象时，slab分配器就从一个slab列表中分配一个这样大小的单元出去，而当要释放时，将其重新保存在该列表中，而不是直接返回给伙伴系统，从而避免内部碎片。slab分配器并不丢弃已经分配的对象，而是释放并把它们保存在内存中。slab分配对象时，会使用最近释放的对象的内存块，因此其驻留在cpu高速缓存中的概率会大大提高。

https://www.cnblogs.com/wangzahngjun/p/4977425.html

## API

下面看一下slab分配器的接口——看看slab缓存是如何创建、撤销以及如何从缓存中分配一个对象的。一个新的kmem_cache通过kmem_cache_create()函数来创建：

```
struct kmem_cache *
kmem_cache_create( const char *name, size_t size, size_t align,
                   unsigned long flags， void (*ctor)(void*));
```

*name是一个字符串，存放kmem_cache缓存的名字；size是缓存所存放的对象的大小；align是slab内第一个对象的偏移；flag是可选的配置项，用来控制缓存的行为。最后一个参数ctor是对象的构造函数，一般是不需要的，以NULL来代替。kmem_cache_create()成功执行之后会返回一个指向所创建的缓存的指针，否则返回NULL。kmem_cache_create()可能会引起阻塞（睡眠），因此不能在中断上下文中使用。

撤销一个kmem_cache则是通过kmem_cache_destroy()函数：

```
int kmem_cache_destroy( struct kmem_cache *cachep);
```

该函数成功则返回0，失败返回非零值。调用kmem_cache_destroy()之前应该满足下面几个条件：首先，cachep所指向的缓存中所有slab都为空闲，否则的话是不可以撤销的；其次在调用kmem_cache_destroy()过程中以及调用之后，调用者需要确保不会再访问这个缓存；最后，该函数也可能会引起阻塞，因此不能在中断上下文中使用。
 可以通过下面函数来从kmem_cache中分配一个对象：

```
void* kmem_cache_alloc(struct kmem_cache* cachep, gfp_t flags);
```

这个函数从cachep指定的缓存中返回一个指向对象的指针。如果缓存中所有slab都是满的，那么slab分配器会通过调用kmem_getpages()创建一个新的slab。

释放一个对象的函数如下：

```
void kmem_cache_free(struct kmem_cache* cachep,  void* objp);
```

**这个函数是将被释放的对象返还给先前的slab，其实就是将cachep中的对象objp标记为空闲而已**

## 例子

其实到了这里，应该去分析以上函数的源码，但是几次奋起分析，都被打趴在地。所以就写个内核模块，鼓励下自己吧。

```
#include <linux/autoconf.h>
#include <linux/module.h>
#include <linux/slab.h>

MODULE_AUTHOR("wangzhangjun");
MODULE_DESCRIPTION("slab test module");

static struct kmem_cache  *test_cachep = NULL;
struct slab_test
{
    int val;
};
void fun_ctor(struct slab_test *object , struct kmem_cache  *cachep , unsigned long flags )
{
    printk(KERN_INFO "ctor fuction ...\n");
    object->val = 1;
}

static int __init slab_init(void)
{
    struct slab_test *object = NULL;//slab的一个对象
	printk(KERN_INFO "slab_init\n");
    test_cachep = kmem_cache_create("test_cachep",sizeof(struct slab_test)*3,0,SLAB_HWCACHE_ALIGN,fun_ctor);
    if(NULL == test_cachep) 
                return  -ENOMEM ;
	printk(KERN_INFO "Cache name is %s\n",kmem_cache_name(test_cachep));//获取高速缓存的名称
	printk(KERN_INFO "Cache object size  is %d\n",kmem_cache_size(test_cachep));//获取高速缓存的大小
 	object = kmem_cache_alloc(test_cachep,GFP_KERNEL);//从高速缓存中分配一个对象
    if(object)
    {
        printk(KERN_INFO "alloc one val = %d\n",object->val);
        kmem_cache_free( test_cachep, object );//归还对象到高速缓存
		//这句话的意思是虽然对象归还到了高速缓存中，但是高速缓存中的值没有做修改
		//只是修改了一些它的状态。
		printk(KERN_INFO "alloc three val = %d\n",object->val);
            object = NULL;
        }else
            return -ENOMEM;
	return 0;
}

static void  __exit slab_clean(void)
{
	printk(KERN_INFO "slab_clean\n");
	if(test_cachep)
                kmem_cache_destroy(test_cachep);//调用这个函数时test_cachep所指向的缓存中所有的slab都要为空

}

module_init(slab_init);
module_exit(slab_clean);
MODULE_LICENSE("GPL");
```

我们结合结果来分析下这个内核模块：
 ![img](https://images2015.cnblogs.com/blog/739465/201511/739465-20151119134922186-539072440.png)

这是dmesg的结果，可以发现我们自己创建的高速缓存的名字test_cachep,还有每个对象的大小。
 ![img](https://images2015.cnblogs.com/blog/739465/201511/739465-20151119134946405-577360396.png)

还有构造函数修改了对象里面的值，至于为什么构造函数会出现这么多次，可能是因为，这个函数被注册了之后，系统的其他地方也会调用这个函数。在这里可以分析源码，当调用keme_cache_create()的时候是没有调用对象的构造函数的，调用kmem_cache_create()并没有分配slab,而是在创建对象的时候发现没有空闲对象，在分配对象的时候，会调用构造函数初始化对象。
 另外结合上面的代码可以发现，alloc three val是在kmem_cache_free之后打印的，但是它的值依然可以被打印出来，这充分说明了，slab这种机制是在将某个对象使用完之后，就其缓存起来，它还是切切实实的存在于内存中。
 再结合/proc/slabinfo的信息看我们自己创建的slab高速缓存
 ![img](https://images2015.cnblogs.com/blog/739465/201511/739465-20151119135007046-647774705.png)

可以发现名字为test_cachep的高速缓存，每个对象的大小（objsize）是16,和上面dmesg看到的值相同，objperslab（每个slab中的对象时202），pagesperslab（每个slab中包含的页数），可以知道`objsize * objperslab < pagesperslab`。

### 6.总结

目前只是对slab机制的原理有了一个感性的认识，对于这部分相关的源码涉及到着色以及内存对齐等细节。看的不是很清楚，后面还需要仔细研究。