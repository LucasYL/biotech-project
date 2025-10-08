# Actinomycete BGC → Metabolomics → Candidate Leads Mini-Pipeline

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 📚 **快速链接**: [安装指南](INSTALL.md) | [配置文件](config/pipeline_defaults.yaml) | [方法文档](REPORT_METHODS.md)

## 项目概述 / Project Overview
- 中文：本仓库展示一个教学级的放线菌基因组 BGC 与代谢组数据整合示例。
- English: This repository demonstrates an educational mini-pipeline that links actinomycete BGC mining with metabolomics data to prioritize candidate natural products.

## 依赖要求 / Requirements
- **Python**: 3.11
- **核心依赖**: pandas, numpy, matplotlib, RDKit, PyArrow, Streamlit
- **环境管理**: Conda (推荐)
- 完整依赖列表请参见 `env/environment.yml`

## 目录结构 / Repository Layout
```
project-root/
├─ data/                # 示例基因组、LC-MS/MS 与参考库数据
├─ scripts/             # 分模块脚本（解析、处理、链接、化学信息学、报告）
├─ dashboard/           # Streamlit 仪表板
├─ env/                 # 环境配置（Conda、Docker）
├─ tests/               # pytest 测试骨架
├─ docs/                # 文档与资源
├─ outputs/             # 运行后生成的结果
```

## 快速开始 / Quick Start

> 💡 **首次使用？** 请查看详细的 [安装指南 (INSTALL.md)](INSTALL.md)

### 1. 安装依赖 / Install Dependencies
```bash
# 使用 Conda 创建专用环境（推荐）
conda env create -f env/environment.yml --solver=classic

# 激活环境
conda activate actino-mini

# 验证安装
python --version  # 应显示 Python 3.11.x
```

### 2. 准备示例数据 / Prepare Example Data
```bash
# 将示例数据复制到工作目录
python scripts/download_example_data.py --force
```

### 3. 运行完整流水线 / Run Full Pipeline
```bash
# 执行完整的数据分析流程
bash scripts/run_all.sh
```

### 4. 启动交互式仪表板 / Launch Dashboard
```bash
# 方法1：使用便捷脚本（推荐）
bash start_dashboard.sh

# 方法2：使用环境中的 Python（手动方式）
/opt/miniconda3/envs/actino-mini/bin/python -m streamlit run dashboard/app.py

# 方法3：如果已激活 actino-mini 环境
streamlit run dashboard/app.py

# 打开浏览器访问：http://localhost:8501
```

### 常见问题 / Troubleshooting
**问题**: Streamlit 显示 "Repetition level histogram size mismatch" 错误  
**原因**: Streamlit 在错误的 Python 环境中运行（如 base 环境的 Python 3.12），导致 Parquet 文件版本不兼容  
**解决方案**: 使用完整路径启动 Streamlit 以确保使用正确的 Python 环境：
```bash
/opt/miniconda3/envs/actino-mini/bin/python -m streamlit run dashboard/app.py
```


## 示例数据 / Example Data
- 中文：仓库内置 `data/example_bundle/`，包含伪造的 BGC 输出、LC-MS/MS 特征表、化合物参考库和 ADMET 占位结果；运行 `python scripts/download_example_data.py` 会将其解压到 `data/` 目录。
- English: The repo ships with `data/example_bundle/`, a synthetic dataset covering BGC predictions, LC-MS/MS features, chemical references, and mock ADMET outputs. Running `python scripts/download_example_data.py` populates the `data/` tree.
- 注意 / Note: 数据完全为教学示例，并非真实实验结果；可在 `data/example/metadata.json` 查看来源说明。

## 配置 / Configuration
- 中文：默认参数定义在 `config/pipeline_defaults.yaml`，可复制后按需调整（如权重、阈值、日志级别）。
- English: Default parameters live in `config/pipeline_defaults.yaml`; copy and modify it to tweak weights, thresholds, and logging preferences.

## 运行输出 / Outputs
- `outputs/ranked_leads.csv`：候选排名列表。
- `outputs/topN.md`：排名前列 Markdown 摘要。
- `figures/top_scores.png`、`figures/cluster_sizes.csv`：报告/仪表板图表。
- `report/report.pdf` 与 `report/report.md`：自动生成的报告（若缺 PDF 依赖，则使用 Markdown）。

## 仪表板 / Dashboard
- 运行 `streamlit run dashboard/app.py` 查看交互式结果。
- 仪表板展示排名、证据、ADMET、聚类信息，并提供下载链接。


## 技术说明 / Technical Notes

### Python 环境兼容性
本项目使用 **Python 3.11** 开发，依赖 PyArrow/Parquet 进行数据序列化。如遇到以下问题：
- `Repetition level histogram size mismatch` 错误
- Parquet 文件无法读取

**根本原因**：
- 不同 Python 版本（如 3.11 vs 3.12）的 PyArrow 库版本不兼容
- 数据生成环境和读取环境的 Python 版本不一致

**解决方案**：
1. 确保所有操作（数据生成、仪表板运行）都在同一个 conda 环境 (`actino-mini`) 中执行
2. 使用显式路径启动 Streamlit：`/opt/miniconda3/envs/actino-mini/bin/python -m streamlit run dashboard/app.py`
3. 这确保了使用的是 actino-mini 环境的 Python 3.11，而不是系统默认的其他版本

### 数据流程架构
```
原始数据 → BGC解析 → 数据关联 → 化学信息学 → 排名评分 → 可视化报告
  (CSV)    (Parquet)  (Parquet)   (Parquet)   (CSV)      (Dashboard)
```

所有中间文件使用 Parquet 格式，确保高效读写和数据类型一致性。

## 学习路线 / Learning Pathway (草稿 Draft)
- BGC 解析 / BGC parsing：antiSMASH, DeepBGC, PRISM 文档链接待补充。
- LC-MS/MS 数据处理 / LC-MS/MS data processing：推荐阅读 MZmine 指南。
- 天然产物数据库 / Natural product databases：NPAtlas, MIBiG 官方资源。
- 化学信息学 / Cheminformatics：RDKit 官方教程。

## 后续计划 / Next Steps
- ✅ 建立脚手架 scaffold 与需求追踪文档。
- ✅ 填充脚本实现与示例数据。
- ✅ 解决环境兼容性问题。
- 🔶 拓展测试、日志和教学注释。
