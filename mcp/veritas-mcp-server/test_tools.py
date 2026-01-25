#!/usr/bin/env python3
"""
Test script for VeritasGraph MCP Server
Tests the MCP tools directly without needing a full MCP client connection.
"""

import asyncio
import sys
import os

# Add paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from veritas_mcp_server import (
    health_check,
    get_graph_stats,
    list_files,
    get_index_status,
    query_graph,
)


async def run_tests():
    """Run all tool tests."""
    print("=" * 70)
    print("🧪 VeritasGraph MCP Server - Tool Quality Tests")
    print("=" * 70)
    
    # Test 1: Health Check
    print("\n📋 Test 1: Health Check")
    print("-" * 50)
    result = await health_check()
    print(f"Status: {result.get('status')}")
    print(f"GraphRAG Available: {result.get('graphrag_available')}")
    print(f"Ingest Available: {result.get('ingest_available')}")
    print(f"Index Ready: {result.get('index_ready')}")
    print(f"Files Count: {result.get('files_count')}")
    
    if result.get('status') != 'healthy':
        print("⚠️  System not fully healthy, some tests may fail")
    
    # Test 2: Graph Statistics
    print("\n📊 Test 2: Graph Statistics")
    print("-" * 50)
    result = await get_graph_stats()
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Entities: {result.get('entities_count')}")
        print(f"Relationships: {result.get('relationships_count')}")
        print(f"Communities: {result.get('communities_count')}")
        print(f"Text Units: {result.get('text_units_count')}")
        if result.get('top_entities'):
            print(f"Top Entities: {result.get('top_entities')[:5]}")
    
    # Test 3: List Files
    print("\n📁 Test 3: List Input Files")
    print("-" * 50)
    result = await list_files()
    print(f"Total Files: {result.get('count')}")
    if result.get('files'):
        print(f"Files: {result.get('files')[:5]}...")
    
    # Test 4: Index Status
    print("\n🔍 Test 4: Index Status")
    print("-" * 50)
    result = await get_index_status()
    print(f"Status: {result.get('status')}")
    print(f"Is Complete: {result.get('is_complete')}")
    print(f"Index Ready: {result.get('index_ready')}")
    
    # Test 5: Local Search Query
    print("\n🔎 Test 5: Local Search Query")
    print("-" * 50)
    test_query = "What are the main entities or topics in the knowledge base?"
    print(f"Query: {test_query}")
    print("Executing...")
    
    result = await query_graph(
        query=test_query,
        search_type="local",
        response_type="List of 3-7 Points"
    )
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\n📝 Response ({result.get('search_type')} search):")
        print("-" * 50)
        response = result.get('response', '')
        # Print first 1500 chars for readability
        if len(response) > 1500:
            print(response[:1500] + "\n...[truncated]")
        else:
            print(response)
    
    # Test 6: Global Search Query
    print("\n\n🌐 Test 6: Global Search Query")
    print("-" * 50)
    test_query = "Provide a high-level summary of the knowledge base contents"
    print(f"Query: {test_query}")
    print("Executing (this may take longer)...")
    
    result = await query_graph(
        query=test_query,
        search_type="global",
        response_type="Single Paragraph"
    )
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\n📝 Response ({result.get('search_type')} search):")
        print("-" * 50)
        response = result.get('response', '')
        if len(response) > 1500:
            print(response[:1500] + "\n...[truncated]")
        else:
            print(response)
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_tests())
