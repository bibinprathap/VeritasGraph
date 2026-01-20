import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types


async def main() -> None:
    # 🔧 CHANGE THIS if your repo path is different
    repo_root = r"C:\Users\Canopus-hp\Documents\Projects\powerBINLP\powerbi-mcp"

    server_path = os.path.join(repo_root, "src", "server.py")
    pythonpath = os.path.join(repo_root, "src")

    print("====================================")
    print(" Power BI MCP Test (User Auth)")
    print("====================================")
    print("Server path :", server_path)
    print("PYTHONPATH  :", pythonpath)
    print("====================================\n")

    server_params = StdioServerParameters(
        command="python",
        args=[server_path],
        env={
            "PYTHONPATH": pythonpath,
            # Server should read these from .env or env vars
            # "TENANT_ID": "...",
            # "CLIENT_ID": "...",
        },
    )

    # 🔌 Start MCP server over stdio
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # 1️⃣ Initialize MCP
            print("🚀 Initializing MCP session...")
            await session.initialize()

            # 2️⃣ List available tools
            print("\n🛠 Listing tools...")
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print("Available tools:", tool_names)

            if "list_workspaces" not in tool_names:
                raise RuntimeError("❌ list_workspaces tool not found")

            # 3️⃣ Call list_workspaces (this triggers device login)
            print("\n🔐 Calling list_workspaces (login required)...")
            print("➡️  If prompted, complete browser login\n")

            result = await session.call_tool(
                "list_workspaces",
                arguments={}
            )

            # 4️⃣ Print results
            print("\n================ RESULT ================")

            if result.structuredContent is not None:
                print("✅ Structured content received:\n")
                for ws in result.structuredContent:
                    print(f"- {ws['name']} ({ws['id']})")
            else:
                print("⚠️ No structured content, printing blocks:\n")
                for block in result.content:
                    if isinstance(block, types.TextContent):
                        print(block.text)
                    else:
                        print(block)

            print("\n========================================")
            print("✅ MCP Power BI test completed successfully")
            print("========================================\n")

            # 5️⃣ (Optional) Test datasets for first workspace
            if result.structuredContent:
                workspace_id = result.structuredContent[0]["id"]

                print(f"📦 Fetching datasets for workspace: {workspace_id}")
                datasets = await session.call_tool(
                    "list_datasets",
                    arguments={"workspace_id": workspace_id},
                )

                if datasets.structuredContent:
                    for ds in datasets.structuredContent:
                        print(f"  - {ds['name']} ({ds['id']})")
                else:
                    print("  ⚠️ No datasets found")

                print("\n✅ Dataset test completed")


if __name__ == "__main__":
    asyncio.run(main())
