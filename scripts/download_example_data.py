# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：下载或解压示例数据集，填充 data/ 目录便于快速演示。
  - English: Download or extract example datasets to populate the data/ directory for quick demos.

输入 / Inputs:
  - destination: Base data directory (defaults to project ./data).
  - source URL or archive path specified via CLI flags or config.

输出 / Outputs:
  - Example genomes, metabolomics tables, and reference data under data/.

主要功能 / Key Functions:
  - fetch_archives(...): Retrieve remote/static archives if necessary.
  - unpack_resources(...): Extract files into the expected directory structure.
  - verify_contents(...): Confirm required example files exist and log guidance.

与其他模块的联系 / Relations to Other Modules:
  - run_all.sh: Ensures required inputs exist before executing the pipeline.
  - README.md: Documents how to invoke this helper for new users.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResourceMapping:
    """Describe how bundled example resources should be deployed."""

    bundle_relative: Path
    target_relative: Path
    is_directory: bool
    description: str


BUNDLE_ROOT_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "example_bundle"
TARGET_ROOT_DEFAULT = Path(__file__).resolve().parents[1] / "data"

RESOURCE_MAP: Tuple[ResourceMapping, ...] = (
    ResourceMapping(Path("genomes"), Path("genomes"), True, "Example genome FASTA files"),
    ResourceMapping(Path("bgc"), Path("example") / "bgc", True, "BGC prediction outputs from multiple tools"),
    ResourceMapping(Path("ms"), Path("ms"), True, "LC-MS/MS feature tables"),
    ResourceMapping(Path("refs"), Path("refs"), True, "Chemical reference subset"),
    ResourceMapping(Path("admet"), Path("example") / "admet", True, "Mock ADMET batch results"),
)

FILE_MAP: Tuple[ResourceMapping, ...] = (
    ResourceMapping(Path("metadata.json"), Path("example") / "metadata.json", False, "Example bundle metadata"),
)


def copy_resource(src: Path, dest: Path, force: bool) -> None:
    """Copy a file or directory, honoring the force flag."""
    if not src.exists():
        raise FileNotFoundError(f"Example resource missing: {src}")

    dest.parent.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        if dest.exists():
            if force:
                shutil.rmtree(dest)
                shutil.copytree(src, dest)
            else:
                shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copytree(src, dest)
    else:
        if dest.exists():
            if not force:
                logger.info("Skipping existing file: %s", dest)
                return
            dest.unlink()
        shutil.copy2(src, dest)

    logger.info("Copied %s -> %s", src, dest)


def load_metadata(bundle_root: Path) -> dict | None:
    metadata_path = bundle_root / "metadata.json"
    if not metadata_path.exists():
        logger.warning("Metadata file not found in bundle: %s", metadata_path)
        return None
    try:
        return json.loads(metadata_path.read_text())
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse metadata JSON: %s", exc)
        return None


def deploy_bundle(bundle_root: Path, target_root: Path, force: bool = False) -> None:
    """Deploy bundled example data into the working data directory."""
    logger.info("Deploying example data from %s to %s", bundle_root, target_root)

    if not bundle_root.exists():
        raise FileNotFoundError(
            f"Bundle directory not found: {bundle_root}. Please check the repository layout."
        )

    for mapping in RESOURCE_MAP:
        src = bundle_root / mapping.bundle_relative
        dest = target_root / mapping.target_relative
        copy_resource(src, dest, force=force)

    for mapping in FILE_MAP:
        src = bundle_root / mapping.bundle_relative
        dest = target_root / mapping.target_relative
        copy_resource(src, dest, force=force)

    metadata = load_metadata(bundle_root)
    if metadata:
        logger.info("Example data summary: %s", metadata.get("description", "(no description)"))
        logger.info("Samples available: %s", ", ".join(metadata.get("samples", [])))
        logger.info("Compounds available: %s", ", ".join(metadata.get("compounds", [])))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare example data for the mini pipeline")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=BUNDLE_ROOT_DEFAULT,
        help="Directory containing the bundled example dataset",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=TARGET_ROOT_DEFAULT,
        help="Target data directory to populate",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in the target directory",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s - %(message)s",
    )

    deploy_bundle(args.bundle_root, args.target_root, force=args.force)


if __name__ == "__main__":  # pragma: no cover
    main()
