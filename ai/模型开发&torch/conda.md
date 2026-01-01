```zsh
# 清理notebook
conda uninstall notebook
pip install pip-autoremove
pip-autoremove jupyter -y

# 强制重装
pip install --upgrade --force-reinstall --no-cache-dir jupyter
conda install -y jupyter 
conda install jupyter notebook

```

# 创建conda虚拟环境

conda create --name myenv python=3.10

# 查看已安装的包

conda list

# 删除conda 虚拟环境

conda remove --name ENV_NAME --all

conda remove --name myenv --all



