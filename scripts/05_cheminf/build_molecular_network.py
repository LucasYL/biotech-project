# -*- coding: utf-8 -*-
"""
文件用途 / Purpose:
  - 中文：构建基于分子相似性的化合物网络，计算网络拓扑指标。
  - English: Build molecular similarity network and calculate network topology metrics.

输入 / Inputs:
  - fingerprints_path: Morgan指纹数据（来自rdkit_fingerprints.py）
  - admet_path: ADMET数据，用于节点属性
  - output_network: 网络数据输出路径（GraphML格式）
  - output_metrics: 网络指标输出路径

输出 / Outputs:
  - network.graphml: 可用Cytoscape打开的网络文件
  - network_metrics.parquet: 节点的网络拓扑指标
  - network_stats.json: 全局网络统计信息

主要功能 / Key Functions:
  - calculate_similarity_matrix(): 计算Tanimoto相似性矩阵
  - build_network(): 构建NetworkX图对象
  - calculate_centrality_metrics(): 计算中心性指标
  - detect_communities(): 社区检测（Louvain算法）
  - export_network(): 导出多种格式

与其他模块的联系 / Relations to Other Modules:
  - rdkit_fingerprints.py: 使用其生成的指纹数据
  - dashboard: 网络可视化
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd
import numpy as np

try:
    from rdkit import DataStructs
    from rdkit.Chem import AllChem
except ImportError as exc:
    raise RuntimeError("RDKit is required. Install with: conda install -c conda-forge rdkit") from exc

try:
    import networkx as nx
except ImportError as exc:
    raise RuntimeError("NetworkX is required. Install with: conda install -c conda-forge networkx") from exc

try:
    import community as community_louvain
except ImportError:
    community_louvain = None
    logging.warning("python-louvain not installed. Community detection will be skipped.")

logger = logging.getLogger(__name__)


def load_fingerprints(path: Path) -> pd.DataFrame:
    """Load fingerprint data from parquet file."""
    if not path.exists():
        raise FileNotFoundError(f"Fingerprint file not found: {path}")
    return pd.read_parquet(path)


def load_admet(path: Path) -> Optional[pd.DataFrame]:
    """Load ADMET data if available."""
    if not path.exists():
        logger.warning(f"ADMET file not found: {path}. Node attributes will be limited.")
        return None
    return pd.read_parquet(path)


def calculate_similarity_matrix(
    fingerprints_df: pd.DataFrame,
    similarity_threshold: float = 0.0
) -> Tuple[np.ndarray, List[str]]:
    """
    Calculate pairwise Tanimoto similarity matrix.
    
    Args:
        fingerprints_df: DataFrame with CompoundID and Fingerprint columns
        similarity_threshold: Minimum similarity to include (0-1)
        
    Returns:
        (similarity_matrix, compound_ids)
    """
    logger.info(f"Calculating similarity matrix for {len(fingerprints_df)} compounds...")
    
    compound_ids = fingerprints_df['CompoundID'].tolist()
    n_compounds = len(compound_ids)
    
    # Parse fingerprints from bit strings
    fps = []
    for _, row in fingerprints_df.iterrows():
        smiles = row['SMILES']
        fp_str = row['Fingerprint']
        
        # Create molecule and generate fingerprint
        mol = AllChem.MolFromSmiles(smiles)
        if mol is None:
            logger.warning(f"Invalid SMILES: {smiles}, using empty fingerprint")
            fp = AllChem.GetMorganFingerprintAsBitVect(
                AllChem.MolFromSmiles('C'),
                2,
                nBits=2048
            )
        else:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
        
        fps.append(fp)
    
    # Calculate similarity matrix
    similarity_matrix = np.zeros((n_compounds, n_compounds))
    
    for i in range(n_compounds):
        for j in range(i, n_compounds):
            sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
            similarity_matrix[i, j] = sim
            similarity_matrix[j, i] = sim
    
    logger.info(f"Similarity matrix calculated. Mean similarity: {similarity_matrix.mean():.3f}")
    
    return similarity_matrix, compound_ids


def build_network(
    similarity_matrix: np.ndarray,
    compound_ids: List[str],
    threshold: float = 0.6,
    admet_df: Optional[pd.DataFrame] = None
) -> nx.Graph:
    """
    Build network graph from similarity matrix.
    
    Args:
        similarity_matrix: Pairwise similarity scores
        compound_ids: List of compound IDs
        threshold: Minimum similarity to create an edge
        admet_df: Optional ADMET data for node attributes
        
    Returns:
        NetworkX Graph object
    """
    logger.info(f"Building network with similarity threshold {threshold}...")
    
    G = nx.Graph()
    n_compounds = len(compound_ids)
    
    # Add nodes with attributes
    for i, compound_id in enumerate(compound_ids):
        node_attrs = {'compound_id': compound_id}
        
        # Add ADMET attributes if available
        if admet_df is not None:
            compound_data = admet_df[admet_df['CompoundID'] == compound_id]
            if not compound_data.empty:
                row = compound_data.iloc[0]
                node_attrs.update({
                    'MW': float(row.get('MW', 0)),
                    'logP': float(row.get('logP', 0)),
                    'QED': float(row.get('QED', 0)),
                    'DrugLikeness': str(row.get('DrugLikeness', 'Unknown')),
                    'Lipinski_Pass': bool(row.get('Lipinski_Pass', False)),
                })
        
        G.add_node(compound_id, **node_attrs)
    
    # Add edges above threshold
    edge_count = 0
    for i in range(n_compounds):
        for j in range(i + 1, n_compounds):
            sim = similarity_matrix[i, j]
            if sim >= threshold and i != j:
                G.add_edge(
                    compound_ids[i],
                    compound_ids[j],
                    weight=float(sim),
                    similarity=float(sim)
                )
                edge_count += 1
    
    logger.info(f"Network built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    return G


def calculate_centrality_metrics(G: nx.Graph) -> pd.DataFrame:
    """
    Calculate various centrality metrics for all nodes.
    
    Args:
        G: NetworkX graph
        
    Returns:
        DataFrame with centrality metrics
    """
    logger.info("Calculating centrality metrics...")
    
    metrics = {
        'CompoundID': list(G.nodes()),
        'Degree': [G.degree(node) for node in G.nodes()],
    }
    
    # Only calculate for connected graphs
    if nx.is_connected(G):
        metrics['Betweenness'] = list(nx.betweenness_centrality(G).values())
        metrics['Closeness'] = list(nx.closeness_centrality(G).values())
    else:
        logger.warning("Graph is not connected. Some metrics will be limited.")
        metrics['Betweenness'] = [0.0] * G.number_of_nodes()
        metrics['Closeness'] = [0.0] * G.number_of_nodes()
    
    # Eigenvector centrality (may fail for disconnected graphs)
    try:
        metrics['Eigenvector'] = list(nx.eigenvector_centrality(G, max_iter=1000).values())
    except:
        logger.warning("Eigenvector centrality calculation failed.")
        metrics['Eigenvector'] = [0.0] * G.number_of_nodes()
    
    # Clustering coefficient
    metrics['Clustering'] = list(nx.clustering(G).values())
    
    return pd.DataFrame(metrics)


def detect_communities(G: nx.Graph) -> Dict[str, int]:
    """
    Detect communities using Louvain algorithm.
    
    Args:
        G: NetworkX graph
        
    Returns:
        Dictionary mapping node to community ID
    """
    if community_louvain is None:
        logger.warning("Louvain algorithm not available. Skipping community detection.")
        return {node: 0 for node in G.nodes()}
    
    logger.info("Detecting communities with Louvain algorithm...")
    partition = community_louvain.best_partition(G)
    
    n_communities = len(set(partition.values()))
    logger.info(f"Found {n_communities} communities")
    
    return partition


def calculate_network_stats(G: nx.Graph) -> Dict[str, Any]:
    """Calculate global network statistics."""
    stats = {
        'num_nodes': G.number_of_nodes(),
        'num_edges': G.number_of_edges(),
        'density': nx.density(G),
        'num_connected_components': nx.number_connected_components(G),
    }
    
    if G.number_of_edges() > 0:
        stats['average_clustering'] = nx.average_clustering(G)
        stats['transitivity'] = nx.transitivity(G)
    
    if nx.is_connected(G):
        stats['diameter'] = nx.diameter(G)
        stats['average_shortest_path_length'] = nx.average_shortest_path_length(G)
    
    return stats


def export_network(
    G: nx.Graph,
    output_network: Path,
    output_metrics: Path,
    output_stats: Path,
    centrality_df: pd.DataFrame,
    stats: Dict[str, Any],
    communities: Dict[str, int]
) -> None:
    """
    Export network in multiple formats.
    
    Args:
        G: NetworkX graph
        output_network: Path for GraphML file
        output_metrics: Path for metrics parquet
        output_stats: Path for stats JSON
        centrality_df: DataFrame with centrality metrics
        stats: Global network statistics
        communities: Community assignments
    """
    # Add community to nodes
    for node in G.nodes():
        G.nodes[node]['community'] = communities.get(node, 0)
    
    # Export GraphML (for Cytoscape)
    output_network.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, output_network)
    logger.info(f"Network exported to GraphML: {output_network}")
    
    # Add community to metrics DataFrame
    centrality_df['Community'] = centrality_df['CompoundID'].map(communities)
    
    # Export metrics
    output_metrics.parent.mkdir(parents=True, exist_ok=True)
    centrality_df.to_parquet(output_metrics, index=False)
    logger.info(f"Network metrics exported: {output_metrics}")
    
    # Export stats
    output_stats.parent.mkdir(parents=True, exist_ok=True)
    with output_stats.open('w') as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Network statistics exported: {output_stats}")


def build_molecular_network(
    fingerprints_path: Path,
    admet_path: Path,
    output_network: Path,
    output_metrics: Path,
    output_stats: Path,
    similarity_threshold: float = 0.6
) -> None:
    """
    Main function to build molecular similarity network.
    
    Args:
        fingerprints_path: Path to fingerprints parquet
        admet_path: Path to ADMET parquet
        output_network: Path for network GraphML
        output_metrics: Path for metrics parquet
        output_stats: Path for stats JSON
        similarity_threshold: Minimum similarity for edges
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    # Load data
    fingerprints_df = load_fingerprints(fingerprints_path)
    admet_df = load_admet(admet_path)
    
    # Calculate similarity
    similarity_matrix, compound_ids = calculate_similarity_matrix(fingerprints_df)
    
    # Build network
    G = build_network(similarity_matrix, compound_ids, similarity_threshold, admet_df)
    
    # Calculate metrics
    centrality_df = calculate_centrality_metrics(G)
    communities = detect_communities(G)
    stats = calculate_network_stats(G)
    
    # Export
    export_network(
        G,
        output_network,
        output_metrics,
        output_stats,
        centrality_df,
        stats,
        communities
    )
    
    logger.info("✅ Molecular network construction completed!")
    logger.info(f"   - Nodes: {stats['num_nodes']}")
    logger.info(f"   - Edges: {stats['num_edges']}")
    logger.info(f"   - Density: {stats['density']:.3f}")
    logger.info(f"   - Communities: {len(set(communities.values()))}")


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Build molecular similarity network from fingerprints"
    )
    parser.add_argument(
        "fingerprints_path",
        type=Path,
        help="Path to fingerprints parquet file"
    )
    parser.add_argument(
        "admet_path",
        type=Path,
        help="Path to ADMET parquet file"
    )
    parser.add_argument(
        "output_network",
        type=Path,
        help="Output path for network GraphML file"
    )
    parser.add_argument(
        "output_metrics",
        type=Path,
        help="Output path for network metrics parquet"
    )
    parser.add_argument(
        "output_stats",
        type=Path,
        help="Output path for network statistics JSON"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Similarity threshold for edges (default: 0.6)"
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    
    build_molecular_network(
        args.fingerprints_path,
        args.admet_path,
        args.output_network,
        args.output_metrics,
        args.output_stats,
        args.threshold
    )


if __name__ == "__main__":
    main()

