#!/usr/bin/env bash
# 文件用途 / Purpose:
#   中文：一键执行示例数据的最小管线，依次运行解析、处理、关联、化学信息学、排名与报告。
#   English: One-click runner for the example mini pipeline covering parsing, processing, linking, cheminformatics, ranking, and reporting.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/data"
INTER_DIR="$ROOT_DIR/intermediate"
OUTPUT_DIR="$ROOT_DIR/outputs"
FIG_DIR="$ROOT_DIR/figures"
REPORT_DIR="$ROOT_DIR/report"

mkdir -p "$INTER_DIR/bgc" "$INTER_DIR/ms" "$INTER_DIR/refs" "$INTER_DIR/linking" "$INTER_DIR/cheminf" "$OUTPUT_DIR" "$FIG_DIR" "$REPORT_DIR"

python "$ROOT_DIR/scripts/01_bgc_parse/parse_antismash.py" \
  "$DATA_DIR/example/bgc/antismash_sample.json" \
  "$INTER_DIR/bgc/antismash.parquet"
python "$ROOT_DIR/scripts/01_bgc_parse/parse_deepbgc.py" \
  "$DATA_DIR/example/bgc/deepbgc_sample.tsv" \
  "$INTER_DIR/bgc/deepbgc.parquet"
python "$ROOT_DIR/scripts/01_bgc_parse/parse_prism.py" \
  "$DATA_DIR/example/bgc/prism_sample.tsv" \
  "$INTER_DIR/bgc/prism.parquet"
python "$ROOT_DIR/scripts/01_bgc_parse/unify_bgc.py" \
  "$INTER_DIR/bgc/antismash.parquet" \
  "$INTER_DIR/bgc/deepbgc.parquet" \
  "$INTER_DIR/bgc/prism.parquet" \
  "$INTER_DIR/bgc/bgc_unified.parquet"

python "$ROOT_DIR/scripts/02_ms_process/normalize_ms_features.py" \
  "$DATA_DIR/ms/features_example.csv" \
  "$INTER_DIR/ms/features.parquet"

python "$ROOT_DIR/scripts/03_ref_load/load_chem_refs.py" \
  "$DATA_DIR/refs/chem_refs_example.csv" \
  "$INTER_DIR/refs/chem_ref.parquet"

python "$ROOT_DIR/scripts/04_linking/link_bgc_ms_refs.py" \
  "$INTER_DIR/bgc/bgc_unified.parquet" \
  "$INTER_DIR/ms/features.parquet" \
  "$INTER_DIR/refs/chem_ref.parquet" \
  "$INTER_DIR/linking/mapping_evidence.parquet"

python "$ROOT_DIR/scripts/05_cheminf/rdkit_fingerprints.py" \
  "$INTER_DIR/refs/chem_ref.parquet" \
  "$INTER_DIR/cheminf/fingerprints.parquet"
python "$ROOT_DIR/scripts/05_cheminf/similarity_cluster.py" \
  "$INTER_DIR/cheminf/fingerprints.parquet" \
  "$INTER_DIR/cheminf/similarity_clusters.parquet" \
  --figure-path "$FIG_DIR/cluster_summary.txt"
python "$ROOT_DIR/scripts/05_cheminf/admet_placeholder.py" \
  "$INTER_DIR/refs/chem_ref.parquet" \
  "$INTER_DIR/cheminf/admet.parquet"

python "$ROOT_DIR/scripts/06_ranking/rank_candidates.py" \
  "$INTER_DIR/linking/mapping_evidence.parquet" \
  "$INTER_DIR/cheminf/admet.parquet" \
  "$INTER_DIR/cheminf/similarity_clusters.parquet" \
  "$OUTPUT_DIR/ranked_leads.csv" \
  "$OUTPUT_DIR/topN.md"

python "$ROOT_DIR/scripts/07_reporting/make_figures.py" \
  "$OUTPUT_DIR/ranked_leads.csv" \
  "$INTER_DIR/cheminf/similarity_clusters.parquet" \
  "$FIG_DIR"
python "$ROOT_DIR/scripts/07_reporting/build_report.py" \
  "$ROOT_DIR/REPORT_METHODS.md" \
  "$OUTPUT_DIR/topN.md" \
  "$FIG_DIR" \
  "$OUTPUT_DIR/ranked_leads.csv" \
  "$REPORT_DIR/report.pdf"

echo "Pipeline execution completed. Outputs available in $OUTPUT_DIR and $REPORT_DIR."
