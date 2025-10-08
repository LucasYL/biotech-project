
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：解析 antiSMASH 输出并生成标准化 BGC 表，供统一模块使用。
  - English: Parse antiSMASH outputs to produce a standardized BGC table for downstream integration.

输入 / Inputs:
  - input_path: antiSMASH JSON or GBK exports bundled with the example dataset.
  - output_path: Destination parquet/CSV path for the normalized BGC records.
  - config: Optional JSON/YAML with field mappings and parsing options.

输出 / Outputs:
  - A tabular file (e.g. Parquet) containing BGC metadata keyed by SampleID and cluster index.

主要功能 / Key Functions:
  - parse_antismash_file(...): Load raw antiSMASH output and extract minimal cluster metadata.
  - sanitize_records(...): Harmonize missing fields and enforce schema defaults.

与其他模块的联系 / Relations to Other Modules:
  - unify_bgc.py: Consumes the standardized table to merge with DeepBGC and PRISM results.
  - link_bgc_ms_refs.py: Relies on consistent BGC fields when generating evidence scores.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - safety net for minimal envs
    raise RuntimeError("PyYAML is required to run parse_antismash.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"
TOOL_NAME = "antismash"


def load_config(config_path: Path | None) -> Dict[str, Any]:
    """Load pipeline configuration with a fallback to the default YAML file."""
    target = config_path or DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with target.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {target}")
    return config


def _iter_clusters(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    """Yield cluster records from the antiSMASH JSON structure."""
    for entry in records:
        sample_id = entry.get("id") or entry.get("sample_id")
        clusters = entry.get("clusters", [])
        if sample_id is None:
            logger.warning("Encountered antiSMASH record without sample id: %s", entry)
            continue
        if not clusters:
            logger.warning("Sample %s contains no cluster entries", sample_id)
        for cluster in clusters:
            yield sample_id, cluster


def parse_antismash_file(input_path: Path) -> pd.DataFrame:
    """Parse a single antiSMASH output file into the canonical BGC schema."""
    if not input_path.exists():
        raise FileNotFoundError(f"antiSMASH file not found: {input_path}")

    if input_path.suffix.lower() == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    else:
        raise NotImplementedError(
            f"Unsupported antiSMASH format: {input_path.suffix} (only JSON supported in the scaffold)"
        )

    records = payload.get("records") if isinstance(payload, dict) else None
    if records is None:
        raise ValueError("antiSMASH JSON missing 'records' key")

    rows: List[Dict[str, Any]] = []
    for sample_id, cluster in _iter_clusters(records):
        rows.append(
            {
                "SampleID": sample_id,
                "Tool": TOOL_NAME,
                "ClusterIndex": cluster.get("cluster_id"),
                "ClusterType": ",".join(cluster.get("type", [])),
                "Start": cluster.get("start"),
                "End": cluster.get("end"),
                "Score": cluster.get("score"),
                "CoreEnzymes": cluster.get("core_genes", []),
                "MIBiGHits": cluster.get("mibig_hits", []),
            }
        )

    frame = pd.DataFrame(rows)
    logger.debug("Parsed %d clusters from %s", len(frame), input_path)
    return frame


def sanitize_records(records: pd.DataFrame, schema_columns: List[str]) -> pd.DataFrame:
    """Clean and standardize field names, types, and missing values."""
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

    missing_sample = df["SampleID"].isna().sum()
    if missing_sample:
        logger.warning("Found %d records without SampleID", missing_sample)

    return df.loc[:, schema_columns]


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    """Persist the sanitized dataframe based on the output file suffix."""
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
    logger.info("Wrote %d records to %s", len(df), output_path)


def build_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for standalone execution."""
    parser = argparse.ArgumentParser(description="Parse antiSMASH outputs into a unified table")
    parser.add_argument("input_path", type=Path, help="Path to antiSMASH output (JSON/GBK)")
    parser.add_argument("output_path", type=Path, help="Destination for standardized table")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional YAML/JSON controlling field extraction rules",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override logging level (e.g. DEBUG)",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)

    logging_config = config.get("logging", {})
    log_level = args.log_level or logging_config.get("level", "INFO")
    logging.basicConfig(
        level=getattr(logging, str(log_level).upper(), logging.INFO),
        format=logging_config.get("format", "%(levelname)s - %(message)s"),
    )

    logger.info("Starting antiSMASH parsing: %s", args.input_path)

    raw = parse_antismash_file(args.input_path)
    schema_columns = config.get("bgc_parsing", {}).get("schema", {}).get("columns")
    if not schema_columns:
        raise ValueError("Configuration missing bgc_parsing.schema.columns entries")

    clean = sanitize_records(raw, schema_columns)
    write_output(clean, args.output_path)


if __name__ == "__main__":  # pragma: no cover - CLI guard
    main()
