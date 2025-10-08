
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：计算指纹相似度并执行简单的 Butina 风格聚类，同时可生成占位图。
  - English: Compute fingerprint similarity and perform a simple Butina-style clustering with optional figure output.

输入 / Inputs:
  - fingerprint_path: 指纹表（Parquet/CSV），需含 CompoundID、Fingerprint。
  - output_path: 聚类结果输出。
  - figure_path: 可选占位图路径。

输出 / Outputs:
  - similarity_clusters.parquet/CSV，含 CompoundID、ClusterID、ClusterSize。
  - 若提供 figure_path，则生成占位文本说明。

主要功能 / Key Functions:
  - load_fingerprints(...): 读取指纹数据。
  - cluster_fingerprints(...): 基于 Tanimoto 阈值的贪心聚类。
  - write_outputs(...): 写出聚类表与可选图示。

与其他模块的联系 / Relations to Other Modules:
  - rank_candidates.py: 使用聚类结果计算新颖度。
  - make_figures.py: 可将聚类摘要用于图表。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run similarity_cluster.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"


def load_config(config_path: Path | None) -> Dict:
    target = config_path or DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with target.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {target}")
    return config


def load_fingerprints(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Fingerprint table not found: {path}")
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        df = pd.read_csv(path, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported table format: {path.suffix}")
    required = {"CompoundID", "Fingerprint"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Fingerprint table missing columns: {missing}")
    return df


def fingerprint_to_bits(bitstring: str) -> Set[int]:
    return {idx for idx, bit in enumerate(bitstring) if bit == "1"}


def tanimoto(a: Set[int], b: Set[int]) -> float:
    if not a and not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return intersection / union


def cluster_fingerprints(
    df: pd.DataFrame,
    threshold: float,
) -> pd.DataFrame:
    entries = []
    for _, row in df.iterrows():
        entries.append(
            {
                "CompoundID": str(row["CompoundID"]),
                "bits": fingerprint_to_bits(str(row["Fingerprint"])),
            }
        )

    clusters: List[Dict[str, Any]] = []
    for entry in entries:
        assigned = False
        for cluster in clusters:
            score = tanimoto(entry["bits"], cluster["representative"])
            if score >= threshold:
                cluster["members"].append(entry["CompoundID"])
                cluster["bitsets"].append(entry["bits"])
                assigned = True
                break
        if not assigned:
            clusters.append(
                {
                    "representative": entry["bits"],
                    "members": [entry["CompoundID"]],
                    "bitsets": [entry["bits"]],
                }
            )

    cluster_rows: List[Dict[str, Any]] = []
    for idx, cluster in enumerate(clusters, start=1):
        cluster_id = f"CLUSTER_{idx:03d}"
        members = sorted(cluster["members"])
        size = len(members)
        for member in members:
            cluster_rows.append(
                {
                    "CompoundID": member,
                    "ClusterID": cluster_id,
                    "ClusterSize": size,
                }
            )

    return pd.DataFrame(cluster_rows)


def write_outputs(df: pd.DataFrame, output_path: Path, figure_path: Path | None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "	"
        df.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported output format: {output_path.suffix}")
    logger.info("Wrote cluster assignments for %d compounds", len(df))

    if figure_path is not None:
        figure_path.parent.mkdir(parents=True, exist_ok=True)
        summary_lines = ["# Similarity Cluster Summary", "", f"Total compounds: {df['CompoundID'].nunique()}"]
        for cluster_id, group in df.groupby("ClusterID"):
            summary_lines.append(f"- {cluster_id}: {group.shape[0]} members")
        figure_path.write_text("\n".join(summary_lines), encoding="utf-8")
        logger.info("Wrote placeholder cluster summary to %s", figure_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cluster molecular fingerprints with a simple heuristic")
    parser.add_argument("fingerprint_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--figure-path", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--log-level", default=None)
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    logging_config = config.get("logging", {})
    log_level = args.log_level or logging_config.get("level", "INFO")
    logging.basicConfig(
        level=getattr(logging, str(log_level).upper(), logging.INFO),
        format=logging_config.get("format", "%(levelname)s - %(message)s"),
    )

    threshold = float(config.get("cheminformatics", {}).get("clustering", {}).get("threshold", 0.7))

    fp_df = load_fingerprints(args.fingerprint_path)
    cluster_df = cluster_fingerprints(fp_df, threshold)
    write_outputs(cluster_df, args.output_path, args.figure_path)


if __name__ == "__main__":  # pragma: no cover
    main()
