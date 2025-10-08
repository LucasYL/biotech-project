# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：测试指纹生成、相似性聚类和 ADMET 占位逻辑。
  - English: Test fingerprint generation, similarity clustering, and ADMET placeholder logic.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FP_MODULE = PROJECT_ROOT / "scripts" / "05_cheminf" / "rdkit_fingerprints.py"
CLUSTER_MODULE = PROJECT_ROOT / "scripts" / "05_cheminf" / "similarity_cluster.py"
ADMET_MODULE = PROJECT_ROOT / "scripts" / "05_cheminf" / "admet_placeholder.py"


def _load_module(path: Path, name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_fingerprint_hash_fallback(tmp_path: Path) -> None:
    module = _load_module(FP_MODULE, "rdkit_fp")
    chem_df = pd.DataFrame(
        {
            "CompoundID": ["C1", "C2"],
            "SMILES": ["CCO", "CCN"],
        }
    )
    chem_path = tmp_path / "chem.csv"
    chem_df.to_csv(chem_path, index=False)

    config = module.load_config(None)
    fp_df = module.compute_fingerprints(chem_df, radius=2, n_bits=256)
    assert fp_df.shape[0] == 2
    assert all(len(fp) == 256 for fp in fp_df["Fingerprint"])


def test_similarity_cluster(tmp_path: Path) -> None:
    fp_module = _load_module(FP_MODULE, "rdkit_fp")
    cluster_module = _load_module(CLUSTER_MODULE, "cluster")

    df = pd.DataFrame(
        {
            "CompoundID": ["A", "B", "C"],
            "SMILES": ["CCO", "CCO", "CCCC"],
        }
    )
    fp_df = fp_module.compute_fingerprints(df, radius=2, n_bits=32)
    fp_path = tmp_path / "fp.csv"
    fp_df.to_csv(fp_path, index=False)

    cluster_df = cluster_module.cluster_fingerprints(fp_df, threshold=0.8)
    assert cluster_df["ClusterID"].nunique() <= 3


def test_admet_placeholder(tmp_path: Path) -> None:
    module = _load_module(ADMET_MODULE, "admet")
    chem_df = pd.DataFrame(
        {
            "CompoundID": ["C1", "C2"],
            "SMILES": ["CCO", "CCCCCCCC"],
        }
    )
    chem_path = tmp_path / "chem.csv"
    chem_df.to_csv(chem_path, index=False)

    admet_df = module.build_admet_table(chem_path, tmp_path / "admet.csv", None, None)
    assert {"CompoundID", "logP", "RuleOfFivePass"}.issubset(admet_df.columns)
    assert admet_df.shape[0] == 2
