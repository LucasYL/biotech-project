
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：解析 DeepBGC 输出结果并转换为统一 BGC 表结构。
  - English: Parse DeepBGC outputs and convert them into the unified BGC table schema.

输入 / Inputs:
  - input_path: DeepBGC JSON/TSV results from the example dataset.
  - output_path: Path to write the standardized table (Parquet/CSV).

输出 / Outputs:
  - A table containing DeepBGC-derived BGC metadata ready for merged analysis.

主要功能 / Key Functions:
  - parse_deepbgc_file(...): Load DeepBGC predictions and format them consistently.
  - sanitize_records(...): Apply schema defaults and collect parsing diagnostics.

与其他模块的联系 / Relations to Other Modules:
  - unify_bgc.py: Consumes DeepBGC tables to merge across tools.
  - link_bgc_ms_refs.py: Uses sanitized BGC fields to connect to metabolomics evidence.
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
    raise RuntimeError("PyYAML is required to run parse_deepbgc.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"
TOOL_NAME = "deepbgc"


def load_config(config_path: Path | None) -> Dict[str, Any]:
    target = config_path or DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with target.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {target}")
    return config


def parse_deepbgc_file(input_path: Path) -> pd.DataFrame:
    """Parse DeepBGC output into the core schema."""
    if not input_path.exists():
        raise FileNotFoundError(f"DeepBGC file not found: {input_path}")

    if input_path.suffix.lower() in {".tsv", ".txt"}:
        df = pd.read_csv(input_path, sep="	")
    elif input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    else:
        raise NotImplementedError(
            f"Unsupported DeepBGC format: {input_path.suffix}. Use TSV or CSV exports."
        )

    rename_map = {
        "sample_id": "SampleID",
        "cluster_index": "ClusterIndex",
        "cluster_type": "ClusterType",
        "start": "Start",
        "end": "End",
        "score": "Score",
        "core_genes": "CoreEnzymes",
        "mibig_hits": "MIBiGHits",
    }
    df = df.rename(columns=rename_map)

    df["Tool"] = TOOL_NAME

    for col in ["CoreEnzymes", "MIBiGHits"]:
        if col not in df.columns:
            df[col] = [[] for _ in range(len(df))]
        else:
            df[col] = df[col].apply(lambda value: value if isinstance(value, list) else [])

    for col in ["ClusterType"]:
        df[col] = df[col].fillna("")

    required = ["SampleID", "Tool", "ClusterIndex", "ClusterType", "Start", "End", "Score", "CoreEnzymes", "MIBiGHits"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"DeepBGC output missing required columns: {missing}")

    return df[required]


def sanitize_records(records: pd.DataFrame, schema_columns: List[str]) -> pd.DataFrame:
    """Normalize column names, data types, and missing values."""
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
    logger.info("Wrote %d DeepBGC records to %s", len(df), output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse DeepBGC results into unified schema")
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

    logger.info("Parsing DeepBGC file: %s", args.input_path)
    raw = parse_deepbgc_file(args.input_path)
    schema_columns = config.get("bgc_parsing", {}).get("schema", {}).get("columns")
    if not schema_columns:
        raise ValueError("Configuration missing bgc_parsing.schema.columns entries")

    cleaned = sanitize_records(raw, schema_columns)
    write_output(cleaned, args.output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
