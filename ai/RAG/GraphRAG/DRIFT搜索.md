DRIFT 搜索（动态推理和灵活遍历推断）建立在微软的 GraphRAG 技术之上，结合了全局和局部搜索的特点，以一种平衡计算成本和质量结果的方法，使用我们的[DRIFT 搜索](https://github.com/microsoft/graphrag/blob/main//graphrag/query/structured_search/drift_search/)方法生成详细的响应。



## 方法论

![](https://msdocs.cn/graphrag/img/drift-search-diagram.png)

*图 1. 一个完整的 DRIFT 搜索层次结构，突出显示了 DRIFT 搜索过程的三个核心阶段。A（引言）：DRIFT 将用户的查询与语义最相关的 K 个社区报告进行比较，生成一个广泛的初始答案和后续问题，以引导进一步的探索。B（后续）：DRIFT 使用局部搜索来优化查询，生成额外的中间答案和后续问题，从而增强特异性，引导引擎获取上下文丰富的信息。图表中的每个节点上的字形显示了算法继续查询扩展步骤的置信度。C（输出层次结构）：最终输出是按相关性排序的问题和答案的分层结构，反映了全局洞察和局部细化的平衡组合，使结果具有适应性和全面性。*

