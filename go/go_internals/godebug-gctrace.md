

# gc trace

| 版本    | GC 算法                                                      | STW 时间               |
| :------ | :----------------------------------------------------------- | :--------------------- |
| Go 1.0  | STW（强依赖 tcmalloc）                                       | 百ms到秒级别           |
| Go 1.3  | Mark STW, Sweep 并行                                         | 百ms级别               |
| Go 1.5  | 三色标记法, 并发标记清除。同时运行时从 C 和少量汇编，改为 Go 和少量汇编实现 | 10-50ms级别            |
| Go 1.6  | 1.5 中一些与并发 GC 不协调的地方更改，集中式的 GC 协调协程，改为状态机实现 | 5ms级别                |
| Go 1.7  | GC 时由 mark 栈收缩改为并发，span 对象分配机制由 freelist 改为 bitmap 模式，SSA引入 | ms级别                 |
| Go 1.8  | 混合写屏障（hybrid write barrier）, 消除 re-scanning stack   | sub ms                 |
| Go 1.12 | Mark Termination 流程优化                                    | sub ms, 但几乎减少一半 |

## 概念

-   mark：标记阶段。
-   markTermination：标记结束阶段。
-   mutator assist：辅助 GC，是指在 GC 过程中 mutator 线程会并发运行，而 mutator assist 机制会协助 GC 做一部分的工作。
-   heaplive：在 Go 的内存管理中，span 是内存页的基本单元，每页大小为 8kb，同时 Go 会根据对象的大小不同而分配不同页数的 span，而 heaplive 就代表着所有 span 的总大小。
-   dedicated / fractional / idle：在标记阶段会分为三种不同的 mark worker 模式，分别是 dedicated、fractional 和 idle，它们代表着不同的专注程度，其中 dedicated 模式最专注，是完整的 GC 回收行为，fractional 只会干部分的 GC 行为，idle 最轻松。这里你只需要了解它是不同专注程度的 mark worker 就好了，详细介绍我们可以等后续的文章。

gctrace用途主要是用于跟踪GC的不同阶段的耗时与GC前后的内存量对比。信息比较简洁，可以用于对runtime本身进行调试之外，还可以观察线上应用的GC情况。

Dave Cheney就写了一个工具[gcvis](https://link.zhihu.com/?target=https%3A//github.com/davecheney/gcvis)专门用于分析gctrace的输出，通过可视化的方式展示出指标的变化。

gctrace取值可以等于1，或任何大于1的数。

下面的输出来自取值gctrace=1：

```text
gc 252 @4316.062s 0%: 0.013+2.9+0.050 ms clock, 0.10+0.23/5.4/12+0.40 ms cpu, 16->17->8 MB, 17 MB goal, 8 P
```

```go
Currently, it is:
    gc # @#s #%: #+#+# ms clock, #+#/#/#+# ms cpu, #->#-># MB, # MB goal, # P
where the fields are as follows:
    gc #        the GC number, incremented at each GC
    @#s         time in seconds since program start
    #%          percentage of time spent in GC since program start
    #+...+#     wall-clock/CPU times for the phases of the GC
    #->#-># MB  heap size at GC start, at GC end, and live heap
    # MB goal   goal heap size
    # P         number of processors used
The phases are stop-the-world (STW) sweep termination, concurrent
mark and scan, and STW mark termination. The CPU times
for mark/scan are broken down in to assist time (GC performed in
line with allocation), background GC time, and idle GC time.
If the line ends with "(forced)", this GC was forced by a
runtime.GC() call and all phases are STW.
```

```
gc 252： 这是第252次gc。

@4316.062s： 这次gc的markTermination阶段完成后，距离runtime启动到现在的时间。

0%：当目前为止，gc的标记工作（包括两次mark阶段的STW和并发标记）所用的CPU时间占总CPU的百分比。

0.013+2.9+0.050 ms clock：按顺序分成三部分，0.013表示mark阶段的STW时间（单P的）；2.9表示并发标记用的时间（所有P的）；0.050表示markTermination阶段的STW时间（单P的）。

0.10+0.23/5.4/12+0.40 ms cpu：按顺序分成三部分，0.10表示整个进程在mark阶段STW停顿时间(0.013 * 8)；0.23/5.4/12有三块信息，0.23是mutator assists占用的时间，5.4是dedicated mark workers+fractional mark worker占用的时间，12是idle mark workers占用的时间。这三块时间加起来会接近2.9*8(P的个数)；0.40 ms表示整个进程在markTermination阶段STW停顿时间(0.050 * 8)。

16->17->8 MB：按顺序分成三部分，16表示开始mark阶段前的heap_live大小；17表示开始markTermination阶段前的heap_live大小；8表示被标记对象的大小。

17 MB goal：表示下一次触发GC的内存占用阀值是17MB，等于8MB * 2，向上取整。

8 P：本次gc共有多少个P。
```

一、heap_live要结合go的内存管理来理解。因为go按照不同的对象大小，会分配不同页数的span。span是对内存页进行管理的基本单元，每页8k大小。所以肯定会出现span中有内存是空闲着没被用上的。

不过怎么用go先不管，反正是把它划分给程序用了。而heap_live就表示所有span的大小。

而程序到底用了多少呢？就是在GC扫描对象时，扫描到的存活对象大小就是已用的大小。对应上面就是8MB。

二、mark worker分为三种，dedicated、fractional和idle。分别表示标记工作干活时的专注程度。dedicated最专注，除非被抢占打断，否则一直干活。idle最偷懒，干一点活就退出，控制权让给出别的goroutine。它们都是并发标记工作里的worker。



这块输出的源码为：

```go
type work struct {
  // ...
  // tSweepTerm 开始mark阶段前的时间戳
    // tMark mark阶段完成后的时间戳
    // tMarkTerm markTermination阶段开始前的时间戳
    // tEnd markTermination阶段结束后的时间戳
    tSweepTerm, tMark, tMarkTerm, tEnd int64 // nanotime() of phase start

  // heap0 开始mark阶段前，当前heap_live的大小
    // heap1 开始marktermination阶段前，当前heap_live的大小
    // heap2 这次GC对heap_live大小的内存进行标记对象的大小
    // heapGoal 下次触发GC的内存占用目标阀值
    heap0, heap1, heap2, heapGoal uint64
}

func gcMarkTermination(nextTriggerRatio float64) {
  // ...

  // mark阶段的STW时间
    sweepTermCpu := int64(work.stwprocs) * (work.tMark - work.tSweepTerm)

    // 并行mark所占用的CPU时间
    markCpu := gcController.assistTime + gcController.dedicatedMarkTime + gcController.fractionalMarkTime

    // markTermination阶段的STW时间
    markTermCpu := int64(work.stwprocs) * (work.tEnd - work.tMarkTerm)

    // 整个标记所占用的时间
    cycleCpu := sweepTermCpu + markCpu + markTermCpu
    work.totaltime += cycleCpu

  // 总CPU时间
    totalCpu := sched.totaltime + (now-sched.procresizetime)*int64(gomaxprocs)
  // 整个标记所占用的时间 / 总CPU时间 。 不能超过25%
    memstats.gc_cpu_fraction = float64(work.totaltime) / float64(totalCpu)


  if debug.gctrace > 0 {
        util := int(memstats.gc_cpu_fraction * 100)

        var sbuf [24]byte
        printlock()
        print("gc ", memstats.numgc,
            " @", string(itoaDiv(sbuf[:], uint64(work.tSweepTerm-runtimeInitTime)/1e6, 3)), "s ",
            util, "%: ")
        prev := work.tSweepTerm
        for i, ns := range []int64{work.tMark, work.tMarkTerm, work.tEnd} {
            if i != 0 {
                print("+")
            }
            print(string(fmtNSAsMS(sbuf[:], uint64(ns-prev))))
            prev = ns
        }
        print(" ms clock, ")
        for i, ns := range []int64{sweepTermCpu, gcController.assistTime, gcController.dedicatedMarkTime + gcController.fractionalMarkTime, gcController.idleMarkTime, markTermCpu} {
            if i == 2 || i == 3 {
                // Separate mark time components with /.
                print("/")
            } else if i != 0 {
                print("+")
            }
            print(string(fmtNSAsMS(sbuf[:], uint64(ns))))
        }
        print(" ms cpu, ",
            work.heap0>>20, "->", work.heap1>>20, "->", work.heap2>>20, " MB, ",
            work.heapGoal>>20, " MB goal, ",
            work.maxprocs, " P")
        if work.userForced {
            print(" (forced)")
        }
        print("\n")
        printunlock()
    }

}
```