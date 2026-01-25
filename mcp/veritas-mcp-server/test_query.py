#!/usr/bin/env python3
"""Test a single query against the MCP server."""
import asyncio
import sys
import os
sys.path.insert(0, '.')

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from veritas_mcp_server import query_graph

async def test_query():
    print("=" * 70)
    print("[TEST] Testing Local Search Query")
    print("=" * 70)
    
    query = "What are the main topics or entities in this knowledge base?"
    print(f"Query: {query}")
    print("-" * 70)
    print("Executing local search...")
    
    result = await query_graph(
        query=query,
        search_type="local",
        response_type="List of 3-7 Points"
    )
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        return
    
    print(f"\n[RESPONSE]:")
    print("-" * 70)
    print(result.get('response', 'No response'))
    print("-" * 70)
    print(f"Search type: {result.get('search_type')}")

if __name__ == "__main__":
    asyncio.run(test_query())
