# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：测试化学参考库加载与标准化逻辑。
  - English: Test chemical reference loading and standardization logic.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "03_ref_load" / "load_chem_refs.py"


def _load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("chem_refs", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_sanitize_references_drops_missing_smiles(tmp_path: Path) -> None:
    mod = _load_module()
    df = pd.DataFrame(
        {
            "compound_id": ["C1", "C2"],
            "name": ["Alpha", "Beta"],
            "source": ["NPAtlas", "MIBiG"],
            "smiles": ["CCO", ""],
            "known_activity": ["Yes", "No"],
        }
    )
    sanitized = mod.sanitize_references(df)
    assert sanitized.shape[0] == 1
    assert sanitized.iloc[0]["CompoundID"] == "C1"
    output_path = tmp_path / "chem.csv"
    mod.write_output(sanitized, output_path)
    assert output_path.exists()
