"""
Graph Visualization Module for VeritasGraph
Creates interactive 2D/3D graph visualizations using PyVis
"""

import os
import pandas as pd
import networkx as nx
from pyvis.network import Network
import json
import base64
from typing import Optional, List, Dict, Any, Tuple

join = os.path.join


def load_graph_data(input_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load entities, relationships, and communities from parquet files."""
    
    ENTITY_TABLE = "create_final_nodes"
    RELATIONSHIP_TABLE = "create_final_relationships"
    COMMUNITY_TABLE = "create_final_communities"
    
    entity_df = pd.read_parquet(join(input_dir, f"{ENTITY_TABLE}.parquet"))
    relationship_df = pd.read_parquet(join(input_dir, f"{RELATIONSHIP_TABLE}.parquet"))
    
    try:
        community_df = pd.read_parquet(join(input_dir, f"{COMMUNITY_TABLE}.parquet"))
    except:
        community_df = pd.DataFrame()
    
    return entity_df, relationship_df, community_df


def create_full_graph(input_dir: str) -> nx.Graph:
    """Create a NetworkX graph from the indexed data."""
    
    entity_df, relationship_df, _ = load_graph_data(input_dir)
    
    G = nx.Graph()
    
    # Add nodes
    for _, row in entity_df.iterrows():
        title = row.get('title', row.get('name', 'Unknown'))
        G.add_node(
            title,
            title=title,
            type=row.get('type', 'entity'),
            description=row.get('description', ''),
            community=row.get('community', 0),
            degree=row.get('degree', 1),
        )
    
    # Add edges
    for _, row in relationship_df.iterrows():
        source = row.get('source', '')
        target = row.get('target', '')
        if source and target and source in G.nodes and target in G.nodes:
            G.add_edge(
                source,
                target,
                description=row.get('description', ''),
                weight=row.get('weight', 1),
                rank=row.get('rank', 1),
            )
    
    return G


def extract_subgraph_for_query(
    G: nx.Graph,
    query_entities: List[str],
    max_depth: int = 2,
    max_nodes: int = 50
) -> nx.Graph:
    """Extract a subgraph centered around query-relevant entities."""
    
    if not query_entities:
        # Return top nodes by degree if no specific entities
        top_nodes = sorted(G.nodes(), key=lambda x: G.degree(x), reverse=True)[:max_nodes]
        return G.subgraph(top_nodes).copy()
    
    # Find matching nodes (case-insensitive partial match)
    matched_nodes = set()
    for entity in query_entities:
        entity_lower = entity.lower()
        for node in G.nodes():
            if entity_lower in node.lower():
                matched_nodes.add(node)
    
    if not matched_nodes:
        # Fallback to top nodes
        top_nodes = sorted(G.nodes(), key=lambda x: G.degree(x), reverse=True)[:max_nodes]
        return G.subgraph(top_nodes).copy()
    
    # Expand to neighbors within max_depth
    expanded_nodes = set(matched_nodes)
    current_frontier = matched_nodes
    
    for _ in range(max_depth):
        next_frontier = set()
        for node in current_frontier:
            neighbors = set(G.neighbors(node))
            next_frontier.update(neighbors - expanded_nodes)
        expanded_nodes.update(next_frontier)
        current_frontier = next_frontier
        
        if len(expanded_nodes) >= max_nodes:
            break
    
    # Limit to max_nodes, prioritizing query entities and high-degree nodes
    if len(expanded_nodes) > max_nodes:
        # Sort by: query entity first, then degree
        sorted_nodes = sorted(
            expanded_nodes,
            key=lambda x: (x not in matched_nodes, -G.degree(x))
        )
        expanded_nodes = set(sorted_nodes[:max_nodes])
    
    return G.subgraph(expanded_nodes).copy()


def get_node_color(node_type: str, is_query_entity: bool = False) -> str:
    """Get color based on node type."""
    if is_query_entity:
        return "#ff6b6b"  # Red for query entities
    
    color_map = {
        "person": "#4ecdc4",
        "organization": "#45b7d1",
        "location": "#96ceb4",
        "event": "#ffeaa7",
        "concept": "#dfe6e9",
        "document": "#a29bfe",
        "default": "#74b9ff",
    }
    
    return color_map.get(node_type.lower(), color_map["default"])


def get_community_color(community_id: int) -> str:
    """Get color based on community ID."""
    colors = [
        "#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12",
        "#1abc9c", "#e91e63", "#00bcd4", "#ff9800", "#8bc34a",
        "#673ab7", "#009688", "#ff5722", "#607d8b", "#795548"
    ]
    return colors[community_id % len(colors)]


def create_pyvis_graph(
    subgraph: nx.Graph,
    query_entities: List[str] = None,
    height: str = "600px",
    width: str = "100%",
    bgcolor: str = "#0a0a0a",
    font_color: str = "white",
    color_by: str = "community"  # "community" or "type"
) -> str:
    """Create an interactive PyVis visualization."""
    
    query_entities = query_entities or []
    query_entities_lower = [e.lower() for e in query_entities]
    
    # Create PyVis network
    net = Network(
        height=height,
        width=width,
        bgcolor=bgcolor,
        font_color=font_color,
        directed=False,
        notebook=False,
        cdn_resources='remote'
    )
    
    # Configure physics for better layout
    net.set_options("""
    {
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {
                "size": 14,
                "face": "Arial"
            }
        },
        "edges": {
            "color": {
                "inherit": true
            },
            "smooth": {
                "type": "continuous",
                "forceDirection": "none"
            }
        },
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -30000,
                "centralGravity": 0.3,
                "springLength": 150,
                "springConstant": 0.04,
                "damping": 0.09
            },
            "stabilization": {
                "enabled": true,
                "iterations": 200,
                "updateInterval": 25
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "dragView": true
        }
    }
    """)
    
    # Add nodes
    for node in subgraph.nodes():
        node_data = subgraph.nodes[node]
        is_query_entity = any(qe in node.lower() for qe in query_entities_lower)
        
        # Determine color
        if color_by == "community":
            community = node_data.get('community', 0)
            color = get_community_color(int(community) if pd.notna(community) else 0)
        else:
            node_type = node_data.get('type', 'default')
            color = get_node_color(node_type, is_query_entity)
        
        if is_query_entity:
            color = "#ff6b6b"  # Override for query entities
        
        # Node size based on degree
        degree = subgraph.degree(node)
        size = min(10 + degree * 3, 50)
        
        # Create tooltip
        description = node_data.get('description', '')
        if len(description) > 200:
            description = description[:200] + "..."
        
        tooltip = f"<b>{node}</b><br><br>{description}"
        
        net.add_node(
            node,
            label=node[:30] + "..." if len(node) > 30 else node,
            title=tooltip,
            color=color,
            size=size,
            borderWidth=4 if is_query_entity else 2,
            font={"size": 12 if is_query_entity else 10}
        )
    
    # Add edges
    for source, target in subgraph.edges():
        edge_data = subgraph.edges[source, target]
        weight = edge_data.get('weight', 1)
        description = edge_data.get('description', '')
        
        net.add_edge(
            source,
            target,
            title=description,
            width=min(1 + weight * 0.5, 5),
            color={"color": "#555555", "opacity": 0.7}
        )
    
    # Generate HTML
    html_content = net.generate_html()
    
    # Encode the HTML as base64 for data URI embedding in iframe
    # This allows Gradio to display full HTML documents
    html_bytes = html_content.encode('utf-8')
    html_base64 = base64.b64encode(html_bytes).decode('utf-8')
    
    # Return an iframe with data URI - works in Gradio's HTML component
    iframe_html = f'''
    <iframe 
        src="data:text/html;base64,{html_base64}" 
        width="100%" 
        height="550px" 
        style="border: 1px solid #444; border-radius: 8px; background: #1a1a1a;"
    ></iframe>
    <p style="color: #888; font-size: 12px; margin-top: 8px; text-align: center;">
        💡 <b>Tip:</b> Drag nodes to rearrange • Scroll to zoom • Hover for details • Click to select
    </p>
    '''
    
    return iframe_html


def create_graph_html_for_query(
    input_dir: str,
    query_entities: List[str] = None,
    max_nodes: int = 50,
    color_by: str = "community"
) -> str:
    """Create a complete HTML visualization for a query."""
    
    try:
        G = create_full_graph(input_dir)
        
        if len(G.nodes()) == 0:
            return "<div style='padding: 20px; color: white;'>No graph data available. Please index your documents first.</div>"
        
        subgraph = extract_subgraph_for_query(G, query_entities or [], max_nodes=max_nodes)
        html = create_pyvis_graph(subgraph, query_entities, color_by=color_by)
        
        return html
        
    except Exception as e:
        return f"<div style='padding: 20px; color: #ff6b6b;'>Error creating graph: {str(e)}</div>"


def get_graph_stats(input_dir: str) -> Dict[str, Any]:
    """Get statistics about the knowledge graph."""
    
    try:
        entity_df, relationship_df, community_df = load_graph_data(input_dir)
        
        return {
            "total_entities": len(entity_df),
            "total_relationships": len(relationship_df),
            "total_communities": len(community_df) if len(community_df) > 0 else "N/A",
            "entity_types": entity_df['type'].value_counts().to_dict() if 'type' in entity_df.columns else {},
        }
    except Exception as e:
        return {"error": str(e)}


def extract_entities_from_response(response: str, entity_df: pd.DataFrame) -> List[str]:
    """Extract entity names mentioned in a response by matching against known entities."""
    
    if entity_df is None or len(entity_df) == 0:
        return []
    
    response_lower = response.lower()
    mentioned_entities = []
    
    # Get entity names
    if 'title' in entity_df.columns:
        entity_names = entity_df['title'].tolist()
    elif 'name' in entity_df.columns:
        entity_names = entity_df['name'].tolist()
    else:
        return []
    
    for entity in entity_names:
        if entity and str(entity).lower() in response_lower:
            mentioned_entities.append(str(entity))
    
    return mentioned_entities[:20]  # Limit to top 20
