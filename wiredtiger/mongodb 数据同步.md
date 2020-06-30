[MongoDB](https://www.qcloud.com/product/mongodb?fromSource=gwzcw.49083.49083.49083)的单实例模式下，一个mongod进程为一个实例，一个实例中包含若干db，每个db包含若干张表。

[MongoDB](https://cloud.tencent.com/product/mongodb?from=10680)通过一张特殊的表`local.oplog.rs`存储oplog，该表的特点是：固定大小，满了会删除最旧记录插入新记录，而且只支持append操作，因此可以理解为一个持久化的ring-buffer。oplog是MongoDB复制集的核心功能点。

MongoDB复制集是指MongoDB实例通过复制并应用其他实例的oplog达到数据冗余的技术。

常用的复制集构成一般有下图两种方式 (注意，可以使用mongoshell 手工指定复制源，但mongdb不保证这个指定是持久的，下文会讲到在某些情况下，MongoDB会自动进行复制源切换）。

![img](https://mc.qcloudimg.com/static/img/b8138ef83cfd3ecc388f5aa0d690ea40/image.png)

MongoDB的复制集技术并不少见，很类似mysql的异步复制模式，这种模式主要有几个技术点：

1. 新节点加入，正常同步前的初始化
2. Primary节点挂掉后，剩余的Secondary节点如何提供服务
3. 如何保证主节点挂掉后数据不丢失/主节点挂掉后丢失数据的处理

MongoDB作为一个成熟的数据库产品，较好的解决了上述问题，一个完整的复制集包含如下几点功能：

1 .数据同步

- initial-sync
- steady-sync
- 异常数据回滚

2 . MongoDB集群心跳与选举

## 一.数据同步

### `initial_sync`

当一个节点刚加入集群时，它需要初始化数据使得 自身与集群中其它节点的数据量差距尽量少，这个过程称为initial-sync。

一个initial-sync 包括六步（阅读`rs_initialSync.cpp:_initialSync`函数的逻辑)。

1. 删除本地除local库以外的所有db
2. 选取一个源节点，将源节点中的所有db导入到本地（注意，此处只导入数据，不导入索引）
3. 将2）开始执行到执行结束中源产生的oplog 应用到本地
4. 将3）开始执行到执行结束中源产生的oplog 应用到本地
5. 从源将所有table的索引在本地重建（导入索引）
6. 将5）开始执行到执行结束中源产生的oplog 应用到本地

当第6）步结束后，源和本地的差距足够小，MongoDB进入Secondary（从节点）状态。

第2）步要拷贝所有数据，因此一般第2）步消耗时间最长，第3）与第4）步是一个连续逼近的过程，MongoDB这里做了两次。

是因为第2）步一般耗时太长，导致第3）步数据量变多，间接受到影响。然而这么做并不是必须的，rs_initialSync.cpp：384 开始的TODO建议使用SyncTail的方式将数据一次性读回来（SyncTail以及TailableCursor的行为与原理如果不熟悉请看[官方文档](https://docs.mongodb.com/manual/core/tailable-cursors/)。

![img](https://mc.qcloudimg.com/static/img/b65acc37de5789dbcdd55a345359b924/image.png)

### `steady-sync`

当节点初始化完成后，会进入steady-sync状态，顾名思义，正常情况下，这是一个稳定静默运行于后台的，从复制源不断同步新oplog的过程。该过程一般会出现这两种问题：

1. 复制源写入过快（或者相对的，本地写入速度过慢），复制源的oplog覆盖了 本地用于同步源oplog而维持在源的游标。
2. 本节点在宕机之前是Primary，在重启后本地oplog有和当前Primary不一致的Oplog。

这两种情况分别如下图所示：

![img](https://mc.qcloudimg.com/static/img/d72eb13c214da4197d63ef3666fd8d6d/image.png)

![img](https://mc.qcloudimg.com/static/img/bc3944f5726a69ac0ebabcb27f070161/image.png)

这两种情况在`bgsync.cpp:_produce`函数中，虽然这两种情况很不一样，但是最终都会进入 `bgsync.cpp:_rollback`函数处理。

对于第二种情况，处理过程在`rs_rollback.cpp`中，具体步骤为：

1. 维持本地与远程的两个反向游标，以线性的时间复杂度找到LCA（最近公共祖先，上conflict.png中为Record4） 该过程与经典的两个有序链表找公共节点的过程类似，具体实现在`roll_back_local_operations.cpp:syncRollBackLocalOperations`中，读者可以自行思考这一过程如何以线性时间复杂度实现。
2. 针对本地每个冲突的oplog，枚举该oplog的类型，推断出回滚该oplog需要的逆操作并记录，如下： 2.1: create_table -> drop_table 2.2: drop_table -> 重新同步该表 2.3: drop_index -> 重新同步并构建索引 2.4: drop_db -> 放弃rollback，改由用户手工init_resync 2.5: apply_ops -> 针对apply_ops 中的每一条子oplog，递归执行 2)这一过程 2.6: create_index -> drop_index 2.7: 普通文档的CUD操作 -> 从Primary重新读取真实值并替换。相关函数为：`rs_rollback.cpp:refetch`
3. 针对2）中分析出的每条oplog的处理方式，执行处理，相关函数为 rs_rollback.cpp:syncFixUp，此处操作主要是对步骤2）的实践，实际处理过程相当繁琐。
4. truncate掉本地冲突的oplog。

上面我们说到，对于本地失速(stale)的情况，也是走_rollback 流程统一处理的，对于失速，走_rollback时会在找LCA这步失败，之后会尝试更换复制源，方法为：从当前存活的所有secondary和primary节点中找一个使自己“不处于失速”的节点。

这里有必要解释一下，oplog是一个有限大小的ring-buffer, 失速的唯一判断条件为：本地维护在复制源的游标被复制源的写覆盖（想象一下你和同学同时开始绕着操场跑步，当你被同学超过一圈时，你和同学相遇了）。因此如果某些节点的oplog设置的比较大，绕完一圈的时间就更长，利用这样的节点作为复制源，失速的可能性会更小。

对MongoDB的集群数据同步的描述暂告段落。我们利用一张流程图来做总结：

![img](https://mc.qcloudimg.com/static/img/2cf41c43c9d38860590af8f4d44ecf12/image.png)

### `steady-sync`的线程模型与 Oplog 指令乱序加速

与steady-sync相关的代码有 bgsync.cpp， sync_tail.cpp。上面我们介绍过，steady-sync过程从复制源读取新产生的oplog，并应用到本地，这样的过程脱不离是一个producer-consumer模型。由于oplog需要保证顺序性，producer只能单线程实现。

对于consumer端，是否有并发提速机制呢?

1. 首先，不相干的文档之间无需保证oplog apply的顺序，因此可以对oplog 按照objid 哈希分组。每一组内必须保证严格的写入顺序性。

```javascript
572 void fillWriterVectors(OperationContext* txn,
 573                        MultiApplier::Operations* ops,
 574                        std::vector<MultiApplier::OperationPtrs>* writerVectors) {
 581     for (auto&& op : *ops) {
 582         StringMapTraits::HashedKey hashedNs(op.ns);
 583         uint32_t hash = hashedNs.hash();
 584
 585         // For doc locking engines, include the _id of the document in the hash so we get
 586         // parallelism even if all writes are to a single collection. We can't do this for capped
 587         // collections because the order of inserts is a guaranteed property, unlike for normal
 588         // collections.
 589         if (supportsDocLocking && op.isCrudOpType() && !isCapped(txn, hashedNs)) {
 590             BSONElement id = op.getIdElement();
 591             const size_t idHash = BSONElement::Hasher()(id);
 592             MurmurHash3_x86_32(&idHash, sizeof(idHash), hash, &hash);
 593         }
 601         auto& writer = (*writerVectors)[hash % numWriters];
 602         if (writer.empty())
 603             writer.reserve(8);  // skip a few growth rounds.
 604         writer.push_back(&op);
 605     }
 606 }
```

1. 其次对于command命令，会对表或者库有全局性的影响，因此command命令必须在当前的consumer完成工作之后单独处理，而且在处理command oplog时，不能有其他命令同时执行。这里可以类比SMP体系结构下的 `cpu-memory-barrior`。

```javascript
899     // Check for ops that must be processed one at a time.
 900     if (entry.raw.isEmpty() ||       // sentinel that network queue is drained.
 901         (entry.opType[0] == 'c') ||  // commands.
 902         // Index builds are achieved through the use of an insert op, not a command op.
 903         // The following line is the same as what the insert code uses to detect an index build.
 904         (!entry.ns.empty() && nsToCollectionSubstring(entry.ns) == "system.indexes")) {
 905         if (ops->getCount() == 1) {
 906             // apply commands one-at-a-time
 907             _networkQueue->consume(txn);
 908         } else {
 909             // This op must be processed alone, but we already had ops in the queue so we can't
 910             // include it in this batch. Since we didn't call consume(), we'll see this again next
 911             // time and process it alone.
 912             ops->pop_back();
 913         }
```

3 . 从库和主库的oplog 顺序必须完全一致，因此不管1、2步写入用户数据的顺序如何，oplog的必须保证顺序性。对于mmap引擎的capped-collection，只能以顺序插入来保证，因此对oplog的插入是单线程进行的。对于wiredtiger引擎的capped-collection，可以在ts(时间戳字段)上加上索引，从而保证读取的顺序与插入的顺序无关。

```javascript
 517     // Only doc-locking engines support parallel writes to the oplog because they are required to
 518     // ensure that oplog entries are ordered correctly, even if inserted out-of-order. Additionally,
 519     // there would be no way to take advantage of multiple threads if a storage engine doesn't
 520     // support document locking.
 521     if (!enoughToMultiThread ||
 522         !txn->getServiceContext()->getGlobalStorageEngine()->supportsDocLocking()) {
 523
 524         threadPool->schedule(makeOplogWriterForRange(0, ops.size()));
 525         return false;
 526     }
```

`steady-sync` 的类依赖与线程模型总结如下图：

![img](https://mc.qcloudimg.com/static/img/ea93f18c671fff23d851ca426545def8/image.png)