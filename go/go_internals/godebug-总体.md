GODEBUG变量支持14个参数。在[runtime](https://link.zhihu.com/?target=https%3A//golang.org/pkg/runtime/)包的doc里其实都有简单介绍。在调度器初始化方法schedinit()里，会调用parsedebugvars()对GODEBUG进行初始化。

```go
// 这些flag可以通过在go run 命令中设置GODEBUG变量来使用。但每个flag的不同取值对应的含义并没常量标识，都是硬编码
var debug struct {
    allocfreetrace   int32
    cgocheck         int32
    efence           int32
    gccheckmark      int32
    gcpacertrace     int32
    gcshrinkstackoff int32
    gcrescanstacks   int32
    gcstoptheworld   int32
    gctrace          int32
    invalidptr       int32
    sbrk             int32
    scavenge         int32
    scheddetail      int32
    schedtrace       int32
}

var dbgvars = []dbgVar{
    {"allocfreetrace", &debug.allocfreetrace},
    {"cgocheck", &debug.cgocheck},
  // ...
}

func parsedebugvars() {
  // ...

    for p := gogetenv("GODEBUG"); p != ""; {
    // ...
    }
  // ...
}
```



