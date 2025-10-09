
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：依据启发式规则构建 BGC、LC-MS 特征和化合物之间的关联证据表。
  - English: Build heuristic evidence linking BGCs, LC-MS features, and compounds.

输入 / Inputs:
  - bgc_path: Unified BGC table.
  - feature_path: Normalized feature table.
  - chem_path: Chemical reference table.
  - output_path: Evidence table destination.
  - params: Weighting and threshold parameters via config or CLI flags.

输出 / Outputs:
  - `mapping_evidence.parquet` 包含 BGCUID、FeatureID、CompoundID、证据类型与得分。

主要功能 / Key Functions:
  - score_bgc_compound(...): Compare BGC types with compound classes.
  - score_feature_compound(...): Match m/z against theoretical masses within ppm window.
  - score_bgc_feature(...): Evaluate co-occurrence signals within the same sample.
  - combine_scores(...): Aggregate and normalize evidence to 0-1 range.

与其他模块的联系 / Relations to Other Modules:
  - rank_candidates.py: Uses resulting evidence scores during final ranking。
  - tests/test_linking_rules.py: Validates scoring edges and parameter boundaries。
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run link_bgc_ms_refs.py") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"
OUTPUT_COLUMNS = ["BGCUID", "FeatureID", "CompoundID", "EvidenceType", "EvidenceScore", "Notes"]

TYPE_MAPPING = {
    "NRPS": {"NPAtlas", "MIBiG"},
    "PKS": {"MIBiG"},
    "RIPP": {"NPAtlas", "MIBiG"},  # Use uppercase to match expand_cluster_types()
}


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
        raise FileNotFoundError(f"Table not found: {path}")
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        return pd.read_csv(path, sep=sep)
    raise NotImplementedError(f"Unsupported table format: {path.suffix}")


def ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, str) and not value.strip():
        return []
    return [str(value)]


def expand_cluster_types(cluster_type: str) -> List[str]:
    if not isinstance(cluster_type, str):
        return []
    tokens = [token.strip().upper() for token in cluster_type.replace("|", ",").split(",")]
    return [token for token in tokens if token]


def estimate_mass(smiles: str) -> float:
    if not isinstance(smiles, str) or not smiles:
        return float("nan")
    carbon_count = smiles.count("C")
    hetero_count = sum(smiles.count(char) for char in "NOSP")
    return carbon_count * 12.0 + hetero_count * 14.0 + 18.0  # placeholder heuristic


def score_bgc_compound(
    bgc_row: pd.Series,
    compound_row: pd.Series,
    alpha: float,
    beta: float,
) -> float:
    cluster_types = expand_cluster_types(bgc_row.get("ClusterType", ""))
    sources = TYPE_MAPPING
    compound_source = str(compound_row.get("Source", "")).strip()

    match_found = any(compound_source in sources.get(ct, set()) for ct in cluster_types)
    score = alpha if match_found else 0.0

    mibig_hits = ensure_list(bgc_row.get("MIBiGHits"))
    if mibig_hits and score > 0:
        score += beta
    return min(score, 1.0)


def score_feature_compound(
    feature_row: pd.Series,
    compound_row: pd.Series,
    ppm_tolerance: float,
    gamma: float,
) -> float:
    mz = feature_row.get("mz")
    if pd.isna(mz):
        return 0.0
    smiles = compound_row.get("SMILES", "")
    mass = estimate_mass(smiles)
    if math.isnan(mass) or mass == 0:
        return 0.0
    diff = abs(mz - mass)
    ppm = diff / mass * 1e6
    if ppm <= ppm_tolerance:
        return min(gamma, 1.0)
    return 0.0


def score_bgc_feature(
    bgc_row: pd.Series,
    feature_row: pd.Series,
    delta: float,
) -> float:
    if str(bgc_row.get("SampleID")) != str(feature_row.get("SampleID")):
        return 0.0
    intensity = feature_row.get("intensity_normalized")
    if pd.isna(intensity):
        raw_intensity = feature_row.get("intensity", 0)
        total = feature_row.get("_sample_total", 0)
        if total:
            intensity = raw_intensity / total
        else:
            intensity = 0
    if intensity >= 0.01:
        return min(delta * float(intensity), 1.0)
    return 0.0


def build_mapping(
    bgc_path: Path,
    feature_path: Path,
    chem_path: Path,
    output_path: Path,
    config: Dict[str, Any],
) -> pd.DataFrame:
    bgc = read_table(bgc_path)
    features = read_table(feature_path)
    compounds = read_table(chem_path)

    linking_cfg = config.get("linking", {})
    alpha = float(linking_cfg.get("weight_bgc_compound", 0.4))
    beta = float(linking_cfg.get("beta_mibig_bonus", 0.2))
    gamma = float(linking_cfg.get("gamma_mass_match", 0.7))
    delta = float(linking_cfg.get("delta_cooccurrence", 0.5))
    ppm_tolerance = float(config.get("ms_processing", {}).get("ppm_tolerance", 10.0))

    features = features.copy()
    if "intensity_normalized" not in features.columns:
        totals = features.groupby("SampleID")["intensity"].transform("sum")
        features["_sample_total"] = totals
        features["intensity_normalized"] = features.apply(
            lambda row: row["intensity"] / row["_sample_total"] if row["_sample_total"] else 0,
            axis=1,
        )
    else:
        features["_sample_total"] = 0

    evidence_rows: List[Dict[str, Any]] = []

    for _, bgc_row in bgc.iterrows():
        for _, compound_row in compounds.iterrows():
            score = score_bgc_compound(bgc_row, compound_row, alpha, beta)
            if score > 0:
                evidence_rows.append(
                    {
                        "BGCUID": bgc_row.get("BGCUID", bgc_row.get("BGCID")),
                        "FeatureID": pd.NA,
                        "CompoundID": compound_row.get("CompoundID"),
                        "EvidenceType": "bgc_compound",
                        "EvidenceScore": round(min(score, 1.0), 4),
                        "Notes": "Cluster type vs compound source match",
                    }
                )

    for _, feature_row in features.iterrows():
        for _, compound_row in compounds.iterrows():
            score = score_feature_compound(feature_row, compound_row, ppm_tolerance, gamma)
            if score > 0:
                evidence_rows.append(
                    {
                        "BGCUID": pd.NA,
                        "FeatureID": feature_row.get("FeatureID"),
                        "CompoundID": compound_row.get("CompoundID"),
                        "EvidenceType": "feature_compound",
                        "EvidenceScore": round(min(score, 1.0), 4),
                        "Notes": "m/z within ppm window",
                    }
                )

    for _, bgc_row in bgc.iterrows():
        for _, feature_row in features.iterrows():
            score = score_bgc_feature(bgc_row, feature_row, delta)
            if score > 0:
                evidence_rows.append(
                    {
                        "BGCUID": bgc_row.get("BGCUID", bgc_row.get("BGCID")),
                        "FeatureID": feature_row.get("FeatureID"),
                        "CompoundID": pd.NA,
                        "EvidenceType": "bgc_feature",
                        "EvidenceScore": round(min(score, 1.0), 4),
                        "Notes": "Co-occurrence in sample with high intensity",
                    }
                )

    evidence = pd.DataFrame(evidence_rows, columns=OUTPUT_COLUMNS)
    evidence = evidence.fillna({"BGCUID": "", "FeatureID": "", "CompoundID": ""})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        evidence.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "	"
        evidence.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported output format: {output_path.suffix}")

    logger.info("Wrote %d evidence rows to %s", len(evidence), output_path)
    return evidence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Link BGCs, features, and compounds using heuristics")
    parser.add_argument("bgc_path", type=Path)
    parser.add_argument("feature_path", type=Path)
    parser.add_argument("chem_path", type=Path)
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

    build_mapping(args.bgc_path, args.feature_path, args.chem_path, args.output_path, config)


if __name__ == "__main__":  # pragma: no cover
    main()
