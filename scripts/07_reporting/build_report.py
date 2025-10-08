# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：汇总方法说明、图表和排名结果，生成 PDF 或 Markdown 报告。
  - English: Assemble methods, figures, and rankings into a PDF or Markdown report.

输入 / Inputs:
  - methods_template: Markdown 模板（如 REPORT_METHODS.md）。
  - topn_md: Top-N Markdown 摘要。
  - figures_dir: 图表目录。
  - ranking_path: 排名 CSV。
  - output_pdf: 目标 PDF 路径（若无法创建 PDF，回退至 Markdown）。
  - metadata_path: 可选运行元数据 JSON。

输出 / Outputs:
  - report/report.pdf 或 report/report.md（回退）。

主要功能 / Key Functions:
  - compose_markdown(...): 拼接 Markdown 内容。
  - export_pdf(...): 尝试使用 FPDF 生成 PDF；若失败，返回 False。

与其他模块的联系 / Relations to Other Modules:
  - make_figures.py: 提供图表资产。
  - rank_candidates.py: 提供排名与 Top-N 摘要。
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

try:  # pragma: no cover - optional dependency
    from fpdf import FPDF  # type: ignore
    _HAS_FPDF = True
except ImportError:  # pragma: no cover
    FPDF = None  # type: ignore
    _HAS_FPDF = False

logger = logging.getLogger(__name__)


def load_text(path: Path) -> str:
    if not path.exists():
        logger.warning("File missing: %s", path)
        return ""
    return path.read_text(encoding="utf-8")


def compose_markdown(
    methods_template: Path,
    topn_md: Path,
    figures_dir: Path,
    ranking_path: Path,
    metadata_path: Optional[Path],
) -> str:
    methods_text = load_text(methods_template)
    topn_text = load_text(topn_md)

    figures_summary = []
    if figures_dir.exists():
        for item in sorted(figures_dir.iterdir()):
            figures_summary.append(f"- {item.name}")
    else:
        figures_summary.append("- (No figures generated)")

    ranking_excerpt = ""
    if ranking_path.exists():
        ranking_df = pd.read_csv(ranking_path)
        if not ranking_df.empty:
            try:
                ranking_excerpt = ranking_df.head(10).to_markdown(index=False)
            except (ImportError, RuntimeError):
                ranking_excerpt = ranking_df.head(10).to_string(index=False)

    metadata = {}
    if metadata_path and metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Failed to parse metadata JSON: %s", metadata_path)

    run_info_lines = [
        "## Run Metadata",
        f"- Generated at: {datetime.utcnow().isoformat()} UTC",
    ]
    for key, value in metadata.items():
        run_info_lines.append(f"- {key}: {value}")

    sections = [
        "# Actinomycete BGC → Metabolomics Mini-Pipeline Report",
        "\n".join(run_info_lines),
        "## Methods",
        methods_text or "(Methods template not found)",
        "## Top Candidates",
        topn_text or "(Top-N summary not found)",
        "## Figures",
        "\n".join(figures_summary),
        "## Ranking Snapshot",
        ranking_excerpt or "(Ranking file not found)",
    ]

    return "\n\n".join(sections)


def export_pdf(markdown: str, output_pdf: Path) -> bool:
    if not _HAS_FPDF:
        logger.warning("FPDF not installed; skipping PDF generation")
        return False

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in markdown.splitlines():
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_line)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_pdf))
    logger.info("Wrote PDF report to %s", output_pdf)
    return True


def build_report(
    methods_template: Path,
    topn_md: Path,
    figures_dir: Path,
    ranking_path: Path,
    output_pdf: Path,
    metadata_path: Optional[Path] = None,
) -> Path:
    markdown = compose_markdown(methods_template, topn_md, figures_dir, ranking_path, metadata_path)

    report_dir = output_pdf.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    fallback_md = report_dir / 'report.md'
    fallback_md.write_text(markdown, encoding="utf-8")
    logger.info("Wrote Markdown report to %s", fallback_md)

    if export_pdf(markdown, output_pdf):
        return output_pdf

    logger.warning("PDF generation skipped; Markdown report available at %s", fallback_md)
    return fallback_md


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build pipeline report (PDF/Markdown)')
    parser.add_argument('methods_template', type=Path)
    parser.add_argument('topn_md', type=Path)
    parser.add_argument('figures_dir', type=Path)
    parser.add_argument('ranking_path', type=Path)
    parser.add_argument('output_pdf', type=Path)
    parser.add_argument('--metadata', type=Path, default=None)
    parser.add_argument('--log-level', default='INFO')
    return parser


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(levelname)s - %(message)s',
    )

    build_report(
        methods_template=args.methods_template,
        topn_md=args.topn_md,
        figures_dir=args.figures_dir,
        ranking_path=args.ranking_path,
        output_pdf=args.output_pdf,
        metadata_path=args.metadata,
    )


if __name__ == '__main__':  # pragma: no cover
    main()
