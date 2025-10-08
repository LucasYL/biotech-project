"""
文件用途 / Purpose:
  - 中文：Streamlit 仪表板入口，展示 BGC、特征、化合物和最终排名。
  - English: Streamlit dashboard showcasing BGCs, features, compounds, and rankings.

模块关系 / Module Relations:
  - 读取 intermediate/ 与 outputs/ 目录下的表格和图表。
  - 与 scripts/06_ranking 与 scripts/07_reporting 的输出保持一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "intermediate"
OUTPUT_DIR = BASE_DIR / "outputs"
FIGURE_DIR = BASE_DIR / "figures"
REPORT_DIR = BASE_DIR / "report"


def load_table(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        if path.suffix == ".parquet":
            return pd.read_parquet(path, engine='pyarrow')
        sep = "," if path.suffix == ".csv" else "\t"
        return pd.read_csv(path, sep=sep)
    except Exception as e:
        st.warning(f"Failed to load {path.name}: {str(e)}")
        return None


def main() -> None:
    st.set_page_config(page_title="Actinomycete Mini-Pipeline", layout="wide")
    st.title("Actinomycete BGC → Metabolomics Mini-Pipeline Dashboard")

    ranking_path = OUTPUT_DIR / "ranked_leads.csv"
    evidence_path = DATA_DIR / "linking" / "mapping_evidence.parquet"
    admet_path = DATA_DIR / "cheminf" / "admet.parquet"
    cluster_path = DATA_DIR / "cheminf" / "similarity_clusters.parquet"

    ranking_df = load_table(ranking_path)
    evidence_df = load_table(evidence_path)
    admet_df = load_table(admet_path)
    cluster_df = load_table(cluster_path)

    if ranking_df is not None:
        st.subheader("Ranked Candidates")
        st.dataframe(ranking_df, use_container_width=True)
        st.download_button(
            label="Download ranked_leads.csv",
            data=ranking_path.read_bytes(),
            file_name="ranked_leads.csv",
            mime="text/csv",
        )
    else:
        st.info("Ranking file not found.")

    with st.expander("Evidence Table", expanded=False):
        if evidence_df is not None:
            st.dataframe(evidence_df.head(200), use_container_width=True)
        else:
            st.write("Evidence table not available.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ADMET Summary")
        if admet_df is not None:
            st.dataframe(admet_df, use_container_width=True)
        else:
            st.write("No ADMET data.")
    with col2:
        st.subheader("Similarity Clusters")
        if cluster_df is not None:
            st.dataframe(cluster_df, use_container_width=True)
        else:
            st.write("No cluster assignments.")

    st.subheader("Figures")
    figure_files = sorted(FIGURE_DIR.glob("*"))
    if not figure_files:
        st.write("No figures generated.")
    for fig in figure_files:
        if fig.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            st.image(str(fig), caption=fig.name, use_column_width=True)
        else:
            st.download_button(
                label=f"Download {fig.name}",
                data=fig.read_bytes(),
                file_name=fig.name,
            )

    report_pdf = REPORT_DIR / "report.pdf"
    if report_pdf.exists():
        st.subheader("Report")
        st.download_button(
            label="Download report.pdf",
            data=report_pdf.read_bytes(),
            file_name="report.pdf",
        )


if __name__ == "__main__":
    main()
