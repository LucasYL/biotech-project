#!/usr/bin/env bash
# 文件用途 / Purpose:
#   中文：一键启动 Streamlit 仪表板的便捷脚本，确保使用正确的 Python 环境。
#   English: Convenience script to launch Streamlit dashboard with the correct Python environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV_PATH="/opt/miniconda3/envs/actino-mini/bin/python"

# Check if actino-mini environment exists
if [ ! -f "$CONDA_ENV_PATH" ]; then
    echo "Error: actino-mini conda environment not found at $CONDA_ENV_PATH"
    echo "Please run: conda env create -f env/environment.yml --solver=classic"
    exit 1
fi

# Check if outputs exist
if [ ! -f "$SCRIPT_DIR/outputs/ranked_leads.csv" ]; then
    echo "Warning: No output files found. Please run the pipeline first:"
    echo "  bash scripts/run_all.sh"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting Streamlit dashboard..."
echo "Access at: http://localhost:8501"
echo "Press Ctrl+C to stop"
echo ""

cd "$SCRIPT_DIR"
"$CONDA_ENV_PATH" -m streamlit run dashboard/app.py

