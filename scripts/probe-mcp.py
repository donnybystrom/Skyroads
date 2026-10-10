#!/usr/bin/env python3
"""Exercise the exact configured stdio launcher and save its advertised tools."""
import asyncio
import json
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def main():
    name = sys.argv[1]
    launcher = "ghidra-mcp.sh" if name == "ghidra" else "rea.sh"
    args = [str(ROOT / "scripts" / launcher)] + ([] if name == "ghidra" else ["mcp"])
    parameters = StdioServerParameters(command="/bin/bash", args=args)
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            initialized = await session.initialize()
            tools = []
            cursor = None
            while True:
                page = await session.list_tools(cursor=cursor)
                tools.extend(page.tools)
                cursor = page.nextCursor
                if not cursor:
                    break
            catalog = [tool.model_dump(mode="json", exclude_none=True) for tool in tools]
            (ROOT / f"analysis/{name}-mcp-tools.json").write_text(json.dumps(catalog, indent=2) + "\n")
            print(json.dumps({"server": initialized.serverInfo.model_dump(), "tools": len(tools)}))
            if len(sys.argv) > 2:
                selected = sys.argv[2]
                arguments = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
                result = await session.call_tool(selected, arguments)
                data = result.model_dump(mode="json", exclude_none=True)
                (ROOT / f"analysis/{name}-{selected}.json").write_text(json.dumps(data, indent=2) + "\n")
                print(json.dumps(data)[:7000])
                if result.isError:
                    raise RuntimeError(f"{selected} returned an MCP error")


asyncio.run(main())
