#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate molecular network visualization from GraphML file.
"""

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def visualize_network(
    graphml_path: Path,
    output_path: Path,
    layout: str = 'spring'
) -> None:
    """
    Visualize molecular network and save to PNG.
    
    Args:
        graphml_path: Path to GraphML file
        output_path: Path to save PNG visualization
        layout: Layout algorithm ('spring', 'circular', 'kamada_kawai')
    """
    if not graphml_path.exists():
        logger.error(f"GraphML file not found: {graphml_path}")
        return
    
    # Load network
    logger.info(f"Loading network from {graphml_path}")
    G = nx.read_graphml(graphml_path)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Choose layout
    if layout == 'spring':
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    elif layout == 'circular':
        pos = nx.circular_layout(G)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G)
    
    # Draw nodes
    node_colors = []
    for node in G.nodes():
        # Color by community if available
        if 'community' in G.nodes[node]:
            node_colors.append(G.nodes[node]['community'])
        else:
            node_colors.append(0)
    
    # Draw network
    nx.draw_networkx_nodes(
        G, pos,
        node_color=node_colors,
        node_size=800,
        cmap=plt.cm.Set3,
        alpha=0.8,
        ax=ax
    )
    
    nx.draw_networkx_edges(
        G, pos,
        edge_color='gray',
        width=2,
        alpha=0.5,
        ax=ax
    )
    
    nx.draw_networkx_labels(
        G, pos,
        font_size=10,
        font_weight='bold',
        ax=ax
    )
    
    # Add title and info
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    density = nx.density(G)
    
    ax.set_title(
        f'Molecular Similarity Network\n'
        f'Nodes: {num_nodes} | Edges: {num_edges} | Density: {density:.3f}',
        fontsize=14,
        fontweight='bold'
    )
    ax.axis('off')
    
    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Network visualization saved to {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Visualize molecular network")
    parser.add_argument(
        'graphml_path',
        type=Path,
        help='Path to GraphML file'
    )
    parser.add_argument(
        'output_path',
        type=Path,
        help='Path to save PNG visualization'
    )
    parser.add_argument(
        '--layout',
        type=str,
        default='spring',
        choices=['spring', 'circular', 'kamada_kawai'],
        help='Layout algorithm'
    )
    
    args = parser.parse_args()
    visualize_network(args.graphml_path, args.output_path, args.layout)


if __name__ == '__main__':
    main()

