下面给你一个 **完整可运行的 Python 示例**，演示如何用 **Faiss** 执行 K-Means 聚类，并包含必要的输入验证与参数说明。

Faiss 的 `Kmeans` 类可以直接在 CPU 或 GPU 上运行，适合大规模向量聚类。

***

## 示例代码（Python）

```python
import numpy as np
import faiss  # pip install faiss-cpu 或 faiss-gpu

def run_faiss_kmeans(data: np.ndarray, k: int, n_iter: int = 20, gpu: bool = False):
    """
    使用 Faiss 执行 K-Means 聚类
    :param data: 输入数据，形状 (num_samples, dim)，必须是 float32
    :param k: 聚类中心数
    :param n_iter: 迭代次数
    :param gpu: 是否使用 GPU
    :return: (centroids, assignments)
    """
    # 输入验证
    if not isinstance(data, np.ndarray):
        raise TypeError("data 必须是 numpy.ndarray 类型")
    if data.ndim != 2:
        raise ValueError("data 必须是二维数组 (num_samples, dim)")
    if data.dtype != np.float32:
        data = data.astype(np.float32)
    if k <= 0 or k > data.shape[0]:
        raise ValueError("k 必须大于 0 且小于等于样本数")

    dim = data.shape[1]

    # 创建 KMeans 对象
    kmeans = faiss.Kmeans(
        d=dim,        # 向量维度
        k=k,          # 聚类数
        niter=n_iter, # 迭代次数
        verbose=True, # 输出训练过程
        gpu=gpu       # 是否使用 GPU
    )

    # 训练
    kmeans.train(data)

    # 获取聚类中心
    centroids = kmeans.centroids

    # 将样本分配到最近的中心
    index = faiss.IndexFlatL2(dim)  # L2 距离索引
    index.add(centroids)
    distances, assignments = index.search(data, 1)  # 每个样本找 1 个最近中心

    return centroids, assignments.flatten()

if __name__ == "__main__":
    # 生成随机数据 (1000 个样本, 每个 128 维)
    np.random.seed(42)
    data = np.random.random((1000, 128)).astype(np.float32)

    # 执行 KMeans
    centroids, labels = run_faiss_kmeans(data, k=10, n_iter=25, gpu=False)

    print("\n聚类中心形状:", centroids.shape)
    print("前 10 个样本的聚类标签:", labels[:10])
```

***

## 运行说明

1. **安装 Faiss**
   
   - CPU 版本：

##### Bash

     `pip install faiss-cpu`

- GPU 版本（需 CUDA）：

##### Bash

     `pip install faiss-gpu`

2. **关键参数**
   
   - `d`：向量维度（自动从数据推断）
   - `k`：聚类中心数
   - `niter`：迭代次数（一般 20~50 即可）
   - `gpu`：是否使用 GPU 加速

3. **输出**
   
   - `centroids`：形状为 `(k, dim)` 的聚类中心
   - `assignments`：每个样本对应的聚类标签

***

✅ 这个版本已经包含 **输入验证**、**CPU/GPU 切换**、**聚类结果输出**，直接运行即可。  
如果你需要处理 **上亿级向量**，可以在 Faiss 中结合 **分块训练（clustering with nredo / spherical kmeans）** 来优化内存和速度。

***

如果你需要，我可以帮你写一个 **支持分批加载数据的 Faiss K-Means 版本**，这样可以直接处理内存放不下的超大数据集。  
你要我帮你加上吗？这样就能做亿级聚类了。