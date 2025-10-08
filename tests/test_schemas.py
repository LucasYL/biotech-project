
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：验证核心数据表的基础 schema 和字段约束。
  - English: Validate baseline schema and field constraints for core tables.

与其他模块的联系 / Relations to Other Modules:
  - 覆盖 BGC 合并、特征归一化等模块输出的基础字段。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline_defaults.yaml"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _roundtrip_parquet(df: pd.DataFrame, tmp_path: Path, filename: str) -> None:
    parquet = pytest.importorskip("pyarrow", reason="pyarrow required for parquet roundtrip")
    output_path = tmp_path / filename
    df.to_parquet(output_path, index=False)
    loaded = pd.read_parquet(output_path)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), loaded)


def test_antismash_parser_schema(tmp_path: Path) -> None:
    module_path = PROJECT_ROOT / "scripts" / "01_bgc_parse" / "parse_antismash.py"
    parser = _load_module(module_path, "parse_antismash")

    config = parser.load_config(None)
    columns = config["bgc_parsing"]["schema"]["columns"]
    sample_path = PROJECT_ROOT / "data" / "example" / "bgc" / "antismash_sample.json"

    raw = parser.parse_antismash_file(sample_path)
    cleaned = parser.sanitize_records(raw, columns)

    assert list(cleaned.columns) == columns
    assert cleaned["Tool"].eq("antismash").all()
    assert cleaned.shape[0] == 3
    assert cleaned[["Start", "End", "Score"]].notna().all().all()

    _roundtrip_parquet(cleaned, tmp_path, "antismash.parquet")


def test_deepbgc_parser_schema(tmp_path: Path) -> None:
    module_path = PROJECT_ROOT / "scripts" / "01_bgc_parse" / "parse_deepbgc.py"
    parser = _load_module(module_path, "parse_deepbgc")

    config = parser.load_config(None)
    columns = config["bgc_parsing"]["schema"]["columns"]
    sample_path = PROJECT_ROOT / "data" / "example" / "bgc" / "deepbgc_sample.tsv"

    raw = parser.parse_deepbgc_file(sample_path)
    cleaned = parser.sanitize_records(raw, columns)

    assert list(cleaned.columns) == columns
    assert cleaned["Tool"].eq("deepbgc").all()
    assert cleaned.shape[0] == 3
    assert cleaned[["Start", "End", "Score"]].notna().all().all()

    _roundtrip_parquet(cleaned, tmp_path, "deepbgc.parquet")


def test_prism_parser_schema(tmp_path: Path) -> None:
    module_path = PROJECT_ROOT / "scripts" / "01_bgc_parse" / "parse_prism.py"
    parser = _load_module(module_path, "parse_prism")

    config = parser.load_config(None)
    columns = config["bgc_parsing"]["schema"]["columns"]
    sample_path = PROJECT_ROOT / "data" / "example" / "bgc" / "prism_sample.tsv"

    raw = parser.parse_prism_file(sample_path)
    cleaned = parser.sanitize_records(raw, columns)

    assert list(cleaned.columns) == columns
    assert cleaned["Tool"].eq("prism").all()
    assert cleaned.shape[0] == 3
    assert cleaned[["Start", "End", "Score"]].notna().all().all()

    _roundtrip_parquet(cleaned, tmp_path, "prism.parquet")
