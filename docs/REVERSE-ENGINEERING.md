# SRE on Apple Silicon

Local reverse-engineering tools for the SkyRoads experiment. Original game files
live in `Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/`.

## Tools

- `ghidra-mcp/`: <https://github.com/bethington/ghidra-mcp>, source checkout.
- `rea/`: <https://github.com/morluto/rea>, source checkout, built locally.
- `tools/ghidra_12.1.4_PUBLIC/`: official Ghidra distribution.
- Java 21 ARM64: `/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home`.
- Node 22.21.1: `/Users/donnybystrom/.nvm/versions/node/v22.21.1/bin/node`.
- Python bridge: `ghidra-mcp/.venv/` (Python 3.12).

Source commit IDs and original input identity are recorded in
`analysis/skyroads-original.json`. The Ghidra download digest is recorded in
`analysis/ghidra-release.json`.

## Codex Desktop

The exact server definitions are in `scripts/codex-mcp.toml`. The installer
`scripts/register-codex.py` appends those two entries to the user Codex config,
preserves unrelated settings, and creates a dated backup. Server names:

- **ghidra-sre**: starts/reuses the local headless Ghidra backend automatically,
  opens the persistent SkyRoads project, then serves MCP over stdio.
- **rea-sre**: starts REA over stdio, using Ghidra as its native-analysis provider.

Codex Desktop was restarted and both integrations were verified with direct
MCP calls in the analysis conversation on 2026-10-09.
Both launchers use absolute runtime paths and work when the app starts from Dock.

## Commands

Run these from `/Users/donnybystrom/code/SRE`:

```bash
# Start Ghidra's backend without starting a bridge.
./scripts/ghidra-mcp.sh --start-only

# Show backend health.
curl -fsS http://127.0.0.1:8089/mcp/health

# Stop only the backend owned by this setup (saves the project on shutdown).
./scripts/ghidra-mcp.sh --stop

# REA's CLI, with the same provider configuration as its MCP server.
./scripts/rea.sh --help
./scripts/rea.sh doctor --provider ghidra --format json
./scripts/rea.sh inspect "$PWD/Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/SKYROADS.EXE" --provider ghidra --format json

# Check MCP startup, tool inventory and a target-free REA request.
./scripts/rea.sh mcp doctor --json

# Check the exact Ghidra stdio launcher with the Python MCP client.
ghidra-mcp/.venv/bin/python scripts/probe-mcp.py ghidra check_connection
```

Ghidra's HTTP backend binds to **127.0.0.1:8089**. Logs are in
`logs/ghidra-server.log`, caches and runtime settings in `runtime/`, and the
persistent Ghidra project in `projects/SkyRoads.gpr` with its companion `.rep`
directory. Keep both project components together. Script execution endpoints
remain at the upstream default; ordinary analysis and annotations work without
them. The backend's filesystem operations are scoped to this SRE directory.

## How the two integrations differ

Ghidra-MCP exposes Ghidra's analysis and editing operations directly. Use its
persistent project for recovered names, types, comments and structures.

REA provides provider-neutral inspection with provenance, explicit unknowns,
load-image verification, and additional application/runtime tools. Its Ghidra
sessions use private temporary projects and target snapshots. Session edits are
discarded on close unless explicitly exported using an available snapshot
workflow; they do not update the persistent Ghidra-MCP project.

REA admits DOS MZ executables using `MzLoader`, `x86:LE:16:Real Mode`, and load
segment `0x1000`. Static analysis does not emulate DOS, BIOS calls, graphics,
sound or self-modifying code. If the original is packed, initial disassembly
can describe its unpacking stub; a separately prepared unpacked copy is needed
for the recovered game code. Preserve the original and transformation evidence.

## Rebuild

```bash
source scripts/env.sh
export GRADLE_USER_HOME="$SRE_ROOT/runtime/gradle"
export UV_CACHE_DIR="$SRE_ROOT/runtime/uv-cache"
/opt/homebrew/bin/uv sync --project ghidra-mcp --no-dev --python /opt/homebrew/bin/python3.12
(cd ghidra-mcp && ./gradlew --no-daemon buildExtension "-PGHIDRA_INSTALL_DIR=$GHIDRA_INSTALL_DIR")
(cd "$GHIDRA_INSTALL_DIR/support/gradle" && "$SRE_ROOT/ghidra-mcp/gradlew" --no-daemon buildNatives)
(cd rea && npm ci --cache "$SRE_ROOT/runtime/npm-cache" --no-audit --no-fund && npm run build:cached)
```

Stop the backend before rebuilding/replacing the Ghidra extension. This setup
does not require Docker, Maven, Hopper, Rosetta or a global npm installation.

The official archive includes Linux/Windows native binaries. The Mac ARM64
decompiler, Sleigh compiler and other native components were built locally with
Ghidra's `buildNatives` task and the existing Xcode toolchain. Reinstall the local
extension from `ghidra-mcp/build/distributions/GhidraMCP-7.0.0.zip` into
`tools/ghidra_12.1.4_PUBLIC/Ghidra/Extensions/` after replacing the distribution.

## Verified setup

- Both source builds completed successfully.
- Native `decompile` and `sleigh` are Mach-O ARM64 executables.
- REA doctor passed all Ghidra prerequisites; its production stdio test found
  139 tools, 6 prompts and a matching catalog identity.
- Ghidra-MCP serves 190 REST endpoints; its bridge exposes 197 MCP tools.
- SkyRoads import, analysis and persistent-project save succeeded.
- Both MCP integrations returned the entry function's decompiled code.
- REA's `inspect_native_load_image` returned `verified` for the MZ mappings,
  relocations, entry point and source identity. See `analysis/` and `logs/`.

The next analysis stage is complete: DIET unpacking was verified by CRC and
independent emulation of the original stub, with all 30,076 initialized module
bytes matching. The initial analysis found 180 functions; 41 named functions
and evidence comments are saved in the project. REA verified its MZ load image.

See [the recovery report and code map](../analysis/skyroads/README.md), including
reproduction commands, pseudocode, decoder observations, and the 31-record road
directory. LZS resource decoding now matches original-code replay on all31 road blocks
(60,872 bytes). A self-contained viewer is in `analysis/skyroads/road-viewer.html`;
its resource-format notes are in `analysis/skyroads/LZS-FORMAT.md`. Tile geometry
and collision queries now match original-code replay in41,328 cases; the
viewer includes an interactive cross-section (see`COLLISION-FORMAT.md`). Game
execution was still unverified at that resource milestone. Movement
resolution and the two jump helpers now match original x86 in3,897 cases,
including intermediate traces. See [the movement report](../analysis/skyroads/MOVEMENT-FORMAT.md)
and [resumption checkpoint](../analysis/skyroads/PHYSICS-CHECKPOINT.md).
The deterministic gameplay tick also now matches5,370 original-code cases,
including sustained trajectories and all25 required semantic branches. A
portable simulator writes JSON/CSV; see [the tick report](../analysis/skyroads/TICK-FORMAT.md).
The timer and gameplay-cycle milestones are complete: local JavaScript integer
physics and original keyboard/start/pause/crash/finish/retry behavior run at
36.00428485 Hz with deterministic replay checked by Python. See
[the current checkpoint](../analysis/skyroads/CYCLE-CHECKPOINT.md),
[prototype controls](../analysis/skyroads/PROTOTYPE.md) and
[cycle semantics](../analysis/skyroads/CYCLE-FORMAT.md). Launch with
`runtime/re-venv/bin/python scripts/skyroads-prototype-server.py --port 8766`
and open http://127.0.0.1:8766/physics-viewer.html . Physical input/display latency
against DOS remains unmeasured. The full packed original now executes in a pinned
ARM64 DOSBox-X reference: Python and JS match 4,667 continuous physics steps,
including DEMO.REC and real-road success. See
[running-original evidence and remaining differences](../analysis/skyroads/RUNNING-ORIGINAL.md).
Original retry fades add roughly 2.2 seconds; the clone currently restarts
immediately. Next: wrapper transitions, profile persistence and the remaining
gameplay/input timing comparisons. Rust with Windows/macOS/Linux and web delivery
follows gameplay parity.

REA's native session supervisor needs macOS process inspection. Native REA
verification was run outside Codex's shell sandbox after its sandboxed launch
failed. Both integrations are now confirmed through direct Desktop MCP calls.
