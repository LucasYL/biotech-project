
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：解析 PRISM 输出版结果并整理为统一 BGC 表。
  - English: Parse PRISM export files and format them into the unified BGC table.

输入 / Inputs:
  - input_path: PRISM TSV/JSON output located in the example dataset.
  - output_path: Path to persist the standardized table.

输出 / Outputs:
  - A tabular dataset with PRISM-derived BGC metadata fields.

主要功能 / Key Functions:
  - parse_prism_file(...): Load and interpret PRISM clusters.
  - sanitize_records(...): Align with shared schema and annotate missing values.

与其他模块的联系 / Relations to Other Modules:
  - unify_bgc.py: Combines PRISM data with antiSMASH and DeepBGC tables.
  - link_bgc_ms_refs.py: Uses the standardized fields when linking to metabolomics evidence.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run parse_prism.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"
TOOL_NAME = "prism"


def load_config(config_path: Path | None) -> Dict[str, Any]:
    target = config_path or DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with target.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {target}")
    return config


def parse_prism_file(input_path: Path) -> pd.DataFrame:
    """Parse PRISM results into the shared schema."""
    if not input_path.exists():
        raise FileNotFoundError(f"PRISM file not found: {input_path}")

    if input_path.suffix.lower() in {".tsv", ".txt"}:
        df = pd.read_csv(input_path, sep="	")
    elif input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    else:
        raise NotImplementedError(
            f"Unsupported PRISM format: {input_path.suffix}. Use TSV or CSV exports."
        )

    rename_map = {
        "sample_id": "SampleID",
        "cluster_start": "Start",
        "cluster_end": "End",
        "product_prediction": "ClusterType",
        "confidence": "Score",
        "cluster_index": "ClusterIndex",
    }
    df = df.rename(columns=rename_map)

    if "ClusterIndex" not in df.columns:
        df["ClusterIndex"] = range(1, len(df) + 1)

    df["Tool"] = TOOL_NAME

    for col in ["CoreEnzymes", "MIBiGHits"]:
        df[col] = [[] for _ in range(len(df))]

    required = ["SampleID", "Tool", "ClusterIndex", "ClusterType", "Start", "End", "Score", "CoreEnzymes", "MIBiGHits"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"PRISM output missing required columns: {missing}")

    return df[required]


def sanitize_records(records: pd.DataFrame, schema_columns: List[str]) -> pd.DataFrame:
    """Clean PRISM records and align them with the canonical schema."""
    df = records.copy()
    for col in schema_columns:
        if col not in df.columns:
            df[col] = pd.NA
            logger.debug("Added missing column %s with NA defaults", col)

    df["Tool"] = TOOL_NAME
    df["ClusterIndex"] = pd.to_numeric(df["ClusterIndex"], errors="coerce")
    df["Start"] = pd.to_numeric(df["Start"], errors="coerce")
    df["End"] = pd.to_numeric(df["End"], errors="coerce")
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce")

    list_columns = {"CoreEnzymes", "MIBiGHits"}
    for col in list_columns:
        df[col] = df[col].apply(lambda value: value if isinstance(value, list) else [])

    return df.loc[:, schema_columns]


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
    logger.info("Wrote %d PRISM records to %s", len(df), output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse PRISM outputs into unified schema")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)
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

    logger.info("Parsing PRISM file: %s", args.input_path)
    raw = parse_prism_file(args.input_path)
    schema_columns = config.get("bgc_parsing", {}).get("schema", {}).get("columns")
    if not schema_columns:
        raise ValueError("Configuration missing bgc_parsing.schema.columns entries")

    cleaned = sanitize_records(raw, schema_columns)
    write_output(cleaned, args.output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
