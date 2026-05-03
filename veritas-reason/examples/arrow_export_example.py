"""
Apache Arrow Exporter - Example Usage

This script demonstrates how to use the ArrowExporter to export
knowledge graphs, entities, and relationships to Apache Arrow format.
"""

from veritasreason.export import ArrowExporter, export_arrow
from pathlib import Path
import tempfile

def main():
    print("=" * 70)
    print("Apache Arrow Exporter - Example Usage")
    print("=" * 70)
    
    # Create a temporary directory for outputs
    temp_dir = Path(tempfile.mkdtemp())
    print(f"\n📁 Output directory: {temp_dir}\n")
    
    # Sample data
    entities = [
        {
            "id": "e1",
            "text": "Alice",
            "type": "Person",
            "confidence": 0.95,
            "start": 0,
            "end": 5,
            "metadata": {"age": 30, "city": "New York"}
        },
        {
            "id": "e2",
            "text": "Acme Corp",
            "type": "Organization",
            "confidence": 0.88,
            "start": 10,
            "end": 19,
            "metadata": {"location": "NY", "employees": 100}
        },
        {
            "id": "e3",
            "text": "Bob",
            "type": "Person",
            "confidence": 0.92,
            "metadata": {"age": 35, "department": "Engineering"}
        }
    ]
    
    relationships = [
        {
            "id": "r1",
            "source_id": "e1",
            "target_id": "e2",
            "type": "WORKS_FOR",
            "confidence": 0.90,
            "metadata": {"role": "Engineer", "since": 2020}
        },
        {
            "id": "r2",
            "source_id": "e3",
            "target_id": "e2",
            "type": "WORKS_FOR",
            "confidence": 0.85,
            "metadata": {"role": "Manager", "since": 2018}
        }
    ]
    
    knowledge_graph = {
        "entities": entities,
        "relationships": relationships,
        "metadata": {"version": "1.0", "created": "2024-01-01"}
    }
    
    # Example 1: Export entities using ArrowExporter class
    print("Example 1: Export entities to Arrow")
    print("-" * 70)
    exporter = ArrowExporter()
    entities_path = temp_dir / "entities.arrow"
    exporter.export_entities(entities, entities_path)
    print(f"✓ Entities exported to: {entities_path}")
    print(f"  File size: {entities_path.stat().st_size} bytes\n")
    
    # Example 2: Export relationships
    print("Example 2: Export relationships to Arrow")
    print("-" * 70)
    rels_path = temp_dir / "relationships.arrow"
    exporter.export_relationships(relationships, rels_path)
    print(f"✓ Relationships exported to: {rels_path}")
    print(f"  File size: {rels_path.stat().st_size} bytes\n")
    
    # Example 3: Export complete knowledge graph
    print("Example 3: Export knowledge graph to multiple Arrow files")
    print("-" * 70)
    kg_base_path = temp_dir / "knowledge_graph"
    exporter.export_knowledge_graph(knowledge_graph, kg_base_path)
    kg_entities = temp_dir / "knowledge_graph_entities.arrow"
    kg_rels = temp_dir / "knowledge_graph_relationships.arrow"
    print(f"✓ Knowledge graph exported to:")
    print(f"  - {kg_entities} ({kg_entities.stat().st_size} bytes)")
    print(f"  - {kg_rels} ({kg_rels.stat().st_size} bytes)\n")
    
    # Example 4: Use convenience function
    print("Example 4: Using export_arrow convenience function")
    print("-" * 70)
    export_path = temp_dir / "entities_via_function.arrow"
    export_arrow(entities, export_path)
    print(f"✓ Exported using convenience function: {export_path}")
    print(f"  File size: {export_path.stat().st_size} bytes\n")
    
    # Example 5: Read back with PyArrow (if available)
    try:
        import pyarrow as pa
        import pyarrow.ipc as ipc
        
        print("Example 5: Reading Arrow file with PyArrow")
        print("-" * 70)
        with pa.OSFile(str(entities_path), 'rb') as source:
            with ipc.open_file(source) as reader:
                table = reader.read_all()
                print(f"✓ Table schema:")
                print(f"  {table.schema}")
                print(f"\n✓ Table data ({table.num_rows} rows):")
                print(f"  {table.to_pandas()}\n")
                
        # Example 6: Convert to Pandas DataFrame
        print("Example 6: Convert to Pandas DataFrame")
        print("-" * 70)
        df = table.to_pandas()
        print(f"✓ DataFrame shape: {df.shape}")
        print(f"✓ DataFrame columns: {list(df.columns)}")
        print(f"\n{df}\n")
        
    except ImportError:
        print("⚠ PyArrow not available for reading examples\n")
    
    print("=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print(f"\n💡 Tip: Arrow files are columnar and highly compressed,")
    print(f"   perfect for analytics and compatible with Pandas/DuckDB!\n")
    
    # Cleanup
    import shutil
    print(f"🗑 Cleaning up: {temp_dir}")
    shutil.rmtree(temp_dir)
    print("Done!\n")

if __name__ == "__main__":
    main()
