# 项目需求追踪 / Project Requirements Tracker

## 元信息 / Meta
- 文档版本 / Revision: v0.1 (自动生成：等待后续更新)
- 更新日期 / Last Updated: 2024-05-17
- 维护人 / Maintainer: Codex (collab with user)
- 参考来源 / Source: 项目 PRD（修订版）| Actinomycete BGC → Metabolomics → Candidate Leads Mini-Pipeline

## 1. 背景与目标 / Background & Objectives
- 构建一个面向教学的放线菌 BGC-代谢组整合最小管线，用示例数据演示从基因组挖掘到候选化合物排名的流程。
- 目标包括：解析 antiSMASH、DeepBGC、PRISM 结果；处理 LC-MS/MS 特征；加载天然产物参考库；根据启发式规则建立 BGC–Feature–Compound 联系；执行化学信息学分析；输出报告与仪表板。
- 框架需可复现、一键运行、具备清晰的日志与文档，并提供中英双语教学支持。

## 2. 角色与场景 / Personas & Scenarios
- 计算研究助理：负责执行脚本、维护管线、生成报告。
- 实验室生物/化学家：阅读候选清单与证据摘要，筛选实验对象。
- 项目主管/审稿人：验证方法、代码质量与复现性。

## 3. 成功标准 / Success Criteria
- **复现性**：提供 conda/Docker 环境；`make all` 或 `bash scripts/run_all.sh` 在示例数据上完整运行。
- **文档与注释**：代码文件头含中英文用途说明；核心函数 docstring；README、REPORT_METHODS、CONTRIBUTING 双语；提供学习资源与模块关系说明。
- **功能完整**：完成 BGC 解析/统一、LC-MS/MS 标准化、参照库加载、证据得分、化学指纹与聚类、ADMET 过滤、候选排序、可视化、报告与仪表板。
- **容错与测试**：对常见输入错误提供友好提示与日志；pytest 覆盖 BGC 合并、归一化、规则边界、随机数种子。

## 4. 范围界定 / Scope Definition
- **纳入 / In Scope**：解析示例输出；占位得分规则；教学性注释；可视化与报告；Streamlit 仪表板。
- **排除 / Out of Scope**：运行完整版 antiSMASH/DeepBGC/PRISM；高精度谱图分析；真实抗菌预测；湿实验验证。

## 5. 数据模型与文件 / Data Model & Files
- 主键：`SampleID`、`BGCID/BGCUID`、`FeatureID`、`CompoundID`。
- 关键表：`bgc_unified.parquet`、`features.parquet`、`chem_ref.parquet`、`mapping_evidence.parquet`、`admet.parquet`、`ranked_leads.csv`。
- 目录结构：按照 PRD 中的 `project-root/` 树进行创建，包含 `data/`, `scripts/01_bgc_parse/` 等子模块，`dashboard/`, `env/`, `tests/`, `docs/` 等。

## 6. 核心模块需求 / Module Requirements
1. **BGC 解析与统一**：各解析脚本支持缺失字段日志；`unify_bgc.py` 根据重叠阈值整合并生成统一 ID；单测覆盖重叠场景。（✅ antismash/deepbgc/prism 解析与合并测试已完成）
2. **LC-MS/MS 特征处理**：`normalize_ms_features.py` 提供列名参数、归一化、异常值处理、日志。（✅ 已实现并生成示例输出）
3. **参照库加载**：`load_chem_refs.py` 标准化字段，跳过无 SMILES，记录日志。（✅ 已实现）
4. **证据关联**：`link_bgc_ms_refs.py` 实现 BGC↔Compound、Feature↔Compound、BGC↔Feature 的启发式评分，可配置权重阈值，并输出归一化得分。（✅ 已实现初版启发式并产出示例数据）
5. **化学信息学**：使用 RDKit 计算 Morgan 指纹、Tanimoto/Butina 聚类，生成 UMAP 图，记录无效 SMILES。（✅ 已实现哈希回退指纹、相似性聚类和占位图摘要）
6. **ADMET 占位**：Lipinski 等规则，可导入外部批量结果。（✅ 占位规则与外部覆盖逻辑已实现）
7. **候选排名**：通过可配置权重整合得分，输出 CSV 与 `topN.md`。（✅ ranking/topN 脚本已实现，生成 report 依赖数据）
8. **报告与仪表板**：`build_report.py` 组合模板与图表输出 PDF；Streamlit `app.py` 提供筛选与下载。（✅ 已实现生成 Markdown→PDF、仪表板加载排名）

## 7. 非功能要求 / Non-Functional Requirements
- **注释与国际化**：所有脚本文件头、主要函数、复杂逻辑需双语说明；提供 *_notes.md 或注释指引学习路径。
- **配置管理**：YAML/JSON 参数文件，报告需写明版本与运行时间。
- **日志**：使用 Python logging，写入 `logs/`。
- **CI/CD**：pytest；可选 GitHub Actions 模板。

## 8. 运行指南 / Runbook Snapshot
1. 创建环境：`conda env create -f env/environment.yml` 或使用 `Dockerfile`。
2. 准备示例数据：使用 `scripts/download_example_data.py`（待实现）填充 `data/example/`。
3. 执行：`make all` 或 `bash scripts/run_all.sh` 生成输出（`outputs/ranked_leads.csv`, `figures/umap.png`, `report/report.pdf`）。
4. 查看结果：`streamlit run dashboard/app.py` 或直接阅读 PDF。

## 9. 里程碑建议 / Suggested Milestones
- D1-2：熟悉数据、搭 scaffold、建测试框架。
- D3-4：完成 BGC 解析与统一，补充双语注释。
- D5-6：实现 LC-MS/MS 处理、参照库、启发式关联与日志。
- D7-8：完成 RDKit、ADMET、排名与可视化；撰写报告草稿。
- D9：开发 Streamlit 仪表板；完善 README 与 Methods。
- D10：综合测试、调参、补齐日志与教学说明。

## 10. 风险与缓解 / Risks & Mitigations
- 工具依赖繁重 → 使用示例数据与解析脚本；附安装指南。
- 启发式得分准确度有限 → 报告中声明局限，提示后续改进方向。
- 新手学习曲线陡峭 → README 添加背景知识与学习路线；各脚本提供学习指引。
- 参数敏感 → 参数文件暴露权重与阈值，提供示例对比案例。

## 11. 待办与开放问题 / TODO & Open Points
- [x] 确认目录结构创建顺序与自动化脚本需求。
- [x] 设计参数配置文件格式（YAML/JSON）。
- [ ] 明确示例数据来源与授权说明。（当前使用教学用伪造数据，需在 README/REPORT 中补充来源与免责声明。）
- [x] 规划日志目录与文件命名规范。（logs/README.md 记录默认策略，后续脚本需读取配置。）
- [ ] 讨论 CI 集成（GitHub Actions）是否需要立即落地。

> 后续每次需求调整请更新本表，并在版本记录中注明变更内容。
