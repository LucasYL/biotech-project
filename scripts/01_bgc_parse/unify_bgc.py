
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：合并 antiSMASH、DeepBGC、PRISM 的标准化输出，生成统一 BGCUID 表。
  - English: Merge normalized outputs from antiSMASH, DeepBGC, and PRISM into a unified BGCUID table.

输入 / Inputs:
  - antismash_path / deepbgc_path / prism_path: Paths to standardized tool-specific tables.
  - output_path: Destination path for the merged table (Parquet/CSV).
  - overlap_threshold: Fractional overlap threshold to cluster regions into single BGCUIDs.

输出 / Outputs:
  - Unified table containing BGCUID, sample identifiers, combined metadata, and aggregated scores.

主要功能 / Key Functions:
  - load_table(...): Read standardized tables and annotate provenance.
  - merge_overlaps(...): Group clusters sharing genomic loci into unified records.
  - write_output(...): Persist merged results with consistent schema.

与其他模块的联系 / Relations to Other Modules:
  - link_bgc_ms_refs.py: Consumes the unified table when building BGC-feature associations.
  - tests/test_schemas.py: Validates schema expectations including overlap handling cases.
"""

from __future__ import annotations

import argparse
import logging
from ast import literal_eval
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run unify_bgc.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"


@dataclass
class BGCRecord:
    sample_id: str
    start: float
    end: float
    score: float | None
    tool: str
    cluster_type: str
    core_enzymes: List[str]
    mibig_hits: List[str]
    bgc_id: str


class UnionFind:
    def __init__(self, nodes: List[int]) -> None:
        self.parent = {node: node for node in nodes}

    def find(self, node: int) -> int:
        parent = self.parent[node]
        if parent != node:
            self.parent[node] = self.find(parent)
        return self.parent[node]

    def union(self, a: int, b: int) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a != root_b:
            self.parent[root_b] = root_a


def load_config(config_path: Path | None) -> Dict:
    path = config_path or DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {path}")
    return config


def load_table(path: Optional[Path]) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    if not path.exists():
        raise FileNotFoundError(f"BGC table not found: {path}")
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        df = pd.read_csv(path, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported table format: {path.suffix}")
    return df


def _ensure_list(series: pd.Series) -> pd.Series:
    def convert(value: object) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value]
        if value is None:
            return []
        if isinstance(value, float) and pd.isna(value):
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = literal_eval(stripped)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed]
                except (ValueError, SyntaxError):
                    pass
            return [stripped]
        return [str(value)]
    return series.apply(convert)


def prepare_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    if "Tool" not in df.columns:
        raise ValueError("Input table missing 'Tool' column")
    if "ClusterIndex" not in df.columns:
        df["ClusterIndex"] = range(1, len(df) + 1)

    df["CoreEnzymes"] = _ensure_list(df.get("CoreEnzymes", pd.Series([[]] * len(df))))
    df["MIBiGHits"] = _ensure_list(df.get("MIBiGHits", pd.Series([[]] * len(df))))

    df["Start"] = pd.to_numeric(df["Start"], errors="coerce")
    df["End"] = pd.to_numeric(df["End"], errors="coerce")
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce")

    df["BGCID"] = (
        df["SampleID"].astype(str)
        + "_"
        + df["Tool"].astype(str)
        + "_"
        + df["ClusterIndex"].fillna(-1).astype(int).astype(str)
    )
    return df


def reciprocal_overlap(record_a: pd.Series, record_b: pd.Series) -> float:
    start = max(record_a["Start"], record_b["Start"])
    end = min(record_a["End"], record_b["End"])
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0.0
    length_a = record_a["End"] - record_a["Start"]
    length_b = record_b["End"] - record_b["Start"]
    if length_a <= 0 or length_b <= 0:
        return 0.0
    intersection = end - start
    frac_a = intersection / length_a
    frac_b = intersection / length_b
    return min(frac_a, frac_b)


def merge_overlaps(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "BGCUID",
                "SampleID",
                "Tool",
                "ClusterType",
                "Start",
                "End",
                "Score",
                "CoreEnzymes",
                "MIBiGHits",
                "MemberBGCIDs",
            ]
        )

    unified_rows = []

    for sample_id, sample_df in df.groupby("SampleID", sort=True):
        sample_df = sample_df.reset_index(drop=True)
        if len(sample_df) == 1:
            row = sample_df.iloc[0]
            unified_rows.append(
                {
                    "SampleID": sample_id,
                    "Tool": row["Tool"],
                    "ClusterType": row["ClusterType"],
                    "Start": row["Start"],
                    "End": row["End"],
                    "Score": row["Score"],
                    "CoreEnzymes": row["CoreEnzymes"],
                    "MIBiGHits": row["MIBiGHits"],
                    "MemberBGCIDs": [row["BGCID"]],
                }
            )
            continue

        uf = UnionFind(list(sample_df.index))
        for idx_a, idx_b in combinations(sample_df.index, 2):
            overlap = reciprocal_overlap(sample_df.loc[idx_a], sample_df.loc[idx_b])
            if overlap >= threshold:
                uf.union(idx_a, idx_b)

        groups: Dict[int, List[int]] = {}
        for idx in sample_df.index:
            root = uf.find(idx)
            groups.setdefault(root, []).append(idx)

        for group_idx, members in sorted(groups.items()):
            subset = sample_df.loc[members]
            tools = sorted(set(subset["Tool"]))
            cluster_types = sorted({ct for ct in subset["ClusterType"] if isinstance(ct, str) and ct})
            start = subset["Start"].min()
            end = subset["End"].max()
            score = subset["Score"].mean(skipna=True)
            enzymes = sorted({gene for row in subset["CoreEnzymes"] for gene in (row or [])})
            mibig = sorted({hit for row in subset["MIBiGHits"] for hit in (row or [])})
            member_ids = subset["BGCID"].tolist()

            unified_rows.append(
                {
                    "SampleID": sample_id,
                    "Tool": "|".join(tools),
                    "ClusterType": "|".join(cluster_types) if cluster_types else "",
                    "Start": start,
                    "End": end,
                    "Score": score,
                    "CoreEnzymes": enzymes,
                    "MIBiGHits": mibig,
                    "MemberBGCIDs": member_ids,
                }
            )

    unified_df = pd.DataFrame(unified_rows)
    if unified_df.empty:
        return unified_df

    unified_df = unified_df.sort_values(["SampleID", "Start", "End"]).reset_index(drop=True)

    grouped_counts: Dict[str, int] = {}
    bgc_uids = []
    for _, row in unified_df.iterrows():
        sample = row["SampleID"]
        grouped_counts.setdefault(sample, 0)
        grouped_counts[sample] += 1
        bgc_uids.append(f"{sample}_BGCUID_{grouped_counts[sample]:03d}")

    unified_df.insert(0, "BGCUID", bgc_uids)
    return unified_df


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "	"
        df.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(
            f"Unsupported output format: {output_path.suffix}. Use .parquet, .csv, or .tsv"
        )
    logger.info("Wrote %d unified BGC records to %s", len(df), output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unify BGC tables across prediction tools")
    parser.add_argument("antismash_path", type=Path)
    parser.add_argument("deepbgc_path", type=Path)
    parser.add_argument("prism_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--overlap-threshold",
        type=float,
        default=0.5,
        help="Minimum reciprocal overlap to consider clusters equivalent",
    )
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

    logger.info(
        "Merging BGC tables with threshold %.2f", args.overlap_threshold
    )

    tables = []
    for path in (args.antismash_path, args.deepbgc_path, args.prism_path):
        df = load_table(path)
        if df.empty:
            logger.warning("Table %s is empty", path)
        tables.append(prepare_records(df))

    combined = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    unified = merge_overlaps(combined, args.overlap_threshold)
    write_output(unified, args.output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
