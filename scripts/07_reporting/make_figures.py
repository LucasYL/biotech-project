# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：生成报告和仪表板所需的核心图表或摘要。
  - English: Produce key visuals or summaries for reports and dashboards.

输入 / Inputs:
  - ranking_path: Ranked candidates CSV。
  - cluster_path: 相似性聚类结果表。
  - output_dir: 图表输出目录。

输出 / Outputs:
  - figures/top_scores.png（若 Matplotlib 可用）或 figures/top_scores.txt（回退）。
  - figures/cluster_sizes.csv 摘要。

主要功能 / Key Functions:
  - load_tables(...): 读取排名与聚类表。
  - generate_top_scores_plot(...): 绘制前 N 名得分条形图（支持占位回退）。
  - summarize_clusters(...): 生成聚类统计。

与其他模块的联系 / Relations to Other Modules:
  - build_report.py: 引用生成的图表与摘要。
  - dashboard/app.py: 可加载相同的可视化资产。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict

import pandas as pd

try:  # pragma: no cover - Matplotlib optional
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:  # pragma: no cover
    plt = None  # type: ignore
    _HAS_MPL = False

logger = logging.getLogger(__name__)


def load_tables(ranking_path: Path, cluster_path: Path) -> Dict[str, pd.DataFrame]:
    if not ranking_path.exists():
        raise FileNotFoundError(f"Ranking file not found: {ranking_path}")
    ranking = pd.read_csv(ranking_path)

    if not cluster_path.exists():
        logger.warning("Cluster file not found: %s", cluster_path)
        clusters = pd.DataFrame()
    else:
        if cluster_path.suffix == '.parquet':
            clusters = pd.read_parquet(cluster_path)
        else:
            sep = ',' if cluster_path.suffix == '.csv' else '\t'
            clusters = pd.read_csv(cluster_path, sep=sep)

    return {"ranking": ranking, "clusters": clusters}


def generate_top_scores_plot(ranking: pd.DataFrame, output_dir: Path, top_n: int = 10) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    subset = ranking.head(max(top_n, 1))
    if subset.empty:
        path = output_dir / 'top_scores.txt'
        path.write_text('No ranking data available for plotting.\n', encoding='utf-8')
        return path

    if _HAS_MPL:
        plt.figure(figsize=(8, 4))
        plt.bar(subset['CompoundID'].astype(str), subset['AggregateScore'])
        plt.xlabel('CompoundID')
        plt.ylabel('Aggregate Score')
        plt.title(f'Top {top_n} Aggregate Scores')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plot_path = output_dir / 'top_scores.png'
        plt.savefig(plot_path, dpi=150)
        plt.close()
        logger.info("Saved bar chart to %s", plot_path)
        return plot_path

    path = output_dir / 'top_scores.txt'
    lines = ['Top Candidates (Score)', '======================', '']
    for _, row in subset.iterrows():
        lines.append(f"{int(row['Rank']):>3}. {row['CompoundID']}: {row['AggregateScore']:.3f}")
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    logger.warning("Matplotlib unavailable; wrote text summary to %s", path)
    return path


def summarize_clusters(clusters: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if clusters.empty or 'ClusterID' not in clusters.columns:
        summary_path = output_dir / 'cluster_sizes.txt'
        summary_path.write_text('No cluster data available.\n', encoding='utf-8')
        return summary_path

    summary = (
        clusters.groupby('ClusterID', dropna=False)['CompoundID']
        .count()
        .reset_index(name='MemberCount')
        .sort_values('MemberCount', ascending=False)
    )
    summary_path = output_dir / 'cluster_sizes.csv'
    summary.to_csv(summary_path, index=False)
    logger.info("Wrote cluster summary to %s", summary_path)
    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate figures for reports and dashboards')
    parser.add_argument('ranking_path', type=Path)
    parser.add_argument('cluster_path', type=Path)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--top-n', type=int, default=10)
    parser.add_argument('--log-level', default='INFO')
    return parser


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - CLI
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(levelname)s - %(message)s',
    )

    tables = load_tables(args.ranking_path, args.cluster_path)
    generate_top_scores_plot(tables['ranking'], args.output_dir, args.top_n)
    summarize_clusters(tables['clusters'], args.output_dir)


if __name__ == '__main__':  # pragma: no cover
    main()
