# SkyRoads: recovered executable and first code map

Latest 2026-10-10: [real-time response and original menus](RESPONSE-MENUS-CHECKPOINT.md).
Original main/Controls/Help/30-road menu frames now match; preview at
http://127.0.0.1:8766/menu-viewer.html . Gameplay integration and fades remain.
Real-time native287-step and browser230-step checks pass; physical response,
initial timer phase and catch-up input remain explicitly unproven.

**Latest milestone, 2026-10-10:** [original dynamic instruments](HUD-CHECKPOINT.md).
Speed, resources, progress, gravity and jump-assist use original masks and
integer rules. 4,291 continuous native updates reconstruct correctly at 554
sampled dashboards; 467 isolated original-code pixel cases also pass.
Physics/input/audio and replay identity are unchanged. Real-time response,
remaining game-cycle coverage, fades and profile saving remain.

Previous milestone: [original music and sound checkpoint](AUDIO-CHECKPOINT.md).
Ten original AdLib scores and five digital effects now play in the browser;
21,552 native OPL writes and 55 physics sound requests match. Physics/input
sources and replay identity are unchanged.

Previous milestone: [original graphics checkpoint](GRAPHICS-CHECKPOINT.md).
The playable scene uses original colors, span geometry, tunnels, sprites, shadows
and fixed projection. 287 native scene buffers match exactly across all roads.
The existing 4,667-step continuous physics comparisons still pass.
Older sections below preserve earlier milestones and their verification limits.

Verified on 2026-10-09 on this Apple Silicon Mac. Both newly connected Codex
Desktop MCP integrations were called directly in the chat. The persistent
Ghidra project is `../../projects/SkyRoads.gpr`; select
`/Unpacked/SKYROADS_UNPACKED.EXE` for game analysis. The original remains
`/SKYROADS.EXE` and contains the executable unpacking stub.

## Recovery evidence

The original EXE is packed with the DIET v1.02-1.20 format family. Identification
uses the stub signature, `dlz` header and Deark's parser, not a recovered exact
packer version. See the [DIET format author's research](https://entropymine.wordpress.com/2023/11/11/diet-compressed-exe-format/)
and [Deark source](https://github.com/jsummers/deark).

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| Original `SKYROADS.EXE` | 18,035 | `ce1b1ec1688eb853b6fbb11614793d8c4bef563b0d31e5cbd76cd1801832ec0f` |
| Reconstructed `unpacked/SKYROADS_UNPACKED.EXE` | 30,588 | `5b7c06dedb0b25f9034c5a898ae9aacf9df15f0c353a0e3969474d2644760104` |

Deark calculated the expected DIET CRC-16/ARC `cf8a`. Independently, Unicorn
emulated the original unpacker until **before** the recovered entry instruction
at `1000:61f3`. After 447,544 executed instructions, all **30,076 initialized
module bytes**, with all three relocation fixups, matched the reconstructed
image. No interrupt or port operation occurred. See `unpack-validation.json`
and `../../logs/skyroads-unpack-deark.log`.

REA independently returned `verified` for the reconstructed MZ image, all
initialized mappings, three relocations, source hashes, and external entry.
Full evidence: `rea-unpacked-load-image.json`. The DOS stack is `218a:0800` at
handoff; the startup routine subsequently establishes the application's stack.

The reconstructed MZ header is synthesized by Deark. Byte agreement is claimed
for the initialized load module, not historical header identity, BSS, or a
complete running DOS process. The game has not been executed in this milestone.

## Code map

Ghidra auto-analysis found **180 functions**. Twenty-one have semantic names
and evidence comments, saved to the persistent project. Names express current
analysis; ABI, types and some gameplay semantics remain provisional.

| Address at load segment 1000 | Name | Evidence |
| --- | --- | --- |
| `1000:61f3` | `InitializeDosRuntime` | External entry, stack/DS setup, DOS allocation, environment, BSS, main call |
| `1000:01b8` | `RunGameSessionLoop` | Hardware checks, initialization, selection, road loop and completion bookkeeping |
| `1000:00bb` | `LoadTrekDataArchive` | Opens `trekdat.lzs`, iterates allocated/decompressed records |
| `1000:5614` | `LoadRoadByIndex` | `roads.lzs` directory seek, metadata and decoded road destination |
| `1000:2b3d` | `RunRoadSession` | Presentation, gameplay call, 'Road completed'/'The End', cleanup |
| `1000:1fd9` | `RunGameplayLoop` | Tick wait, input/render calls, movement arithmetic, collision helpers and exits |
| `1000:3acc` | `InstallTimerHandlers` | Interrupt vectors 08h/24h and PIT port writes |
| `1000:66e6` | `DecodeLzsBlock` | Shared resource decoder, literals/backreferences, three control bytes, self-modified immediates |
| `1000:64ab` / `1000:64ff` | `ReadBufferedBitMSB` / `ReadBufferedBitsMSB` | MSB-first bit consumption and buffer refill |

`annotated-functions.json` contains the selected functions and their callees.
`recovered-pseudocode.c` is a convenient **Ghidra analysis export**, not original
or compilable C source. `function-annotations.json` is the reusable name/comment
set; `function-inventory-initial.json` preserves the initial 180-function list.

### ROADS.LZS structure

The loader reads `{uint16 offset, uint16 decoded_length}` at `index * 4`. The
first block starts at file offset 124, implying 31 directory entries; all entries
are increasing, in bounds, and their decoded lengths are divisible by 14.
Each block begins with three 16-bit metadata fields, then 216 metadata bytes,
followed by the encoded stream. The loader clears a 7000-byte destination at
`DS:162c`, decodes the requested length there, and returns `decoded_length / 14`.
The 216-byte metadata buffer is `DS:41c2`. Exact metadata meanings and tile bits
remain unknown. Inventory: `roads-directory.json`.

The decoder at `66e6` patches its own instruction immediates at `6729`, `671f`,
`674c` and `6751`. Its raw ABI is a far destination pointer at `BP+4` followed
by a 16-bit output length at `BP+8`. Static pseudocode alone misses the changing
bit widths and can infer incorrect argument/return types. No complete LZS
decoder replay has been verified yet; its exact external LZ variant is unknown.

### Analysis cautions

Real-mode segment aliases are not unique addresses. Resource pointers are
DS-relative (`DS=1676` after startup); Ghidra currently misses many string xrefs.
The bit reader's inferred `void` return is wrong: raw instructions accumulate
its result in AX. Other register and far-pointer conventions need correction.
Use `instruction-evidence.json` (Capstone 5.0.9, original unrelocated module
bytes) alongside Ghidra. The bundled Sleigh segment-MOV display also reverses
some printed operands while its p-code semantics are correct; consult bytes
when interpreting segment setup.

Import the unpacked EXE using auto-detected **MzLoader**. In this MCP version,
supplying an explicit `language` to `import_file` selects a raw binary loader;
that would analyze the MZ header as code and invalidate the address map.

## Reproduce

From `/Users/donnybystrom/code/SRE`:

```bash
# Deark was built from commit 8f2db0af0b5e322eb19a7d9cf75505b8bf236a5d.
make -C tools/deark -j4
mkdir -p analysis/skyroads/unpacked
tools/deark/deark -m diet -d -od analysis/skyroads/unpacked \
  Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/SKYROADS.EXE
cp -n analysis/skyroads/unpacked/output.000.exe \
  analysis/skyroads/unpacked/SKYROADS_UNPACKED.EXE

# Local Python 3.12 environment: capstone==5.0.9, unicorn==2.1.4.
runtime/re-venv/bin/python scripts/validate-skyroads-unpack.py
runtime/re-venv/bin/python scripts/inspect-skyroads-roads.py
```

Unicorn's native emulation required an approved run outside the shell sandbox
on this Mac (inside it exited with SIGILL); this does not require changing the
script or launching the DOS executable natively. Saved verification includes
the entire compared runtime image in `runtime-load-image.bin`.

## Verified LZS decoding and road viewer

The next stage is now complete. The standalone resource decoder matched the
original self-modifying x86 decoder on all 31 road blocks: **60,872 decoded
bytes**, with exact encoded-block consumption. Seven independent bounds/token
edge tests also pass. The game has not been executed as a complete application.

- [Resource format and verification](LZS-FORMAT.md)
- [Offline road viewer](road-viewer.html)
- [Original-code comparison evidence](lzs-validation.json)
- [Decoded road manifest and raw files](roads/manifest.json)
- [Current 28-function annotated export](collision-annotated-functions.json)
- [Model recommendations and next prompts in Swedish](NEXT-PROMPTS.md)

Earlier descriptions above record the first milestone. The current exports
supersede those initial comments about unverified resource decoding.

Run `runtime/re-venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory analysis/skyroads`
and open `http://127.0.0.1:8765/road-viewer.html`, or open the standalone HTML
locally. The viewer shows analytical colors, seven-lane rows, raw tile values,
metadata, zoom, and CSV/BIN export. UI checks covered all31 records, the three
color modes, index wraparound, keyboard selection, zoom endpoints and a BIN
export byte comparison. CSV download has not separately been tested.

## Verified tile geometry and collisions

Tile ground/top surface fields, six structure profiles, support heights,
position collision, tunnel-context and landing-filter predicates are now
reconstructed. **41,328 cases match original x86**; **15,808 browser-model
comparisons** also pass. All 31 road selectors and the new cross-section controls
were exercised in the browser, including free tunnel passage, a side wall and
a roof hit. No console warnings/errors were observed.

See [the collision report](COLLISION-FORMAT.md), [x86 verification](collision-validation.json),
and [original geometry tables](collision-geometry.json). In the viewer, select
road index3 and row4/column3, then vary the cross-section probe. Tunnel context
is shown independently from collision because both can be true at a side wall.

This geometry milestone was completed with Sol6.1 Extra High.

## Verified movement and jump helpers

The next milestone is complete: movement resolution, projected landing and
jump adjustment now match original x86 in **3,897 cases**, including every
intermediate collision probe and projected-flight state. All 31 roads are
represented. The persistent Ghidra project now contains31 documented functions.
The geometry regression suite still passes all41,328 cases.

See [movement semantics and verification](MOVEMENT-FORMAT.md),
[the new comparison report](movement-validation.json), and
[the checkpoint for continuing](PHYSICS-CHECKPOINT.md). Replay one saved
example without emulation with `scripts/replay-skyroads-movement.py`.
The viewer remains a geometry viewer; a complete playable physics loop is
not yet implemented at that milestone.

## Verified deterministic gameplay tick

The live update is now reconstructed: steering, jumping, gravity, surface
effects, bounce, obstruction responses, landing, resources and exit reasons.
**5,370 ticks match unchanged original x86**, including3,671 chained ticks and
all31 roads. The required25 semantic branches and127,137 collision queries
were compared. Sound requests retain their original timestamps in muted mode.
Device polling, real-time scheduling, graphics and finish animation remain
outside this verification boundary.

See [the tick report](TICK-FORMAT.md), [verification](tick-validation.json), and
[the current checkpoint](PHYSICS-CHECKPOINT.md). The portable simulator at
`scripts/simulate-skyroads.py` produces JSON/CSV trajectories and replays saved
branch examples without an emulator. The Ghidra project now has33 documented
functions. That milestone is preserved in the tick report.

## Recovered timer and controllable prototype

The PIT divisor and IRQ phase now establish a nominal **36.00428485 Hz**
physics cadence. **1324 timer comparisons** pass against unchanged code.
The new local prototype uses the same verified Python core with all31 roads,
keyboard controls, pause/step/reset, raw-state inspection and saved replay.
**2876 additional ticks** match original x86, including two real keyboard
recordings. Server replays, batch equivalence and file/CLI replay also pass.

See [timer semantics](TIMER-FORMAT.md), [prototype controls and launch](PROTOTYPE.md),
[API/oracle evidence](prototype-validation.json), [additional keyboard evidence](prototype-keyboard-validation.json)
and [the resumption checkpoint](PHYSICS-CHECKPOINT.md). The persistent project
now has34 documented functions. Current reusable annotations are in
`all-function-annotations.json`; `current-annotated-functions.json` combines
the latest exports. The visual prototype uses analytical graphics; original
palette/assets/projection, audio, menus and finish/crash animations remain.

## Current gameplay cycle milestone — 2026-10-09

The HTTP-driven prototype above is historical. The browser now runs local JS
integer physics and original lifecycle/input, checked against 5,370 tick cases,
6,952 cycle samples and 1,571 lifecycle frames. Ghidra now has 41 documented
functions. See [current checkpoint](CYCLE-CHECKPOINT.md),
[cycle contract](CYCLE-FORMAT.md) and [current controls](PROTOTYPE.md).
The full original now runs in DOSBox-X: 4,667 continuous physics steps match the
Python and JS models, including original DEMO.REC and successful ordinary-road
completion. The comparison found missing retry fade delays and profile behavior
in the clone. See [running-original evidence and coverage](RUNNING-ORIGINAL.md).
The current priority is complete functional/gameplay parity, wrapper transitions,
profile persistence and remaining input/display comparisons. Only after that comes
a portable Rust core with Windows/macOS/Linux builds and a simple web export.
