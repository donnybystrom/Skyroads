# Original graphics checkpoint — 2026-10-10

The playable inspection surface now uses the original VGA road renderer's
projection, palette indices, span geometry, ship frames and shadow rules.
**287 native scene buffers match exactly: 12,673,920 indexed pixels.**
The existing Python/JS integer physics and timestamped input code are unchanged.
Play at http://127.0.0.1:8766/physics-viewer.html .

## User priority

Match traversal and the vehicle's perceived response first. Preserve each road's
original colors/patterns, tunnels and graphical details. Modern rendering is
allowed. Original fades should eventually be present, but the exact wait before
retry is explicitly lower priority. Rust/platform delivery follows gameplay
verification; do not begin the Rust port yet.

## Recovered graphics

- `CMAP`: signature, byte color count, RGB6 triples, then two EGA mapping bytes
  per color. `PICT`: signature, three little-endian words (destination offset,
  height, width), then LZS. Decoder consumption locates the following block.
- Palette slots: road 0–71, ship 72–91, dashboard 92–141, world 142–255. Each
  road keeps its own palette and tile surface nibbles. Three playable roads
  share a world background; archive demo 0 uses world 0.
- `TREKDAT.LZS` has eight records: allocation size, decoded size, LZS stream.
  Each decoded bank begins with 312 span pointers (624 bytes), followed by
  1,040 variable-length span records. Original initialization expands each
  `(start,width)` pair to `(start,width,0)`; 255 terminates a span. The resulting
  sizes equal the original allocations. Span banks select eight forward phases.
- The original camera is fixed. Lateral position changes the ship view and
  screen position; it does not shift the world camera. Ship height changes the
  sprite position. The former analytical camera followed height and is replaced.
- Road rows draw far to near. Each half draws outer columns toward the center:
  0,1,2,3 then mirrored 6,5,4,3. Six structure types include arched and flat
  tunnels and two block heights. Two special layers insert the ship between
  tunnel facets for occlusion. Color pairs encode side shading, ground edges,
  arch facets and shadow colors; 74 logical pairs reference 72 road colors.
- `CARS.LZS` decodes to 55,440 bytes: 77 frames with 720-byte stride. Each
  visible frame is 29 columns × 24 rows, column-major; 24 trailing bytes are
  unused. Fourteen explosion frames precede seven views × three poses × three
  animation frames. Original clipping and five shadow masks are implemented.
- Dashboard nonzero pixels overlay the world at byte offset 41,280. The
  browser composes a 320×200 indexed picture and displays it at 4:3 with nearest
  sampling. Dynamic instrument indicators are still pending; sidebar values
  show the actual simulated resources and speed.

Raw instruction evidence is in `render-instructions.txt`; decompiler exports
are `graphics-functions-initial.json`, `graphics-loading-functions.json` and
`graphics-asset-functions.json`. Eight functions were named/commented and saved
in the persistent Ghidra program; see `graphics-function-annotations.json`.
Do not infer register/segment conventions from decompiled prototypes alone.

## Evidence and exact limits

`graphics-validation.json` compares the independent JS renderer with raw RAM
captured before and after original `1000:2d1f` calls from `1000:0c98`. The DOS
program runs unchanged, including its real asset loaders. The observer only
reads graphics state; road selection uses real guest keyboard input.

| Native run | Scene buffers | Coverage |
| --- | ---: | --- |
| `graphics-demo` | 111 | Complete original demo traversal |
| `graphics-keyboard` | 86 | Seven ordinary attempts, steering, jumping, pause, failures, finish |
| `graphics-all-roads` | 90 | All 30 menu roads and ten world palettes/backgrounds |

The combined comparison covers all eight forward phases and structure kinds
0–5. Extracted car bytes, the scene background bytes and full RGB6 palettes
match native RAM. Derived ship/render arguments are checked as well as the
output pixels. Full redraw replaces the original incremental copy optimization;
the resulting indexed scenes agree in these samples.

**The original scene allocation is only 320×138 = 44,160 bytes.** Observer
dumps contain 64,000 bytes for convenience, but bytes past 44,160 are neighboring
allocation contents, not verified scene pixels. The pixel claim excludes the
remaining dashboard area, animated instrument updates and wrapper messages.
RGB6-to-RGB8 conversion, browser scaling, physical input/display latency and
audio have not been compared pixel/timing-exactly. Finite sampled agreement is
not proof of every possible graphical or gameplay state.

Run manifests retain source, probe, configuration, runner and emulator hashes
with archived source snapshots. The validator checks provenance and current
original-file hashes. Original assets are unchanged.

UI evidence: `graphics-ui-validation.json`, screenshots under `screenshots/`,
and `recordings/cycle-01-20261010-082028-7f68b9fe.json`. All 31 road selector
values were exercised; play/step/jump/steer/replay/save worked with no console
warnings or errors. The new 328-sample recording and previous 162-sample
recording replay in Python with the same model identity. The earlier native
physics comparison was rerun: Python and JS still match 4,667 physics steps,
212 finish advances and 15 pause polls. See `RUNNING-ORIGINAL.md`.

## Files and reproduction

- `scripts/extract-skyroads-graphics.py`: original asset decoder, manifest and
  previews, using the existing verified LZS decoder.
- `scripts/skyroads-renderer.js`: reusable pure indexed renderer.
- `scripts/skyroads-renderer-ui.js`: browser composition and inspection bridge.
  It keeps the original rendering boundary and holds the previous picture
  during pause/return. Renderer sources are outside physics/input replay identity.
- `scripts/dosbox-skyroads-probe.h`: optional read-only render captures;
  `--gallery` visits thirty menu roads through guest input.
- `scripts/validate-skyroads-renderer.js`: native image/argument/asset comparison.

From the project root:

```bash
# Pillow is available in the bundled Python; runtime/re-venv is sufficient
# for the original runner, physics verification and local HTTP server.
/Users/donnybystrom/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/extract-skyroads-graphics.py
node scripts/validate-skyroads-renderer.js \
  analysis/skyroads/original-runs/graphics-demo \
  analysis/skyroads/original-runs/graphics-keyboard \
  analysis/skyroads/original-runs/graphics-all-roads
runtime/re-venv/bin/python scripts/skyroads-prototype-server.py --port 8766
```

To capture a fresh gallery (use a new name; existing evidence is preserved):

```bash
bash scripts/build-skyroads-dosbox.sh
runtime/re-venv/bin/python scripts/run-skyroads-original.py \
  --name graphics-gallery-next --gallery --graphics --sessions 30 --max-ms 300000
```

## Next milestone

Recover dynamic speed/fuel/oxygen/gravity/jump-assist indicators and sound
requests/output so that the player receives the original traversal feedback.
Measure logical input-to-visible-frame response against a real-time native
reference, then physical keyboard/display latency where the available setup
permits. Extend continuous native coverage to frontal crashes, resource
exhaustion and final-road completion. Preserve verified integer arithmetic,
input queues and deterministic replay. Original fades/messages and profile
initialization/persistence remain required functional work; exact retry wait
milliseconds are lower priority under the user's latest instruction.
