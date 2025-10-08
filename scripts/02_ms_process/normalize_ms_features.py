
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：读取 MZmine/MS-DIAL 特征表，执行字段标准化与强度归一化。
  - English: Load MZmine/MS-DIAL feature tables, standardize fields, and perform intensity normalization.

输入 / Inputs:
  - input_path: CSV from MZmine/MS-DIAL exports.
  - output_path: Parquet path for normalized feature table.
  - column aliases via CLI flags; optional config for normalization strategy.

输出 / Outputs:
  - Parquet/CSV table containing normalized intensities and sanitized metadata.

主要功能 / Key Functions:
  - load_features(...): Read raw features with flexible column mapping.
  - normalize_intensity(...): Apply TIC normalization and clipping rules.
  - validate_schema(...): Ensure required columns exist, provide friendly errors.

与其他模块的联系 / Relations to Other Modules:
  - link_bgc_ms_refs.py: Requires standardized FeatureID, mz, rt, intensity columns.
  - tests/test_schemas.py: Includes validation for missing/renamed columns。
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
    raise RuntimeError("PyYAML is required to run normalize_ms_features.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"

REQUIRED_COLUMNS = ["FeatureID", "SampleID", "mz", "rt", "intensity"]


def load_config(config_path: Path | None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {path}")
    return config


def load_features(input_path: Path, column_map: Dict[str, str]) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Feature table not found: {input_path}")

    df = pd.read_csv(input_path)
    rename_dict = {column_map.get(key, key): key for key in ["FeatureID", "mz", "rt", "intensity", "SampleID"] if column_map.get(key)}
    inverted_map = {column_map[key]: key for key in column_map if column_map[key] is not None}
    df = df.rename(columns=inverted_map)

    missing = [col for col in ["FeatureID", "mz", "rt", "intensity"] if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if "SampleID" not in df.columns:
        df["SampleID"] = "UNKNOWN"

    df["FeatureID"] = df["FeatureID"].astype(str)
    df["SampleID"] = df["SampleID"].astype(str)
    df["mz"] = pd.to_numeric(df["mz"], errors="coerce")
    df["rt"] = pd.to_numeric(df["rt"], errors="coerce")
    df["intensity"] = pd.to_numeric(df["intensity"], errors="coerce")

    return df


def clip_and_normalize(
    df: pd.DataFrame,
    intensity_floor: float,
    method: str,
) -> pd.DataFrame:
    data = df.copy()
    data["intensity_raw"] = data["intensity"]
    data["intensity"] = data["intensity"].fillna(0).clip(lower=0)
    if intensity_floor > 0:
        below_floor = data["intensity"] < intensity_floor
        if below_floor.any():
            logger.debug("Applying intensity floor to %d rows", below_floor.sum())
        data.loc[below_floor, "intensity"] = intensity_floor

    if method.lower() == "tic":
        normalized = []
        for sample_id, group in data.groupby("SampleID"):
            total = group["intensity"].sum()
            if total <= 0:
                logger.warning("Sample %s has non-positive total intensity; skipping normalization", sample_id)
                normalized.extend([0.0] * len(group))
            else:
                normalized.extend((group["intensity"] / total).tolist())
        data["intensity_normalized"] = normalized
    else:
        raise NotImplementedError(f"Normalization method '{method}' not implemented")

    return data


def validate_schema(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Normalized table missing required columns: {missing}")


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "	"
        df.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported output format: {output_path.suffix}")
    logger.info("Wrote %d feature rows to %s", len(df), output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize LC-MS/MS feature tables")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--id-col", default="row ID")
    parser.add_argument("--mz-col", default="m/z")
    parser.add_argument("--rt-col", default="rt")
    parser.add_argument("--intensity-col", default="intensity")
    parser.add_argument("--sample-col", default="SampleID")
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

    column_map = {
        "FeatureID": args.id_col,
        "mz": args.mz_col,
        "rt": args.rt_col,
        "intensity": args.intensity_col,
        "SampleID": args.sample_col,
    }

    logger.info("Loading feature table: %s", args.input_path)
    raw = load_features(args.input_path, column_map)

    ms_config = config.get("ms_processing", {})
    floor = float(ms_config.get("intensity_floor", 0))
    method = ms_config.get("normalization", "tic")
    processed = clip_and_normalize(raw, floor, method)

    validate_schema(processed)
    write_output(processed, args.output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
