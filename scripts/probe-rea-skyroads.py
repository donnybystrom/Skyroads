#!/usr/bin/env python3
"""Verify real DOS analysis through REA's configured MCP launcher."""
import asyncio
from datetime import timedelta
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/SKYROADS.EXE"


async def main():
    params = StdioServerParameters(command="/bin/bash", args=[str(ROOT / "scripts/rea.sh"), "mcp"])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            calls = [
                ("open_binary", {"path": str(TARGET), "provider_id": "ghidra"}),
                ("list_procedures", {}),
                ("analyze_function", {"procedure": "entry"}),
                ("inspect_native_load_image", {}),
                ("close_binary", {}),
            ]
            for name, args in calls:
                result = await session.call_tool(name, args, read_timeout_seconds=timedelta(seconds=240))
                data = result.model_dump(mode="json", exclude_none=True)
                (ROOT / f"analysis/rea-skyroads-{name}.json").write_text(json.dumps(data, indent=2) + "\n")
                print(f"{name}: isError={result.isError}", flush=True)
                if result.isError:
                    raise RuntimeError(f"{name} failed; see analysis/rea-skyroads-{name}.json")


asyncio.run(main())
