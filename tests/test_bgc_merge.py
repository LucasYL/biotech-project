# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：测试 BGC 合并逻辑在不同重叠场景下的行为。
  - English: Test the BGC merge logic under various overlap scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "01_bgc_parse" / "unify_bgc.py"


def _load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("unify_bgc", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_merge_overlaps_reciprocal_threshold() -> None:
    mod = _load_module()
    data = pd.DataFrame(
        [
            {"SampleID": "S1", "Tool": "antismash", "ClusterIndex": 1, "ClusterType": "NRPS", "Start": 0, "End": 100, "Score": 80, "CoreEnzymes": ["a"], "MIBiGHits": [], "BGCID": "S1_antismash_1"},
            {"SampleID": "S1", "Tool": "deepbgc", "ClusterIndex": 1, "ClusterType": "NRPS", "Start": 10, "End": 110, "Score": 0.9, "CoreEnzymes": ["b"], "MIBiGHits": ["X"], "BGCID": "S1_deepbgc_1"},
        ]
    )
    merged = mod.merge_overlaps(data, threshold=0.5)
    assert merged.shape[0] == 1
    row = merged.iloc[0]
    assert row["Tool"] == "antismash|deepbgc"
    assert row["Start"] == 0
    assert row["End"] == 110
    assert "S1_antismash_1" in row["MemberBGCIDs"]
    assert "S1_deepbgc_1" in row["MemberBGCIDs"]
    assert set(row["MIBiGHits"]) == {"X"}


def test_merge_overlaps_below_threshold_retains_separate() -> None:
    mod = _load_module()
    data = pd.DataFrame(
        [
            {"SampleID": "S1", "Tool": "antismash", "ClusterIndex": 1, "ClusterType": "NRPS", "Start": 0, "End": 100, "Score": 80, "CoreEnzymes": ["a"], "MIBiGHits": [], "BGCID": "S1_antismash_1"},
            {"SampleID": "S1", "Tool": "deepbgc", "ClusterIndex": 2, "ClusterType": "PKS", "Start": 120, "End": 220, "Score": 0.8, "CoreEnzymes": ["b"], "MIBiGHits": [], "BGCID": "S1_deepbgc_2"},
        ]
    )
    merged = mod.merge_overlaps(data, threshold=0.5)
    assert merged.shape[0] == 2
    tools = set(merged["Tool"].tolist())
    assert tools == {"antismash", "deepbgc"}


def test_merge_overlaps_partial_overlap_requires_threshold() -> None:
    mod = _load_module()
    data = pd.DataFrame(
        [
            {"SampleID": "S1", "Tool": "antismash", "ClusterIndex": 1, "ClusterType": "NRPS", "Start": 0, "End": 100, "Score": 80, "CoreEnzymes": [], "MIBiGHits": [], "BGCID": "S1_antismash_1"},
            {"SampleID": "S1", "Tool": "prism", "ClusterIndex": 1, "ClusterType": "NRPS", "Start": 60, "End": 160, "Score": 0.7, "CoreEnzymes": [], "MIBiGHits": [], "BGCID": "S1_prism_1"},
        ]
    )
    merged_low = mod.merge_overlaps(data, threshold=0.6)
    assert merged_low.shape[0] == 2  # reciprocal overlap ≈0.4, below 0.6
    merged_high = mod.merge_overlaps(data, threshold=0.4)
    assert merged_high.shape[0] == 1
