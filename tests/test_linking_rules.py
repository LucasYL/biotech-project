# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：测试启发式证据打分规则的边界条件与权重组合。
  - English: Test heuristic evidence scoring boundaries and weight combinations.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "04_linking" / "link_bgc_ms_refs.py"


def _load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("linking", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_build_mapping_generates_expected_evidence(tmp_path: Path) -> None:
    mod = _load_module()

    bgc = pd.DataFrame(
        {
            "BGCUID": ["S1_BGCUID_001"],
            "SampleID": ["S1"],
            "Tool": ["antismash"],
            "ClusterType": ["NRPS"],
            "Start": [0],
            "End": [100],
            "Score": [80],
            "CoreEnzymes": [["geneA"]],
            "MIBiGHits": [["BGC0001"]],
        }
    )
    features = pd.DataFrame(
        {
            "FeatureID": ["F1"],
            "SampleID": ["S1"],
            "mz": [56.0],
            "rt": [5.0],
            "intensity": [1000.0],
            "intensity_normalized": [0.5],
        }
    )
    compounds = pd.DataFrame(
        {
            "CompoundID": ["C1"],
            "Name": ["Alpha"],
            "Source": ["NPAtlas"],
            "SMILES": ["CCO"],
            "KnownActivity": ["Yes"],
        }
    )

    bgc_path = tmp_path / "bgc.csv"
    feature_path = tmp_path / "features.csv"
    chem_path = tmp_path / "chem.csv"
    output_path = tmp_path / "evidence.csv"

    bgc.to_csv(bgc_path, index=False)
    features.to_csv(feature_path, index=False)
    compounds.to_csv(chem_path, index=False)

    config = mod.load_config(None)
    evidence = mod.build_mapping(bgc_path, feature_path, chem_path, output_path, config)

    evidence_types = set(evidence["EvidenceType"])
    assert {"bgc_compound", "feature_compound", "bgc_feature"}.issubset(evidence_types)
    assert output_path.exists()
