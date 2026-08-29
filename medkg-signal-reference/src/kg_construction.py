#!/usr/bin/env python3
"""
Knowledge Graph Construction for MedKG-Signal
Builds heterogeneous medical KG from EHR data
"""

import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import random

import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from loguru import logger


@dataclass
class MedicalEntity:
    """Base class for medical entities"""
    id: str
    name: str
    entity_type: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class Relation:
    """Edge between entities"""
    source_id: str
    target_id: str
    relation_type: str
    confidence: float = 1.0
    timestamp: Optional[str] = None
    provenance: Optional[str] = None


class MedicalKnowledgeGraph:
    """Heterogeneous medical knowledge graph"""
    
    ENTITY_TYPES = [
        'encounter',
        'diagnosis', 
        'symptom',
        'medication',
        'lab_marker',
        'signal_phenotype',
        'evidence'
    ]
    
    RELATION_TYPES = [
        'encounter_has_diagnosis',
        'encounter_has_symptom',
        'encounter_has_medication',
        'encounter_has_lab',
        'encounter_has_signal',
        'medication_treats_diagnosis',
        'lab_supports_diagnosis',
        'signal_indicates_condition',
        'symptom_suggests_diagnosis',
        'evidence_supports_relation',
        'diagnosis_co_occurs_with',
        'temporal_precedes',
    ]
    
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.entities: Dict[str, MedicalEntity] = {}
        self.relations: List[Relation] = []
        
    def add_entity(self, entity: MedicalEntity):
        """Add entity to graph"""
        self.entities[entity.id] = entity
        self.graph.add_node(
            entity.id,
            name=entity.name,
            type=entity.entity_type,
            **entity.metadata
        )
        
    def add_relation(self, relation: Relation):
        """Add relation to graph"""
        if relation.source_id not in self.entities:
            logger.warning(f"Source entity {relation.source_id} not found")
            return
        if relation.target_id not in self.entities:
            logger.warning(f"Target entity {relation.target_id} not found")
            return
            
        self.relations.append(relation)
        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            relation_type=relation.relation_type,
            confidence=relation.confidence,
            timestamp=relation.timestamp,
            provenance=relation.provenance
        )
        
    def get_entity_neighbors(self, entity_id: str, relation_type: Optional[str] = None) -> List[str]:
        """Get neighboring entities"""
        if entity_id not in self.graph:
            return []
            
        neighbors = []
        for _, target, data in self.graph.out_edges(entity_id, data=True):
            if relation_type is None or data.get('relation_type') == relation_type:
                neighbors.append(target)
        return neighbors
        
    def get_subgraph(self, entity_id: str, depth: int = 2) -> nx.DiGraph:
        """Extract k-hop neighborhood subgraph"""
        if entity_id not in self.graph:
            return nx.DiGraph()
            
        # BFS to depth
        visited = {entity_id}
        current_level = {entity_id}
        
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                neighbors = set(self.graph.successors(node))
                next_level.update(neighbors - visited)
            visited.update(next_level)
            current_level = next_level
            
        return self.graph.subgraph(visited).copy()
        
    def get_path(self, source: str, target: str, max_length: int = 5) -> List[List[str]]:
        """Find all paths between two entities"""
        try:
            paths = list(nx.all_simple_paths(
                self.graph, source, target, cutoff=max_length
            ))
            return paths
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
            
    def save(self, filepath: Path):
        """Save graph to disk"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as pickle
        with open(filepath.with_suffix('.pkl'), 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'entities': self.entities,
                'relations': self.relations
            }, f)
            
        # Save as GraphML for external tools (clean None values first)
        try:
            # Create a copy with None values removed for GraphML export
            clean_graph = self.graph.copy()
            for node, data in clean_graph.nodes(data=True):
                for key in list(data.keys()):
                    if data[key] is None:
                        del data[key]
            for u, v, k, data in clean_graph.edges(keys=True, data=True):
                for key in list(data.keys()):
                    if data[key] is None:
                        del data[key]
            nx.write_graphml(clean_graph, filepath.with_suffix('.graphml'))
        except Exception as e:
            logger.warning(f"Could not save GraphML: {e}")
        
        # Save statistics
        stats = self.get_statistics()
        with open(filepath.with_suffix('.stats.json'), 'w') as f:
            json.dump(stats, f, indent=2)
            
        logger.info(f"Saved KG to {filepath}")
        
    @classmethod
    def load(cls, filepath: Path) -> 'MedicalKnowledgeGraph':
        """Load graph from disk"""
        with open(Path(filepath).with_suffix('.pkl'), 'rb') as f:
            data = pickle.load(f)
            
        kg = cls()
        kg.graph = data['graph']
        kg.entities = data['entities']
        kg.relations = data['relations']
        
        logger.info(f"Loaded KG from {filepath}")
        return kg
        
    def get_statistics(self) -> Dict:
        """Compute graph statistics"""
        stats = {
            'num_nodes': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'num_entities_by_type': {},
            'num_relations_by_type': {},
            'avg_degree': sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1),
            'density': nx.density(self.graph),
        }
        
        # Count by entity type
        for entity in self.entities.values():
            entity_type = entity.entity_type
            stats['num_entities_by_type'][entity_type] = \
                stats['num_entities_by_type'].get(entity_type, 0) + 1
                
        # Count by relation type
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get('relation_type', 'unknown')
            stats['num_relations_by_type'][rel_type] = \
                stats['num_relations_by_type'].get(rel_type, 0) + 1
                
        return stats


def generate_sample_medical_kg(num_encounters: int = 100) -> MedicalKnowledgeGraph:
    """
    Generate synthetic medical knowledge graph for demonstration
    
    Creates realistic EHR-like graph with:
    - Patient encounters
    - Diagnoses (ICD-10)
    - Symptoms
    - Medications
    - Lab results
    - Signal phenotypes (ECG/PPG features)
    """
    logger.info(f"Generating sample KG with {num_encounters} encounters...")
    
    kg = MedicalKnowledgeGraph()
    
    # Sample medical vocabulary
    diagnoses = [
        ('D001', 'Heart Failure', 'I50.9'),
        ('D002', 'Atrial Fibrillation', 'I48.91'),
        ('D003', 'Sepsis', 'A41.9'),
        ('D004', 'Pneumonia', 'J18.9'),
        ('D005', 'Acute Kidney Injury', 'N17.9'),
        ('D006', 'Type 2 Diabetes', 'E11.9'),
        ('D007', 'Hypertension', 'I10'),
        ('D008', 'COPD', 'J44.9'),
    ]
    
    symptoms = [
        ('S001', 'Dyspnea'),
        ('S002', 'Chest Pain'),
        ('S003', 'Fever'),
        ('S004', 'Confusion'),
        ('S005', 'Hypotension'),
        ('S006', 'Tachycardia'),
    ]
    
    medications = [
        ('M001', 'Furosemide'),
        ('M002', 'Metoprolol'),
        ('M003', 'Lisinopril'),
        ('M004', 'Vancomycin'),
        ('M005', 'Insulin'),
        ('M006', 'Warfarin'),
    ]
    
    lab_markers = [
        ('L001', 'Creatinine'),
        ('L002', 'BNP'),
        ('L003', 'Troponin'),
        ('L004', 'WBC'),
        ('L005', 'Lactate'),
        ('L006', 'Glucose'),
    ]
    
    signal_phenotypes = [
        ('SP001', 'AF_Pattern', 'Atrial fibrillation detected in ECG'),
        ('SP002', 'ST_Elevation', 'ST segment elevation'),
        ('SP003', 'Low_HRV', 'Reduced heart rate variability'),
        ('SP004', 'PPG_Low_Perfusion', 'Poor peripheral perfusion'),
        ('SP005', 'QRS_Prolongation', 'Widened QRS complex'),
    ]
    
    # Add diagnosis entities
    for diag_id, name, icd_code in diagnoses:
        kg.add_entity(MedicalEntity(
            id=diag_id,
            name=name,
            entity_type='diagnosis',
            metadata={'icd10_code': icd_code}
        ))
        
    # Add symptom entities
    for symp_id, name in symptoms:
        kg.add_entity(MedicalEntity(
            id=symp_id,
            name=name,
            entity_type='symptom'
        ))
        
    # Add medication entities
    for med_id, name in medications:
        kg.add_entity(MedicalEntity(
            id=med_id,
            name=name,
            entity_type='medication'
        ))
        
    # Add lab marker entities
    for lab_id, name in lab_markers:
        kg.add_entity(MedicalEntity(
            id=lab_id,
            name=name,
            entity_type='lab_marker'
        ))
        
    # Add signal phenotype entities
    for sp_id, name, desc in signal_phenotypes:
        kg.add_entity(MedicalEntity(
            id=sp_id,
            name=name,
            entity_type='signal_phenotype',
            metadata={'description': desc}
        ))
        
    # Generate encounters with realistic patterns
    for i in range(num_encounters):
        encounter_id = f'E{i+1:04d}'
        
        kg.add_entity(MedicalEntity(
            id=encounter_id,
            name=f'Encounter {i+1}',
            entity_type='encounter',
            metadata={
                'age': random.randint(45, 85),
                'gender': random.choice(['M', 'F']),
                'los_hours': random.randint(24, 240)
            }
        ))
        
        # Assign 1-3 diagnoses per encounter
        num_diagnoses = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
        encounter_diagnoses = random.sample(diagnoses, num_diagnoses)
        
        for diag_id, _, _ in encounter_diagnoses:
            kg.add_relation(Relation(
                source_id=encounter_id,
                target_id=diag_id,
                relation_type='encounter_has_diagnosis',
                confidence=random.uniform(0.85, 1.0)
            ))
            
            # Add related symptoms
            num_symptoms = random.randint(1, 3)
            for symp_id, _ in random.sample(symptoms, num_symptoms):
                kg.add_relation(Relation(
                    source_id=encounter_id,
                    target_id=symp_id,
                    relation_type='encounter_has_symptom',
                    confidence=random.uniform(0.7, 1.0)
                ))
                
                # Symptom suggests diagnosis
                kg.add_relation(Relation(
                    source_id=symp_id,
                    target_id=diag_id,
                    relation_type='symptom_suggests_diagnosis',
                    confidence=random.uniform(0.6, 0.9)
                ))
                
        # Add medications (treatment)
        num_meds = random.randint(1, 4)
        for med_id, _ in random.sample(medications, num_meds):
            kg.add_relation(Relation(
                source_id=encounter_id,
                target_id=med_id,
                relation_type='encounter_has_medication',
                confidence=1.0
            ))
            
            # Medication treats one of the diagnoses
            if encounter_diagnoses:
                treated_diag = random.choice(encounter_diagnoses)[0]
                kg.add_relation(Relation(
                    source_id=med_id,
                    target_id=treated_diag,
                    relation_type='medication_treats_diagnosis',
                    confidence=random.uniform(0.7, 0.95)
                ))
                
        # Add lab results
        num_labs = random.randint(2, 5)
        for lab_id, _ in random.sample(lab_markers, num_labs):
            kg.add_relation(Relation(
                source_id=encounter_id,
                target_id=lab_id,
                relation_type='encounter_has_lab',
                confidence=1.0
            ))
            
            # Lab supports diagnosis
            if encounter_diagnoses and random.random() > 0.4:
                supported_diag = random.choice(encounter_diagnoses)[0]
                kg.add_relation(Relation(
                    source_id=lab_id,
                    target_id=supported_diag,
                    relation_type='lab_supports_diagnosis',
                    confidence=random.uniform(0.6, 0.9)
                ))
                
        # Add signal phenotypes
        num_signals = random.randint(1, 3)
        for sp_id, _, _ in random.sample(signal_phenotypes, num_signals):
            kg.add_relation(Relation(
                source_id=encounter_id,
                target_id=sp_id,
                relation_type='encounter_has_signal',
                confidence=random.uniform(0.8, 1.0)
            ))
            
            # Signal indicates condition
            if encounter_diagnoses and random.random() > 0.3:
                indicated_diag = random.choice(encounter_diagnoses)[0]
                kg.add_relation(Relation(
                    source_id=sp_id,
                    target_id=indicated_diag,
                    relation_type='signal_indicates_condition',
                    confidence=random.uniform(0.65, 0.95)
                ))
                
    logger.info(f"Generated KG: {kg.get_statistics()}")
    return kg


def visualize_kg_static(kg: MedicalKnowledgeGraph, output_path: Path, max_nodes: int = 50):
    """Create static matplotlib visualization"""
    logger.info("Creating static KG visualization...")
    
    # Use subgraph if too large
    if kg.graph.number_of_nodes() > max_nodes:
        # Sample encounters
        encounters = [e for e in kg.entities.keys() if e.startswith('E')]
        sample_encounter = random.choice(encounters)
        subgraph = kg.get_subgraph(sample_encounter, depth=2)
        logger.info(f"Using subgraph centered on {sample_encounter}")
    else:
        subgraph = kg.graph
        
    # Color by entity type
    color_map = {
        'encounter': '#FF6B6B',
        'diagnosis': '#4ECDC4',
        'symptom': '#FFE66D',
        'medication': '#95E1D3',
        'lab_marker': '#F38181',
        'signal_phenotype': '#AA96DA',
        'evidence': '#FCBAD3'
    }
    
    node_colors = [
        color_map.get(subgraph.nodes[node].get('type', 'unknown'), '#CCCCCC')
        for node in subgraph.nodes()
    ]
    
    # Layout
    pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
    
    plt.figure(figsize=(16, 12))
    
    # Draw edges
    nx.draw_networkx_edges(
        subgraph, pos,
        alpha=0.3,
        arrows=True,
        arrowsize=10,
        edge_color='#666666',
        width=1.5
    )
    
    # Draw nodes
    nx.draw_networkx_nodes(
        subgraph, pos,
        node_color=node_colors,
        node_size=800,
        alpha=0.9,
        edgecolors='black',
        linewidths=1.5
    )
    
    # Draw labels
    labels = {node: subgraph.nodes[node].get('name', node)[:20] for node in subgraph.nodes()}
    nx.draw_networkx_labels(
        subgraph, pos,
        labels,
        font_size=8,
        font_weight='bold'
    )
    
    # Legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, 
                   markersize=10, label=entity_type.replace('_', ' ').title())
        for entity_type, color in color_map.items()
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    plt.title("Medical Knowledge Graph Visualization", fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved static visualization to {output_path}")
    plt.close()


def visualize_kg_interactive(kg: MedicalKnowledgeGraph, output_path: Path, max_nodes: int = 100):
    """Create interactive Plotly visualization"""
    logger.info("Creating interactive KG visualization...")
    
    # Use subgraph if too large
    if kg.graph.number_of_nodes() > max_nodes:
        encounters = [e for e in kg.entities.keys() if e.startswith('E')]
        sample_encounter = random.choice(encounters[:20])
        subgraph = kg.get_subgraph(sample_encounter, depth=2)
    else:
        subgraph = kg.graph
        
    # Layout
    pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
    
    # Edge traces
    edge_traces = []
    for edge in subgraph.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            showlegend=False
        )
        edge_traces.append(edge_trace)
        
    # Node trace
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    
    color_map = {
        'encounter': '#FF6B6B',
        'diagnosis': '#4ECDC4',
        'symptom': '#FFE66D',
        'medication': '#95E1D3',
        'lab_marker': '#F38181',
        'signal_phenotype': '#AA96DA',
        'evidence': '#FCBAD3'
    }
    
    for node in subgraph.nodes(data=True):
        x, y = pos[node[0]]
        node_x.append(x)
        node_y.append(y)
        
        node_info = f"ID: {node[0]}<br>"
        node_info += f"Name: {node[1].get('name', 'N/A')}<br>"
        node_info += f"Type: {node[1].get('type', 'N/A')}<br>"
        node_info += f"Degree: {subgraph.degree(node[0])}"
        node_text.append(node_info)
        
        node_type = node[1].get('type', 'unknown')
        node_color.append(color_map.get(node_type, '#CCCCCC'))
        
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[subgraph.nodes[node].get('name', node)[:15] for node in subgraph.nodes()],
        textposition='top center',
        textfont=dict(size=8),
        hovertext=node_text,
        marker=dict(
            color=node_color,
            size=15,
            line=dict(width=2, color='black')
        ),
        showlegend=False
    )
    
    # Create figure
    fig = go.Figure(data=edge_traces + [node_trace])
    
    fig.update_layout(
        title=dict(text="Interactive Medical Knowledge Graph", font=dict(size=20)),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=0, l=0, r=0, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=800
    )
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    logger.info(f"Saved interactive visualization to {output_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Medical KG Construction and Visualization')
    parser.add_argument('--generate-sample-data', action='store_true',
                        help='Generate sample medical KG')
    parser.add_argument('--num-encounters', type=int, default=100,
                        help='Number of encounters to generate')
    parser.add_argument('--visualize', action='store_true',
                        help='Create visualizations')
    parser.add_argument('--output-dir', type=Path, 
                        default=Path('../data/graphs'),
                        help='Output directory')
    
    args = parser.parse_args()
    
    if args.generate_sample_data:
        # Generate sample KG
        kg = generate_sample_medical_kg(num_encounters=args.num_encounters)
        
        # Save
        output_path = args.output_dir / 'medical_kg'
        kg.save(output_path)
        
        # Visualize
        if args.visualize:
            visualize_kg_static(
                kg,
                args.output_dir.parent.parent / 'results' / 'images' / 'kg_static.png'
            )
            visualize_kg_interactive(
                kg,
                args.output_dir.parent.parent / 'results' / 'images' / 'kg_interactive.html'
            )
    else:
        print("Use --generate-sample-data to create a sample knowledge graph")
        print("Use --visualize to create visualizations")
