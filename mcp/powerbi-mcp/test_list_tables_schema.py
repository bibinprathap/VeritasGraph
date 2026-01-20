"""
Test script to list tables and their schemas for a Power BI dataset

This script demonstrates:
1. Setting access token
2. Listing tables in a dataset
3. Getting schema (columns) for each table
"""
import asyncio
import os
import sys
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types

# Optional: Import msal for token acquisition
try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False


def get_access_token_interactive(tenant_id: str, client_id: str) -> Optional[str]:
    """Get access token using interactive device code flow"""
    if not MSAL_AVAILABLE:
        return None
        
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = [
        "https://analysis.windows.net/powerbi/api/Workspace.Read.All",
        "https://analysis.windows.net/powerbi/api/Dataset.Read.All",
    ]
    
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=authority,
    )
    
    print("\n🔐 Starting device code flow authentication...")
    flow = app.initiate_device_flow(scopes=scopes)
    
    if "user_code" not in flow:
        print("❌ Failed to create device flow")
        return None
    
    print(f"\n{flow['message']}\n")
    print("➡️  Please complete the authentication in your browser...")
    
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        print("✅ Authentication successful!")
        return result["access_token"]
    else:
        print(f"❌ Authentication failed: {result.get('error_description', 'Unknown error')}")
        return None


async def get_workspace_name(session: ClientSession, workspace_id: str) -> Optional[str]:
    """Get workspace name from workspace ID"""
    print(f"\n🔍 Looking up workspace name for ID: {workspace_id}")
    
    result = await session.call_tool(
        "list_workspaces",
        arguments={}
    )
    
    for block in result.content:
        if isinstance(block, types.TextContent):
            text = block.text
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if workspace_id in line:
                    # The workspace name should be on the line before "ID:"
                    if i > 0 and "ID:" in line:
                        # Look backwards for the workspace name
                        for j in range(i-1, max(0, i-5), -1):
                            if lines[j].strip().startswith("- "):
                                workspace_name = lines[j].strip().replace("- ", "").strip()
                                print(f"✅ Found workspace name: {workspace_name}")
                                return workspace_name
    
    print("⚠️  Could not find workspace name. You may need to provide it manually.")
    return None


async def main() -> None:
    """Main test function"""
    # Configuration
    repo_root = r"C:\Users\Canopus-hp\Documents\Projects\powerBINLP\powerbi-mcp"
    server_path = os.path.join(repo_root, "src", "server.py")
    pythonpath = os.path.join(repo_root, "src")
    
    # Dataset information (from your test results)
    workspace_id = "3fae44c2-94db-4d3b-8f39-f64b937a5d10"
    dataset_name = "GIS Self Service"
    dataset_id = "1e50eb69-ffac-4f25-8fac-57a289e5e6d6"
    
    print("=" * 70)
    print(" Power BI MCP - List Tables and Schemas Test")
    print("=" * 70)
    print(f"Workspace ID: {workspace_id}")
    print(f"Dataset: {dataset_name}")
    print(f"Dataset ID: {dataset_id}")
    print("=" * 70)
    
    # Get access token
    access_token = os.getenv("POWERBI_ACCESS_TOKEN")
    
    if not access_token:
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        
        if tenant_id and client_id and MSAL_AVAILABLE:
            print("\n📝 Attempting interactive authentication...")
            access_token = get_access_token_interactive(tenant_id, client_id)
        else:
            print("\n⚠️  No access token found!")
            print("   Set POWERBI_ACCESS_TOKEN environment variable or")
            print("   Set TENANT_ID and CLIENT_ID for interactive auth")
            manual_token = input("\nEnter access token manually (or press Enter to exit): ").strip()
            if not manual_token:
                print("❌ Cannot proceed without access token. Exiting.")
                return
            access_token = manual_token
    
    if not access_token:
        print("\n❌ Cannot proceed without access token. Exiting.")
        return
    
    token_display = f"{access_token[:10]}...{access_token[-10:]}" if len(access_token) > 20 else access_token
    print(f"\n🔑 Using access token: {token_display}")
    
    # Start MCP server
    server_params = StdioServerParameters(
        command="python",
        args=[server_path],
        env={
            "PYTHONPATH": pythonpath,
        },
    )
    
    # Connect to MCP server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize MCP
            print("\n🚀 Initializing MCP session...")
            await session.initialize()
            
            # Set access token
            print("\n🔐 Setting access token...")
            set_token_result = await session.call_tool(
                "set_access_token",
                arguments={"access_token": access_token}
            )
            
            for block in set_token_result.content:
                if isinstance(block, types.TextContent):
                    print(f"  {block.text}")
            
            # Get workspace name from workspace ID
            workspace_name = await get_workspace_name(session, workspace_id)
            
            if not workspace_name:
                # Fallback: try to extract from list_workspaces or ask user
                workspace_name = input("\nEnter workspace name manually (or press Enter to use workspace ID): ").strip()
                if not workspace_name:
                    workspace_name = workspace_id  # Use ID as fallback
            
            # 1️⃣ List tables in the dataset
            print("\n" + "=" * 70)
            print(f" 📋 LISTING TABLES IN DATASET: {dataset_name}")
            print("=" * 70)
            
            tables_result = await session.call_tool(
                "list_tables",
                arguments={
                    "workspace_name": workspace_name,
                    "dataset_name": dataset_name
                }
            )
            
            # Extract table names from result
            table_names = []
            tables_text = ""
            
            for block in tables_result.content:
                if isinstance(block, types.TextContent):
                    tables_text = block.text
                    print(block.text)
            
            # Parse table names from the output
            lines = tables_text.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("- "):
                    table_name = line.replace("- ", "").strip()
                    if table_name and not table_name.startswith("Description:"):
                        table_names.append(table_name)
            
            if not table_names:
                print("\n⚠️  No tables found or could not parse table names.")
                print("   Raw output:")
                print(tables_text)
                return
            
            print(f"\n✅ Found {len(table_names)} table(s)")
            
            # 2️⃣ Get schema for each table
            print("\n" + "=" * 70)
            print(" 📊 GETTING SCHEMAS FOR EACH TABLE")
            print("=" * 70)
            
            for i, table_name in enumerate(table_names, 1):
                print(f"\n{'─' * 70}")
                print(f"Table {i}/{len(table_names)}: {table_name}")
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
            
            # 3️⃣ Optional: Get comprehensive model info
            print("\n" + "=" * 70)
            print(" 📋 GETTING COMPREHENSIVE MODEL INFO")
            print("=" * 70)
            
            model_info_result = await session.call_tool(
                "get_model_info",
                arguments={
                    "workspace_name": workspace_name,
                    "dataset_name": dataset_name
                }
            )
            
            for block in model_info_result.content:
                if isinstance(block, types.TextContent):
                    print(block.text)
            
            print("\n" + "=" * 70)
            print("✅ All tests completed successfully!")
            print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

