# Actinomycete BGC → Metabolomics Mini-Pipeline Report

## Run Metadata
- Generated at: 2025-10-03T19:50:10.813840 UTC

## Methods

# Methods Documentation / 方法文档

> 中文：本文件将在最终报告中引用，描述数据来源、处理步骤、评分规则及局限性。
> English: This document will be referenced in the final report, detailing data sources, processing steps, scoring rules, and limitations.

## Data Sources / 数据来源
- TODO: antiSMASH / DeepBGC / PRISM 示例文件说明。
- TODO: LC-MS/MS 示例表格说明。
- TODO: NPAtlas/MIBiG 子集说明。

## Processing Steps / 处理步骤
- TODO: BGC 解析与统一。
- TODO: LC-MS/MS 归一化。
- TODO: 化学参考库加载。
- TODO: 证据关联与打分。
- TODO: 化学指纹与聚类。
- TODO: ADMET 过滤与候选排名。

## Parameters & Versions / 参数与版本
- TODO: 记录关键权重、阈值、版本号与运行日期。

## Limitations & Future Work / 局限与未来工作
- TODO: 描述启发式方法的限制、潜在改进方向。


## Top Candidates

# Top Candidates

- **Rank 1** – Compound CMP001 | Score: 0.760 | ADMET: Pass | Cluster: CLUSTER_001
- **Rank 2** – Compound CMP002 | Score: 0.760 | ADMET: Pass | Cluster: CLUSTER_002
- **Rank 3** – Compound CMP003 | Score: 0.760 | ADMET: Pass | Cluster: CLUSTER_003
- **Rank 4** – Compound <NA> | Score: 0.200 | ADMET: Pass | Cluster: nan

## Figures

- cluster_sizes.csv
- cluster_summary.txt
- top_scores.png

## Ranking Snapshot

| CompoundID   |   EvidenceScore |   EvidenceCount | BGCUIDs                                                  | FeatureIDs                    |   logP |   TPSA |   HBD |   HBA |   MW | ToxicityFlag   |   RuleOfFivePass | ClusterID   |   ClusterSize |   Novelty |   ADMETScore |   AggregateScore |   Rank | EvidenceSummary   |
|:-------------|----------------:|----------------:|:---------------------------------------------------------|:------------------------------|-------:|-------:|------:|------:|-----:|:---------------|-----------------:|:------------|--------------:|----------:|-------------:|-----------------:|-------:|:------------------|
| CMP001       |        0.6      |               1 | SampleA_BGCUID_001                                       | F001|F002|F003                |   1    |     48 |     4 |     8 |  166 | Low            |                1 | CLUSTER_001 |             1 |         1 |            1 |             0.76 |      1 | 1 evidence links  |
| CMP002       |        0.6      |               2 | SampleA_BGCUID_001|SampleA_BGCUID_002                    | F001|F002|F003                |   1.25 |     36 |     3 |     6 |  190 | Low            |                1 | CLUSTER_002 |             1 |         1 |            1 |             0.76 |      2 | 2 evidence links  |
| CMP003       |        0.6      |               1 | SampleA_BGCUID_001                                       | F001|F002|F003                |   1.25 |     60 |     5 |    10 |  206 | Low            |                1 | CLUSTER_003 |             1 |         1 |            1 |             0.76 |      3 | 1 evidence links  |
| nan          |        0.166667 |               9 | SampleA_BGCUID_001|SampleA_BGCUID_002|SampleB_BGCUID_001 | F001|F002|F003|F004|F005|F006 | nan    |    nan |   nan |   nan |  nan | nan            |              nan | nan         |           nan |         1 |            0 |             0.2  |      4 | 9 evidence links  |