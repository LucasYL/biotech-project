# 安装指南 / Installation Guide

## 系统要求 / System Requirements
- macOS / Linux / Windows (with WSL)
- Conda or Miniconda
- 至少 2GB 可用磁盘空间

## 详细安装步骤 / Detailed Installation Steps

### 步骤 1: 安装 Conda (如果尚未安装)

如果您还没有 Conda，请从以下网站下载安装：
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (推荐，轻量级)
- [Anaconda](https://www.anaconda.com/download) (包含更多预装包)

### 步骤 2: 创建专用环境

```bash
# 进入项目目录
cd /path/to/Biotech

# 创建 conda 环境（使用 classic solver 避免兼容性问题）
conda env create -f env/environment.yml --solver=classic
```

**预期输出**：
```
Collecting package metadata (repodata.json): done
Solving environment: done
...
Installing pip dependencies: done
```

### 步骤 3: 激活环境

```bash
conda activate actino-mini
```

**验证环境**：
```bash
# 检查 Python 版本（应为 3.11.x）
python --version

# 检查关键包
python -c "import pandas; import rdkit; import streamlit; print('✓ All packages OK')"
```

### 步骤 4: 准备数据

```bash
# 运行数据准备脚本
python scripts/download_example_data.py --force
```

**预期输出**：
```
INFO - Deploying example data from .../data/example_bundle to .../data
INFO - Copied .../genomes
INFO - Copied .../bgc
...
```

### 步骤 5: 运行流水线

```bash
# 执行完整分析流程
bash scripts/run_all.sh
```

**流程步骤**：
1. ✓ BGC 解析 (antiSMASH, DeepBGC, PRISM)
2. ✓ MS 特征处理
3. ✓ 化学参考库加载
4. ✓ 多源数据关联
5. ✓ 分子指纹计算
6. ✓ 相似性聚类
7. ✓ ADMET 评估
8. ✓ 候选排名
9. ✓ 图表生成
10. ✓ 报告生成

**预期运行时间**: 约 30-60 秒

### 步骤 6: 启动仪表板

```bash
# 使用便捷脚本
bash start_dashboard.sh
```

浏览器将自动打开 `http://localhost:8501`

## 常见问题排查 / Troubleshooting

### 问题 1: Conda 命令找不到
```bash
# 确保 Conda 已添加到 PATH
echo $PATH | grep conda

# 如果没有，需要初始化 Conda
conda init bash  # 或 zsh, 根据您的 shell
```

### 问题 2: 环境创建失败
```bash
# 清理缓存后重试
conda clean --all
conda env create -f env/environment.yml --solver=classic
```

### 问题 3: Parquet 文件读取错误
**错误信息**: `Repetition level histogram size mismatch`

**原因**: Python 版本不一致（数据生成用 3.11，读取用 3.12）

**解决方案**:
```bash
# 方法1: 使用显式路径启动
/opt/miniconda3/envs/actino-mini/bin/python -m streamlit run dashboard/app.py

# 方法2: 重新生成数据
conda activate actino-mini
rm -rf intermediate/*
bash scripts/run_all.sh
```

### 问题 4: RDKit 安装失败
RDKit 需要从 conda-forge 频道安装：
```bash
conda install -c conda-forge rdkit
```

### 问题 5: 端口 8501 已被占用
```bash
# 查找并终止占用端口的进程
lsof -ti:8501 | xargs kill -9

# 或使用不同端口
streamlit run dashboard/app.py --server.port 8502
```

## 环境管理 / Environment Management

### 查看已安装的环境
```bash
conda env list
```

### 删除环境
```bash
conda env remove -n actino-mini
```

### 导出环境配置
```bash
conda env export > my_environment.yml
```

### 更新环境
```bash
conda env update -f env/environment.yml --prune
```

## 依赖说明 / Dependencies Explanation

### 核心依赖
- **pandas**: 数据处理和表格操作
- **numpy**: 数值计算
- **RDKit**: 化学信息学（分子指纹、性质计算）
- **PyArrow**: Parquet 文件读写
- **Streamlit**: 交互式仪表板
- **matplotlib**: 数据可视化

### 开发依赖
- **pytest**: 单元测试
- **pyyaml**: 配置文件解析
- **tabulate**: 表格格式化
- **fpdf2**: PDF 报告生成

## 性能优化建议 / Performance Tips

1. **使用 SSD**: Parquet 文件读写受 I/O 性能影响
2. **增加内存**: 大型数据集建议 8GB+ RAM
3. **安装 Watchdog**: 提升 Streamlit 文件监控性能
   ```bash
   pip install watchdog
   ```

## 下一步 / Next Steps

安装完成后，您可以：
1. 📊 浏览仪表板查看结果
2. 📝 阅读 `report/report.md` 查看详细报告
3. 🔬 修改 `config/pipeline_defaults.yaml` 调整参数
4. 📦 替换 `data/` 目录中的数据进行自己的分析

## 获取帮助 / Getting Help

- 查看项目 README.md
- 检查 `docs/requirements_tracker.md` 了解功能状态
- 查看 `REPORT_METHODS.md` 了解方法细节

