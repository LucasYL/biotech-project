
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：生成化合物分子指纹（优先使用 RDKit，若不可用则回退至哈希指纹）。
  - English: Generate molecular fingerprints (RDKit when available, hash-based fallback).

输入 / Inputs:
  - chem_path: 标准化化学参考表路径。
  - output_path: 指纹输出（Parquet/CSV）。
  - config: 可选 YAML，控制指纹半径、位数等。

输出 / Outputs:
  - 含 CompoundID、SMILES、Fingerprint 字符串的表；附加 .meta.json 记录统计。

主要功能 / Key Functions:
  - load_config(...): 读取全局配置。
  - compute_fingerprints(...): 生成 Morgan 或哈希指纹。
  - write_output(...): 写出指纹与元数据。

与其他模块的联系 / Relations to Other Modules:
  - similarity_cluster.py: 消费指纹表执行聚类。
  - rank_candidates.py: 使用聚类结果衡量新颖度。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

try:  # pragma: no cover - RDKit 可能缺失
    from rdkit import Chem
    from rdkit.Chem import AllChem
    _HAS_RDKIT = True
except ImportError:  # pragma: no cover
    Chem = None  # type: ignore
    AllChem = None  # type: ignore
    _HAS_RDKIT = False

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run rdkit_fingerprints.py") from exc

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


def load_compounds(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Chemical reference table not found: {path}")
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        return pd.read_csv(path, sep=sep)
    raise NotImplementedError(f"Unsupported table format: {path.suffix}")


def _smiles_to_mol(smiles: str):  # pragma: no cover - 只有 RDKit 时使用
    if not _HAS_RDKIT or not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is not None:
        Chem.SanitizeMol(mol)
    return mol


def _hash_fingerprint(smiles: str, n_bits: int) -> str:
    smiles = smiles or ""
    bit_chars = []
    needed_hex_chars = (n_bits + 3) // 4
    chunk_count = (needed_hex_chars + 63) // 64
    for chunk_idx in range(chunk_count):
        digest = hashlib.sha256(f"{smiles}-{chunk_idx}".encode("utf-8")).hexdigest()
        bit_chars.append(digest)
    hex_string = "".join(bit_chars)[:needed_hex_chars]
    bit_string = bin(int(hex_string, 16))[2:].zfill(needed_hex_chars * 4)
    return bit_string[:n_bits]


def compute_fingerprints(df: pd.DataFrame, radius: int, n_bits: int) -> pd.DataFrame:
    fingerprints: List[Dict[str, str]] = []
    invalid: List[str] = []
    for _, row in df.iterrows():
        compound_id = str(row.get("CompoundID"))
        smiles = str(row.get("SMILES", ""))
        if _HAS_RDKIT:
            mol = _smiles_to_mol(smiles)
            if mol is None:
                invalid.append(compound_id)
                continue
            bitvect = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
            fingerprint = bitvect.ToBitString()
        else:
            if not smiles:
                invalid.append(compound_id)
                continue
            fingerprint = _hash_fingerprint(smiles, n_bits)
        fingerprints.append(
            {
                "CompoundID": compound_id,
                "SMILES": smiles,
                "Fingerprint": fingerprint,
            }
        )
    if invalid:
        logger.warning("Skipped %d compounds due to invalid SMILES", len(invalid))
    return pd.DataFrame(fingerprints)


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "	"
        df.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported output format: {output_path.suffix}")
    metadata = {
        "count": int(df.shape[0]),
        "columns": df.columns.tolist(),
        "fingerprint_bits": len(df["Fingerprint"].iloc[0]) if not df.empty else 0,
        "tool": "rdkit" if _HAS_RDKIT else "hash_fallback",
    }
    output_path.with_suffix(output_path.suffix + ".meta.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Wrote %d fingerprints (%s) to %s",
        metadata["count"],
        metadata["tool"],
        output_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate molecular fingerprints")
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

    chem_df = load_compounds(args.chem_path)
    fp_cfg = config.get("cheminformatics", {}).get("fingerprint", {})
    radius = int(fp_cfg.get("radius", 2))
    n_bits = int(fp_cfg.get("n_bits", 2048))

    if not _HAS_RDKIT:
        logger.warning("RDKit not available; using hash-based fingerprints as fallback")

    fp_df = compute_fingerprints(chem_df, radius, n_bits)
    if fp_df.empty:
        logger.warning("No fingerprints generated; check input data")
    write_output(fp_df, args.output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
