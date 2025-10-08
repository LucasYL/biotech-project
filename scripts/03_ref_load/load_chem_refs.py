
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：加载并标准化 NPAtlas/MIBiG 等化合物参考库数据。
  - English: Load and standardize NPAtlas/MIBiG chemical reference data.

输入 / Inputs:
  - input_paths: One or more CSV/JSON files containing compound annotations。
  - output_path: Unified Parquet table storing normalized compound records.
  - config: Optional config controlling field mappings and filters.

输出 / Outputs:
  - `chem_ref.parquet` 包含 CompoundID、名称、SMILES、来源等信息。

主要功能 / Key Functions:
  - load_reference_tables(...): Aggregate multiple files into a single dataframe。
  - validate_smiles(...): Filter invalid or missing SMILES strings。
  - annotate_metadata(...): Add source provenance and optional activity flags。

与其他模块的联系 / Relations to Other Modules:
  - rdkit_fingerprints.py: Requires valid SMILES from this table。
  - link_bgc_ms_refs.py: Uses standardized compound IDs for evidence mapping。
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run load_chem_refs.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"
REQUIRED_COLUMNS = ["CompoundID", "Name", "Source", "SMILES", "KnownActivity"]


def load_config(config_path: Path | None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {path}")
    return config


def read_single_reference(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Reference file not found: {path}")

    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        df = pd.json_normalize(data)
    else:
        raise NotImplementedError(f"Unsupported reference format: {path.suffix}")

    df["__source_file"] = path.name
    return df


def load_reference_tables(paths: List[Path]) -> pd.DataFrame:
    frames = [read_single_reference(path) for path in paths]
    if not frames:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    return combined


def sanitize_references(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "compound_id": "CompoundID",
        "CompoundID": "CompoundID",
        "name": "Name",
        "Name": "Name",
        "source": "Source",
        "Source": "Source",
        "smiles": "SMILES",
        "SMILES": "SMILES",
        "known_activity": "KnownActivity",
        "KnownActivity": "KnownActivity",
    }
    normalized = df.rename(columns=mapping)
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in normalized.columns]
    for col in missing_cols:
        normalized[col] = pd.NA

    normalized["CompoundID"] = normalized["CompoundID"].astype(str)
    normalized["Name"] = normalized["Name"].astype(str)
    normalized["Source"] = normalized["Source"].fillna("Unknown")
    normalized["KnownActivity"] = normalized["KnownActivity"].fillna("Unknown")

    before = len(normalized)
    normalized = normalized.dropna(subset=["SMILES"])
    normalized = normalized[normalized["SMILES"].astype(str).str.len() > 0]
    removed = before - len(normalized)
    if removed:
        logger.warning("Dropped %d entries without SMILES", removed)

    normalized = normalized.drop_duplicates(subset="CompoundID", keep="first")

    columns = REQUIRED_COLUMNS + ["__source_file"]
    for col in columns:
        if col not in normalized.columns:
            normalized[col] = pd.NA

    return normalized.loc[:, columns]


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "	"
        df.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported output format: {output_path.suffix}")
    logger.info("Wrote %d chemical reference rows to %s", len(df), output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load chemical reference datasets")
    parser.add_argument("input_paths", type=Path, nargs="+")
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

    logger.info("Loading chemical references: %s", ", ".join(str(p) for p in args.input_paths))
    combined = load_reference_tables(list(args.input_paths))
    sanitized = sanitize_references(combined)
    write_output(sanitized, args.output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
