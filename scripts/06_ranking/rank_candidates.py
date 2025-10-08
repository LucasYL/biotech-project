
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：将证据得分、ADMET 与化学新颖度整合，生成候选化合物排名。
  - English: Combine evidence scores, ADMET flags, and novelty metrics to produce ranked candidates.

输入 / Inputs:
  - evidence_path: 证据表（mapping_evidence）。
  - admet_path: ADMET 结果表。
  - cluster_path: 化学相似性聚类表。
  - output_csv/topn_md: 排名 CSV 与 Top-N Markdown 输出路径。
  - config: 可选 YAML 配置（包含权重与 Top-N 数量）。

输出 / Outputs:
  - outputs/ranked_leads.csv
  - outputs/topN.md

主要功能 / Key Functions:
  - load_tables(...): 读取输入数据。
  - aggregate_evidence(...): 汇总每个化合物的证据得分与关联。
  - compute_scores(...): 应用权重计算最终分数并排序。

与其他模块的联系 / Relations to Other Modules:
  - build_report.py: 使用排名/TopN 生成报告内容。
  - dashboard/app.py: 展示排名结果与详细信息。
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
    raise RuntimeError("PyYAML is required to run rank_candidates.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"


def load_config(config_path: Path | None) -> Dict[str, Any]:
    target = config_path or DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with target.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {target}")
    return config


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required table not found: {path}")
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        return pd.read_csv(path, sep=sep)
    raise NotImplementedError(f"Unsupported table format: {path.suffix}")


def _sanitize_compound_id(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    return value


def aggregate_evidence(evidence: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame(
            columns=[
                "CompoundID",
                "EvidenceScore",
                "BGCUIDs",
                "FeatureIDs",
                "EvidenceCount",
            ]
        )

    df = evidence.copy()
    df.replace({"": pd.NA}, inplace=True)

    df["CompoundID"] = df["CompoundID"].apply(_sanitize_compound_id)
    df = df[df["CompoundID"] != ""]

    grouped = df.groupby("CompoundID", dropna=False)

    aggregated = grouped["EvidenceScore"].mean().to_frame(name="EvidenceScore")
    aggregated["EvidenceCount"] = grouped["EvidenceScore"].count()
    aggregated["BGCUIDs"] = grouped["BGCUID"].apply(
        lambda series: sorted({str(val) for val in series if pd.notna(val) and str(val).strip()})
    )
    aggregated["FeatureIDs"] = grouped["FeatureID"].apply(
        lambda series: sorted({str(val) for val in series if pd.notna(val) and str(val).strip()})
    )

    return aggregated.reset_index()


def enrich_with_bgc_feature_links(evidence: pd.DataFrame, aggregated: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty or aggregated.empty:
        return aggregated

    df = evidence.copy()
    df.replace({"": pd.NA}, inplace=True)

    compound_bgc = (
        df[df["EvidenceType"] == "bgc_compound"]
        .dropna(subset=["CompoundID", "BGCUID"])
        .groupby("BGCUID")["CompoundID"]
        .unique()
        .to_dict()
    )

    bgc_feature = (
        df[df["EvidenceType"] == "bgc_feature"]
        .dropna(subset=["BGCUID", "FeatureID"])
        .groupby("BGCUID")["FeatureID"]
        .unique()
        .to_dict()
    )

    feature_links: Dict[str, Set[str]] = {row["CompoundID"]: set(row["FeatureIDs"]) for _, row in aggregated.iterrows()}

    for bgc_uid, features in bgc_feature.items():
        compounds = compound_bgc.get(bgc_uid, [])
        for compound in compounds:
            feature_links.setdefault(compound, set()).update(str(f) for f in features)

    aggregated = aggregated.copy()
    aggregated["FeatureIDs"] = aggregated["CompoundID"].map(
        lambda cid: sorted(feature_links.get(cid, set()))
    )
    return aggregated


def join_metadata(
    ranking: pd.DataFrame,
    admet: pd.DataFrame,
    clusters: pd.DataFrame,
) -> pd.DataFrame:
    result = ranking.merge(admet, on="CompoundID", how="left", suffixes=('', '_admet'))
    clusters_unique = clusters.drop_duplicates("CompoundID") if not clusters.empty else clusters
    result = result.merge(clusters_unique, on="CompoundID", how="left")
    if "ClusterSize" not in result.columns:
        result["ClusterSize"] = pd.NA
    result["Novelty"] = result["ClusterSize"].apply(lambda size: 1.0 / size if isinstance(size, (int, float)) and size and size > 0 else 1.0)
    result["ADMETScore"] = result["RuleOfFivePass"].fillna(False).astype(float)
    return result


def compute_scores(df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    w1 = float(weights.get("evidence", 0.6))
    w2 = float(weights.get("admet", 0.3))
    w3 = float(weights.get("novelty", 0.1))

    df = df.copy()
    df["EvidenceScore"].fillna(0.0, inplace=True)
    df["AggregateScore"] = (
        w1 * df["EvidenceScore"].astype(float)
        + w2 * df["ADMETScore"].astype(float)
        + w3 * df["Novelty"].astype(float)
    )
    df.sort_values("AggregateScore", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["Rank"] = df.index + 1
    df["BGCUIDs"] = df["BGCUIDs"].apply(lambda values: "|".join(values) if isinstance(values, list) else "")
    df["FeatureIDs"] = df["FeatureIDs"].apply(lambda values: "|".join(values) if isinstance(values, list) else "")
    df["EvidenceSummary"] = df["EvidenceCount"].apply(lambda c: f"{int(c)} evidence links" if pd.notna(c) else "0 evidence links")
    return df


def write_outputs(df: pd.DataFrame, output_csv: Path, topn_md: Path, top_n: int) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    logger.info("Wrote ranked candidates to %s", output_csv)

    topn_md.parent.mkdir(parents=True, exist_ok=True)
    top_df = df.head(top_n)
    lines = ["# Top Candidates", ""]
    for _, row in top_df.iterrows():
        admet_label = "Pass" if bool(row.get("RuleOfFivePass", False)) else "Fail"
        cluster_label = row.get("ClusterID", "N/A")
        summary = (
            "- **Rank {rank}** – Compound {compound} | Score: {score:.3f} | ADMET: {admet} | Cluster: {cluster}"
        ).format(
            rank=int(row["Rank"]),
            compound=row["CompoundID"],
            score=float(row["AggregateScore"]),
            admet=admet_label,
            cluster=cluster_label,
        )
        lines.append(summary)
    topn_md.write_text("\n".join(lines), encoding="utf-8")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank candidate compounds using heuristic scores")
    parser.add_argument("evidence_path", type=Path)
    parser.add_argument("admet_path", type=Path)
    parser.add_argument("cluster_path", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("topn_md", type=Path)
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

    evidence = read_table(args.evidence_path)
    admet = read_table(args.admet_path)
    clusters = read_table(args.cluster_path)

    ranking_base = aggregate_evidence(evidence)
    ranking_base = enrich_with_bgc_feature_links(evidence, ranking_base)
    ranking_full = join_metadata(ranking_base, admet, clusters)

    weight_cfg = config.get("ranking", {}).get("weights", {})
    ranked = compute_scores(ranking_full, weight_cfg)

    top_n = int(config.get("ranking", {}).get("top_n", 5))
    write_outputs(ranked, args.output_csv, args.topn_md, top_n)


if __name__ == "__main__":  # pragma: no cover
    main()
