# Actinomycete BGC → Metabolomics Mini-Pipeline Report

## Run Metadata
- Generated at: 2025-10-09T22:59:02.962037 UTC

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

- **Rank 1** – Compound CMP010 | Score: 0.701 | ADMET: Fail | Cluster: CLUSTER_010
- **Rank 2** – Compound CMP003 | Score: 0.689 | ADMET: Fail | Cluster: CLUSTER_003
- **Rank 3** – Compound CMP006 | Score: 0.676 | ADMET: Fail | Cluster: CLUSTER_006
- **Rank 4** – Compound CMP002 | Score: 0.665 | ADMET: Fail | Cluster: CLUSTER_002
- **Rank 5** – Compound CMP001 | Score: 0.655 | ADMET: Fail | Cluster: CLUSTER_001

## Figures

- cluster_sizes.csv
- cluster_summary.txt
- top_scores.png

## Ranking Snapshot

| CompoundID   |   EvidenceScore |   EvidenceCount | BGCUIDs                                                  | FeatureIDs                                                  | SMILES                                                   |     MW |   logP |   TPSA |   HBD |   HBA |   RotatableBonds |   AromaticRings |   QED |   MolarRefractivity |   FractionCSP3 | Lipinski_Pass   | Veber_Pass   | DrugLikeness   | OralBioavailability   | ClusterID   |   ClusterSize |   Novelty |   ADMETScore |   AggregateScore |   Rank | EvidenceSummary   |
|:-------------|----------------:|----------------:|:---------------------------------------------------------|:------------------------------------------------------------|:---------------------------------------------------------|-------:|-------:|-------:|------:|------:|-----------------:|----------------:|------:|--------------------:|---------------:|:----------------|:-------------|:---------------|:----------------------|:------------|--------------:|----------:|-------------:|-----------------:|-------:|:------------------|
| CMP010       |             0.6 |               3 | SampleA_BGCUID_001|SampleA_BGCUID_002|SampleB_BGCUID_001 | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CCC(C)C(=O)C1=CC=C(C=C1)OC2=CC=CC=C2C(=O)O               | 298.34 |   4.41 |  63.6  |     1 |     3 |                6 |               2 | 0.802 |               83.7  |          0.222 | True            | True         | Excellent      | Likely                | CLUSTER_010 |             1 |         1 |        0.802 |           0.7006 |      1 | 3 evidence links  |
| CMP003       |             0.6 |               2 | SampleA_BGCUID_001|SampleB_BGCUID_001                    | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CCN(CC)C(=O)C1CCCN1C(=O)O                                | 214.26 |   1    |  60.85 |     1 |     2 |                3 |               0 | 0.762 |               55.68 |          0.8   | True            | True         | Excellent      | Likely                | CLUSTER_003 |             1 |         1 |        0.762 |           0.6886 |      2 | 2 evidence links  |
| CMP006       |             0.6 |               3 | SampleA_BGCUID_001|SampleA_BGCUID_002|SampleB_BGCUID_001 | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CCCCC(=O)C1=CC=CC=C1O                                    | 178.23 |   2.77 |  37.3  |     1 |     2 |                4 |               1 | 0.72  |               51.96 |          0.364 | True            | True         | Excellent      | Likely                | CLUSTER_006 |             1 |         1 |        0.72  |           0.676  |      3 | 3 evidence links  |
| CMP002       |             0.6 |               3 | SampleA_BGCUID_001|SampleA_BGCUID_002|SampleB_BGCUID_001 | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CCC1C(C(=O)O1)OC2=CC=CC=C2                               | 192.21 |   1.77 |  35.53 |     0 |     3 |                3 |               1 | 0.685 |               51.03 |          0.364 | True            | True         | Good           | Likely                | CLUSTER_002 |             1 |         1 |        0.685 |           0.6655 |      4 | 3 evidence links  |
| CMP001       |             0.6 |               2 | SampleA_BGCUID_001|SampleB_BGCUID_001                    | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CC(C)C1=CC(=O)NC(=O)N1C                                  | 168.2  |   0.2  |  54.86 |     1 |     3 |                1 |               1 | 0.651 |               46.39 |          0.5   | True            | True         | Good           | Likely                | CLUSTER_001 |             1 |         1 |        0.651 |           0.6553 |      5 | 2 evidence links  |
| CMP005       |             0.6 |               2 | SampleA_BGCUID_001|SampleB_BGCUID_001                    | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CC(C)CC1NC(=O)C(NC(=O)C(NC1=O)C)C                        | 255.32 |  -0.46 |  87.3  |     3 |     3 |                2 |               0 | 0.624 |               66.6  |          0.75  | True            | True         | Good           | Likely                | CLUSTER_005 |             1 |         1 |        0.624 |           0.6472 |      6 | 2 evidence links  |
| CMP008       |             0.6 |               2 | SampleA_BGCUID_001|SampleB_BGCUID_001                    | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CC(C)C(=O)NC(C)C(=O)O                                    | 159.18 |   0.23 |  66.4  |     2 |     2 |                3 |               0 | 0.619 |               40.08 |          0.714 | True            | True         | Good           | Likely                | CLUSTER_008 |             1 |         1 |        0.619 |           0.6457 |      7 | 2 evidence links  |
| CMP004       |             0.6 |               3 | SampleA_BGCUID_001|SampleA_BGCUID_002|SampleB_BGCUID_001 | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CN1C=NC2=C1C(=O)N(C(=O)N2C)C                             | 194.19 |  -1.03 |  61.82 |     0 |     6 |                0 |               2 | 0.538 |               51.2  |          0.375 | True            | True         | Good           | Likely                | CLUSTER_004 |             1 |         1 |        0.538 |           0.6214 |      8 | 3 evidence links  |
| CMP007       |             0.6 |               2 | SampleA_BGCUID_001|SampleB_BGCUID_001                    | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CCCCCCCCCCCCCC(=O)NC(CO)C(=O)O                           | 315.45 |   3.25 |  86.63 |     3 |     3 |               15 |               0 | 0.405 |               87.73 |          0.882 | True            | False        | Moderate       | Unlikely              | CLUSTER_007 |             1 |         1 |        0.405 |           0.5815 |      9 | 2 evidence links  |
| CMP009       |             0.6 |               3 | SampleA_BGCUID_001|SampleA_BGCUID_002|SampleB_BGCUID_001 | F001|F002|F003|F004|F005|F006|F007|F008|F009|F010|F011|F012 | CC(C)CC(NC(=O)C(NC(=O)C(NC(=O)C(N)CC(C)C)C)CC(C)C)C(=O)O | 428.57 |   1.01 | 150.62 |     5 |     5 |               13 |               0 | 0.295 |              115.44 |          0.81  | True            | False        | Poor           | Unlikely              | CLUSTER_009 |             1 |         1 |        0.295 |           0.5485 |     10 | 3 evidence links  |