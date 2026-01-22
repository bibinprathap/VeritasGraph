#!/usr/bin/env python
"""
Test script for listing tables and columns using REST API with COLUMNSTATISTICS()
Uses workspace_id and dataset_id directly.
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server import PowerBIMCPServer

# Configuration - Update these values
WORKSPACE_ID = "3fae44c2-94db-4d3b-8f39-f64b937a5d10"  # mcp dev workspace
DATASET_ID = "1e50eb69-ffac-4f25-8fac-57a289e5e6d6"    # GIS Self Service dataset

# Access token - set via environment variable or paste here
ACCESS_TOKEN = os.getenv("POWERBI_ACCESS_TOKEN", "")


async def main():
    print("=" * 70)
    print(" Power BI MCP - List Tables and Columns (REST API)")
    print("=" * 70)
    print(f"Workspace ID: {WORKSPACE_ID}")
    print(f"Dataset ID: {DATASET_ID}")
    print("=" * 70)
    
    if not ACCESS_TOKEN:
        print("\n❌ Error: POWERBI_ACCESS_TOKEN environment variable not set.")
        print("   Set it using: $env:POWERBI_ACCESS_TOKEN = 'your_token_here'")
        return
    
    # Initialize server
    server = PowerBIMCPServer()
    
    # Set access token
    print("\n🔐 Setting access token...")
    result = await server._handle_set_access_token({"access_token": ACCESS_TOKEN})
    print(f"   {result}")
    
    # List tables
    print(f"\n📋 Listing tables...")
    result = await server._handle_list_tables({
        "workspace_id": WORKSPACE_ID,
        "dataset_id": DATASET_ID
    })
    
    print("\n" + "=" * 70)
    print(" TABLES")
    print("=" * 70)
    print(result)
    
    # Parse tables from result to get table names for column listing
    tables = []
    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            table_name = line[2:].strip()
            tables.append(table_name)
    
    # List columns for each table
    if tables:
        print("\n" + "=" * 70)
        print(" TABLE SCHEMAS")
        print("=" * 70)
        
        for table_name in tables:
            print("\n" + "-" * 70)
            print(f"📊 Table: {table_name}")
            print("-" * 70)
            
            columns_result = await server._handle_list_columns({
                "workspace_id": WORKSPACE_ID,
                "dataset_id": DATASET_ID,
                "table_name": table_name
            })
            print(columns_result)
    
    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

