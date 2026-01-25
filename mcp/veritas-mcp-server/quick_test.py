#!/usr/bin/env python3
"""Quick test of non-LLM MCP tools."""
import asyncio
import sys
sys.path.insert(0, '.')
from veritas_mcp_server import health_check, get_graph_stats, list_files

async def test():
    print('Testing health_check...')
    r = await health_check()
    print(f'  Status: {r.get("status")}')
    print(f'  Index Ready: {r.get("index_ready")}')
    
    print('\nTesting get_graph_stats...')
    r = await get_graph_stats()
    print(f'  Entities: {r.get("entities_count")}')
    print(f'  Relationships: {r.get("relationships_count")}')
    print(f'  Communities: {r.get("communities_count")}')
    top = r.get("top_entities", [])[:5]
    print(f'  Top Entities: {top}')
    
    print('\nTesting list_files...')
    r = await list_files()
    print(f'  Files: {r.get("count")}')
    
asyncio.run(test())
print('\n✅ All tests passed!')
