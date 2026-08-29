#!/usr/bin/env python3
"""Quick script to generate KG visualization"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from kg_construction import generate_sample_medical_kg, visualize_kg_static

print("Generating medical knowledge graph...")
kg = generate_sample_medical_kg(num_encounters=100)

print("Creating visualization...")
output_path = Path('results/images/kg_static.png')
visualize_kg_static(kg, output_path)

print(f"✓ Knowledge graph visualization saved to {output_path}")
