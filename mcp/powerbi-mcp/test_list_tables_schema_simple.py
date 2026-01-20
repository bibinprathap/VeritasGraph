"""
Simple test script to list tables and schemas - with workspace name

Usage:
    python test_list_tables_schema_simple.py
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
    
    # 🔧 CONFIGURE THESE VALUES
    workspace_name = "Your Workspace Name"  # Change this to your workspace name
    dataset_name = "GIS Self Service"
    access_token = os.getenv("POWERBI_ACCESS_TOKEN")
    
    if not access_token:
        print("❌ POWERBI_ACCESS_TOKEN not set!")
        print("   Set it with: set POWERBI_ACCESS_TOKEN=your_token")
        return
    
    print("=" * 70)
    print(" Power BI MCP - List Tables and Schemas")
    print("=" * 70)
    print(f"Workspace: {workspace_name}")
    print(f"Dataset: {dataset_name}")
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
            await session.call_tool(
                "set_access_token",
                arguments={"access_token": access_token}
            )
            
            # 1️⃣ List tables
            print(f"\n📋 Listing tables in '{dataset_name}'...")
            tables_result = await session.call_tool(
                "list_tables",
                arguments={
                    "workspace_name": workspace_name,
                    "dataset_name": dataset_name
                }
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
                print("⚠️  No tables found!")
                return
            
            # 2️⃣ Get schema for each table
            print("\n" + "=" * 70)
            print(" TABLE SCHEMAS")
            print("=" * 70)
            
            for table_name in table_names:
                print(f"\n{'─' * 70}")
                print(f"📊 Table: {table_name}")
                print("─" * 70)
                
                columns_result = await session.call_tool(
                    "list_columns",
                    arguments={
                        "workspace_name": workspace_name,
                        "dataset_name": dataset_name,
                        "table_name": table_name
                    }
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

