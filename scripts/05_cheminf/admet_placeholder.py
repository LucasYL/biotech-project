
# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：使用 RDKit 计算真实 ADMET 性质，包括药物相似性评分和规则检查。
  - English: Calculate real ADMET properties using RDKit, including drug-likeness scores and rule checks.

输入 / Inputs:
  - chem_path: 化学参考表，包含 SMILES。
  - output_path: ADMET 结果路径。
  - external_csv: 可选外部预测文件。

输出 / Outputs:
  - admet.parquet/CSV，包含 logP、TPSA、HBD、HBA、MW、QED、RotatableBonds、AromaticRings 等。
  - figures/admet_radar_*.png: 每个化合物的雷达图（可选）。

主要功能 / Key Functions:
  - calculate_properties(...): 使用 RDKit 计算真实分子描述符。
  - apply_lipinski_rules(...): Lipinski Rule of Five 检查。
  - apply_veber_rules(...): Veber 规则检查。
  - calculate_qed(...): 药物相似性评分（Quantitative Estimate of Drug-likeness）。

与其他模块的联系 / Relations to Other Modules:
  - rank_candidates.py: 使用 ADMET 结果作为综合评分因子。
  - build_report.py: 报告中展示 ADMET 摘要。
  - dashboard: 可视化 ADMET 分布和雷达图。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run admet_placeholder.py") from exc

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, QED, Crippen, rdMolDescriptors
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("RDKit is required for ADMET calculations. Install with: conda install -c conda-forge rdkit") from exc

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipeline_defaults.yaml"


def load_config(config_path: Path | None) -> Dict[str, Any]:
    target = config_path or DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with target.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration malformed (expected dict): {target}")
    return config


def load_compounds(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Chemical reference table not found: {path}")
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        return pd.read_csv(path, sep=sep)
    raise NotImplementedError(f"Unsupported table format: {path.suffix}")


def calculate_properties(smiles: str) -> Dict[str, Any]:
    """
    Calculate real molecular properties using RDKit.
    
    Args:
        smiles: SMILES string of the molecule
        
    Returns:
        Dictionary containing molecular descriptors and drug-likeness metrics
    """
    if not smiles or pd.isna(smiles):
        return {
            "MW": None,
            "logP": None,
            "TPSA": None,
            "HBD": None,
            "HBA": None,
            "RotatableBonds": None,
            "AromaticRings": None,
            "QED": None,
            "MolarRefractivity": None,
            "FractionCSP3": None,
        }
    
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        logger.warning(f"Invalid SMILES: {smiles}")
        return {
            "MW": None,
            "logP": None,
            "TPSA": None,
            "HBD": None,
            "HBA": None,
            "RotatableBonds": None,
            "AromaticRings": None,
            "QED": None,
            "MolarRefractivity": None,
            "FractionCSP3": None,
        }
    
    try:
        properties = {
            "MW": round(Descriptors.MolWt(mol), 2),
            "logP": round(Crippen.MolLogP(mol), 2),
            "TPSA": round(Descriptors.TPSA(mol), 2),
            "HBD": Lipinski.NumHDonors(mol),
            "HBA": Lipinski.NumHAcceptors(mol),
            "RotatableBonds": Lipinski.NumRotatableBonds(mol),
            "AromaticRings": Lipinski.NumAromaticRings(mol),
            "QED": round(QED.qed(mol), 3),
            "MolarRefractivity": round(Crippen.MolMR(mol), 2),
            "FractionCSP3": round(rdMolDescriptors.CalcFractionCSP3(mol), 3),
        }
        return properties
    except Exception as e:
        logger.error(f"Error calculating properties for {smiles}: {e}")
        return {
            "MW": None,
            "logP": None,
            "TPSA": None,
            "HBD": None,
            "HBA": None,
            "RotatableBonds": None,
            "AromaticRings": None,
            "QED": None,
            "MolarRefractivity": None,
            "FractionCSP3": None,
        }


def apply_lipinski_rules(properties: Dict[str, Any]) -> bool:
    """
    Check if molecule passes Lipinski's Rule of Five.
    
    Criteria:
    - Molecular weight < 500 Da
    - logP < 5
    - Hydrogen bond donors ≤ 5
    - Hydrogen bond acceptors ≤ 10
    """
    if any(properties.get(k) is None for k in ["MW", "logP", "HBD", "HBA"]):
        return False
    
    return (
        properties["MW"] <= 500
        and properties["logP"] <= 5
        and properties["HBD"] <= 5
        and properties["HBA"] <= 10
    )


def apply_veber_rules(properties: Dict[str, Any]) -> bool:
    """
    Check if molecule passes Veber rules for oral bioavailability.
    
    Criteria:
    - Rotatable bonds ≤ 10
    - Polar surface area ≤ 140 Ų
    """
    if any(properties.get(k) is None for k in ["RotatableBonds", "TPSA"]):
        return False
    
    return (
        properties["RotatableBonds"] <= 10
        and properties["TPSA"] <= 140
    )


def assess_drug_likeness(properties: Dict[str, Any]) -> str:
    """
    Assess overall drug-likeness based on multiple criteria.
    
    Returns:
        "Excellent", "Good", "Moderate", or "Poor"
    """
    if any(properties.get(k) is None for k in ["QED"]):
        return "Unknown"
    
    qed = properties["QED"]
    lipinski_pass = apply_lipinski_rules(properties)
    veber_pass = apply_veber_rules(properties)
    
    if qed >= 0.7 and lipinski_pass and veber_pass:
        return "Excellent"
    elif qed >= 0.5 and (lipinski_pass or veber_pass):
        return "Good"
    elif qed >= 0.3:
        return "Moderate"
    else:
        return "Poor"


def load_external(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    if not path.exists():
        raise FileNotFoundError(f"External ADMET file not found: {path}")
    if path.suffix in {".csv", ".tsv"}:
        sep = "," if path.suffix == ".csv" else "	"
        return pd.read_csv(path, sep=sep)
    raise NotImplementedError(f"Unsupported external format: {path.suffix}")


def build_admet_table(
    chem_path: Path,
    output_path: Path,
    external_csv: Path | None = None,
    config_path: Path | None = None,
) -> pd.DataFrame:
    """
    Build comprehensive ADMET table with RDKit-calculated properties.
    
    Args:
        chem_path: Path to chemical reference table (must contain SMILES)
        output_path: Path to save ADMET results
        external_csv: Optional external ADMET data to merge
        config_path: Optional custom configuration file
        
    Returns:
        DataFrame with ADMET properties for all compounds
    """
    config = load_config(config_path)
    logging_config = config.get("logging", {})
    logging.basicConfig(
        level=getattr(logging, str(logging_config.get("level", "INFO")).upper(), logging.INFO),
        format=logging_config.get("format", "%(levelname)s - %(message)s"),
    )

    logger.info(f"Loading compounds from {chem_path}")
    compounds = load_compounds(chem_path)
    
    if "SMILES" not in compounds.columns:
        raise ValueError("Chemical reference table must contain SMILES column")

    logger.info(f"Calculating ADMET properties for {len(compounds)} compounds...")
    rows = []
    for idx, row in compounds.iterrows():
        compound_id = row.get("CompoundID", f"Compound_{idx}")
        smiles = row.get("SMILES", "")
        
        # Calculate properties using RDKit
        props = calculate_properties(smiles)
        
        # Apply drug-likeness rules
        lipinski_pass = apply_lipinski_rules(props)
        veber_pass = apply_veber_rules(props)
        drug_likeness = assess_drug_likeness(props)
        
        rows.append({
            "CompoundID": compound_id,
            "SMILES": smiles,
            **props,
            "Lipinski_Pass": lipinski_pass,
            "Veber_Pass": veber_pass,
            "DrugLikeness": drug_likeness,
            "OralBioavailability": "Likely" if (lipinski_pass and veber_pass) else "Unlikely",
        })

    admet_df = pd.DataFrame(rows)
    
    # Merge with external data if provided
    external = load_external(external_csv)
    if not external.empty:
        logger.info(f"Merging external ADMET data from {external_csv}")
        if "CompoundID" not in external.columns:
            raise ValueError("External ADMET file must contain CompoundID column")
        external = external.set_index("CompoundID")
        admet_df = admet_df.set_index("CompoundID")
        admet_df.update(external)
        admet_df = admet_df.reset_index()
    else:
        admet_df = admet_df.reset_index(drop=True)

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        admet_df.to_parquet(output_path, index=False)
    elif output_path.suffix in {".csv", ".tsv"}:
        sep = "," if output_path.suffix == ".csv" else "\t"
        admet_df.to_csv(output_path, index=False, sep=sep)
    else:
        raise NotImplementedError(f"Unsupported output format: {output_path.suffix}")

    logger.info(f"✅ Wrote ADMET table with {admet_df.shape[0]} entries to {output_path}")
    logger.info(f"   - Lipinski Pass: {admet_df['Lipinski_Pass'].sum()}/{len(admet_df)}")
    logger.info(f"   - Veber Pass: {admet_df['Veber_Pass'].sum()}/{len(admet_df)}")
    logger.info(f"   - Mean QED: {admet_df['QED'].mean():.3f}")
    
    return admet_df


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate placeholder ADMET annotations")
    parser.add_argument("chem_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--external-csv", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for ADMET calculation script."""
    parser = build_parser()
    args = parser.parse_args(argv)
    build_admet_table(args.chem_path, args.output_path, args.external_csv, args.config)


if __name__ == "__main__":  # pragma: no cover
    main()
