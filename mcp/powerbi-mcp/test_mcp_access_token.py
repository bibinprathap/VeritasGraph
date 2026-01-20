"""
Test script for Power BI MCP Server with Access Token Authentication

This script demonstrates how to:
1. Obtain an OAuth2 access token using MSAL
2. Set the access token via the set_access_token tool
3. Test various Power BI operations

Prerequisites:
- Azure AD App Registration with Power BI API permissions
- Client ID and Tenant ID configured
- User credentials for authentication
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
    print("⚠️  msal not installed. Install with: pip install msal")
    print("   You can still test by providing an access token manually.")


def get_access_token_interactive(tenant_id: str, client_id: str) -> Optional[str]:
    """
    Get access token using interactive device code flow
    
    Args:
        tenant_id: Azure AD tenant ID
        client_id: Azure AD application (client) ID
        
    Returns:
        Access token string or None if failed
    """
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


async def main() -> None:
    """Main test function"""
    # 🔧 CHANGE THIS if your repo path is different
    repo_root = r"C:\Users\Canopus-hp\Documents\Projects\powerBINLP\powerbi-mcp"
    
    server_path = os.path.join(repo_root, "src", "server.py")
    pythonpath = os.path.join(repo_root, "src")
    
    print("=" * 60)
    print(" Power BI MCP Test - Access Token Authentication")
    print("=" * 60)
    print(f"Server path: {server_path}")
    print(f"PYTHONPATH:  {pythonpath}")
    print("=" * 60)
    
    # Get access token
    access_token = None
    
    # Option 1: Get from environment variable
    access_token = os.getenv("POWERBI_ACCESS_TOKEN")
    if access_token:
        print("\n✅ Found access token from POWERBI_ACCESS_TOKEN environment variable")
    else:
        # Option 2: Get via interactive authentication
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        
        if tenant_id and client_id and MSAL_AVAILABLE:
            print("\n📝 Attempting interactive authentication...")
            access_token = get_access_token_interactive(tenant_id, client_id)
        else:
            print("\n⚠️  No access token found!")
            print("   Options:")
            print("   1. Set POWERBI_ACCESS_TOKEN environment variable")
            print("   2. Set TENANT_ID and CLIENT_ID for interactive auth")
            print("   3. Provide token manually below")
            
            # Option 3: Manual input
            manual_token = input("\nEnter access token manually (or press Enter to skip): ").strip()
            if manual_token:
                access_token = manual_token
    
    if not access_token:
        print("\n❌ Cannot proceed without access token. Exiting.")
        return
    
    # Truncate token for display (show first/last few chars)
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
            
            # 1️⃣ Initialize MCP
            print("\n🚀 Initializing MCP session...")
            await session.initialize()
            
            # 2️⃣ List available tools
            print("\n🛠️  Listing available tools...")
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"Available tools ({len(tool_names)}):")
            for tool_name in sorted(tool_names):
                print(f"  - {tool_name}")
            
            # 3️⃣ Set access token
            print("\n🔐 Setting access token via set_access_token tool...")
            set_token_result = await session.call_tool(
                "set_access_token",
                arguments={"access_token": access_token}
            )
            
            # Print result
            for block in set_token_result.content:
                if isinstance(block, types.TextContent):
                    print(f"  {block.text}")
            
            # 4️⃣ Test list_workspaces (without passing token - should use stored token)
            print("\n📋 Testing list_workspaces (using stored token)...")
            workspaces_result = await session.call_tool(
                "list_workspaces",
                arguments={}  # No token passed - should use stored token
            )
            
            print("\n" + "=" * 60)
            print(" WORKSPACES RESULT")
            print("=" * 60)
            
            for block in workspaces_result.content:
                if isinstance(block, types.TextContent):
                    print(block.text)
            
            # 5️⃣ Test list_workspaces with token in arguments (should override stored token)
            print("\n📋 Testing list_workspaces (with token in arguments)...")
            workspaces_result2 = await session.call_tool(
                "list_workspaces",
                arguments={"access_token": access_token}  # Explicit token
            )
            
            print("\n" + "=" * 60)
            print(" WORKSPACES RESULT (with explicit token)")
            print("=" * 60)
            
            for block in workspaces_result2.content:
                if isinstance(block, types.TextContent):
                    print(block.text)
            
            # 6️⃣ Extract workspace ID and test list_datasets
            workspace_id = None
            for block in workspaces_result.content:
                if isinstance(block, types.TextContent):
                    text = block.text
                    # Try to extract workspace ID from text
                    if "ID:" in text:
                        lines = text.split("\n")
                        for line in lines:
                            if "ID:" in line:
                                workspace_id = line.split("ID:")[-1].strip()
                                break
                    if workspace_id:
                        break
            
            if workspace_id:
                print(f"\n📦 Testing list_datasets for workspace: {workspace_id}")
                datasets_result = await session.call_tool(
                    "list_datasets",
                    arguments={"workspace_id": workspace_id}
                )
                
                print("\n" + "=" * 60)
                print(" DATASETS RESULT")
                print("=" * 60)
                
                for block in datasets_result.content:
                    if isinstance(block, types.TextContent):
                        print(block.text)
            else:
                print("\n⚠️  Could not extract workspace ID. Skipping dataset test.")
            
            # 7️⃣ Test security_status
            print("\n🔒 Testing security_status...")
            security_result = await session.call_tool(
                "security_status",
                arguments={}
            )
            
            print("\n" + "=" * 60)
            print(" SECURITY STATUS")
            print("=" * 60)
            
            for block in security_result.content:
                if isinstance(block, types.TextContent):
                    print(block.text)
            
            print("\n" + "=" * 60)
            print("✅ All tests completed successfully!")
            print("=" * 60)


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

