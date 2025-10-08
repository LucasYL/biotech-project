# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：验证 LC-MS/MS 特征归一化逻辑的正确性和容错能力。
  - English: Validate LC-MS/MS feature normalization logic and error handling.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "02_ms_process" / "normalize_ms_features.py"


def _load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("normalize_ms", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_tic_normalization(tmp_path: Path) -> None:
    mod = _load_module()

    df = pd.DataFrame(
        {
            "row ID": ["F1", "F2", "F3"],
            "m/z": [100.0, 200.0, 300.0],
            "rt": [5.0, 10.0, 15.0],
            "intensity": [100.0, -50.0, np.nan],
            "SampleID": ["S1", "S1", "S1"],
        }
    )
    input_path = tmp_path / "features.csv"
    df.to_csv(input_path, index=False)

    column_map = {
        "FeatureID": "row ID",
        "mz": "m/z",
        "rt": "rt",
        "intensity": "intensity",
        "SampleID": "SampleID",
    }

    loaded = mod.load_features(input_path, column_map)
    processed = mod.clip_and_normalize(loaded, intensity_floor=10.0, method="tic")
    mod.validate_schema(processed)

    norm_values = processed["intensity_normalized"].tolist()
    assert sum(norm_values) == pytest.approx(1.0, rel=1e-6)
    assert all(value >= 0 for value in norm_values)

    raw_intensity = processed.loc[processed["FeatureID"] == "F2", "intensity_raw"].iloc[0]
    assert raw_intensity == -50.0

    output_path = tmp_path / "features.csv"
    mod.write_output(processed, output_path)
    assert output_path.exists()
