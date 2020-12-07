# 安装catechism](https://github.com/CCD-MPC/catechism

## 下载

```shell

git clone https://github.com/CCD-MPC/catechism.git	
```

## 生成配置中心[chamberlain](https://github.com/CCD-MPC/catechism/tree/master/chamberlain),并启动

```bash
cd chamberlain
docker build . -t chamberlain:v1
# 该容器是一个flask写的web程序，绑定端口为8080
docker run -d --name chamberlain -p 8080:8080 chamberlain:v1
# 查看是否运行
```

# 

