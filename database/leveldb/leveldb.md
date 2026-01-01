​		

[TOC]

​		leveldb是两位来自google的大牛Jeff Dean和Sanjay Ghemawat开源的KV存储引擎，底层实现采用LSM tree的方式组织，基于机械硬盘顺序访问速度快于随机访问的情况，将数据有序排列并按顺序写入磁盘，从而提高了写入速度；但随着数据的持续写入，文件占用空间越来越大，为避免操作大文件造成的额外开销，将文件拆分并分层，每一层的文件达到一定容量(L0是根据文件数/设定阈值)触发合并操作向下一层归并。这就是leveldb名字的由来。

![](https://pic2.zhimg.com/80/v2-a20fb54bc2b73aee29ffa42ea2296cf5_1440w.jpg)

# 整体架构

## 基本原理

​		leveldb是根据lsm实现的一个kv存储引擎，既然可以作为数据库就要支持Put，Get，Delete 操作和持久化；

+ 缓存：

  为了增加查询和写入的速度通常需要缓存一部分数据(leveldb memtable)。

+ 避免数据丢失：

  如果用户的写入的数据写入缓存就立即返回，这样增加了响应速度但是带来了数据丢失的风险，因此引入WAL(也有人称为binlog)是有必要的(xxxxxx.log)，wal是append到log文件属于顺序写因此写入速度非常快。

+ 持久化：

  用户数据最终要保存到数据库文件中(xxxxxx.ldb)。

+ 文件访问速度：

  缓存没有命中的情况下必须要到文件中获取数据，为提高文件内容的访问速度，一种方法是设定index然后把index组织处b+树放到内存中，而leveldb采用另外一种方式ldb文件存储的key是有序的并且文件中固定位置保存了data index因此可以快速找到key 的位置。

+ 数据恢复

  系统启动的时候如何重新恢复数据以及系统运行状态，leveldb设计了manifest文件保存系统的一些元数据比如next log number，sequence，每一层的数据文件。压缩数据合并文件之后会更新manifest文件，实际上并非直接更新该文件，而是创建一个新的manifest将元数据写入，这样做避免了写入过程系统崩溃导致整个数据库的无法恢复。

+ 使用哪个元数据文件

  既然manifest文件可能存在多个，那么应该使用哪个manifest文件呢，leveldb设计一个CURRENT文件指示使用的manifest文件名。

  > CURRENT会不会存在部分写入呢？
  >
  > 由于CURRENT文件很小，在调用系统fsync的基础上，硬盘对于单个数据块的写入是原子性的即使掉电，电容中的电量也可以保证单个数据块的成功写入。

leveldb的基本结构如下：

​		leveldb在处理写入的时候首先写入内存中的Memtable，当memtable size超过阈值后转换为只读的immutable 并dump成为文件。查找的时候也是根据数据的新旧首先在内存中查找然后在各层的文件中查找。

![architecture.png](https://upload-images.jianshu.io/upload_images/9243349-738a0c16399eeac4.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

+ CURRENT

  指示有效的manifest文件

+ manifest-xxxxxx（xxxxxx表示六位的数字）

  保存db的元信息

+ xxxxxx.ldb

  `level-0`-`level-n`的数据文件，level0的文件由immutable Memtable dump生成，其他层的文件在触发compaction的时候生成。

+ xxxxxx.log

  write wal文件

## 数据结构

+ MemTable

  memtable内部实现是一个Skiplist整个table都放在内存中，当容量达到`Options.write_buffer_size`即`4MB`转换为immutable，并触发另外一个线程执行`immutable memtable` 的 `compaction`。只用来查询不再继续添加；

+ log文件

  + log文件的结构，log文件被划分为32k为单位的block，读取和写入都以block为单位，这样做保证了如果block被破坏，不会影响其他的block，仅当前的block内的数据丢失，是一种提高**可用性**的方法。

    ![log.png](https://upload-images.jianshu.io/upload_images/9243349-683d87212d0eb4f3.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

    record的格式：

     1. header(7)

        header共7个字节,checksum 4字节，length 2个字节，type 1个字节

     2. data

        有header中的length指定长度。

    

    record可能被切分成多块，切分block存在以下三种情况：

    1. 一个Record刚好在一个Block里面
    2. 一个Record被分到两个Block里面
    3. 一个Record被切分到多个Block里面。

    

    根据上面三种情况将block的type设置为：
    
    1. FULL: 完整的record，没有跨block
    2. First：跨block当前为开头部分
    3. Middle：跨block当前为中间部分，可能存在多个
    4. Last：跨block当前为最后部分

  

+ SSTable

  sstable中保存的数据是按序保存用的数据，物理结构分为block以及footer，每个block包含多个entry；

  ![axlb4-qx8an.png](https://upload-images.jianshu.io/upload_images/9243349-5bb80e9cdc3b17a5.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

  

  sstable的逻辑上分为

  + `data block`

    保存key value数据

  + `metablock`

  + `metaindex block`

  + `index block`

    保存每个 data_block 的 last_key 及其在 sstable 文件中的索引。block 中entry 的 key 即是 last_key(依赖于 FindShortestSeparator()/FindShortSuccessor()的实现)，

    value 即是该 data_block 的 BlockHandler(offset/size)。

  + `footer`

    文件末尾的固定长度的数据。保存着 metaindex_block 和 index_block 的索引信息(BlockHandler),为达到固定的长度，添加 padding_bytes。最后有 8 个字节的 magic 校验

  

  

  ![a4ev3-9hnio.png](https://upload-images.jianshu.io/upload_images/9243349-f85848480084d65d.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

  

+ ValueType

  包含如下两种`valuetype`，注意的是在删除数据的时候，生成一个type为kTypeDeletion的record插入到writebatch中。

  ```c++
  enum ValueType { 
    kTypeDeletion = 0x0, //删除数据
    kTypeValue = 0x1 //修改或者put
  };
  ```

+ InternalKey 

  internal key实现了MVCC，通过sequence number实现，并且在设置比较操作符的时候，userKey + sequenceNumber(倒序) 这样保证了最新的更新在最前面

  `userkey`+`SequnceNumber`|`ValueType`，其中`sequence number`和`valuetype`总共占用64个字节。

  ![memtable_entry.png](https://upload-images.jianshu.io/upload_images/9243349-d203a50394081489.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

+ WriteBatch

  用户提交的多条数据会封装成WriteBatch，每个write batch使用一个sequence number，结构如下：

  ![wal.png](https://upload-images.jianshu.io/upload_images/9243349-8115e065471c5fed.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

  writebatch中的record会直接保存到log中

   1. WriteBatchInternal

   2. Record

      

# 特性

## WAL

### log文件

当执行write操作时，首先将writebatch 写入log文件中，然后再向memtable中写入。当db异常退出或者系统崩溃时，可以通过log文件恢复memtable中的内容，避免了数据丢失。

### manifest：

manifest文件也充当了compaction的wal，每次compact的元数据保存到manifest中，然后再将version添加到version set中，这样可以保证在机器宕机的情况下从manifest能恢复出本次compact的结果。

## Cache

### TableCache

缓存`SST`文件里面的`data block index`

### BlockCache

缓存`data block`

## 并发控制

​		对于并发的情况下，比如同时的读写同一个记录，比如写到一半读，那么读到的数据可能是不完整的，对于并发控制一般采取下面的三种方法：

 1. 悲观锁

    这种方式简单粗暴，直接加读写锁写的时候是不允许读操作的。

 2. 乐观锁

    首先假设各个事务之间相互不影响；在提交事务之前先检查是否有其他的事务在当前事务期间修改了数据，如果有修改则回滚当前事务。

 3. mvcc

    mvcc的实现写事务不直接修改原有数据而是产生一份新的数据，仅当写事务完成之后更新版本号并添加到新的版本库中。读事务访问的数据是事务开始时看到的一份快照。这种策略维护了多个版本的数据，提高了系统的并发性能。

### mvcc数据结构

 + FileMetaData

   记录文件的元信息，包括文件编号，大小，以及最大最小的key；

   ```C++
   struct FileMetaData {
       FileMetaData() : refs(0), allowed_seeks(1 << 30), file_size(0) {}
       int refs;
       int allowed_seeks;  // Seeks allowed until compaction
       uint64_t number;
       uint64_t file_size;    // File size in bytes
       InternalKey smallest;  // Smallest internal key served by table
       InternalKey largest;   // Largest internal key served by table
   };
   
   ```

+ version

  version是一个双向链表记录了前后的指针，以及当前version的每个level的FileMetaData.

  LevelDB会触发Compaction，会对一些文件进行清理操作，清理后的数据放到新的版本里面，而老的数据作为早期的版本最终是要清理掉的，但是如果有读事务位于旧的文件，那么暂时就不能删除。采取的方案是利用引用计数，只要一个Verison还活着，就不允许删除该Verison管理的所有文件。当一个Version生命周期结束，它管理的所有文件的引用计数减1.

  当进行通过version访问(比如查询)时候会增加version引用计数`ref`，当使用完毕时候就执行`Unref()`，如果version的引用计数已经为0，说明当前version已经没有在使用了，就会删除当前的version；

  

  ```c++
  void Version::Unref()
  {
      assert(this != &vset_->dummy_versions_);
      assert(refs_ >= 1);
      --refs_;
      if (refs_ == 0) {
          delete this;
      }
  }
  ```

  删除当前的version执行过程首先从链表中去掉当前的version；然后针对每一层的文件的引用计数减1，当文件不再被使用的时候就删除该文件；

  ```c++
  Version::~Version()
  {
      assert(refs_ == 0);
      // Remove from linked list
      prev_->next_ = next_;
      next_->prev_ = prev_;
      // Drop references to files
      for (int level = 0; level < config::kNumLevels; level++) {
          for (size_t i = 0; i < files_[level].size(); i++) {
              FileMetaData* f = files_[level][i];
              assert(f->refs > 0);
              f->refs--;
              if (f->refs <= 0) {
                  delete f;
              }
          }
      }
  }
  
  
  ```

+ version edit

  每次compact都产生一个新的version，为了保证数据完整性在做compact之前都会生成一个version edit，version edit反映的是当前compact所做的变更。

  `version(n) + versionEdit = version(n+1)`

  ![a5hrp-zfv5n.png](https://upload-images.jianshu.io/upload_images/9243349-bffc994e36bb6b53.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

  version edit的属性如下：

  ```c++
  typedef std::set<std::pair<int, uint64_t>> DeletedFileSet;
  std::string comparator_;
  // log 的 FileNumber
  uint64_t log_number_;
  uint64_t prev_log_number_;
  // 下一个可用的 FileNumber
  uint64_t next_file_number_;
  // 用过的最后一个 SequnceNumber
  SequenceNumber last_sequence_;
  bool has_comparator_;
  bool has_log_number_;
  bool has_prev_log_number_;
  bool has_next_file_number_;
  bool has_last_sequence_;
  // 要更新的 level  compact_pointer。
  std::vector<std::pair<int, InternalKey>> compact_pointers_;
  // 要删除的 sstable 文件(compact 的 input)
  DeletedFileSet deleted_files_;
  // 新的文件(compact 的 output)
  std::vector<std::pair<int, FileMetaData>> new_files_;
  ```

+ version set

  version set管理leveldb的内部状态，包括如下属性：

  ```c++
  const std::string dbname_;
  const Options* const options_;
  // 操作 sstable 的 TableCache
  TableCache* const table_cache_;
  const InternalKeyComparator icmp_;
  // 下一个可用的 FileNumber
  uint64_t next_file_number_;
  // manifest 文件的 FileNumber
  uint64_t manifest_file_number_;
  // 最后一个 SequnceNumber
  uint64_t last_sequence_;
  // log 文件的 FileNumber
  uint64_t log_number_;
  uint64_t prev_log_number_;  // 0 or backing store for memtable being compacted
  
  // manifest 文件的封装
  WritableFile* descriptor_file_;
  // manifest 文件的writer
  log::Writer* descriptor_log_;
  Version dummy_versions_;  // Head of circular doubly-linked list of versions.
  // 当前最新的的 Version
  Version* current_;        // == dummy_versions_.prev_
  // 为了尽量均匀 compact 每个 level，所以会将这一次 compact 的 end-key 作为
  // 下一次 compact 的 start-key。compactor_pointer_就保存着每个 level
  // 下一次 compact 的 start-key.
  // 除了 current_外的 Version，并不会做 compact，所以这个值并不保存在 Version 中。
  std::string compact_pointer_[config::kNumLevels];
  ```

  ![version_versionset.png](https://upload-images.jianshu.io/upload_images/9243349-9df3d8291992b9e5.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

## 快照(Snapshot)

snapshot是由客户端创建，实现上只是绑定了当前的sequence number，查找数据的时候都是以创建snapshot时的sequence number为基准，如果没有Snapshot会使用当前系统最新的sequence。

1. 取得当前的 SequnceNumber
2. 构造出 Snapshot，插入到已有链表中。

## compaction

level0文件超过一定数量(4)时，都会触发 Compaction 操作。非 Level 0 层的 Compaction 的流程和 Level 0 层的 Compaction  类似。区别在于，非 Level 0 层进行 Compaction 时，不一定将这一层的所有文件都 Compact  到下一层，而是可以选择指定的几个文件，或一个特定的 Key Range 进行 Compaction。compaction触发函数 `DBImpl::MaybeScheduleCompaction() `

### Minor Compaction

1. Write the contents of the previous memtable to an sstable.
2. Discard the memtable.
3. Delete the old log file and the old memtable.
4. Add the new sstable to the young (level-0) level.

#### 时机

1. 在调用put/delete API时，检查DBImpl::MakeRoomForWrite, 发现memtable的使用空间超过4M了；
2. 当前的immtable已经被dump出去成sstable. 也就是immtable=NULL 在上面的两个条件同时满足的情况下，会阻塞写线程，把memtable移到immtable。然后新起一个memtable,删除旧的log文件，让写操作写到这个memtable里。最后将imm放到后台线程去做compaction.

minor compaction是一个时效性要求非常高的过程，要求其在尽可能短的时间内完成，否则就会堵塞正常的写入操作，因此minor compaction的优先级高于major compaction。当进行minor compaction的时候有major compaction正在进行，则会首先暂停major compaction。

### Major Compaction

#### 时机

+ 当0层文件数超过预定的上限(默认为4个)
+ 当level i层文件的总大小超过(10 ^ i) MB
+ 当某个文件无效读取的次数过多

以level0为例，执行过程如下：

1. 将 Record 从 Level 0 中读出，并获取这组 Record 的 Key Range
2. 扫描 Level 1 中的文件，如果文件的中保存的 Record 和内存中的 Record 的 Key Range 有重叠，则将这个文件中的 Record 也加载到内存，以保证 Level 1 的 Record 在 Compaction 结束后依然是有序的
3. 将所有加载到内存的 Record 按照 <Key, SN> 进行排序
4. 如果发现有相同 Key 的 Record，则只保留 SN 最大的 Record
5. 将排序并清理后的 Record 拆分成多个文件，并写入磁盘，作为 Level 1 的文件
6. 将 Level 0 和 Level 1 中被 Compaction 的文件从磁盘上删除

# 流程

## put

- 生成一个新的 SN
- 将 Record 写入 WAL，用于保证 Crash Consistency
- 将 Record 写入内存中的 Memtable
- 当内存中的 Memtable 超过一定大小时，被 Dump 到 Level 0，作为一个数据文件。

## get

get操作会获取小于当前sequence或者snapshot指定sequence中最大的一个sequence作为匹配可以。

**查找过程：** 从 Level 0 层开始逐层扫描，寻找这一层中 Key 相同且 SN 最大的 Record，如果这个 Record 的  ValueType 为有效（type），则返回这个 Record 的 Value，如果 ValueType 为无效（delete），则意味着这个 Key 已经被删除了，返回 NotFound 错误。如果在某一层中找到了一个 Key 相同的 Record，则不会再向下一层寻找。由于每一层的 Record 是有序的，所以 LevelDB 在内存中保存了每个文件的 Key Range作为索引，这样可以加速查找的过程。

## delete

在 LevelDB 中，Delete 操作并不是通过直接在文件中删除一个 Record 的方式来实现的。实际上 Delete 的过程和 Put 的过程相似，也是写入一个 Record，唯一的区别是，Record 中的 ValueType 为 `DELETE`。 这样当执行 Get 操作时，如果发现 Record 中的 ValueType 为 `DELETE`， 则认为这个 Record 已经被删除掉了。而 Record 实际上从文件中被清除是在 Compaction 阶段完成的。

## Recovery

系统启动的时候需要恢复上次的状态以及数据基本流程如下：

* Read CURRENT to find name of the latest committed MANIFEST
* Read the named MANIFEST file
* Clean up stale files
* We could open all sstables here, but it is probably better to be lazy...
* Convert log（wal） chunk to a new level-0 sstable
* Start directing new writes to a new log file with recovered sequence#

## Compactions

​		When the size of level L exceeds its limit, we compact it in a background
thread. The compaction picks a file from level L and all overlapping files from
the next level L+1. Note that if a level-L file overlaps only part of a
level-(L+1) file, the entire file at level-(L+1) is used as an input to the
compaction and will be discarded after the compaction.  Aside: because level-0
is special (files in it may overlap each other), we treat compactions from
level-0 to level-1 specially: a level-0 compaction may pick more than one
level-0 file in case some of these files overlap each other.

A compaction merges the contents of the picked files to produce a sequence of
level-(L+1) files. We switch to producing a new level-(L+1) file after the
current output file has reached the target file size (2MB). We also switch to a
new output file when the key range of the current output file has grown enough
to overlap more than ten level-(L+2) files.  This last rule ensures that a later
compaction of a level-(L+1) file will not pick up too much data from
level-(L+2).

The old files are discarded and the new files are added to the serving state.

Compactions for a particular level rotate through the key space. In more detail,
for each level L, we remember the ending key of the last compaction at level L.
The next compaction for level L will pick the first file that starts after this
key (wrapping around to the beginning of the key space if there is no such
file).

Compactions drop overwritten values. They also drop deletion markers if there
are no higher numbered levels that contain a file whose range overlaps the
current key.

## 文件清理

`RemoveObsoleteFiles()` is called at the end of every compaction and at the end
of recovery. It finds the names of all files in the database. It deletes all log
files that are not the current log file. It deletes all table files that are not
referenced from some level and are not the output of an active compaction.

# 设计和实现

leveldb的设计和实现总的来说还是比较清晰的，个人觉得Iterator,builder, cache等的设计比较清晰，但是感觉compaction触发以及compact的操作应该单独设计一个模块，中间通过消息传递来清晰的划分出边界，这样读起来可能更容易一些。

## .log .ldb 等文件的序号统一管理

​       filenumber统一编码ldb，log等，编号代表文件数据的新旧程度。主要有以下两种用途：

+ 在恢复的时候可以按照序号递增排序，按照这个顺序恢复就能恢复出所有的数据，比如在启动时候从xxxxxx.log中恢复memtable中的内容，首先排序然后按照序号恢复就能得到最新的数据。
+ SSTable：在查找数据的时候，针对同一层的数据根据编号首先查找编号大的文件。

## Iterator

由于查找，merge等操作经常需要遍历整个table，为了接口的统一实现了Iterator。

## builder

生成 block 的过程封装成 BlockBuilder 处理。生成sstable 的过程封装成 TableBuilder 处理。

## 多线程内存模型

# 问题和优化

## 问题：写放大

**LSM Tree 将随机写转化为顺序写，而作为代价带来了大量的重复写入**

## 针对ssd的优化

由于在ssd上随机读写跟顺序读写只相差十倍左右，而且写放大也会造成ssd寿命下降。因此完全参照lsm树的设计并不能适应当前系统。

**优化策略:**

LSM需要的其实是key的有序，而跟value无关。所以自然而然的思路：**Key Value 分离存储**

![](https://pic3.zhimg.com/80/v2-295609fe3003aa8c2c3c6f3abb9150f6_1440w.jpg)

仅将Key值存储在LSM中，而将Value区分存储在Log中，数据访问就变成了：

- 修改：先append到value Log末尾，再将Key，Value地址插入LSM
- 删除：直接从LSM中删除，无效Value交给之后的垃圾回收
- 查询：LSM中获得地址，vLog中读取

这样带来显而易见的好处：

- 避免了归并时无效的value而移动，从而极大的降低了读写放大
- 显著减少了LSM的大小，以获得更好的cache效果

## PebblesDB优化写放大

PebblesDB 将 LSM-Tree 和 Skip-List 数据结构进行结合。在 LSM-Tree 中每一层引入 Guard 概念。  每一层中包含多个 Guard，Guard 和 Guard 之间的 Key 的范围是有序的，且没有重叠，但 Guard 内部包含多个  SSTable，这些 SSTable 的 Key 的范围允许重叠。参照论文[Fragemented Log-Structured Tree](https://link.zhihu.com/?target=http%3A//www.cs.utexas.edu/~vijay/papers/sosp17-pebblesdb.pdf)

![](https://pic3.zhimg.com/80/v2-aff05a477ab284c9be47eac7c69f292e_1440w.jpg)

当需要进行 Compaction 时，只需要将上层的 SSTable 读入内存，并按照下层的 Guard 将 SSTable  切分成多个新的 SSTable，并存放到下层对应的 Guard 中。**在这个过程中不需要读取下层的  SSTable**，也就在一定程度上避免了读写放大。作者将这种数据结构命名为 `Fragemented Log-Structured  Tree（FLSM)`。PebblesDB 最多可以减低 6.7 倍的写放大，写入性能最多提升 105%。

和 WiscKey  类似，PebblesDB 也会多 Range Query 的性能造成影响。这是由于 Guard 内部的 SSTable 的 Key  存在重叠，所以在读取连续的 Key 时，需要同时读取 Guard 中所有的 SSTable，才能够获得正确的结果。

WiscKey 和 PebblesDB 都已经开源，但在目前最主流的单机存储引擎 LevelDB 和 RocksDB 中，相关优化还并没有得到体现。我们也期待未来能有更多的关于 LSM-Tree 相关的优化算法出现。







[lsm upon ssd]: https://zhuanlan.zhihu.com/p/30773636

一些插图和部分描述是网上搜来的，如果侵权请通知我







