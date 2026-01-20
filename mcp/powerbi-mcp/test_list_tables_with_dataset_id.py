"""
Test script to list tables and schemas using dataset_id (more reliable)

This script uses the REST API fallback method which is more reliable than XMLA
for bearer token authentication.

Usage:
    python test_list_tables_with_dataset_id.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types


async def main() -> None:
    """Main test function"""
    # Configuration
    repo_root = r"C:\Users\Canopus-hp\Documents\Projects\powerBINLP\powerbi-mcp"
    server_path = os.path.join(repo_root, "src", "server.py")
    pythonpath = os.path.join(repo_root, "src")
    
    # 🔧 CONFIGURE THESE VALUES (from your test results)
    workspace_id = "3fae44c2-94db-4d3b-8f39-f64b937a5d10"
    dataset_name = "GIS Self Service"
    dataset_id = "1e50eb69-ffac-4f25-8fac-57a289e5e6d6"
    
    # Get workspace name for XMLA (default method)
    workspace_name = None  # Will be looked up from workspace_id
    
    access_token = os.getenv("POWERBI_ACCESS_TOKEN")
    
    if not access_token:
        print("❌ POWERBI_ACCESS_TOKEN not set!")
        print("   Set it with: set POWERBI_ACCESS_TOKEN=your_token")
        return
    
    print("=" * 70)
    print(" Power BI MCP - List Tables and Schemas (Using Dataset ID)")
    print("=" * 70)
    print(f"Workspace ID: {workspace_id}")
    print(f"Dataset: {dataset_name}")
    print(f"Dataset ID: {dataset_id}")
    print("=" * 70)
    
    # Start MCP server
    server_params = StdioServerParameters(
        command="python",
        args=[server_path],
        env={"PYTHONPATH": pythonpath},
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            await session.initialize()
            
            # Set access token
            print("\n🔐 Setting access token...")
            set_result = await session.call_tool(
                "set_access_token",
                arguments={"access_token": access_token}
            )
            for block in set_result.content:
                if isinstance(block, types.TextContent):
                    print(f"  {block.text}")
            
            # 1️⃣ Get workspace name for XMLA (default method)
            if not workspace_name:
                print(f"\n🔍 Getting workspace name from workspace ID...")
                workspaces_result = await session.call_tool("list_workspaces", arguments={})
                for block in workspaces_result.content:
                    if isinstance(block, types.TextContent):
                        text = block.text
                        if workspace_id in text:
                            # Extract workspace name
                            lines = text.split("\n")
                            for i, line in enumerate(lines):
                                if workspace_id in line and i > 0:
                                    for j in range(i-1, max(0, i-3), -1):
                                        if lines[j].strip().startswith("- "):
                                            workspace_name = lines[j].strip().replace("- ", "").strip()
                                            break
                                    break
                
                if workspace_name:
                    print(f"✅ Found workspace name: {workspace_name}")
                else:
                    print("⚠️  Could not find workspace name. Will use REST API fallback.")
            
            # 2️⃣ List tables using XMLA (default) with REST API fallback
            print(f"\n📋 Listing tables in '{dataset_name}'...")
            print("   (Using XMLA by default, REST API as fallback)")
            
            tables_args = {}
            if workspace_name and dataset_name:
                tables_args = {
                    "workspace_name": workspace_name,
                    "dataset_name": dataset_name,
                    "dataset_id": dataset_id  # For REST API fallback if XMLA fails
                }
            else:
                tables_args = {"dataset_id": dataset_id}  # REST API only
            
            tables_result = await session.call_tool(
                "list_tables",
                arguments=tables_args
            )
            
            print("\n" + "=" * 70)
            print(" TABLES")
            print("=" * 70)
            
            table_names = []
            for block in tables_result.content:
                if isinstance(block, types.TextContent):
                    text = block.text
                    print(text)
                    # Extract table names
                    for line in text.split("\n"):
                        line = line.strip()
                        if line.startswith("- ") and not line.startswith("- Description:"):
                            table_name = line.replace("- ", "").strip()
                            if table_name:
                                table_names.append(table_name)
            
            if not table_names:
                print("\n❌ Could not retrieve tables. Check logs for errors.")
                return
            
            # 2️⃣ Get schema for each table
            print("\n" + "=" * 70)
            print(" TABLE SCHEMAS")
            print("=" * 70)
            
            for table_name in table_names:
                print(f"\n{'─' * 70}")
                print(f"📊 Table: {table_name}")
                print("─" * 70)
                
                # Use XMLA (default) with REST API fallback
                columns_args = {
                    "table_name": table_name
                }
                if workspace_name and dataset_name:
                    columns_args.update({
                        "workspace_name": workspace_name,
                        "dataset_name": dataset_name,
                        "dataset_id": dataset_id  # For REST API fallback if XMLA fails
                    })
                else:
                    columns_args["dataset_id"] = dataset_id  # REST API only
                
                columns_result = await session.call_tool(
                    "list_columns",
                    arguments=columns_args
                )
                
                for block in columns_result.content:
                    if isinstance(block, types.TextContent):
                        print(block.text)
            
            print("\n" + "=" * 70)
            print("✅ Test completed!")
            print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

