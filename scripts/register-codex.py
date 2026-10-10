#!/usr/bin/env python3
"""Add only the SRE server entries, preserving existing user config and a backup."""
from datetime import datetime
from pathlib import Path
import os
import sys
import tomllib

root = Path(__file__).resolve().parent.parent
target = Path(sys.argv[1]).expanduser()
original = target.read_text() if target.exists() else ""
parsed = tomllib.loads(original)
addition = (root / "scripts/codex-mcp.toml").read_text()
desired = tomllib.loads(addition)["mcp_servers"]
existing = parsed.get("mcp_servers", {})
pending = {}
for name, definition in desired.items():
    if name in existing:
        if existing[name] != definition:
            raise SystemExit(f"Existing {name} differs; refusing to overwrite it")
    else:
        pending[name] = definition
if not pending:
    print("SRE MCP servers already registered")
    raise SystemExit(0)
if set(pending) != set(desired):
    # Keep this script narrow: a partially installed config needs an explicit repair.
    raise SystemExit("Partial SRE registration; refusing to duplicate existing tables")
updated = original.rstrip() + "\n\n" + addition
tomllib.loads(updated)
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    backup = target.with_name(target.name + ".sre-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.write_text(original)
    os.chmod(backup, 0o600)
    print(f"Backup: {backup}")
temporary = target.with_name(target.name + ".sre-tmp")
temporary.write_text(updated)
os.chmod(temporary, target.stat().st_mode & 0o777 if target.exists() else 0o600)
os.replace(temporary, target)
print(f"Registered ghidra-sre and rea-sre in {target}")

