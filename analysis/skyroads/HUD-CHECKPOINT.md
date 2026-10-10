# Original dynamic instruments — 2026-10-10

The browser now renders original speed, oxygen, fuel, road-progress, gravity and
jump-assist instruments. Original masks, palette indices, integer divisions
and incremental drawing rules are preserved. Physics/input/audio sources and
v2 replay identity are unchanged. Rust remains a later milestone.
Play at http://127.0.0.1:8766/physics-viewer.html .

## Recovered rules

OXY_DISP.DAT and FUL_DISP.DAT have ten uint16 pointers; SPEED.DAT has 34.
Pointers address the payload after the table. Each record is destination word,
width byte, height byte, then row-major mask. Zero is transparent, 1 selects the
first shade, other nonzero bytes the second. Lit colors 94/95, unlit 92/93.
All 54 records match native heap bytes. Ten 4x5 digit masks at DS016c and two
26x5 assist masks at DS0234 are extracted too. Digits/symbols use colors 97/98
and opaque zero. Assist source values 5/6 both map to 98 through original 0f62.
The indicator shows active assistance, not simply the enabled checkbox.

UpdateGameplayHud (1000:12f8) computes:

- Speed: signed32(speed-speed_delta)/321 truncated toward zero, retain low
  uint16, then clamp 34. This removes the temporary landing speed loss.
- Resources: uint16(resource+2999)/3000 unsigned, clamp 10; preserve word wrap.
- Progress: denominator=signed32((rows-3)<<16)/30, truncated first. Then
  unsigned32(forward-(3<<16))/denominator, retain low uint16, clamp 29.
  Newly reached columns x=42+segment read color at y143, find its upper
  boundary and replace that contiguous run with color 96.
- Warning icons swap only 99/100 on an edge of (timer%9)>4 while exit 4/5 is
  active. Their pixel state depends on preceding updates.

The wrapper 2b3d resets caches and writes (gravity_factor-3)*100 at (96,156),
four places with omitted leading digits and at least one zero. P-pause and
RunFinishSequence do not call HUD. The host holds the panel during those phases
and initializes a fresh one on retry. Identical pictures share buffers rather
than allocating a bitmap for every physics step. Core warning sound requests
already belong to the verified cycle; the HUD renderer never writes physics
state or emits duplicate sound requests.

## Evidence and limits

hud-validation.json passes against three full, unchanged DOS runs:

| Native run | Continuous HUD calls | Sampled pixel comparisons |
| --- | ---: | ---: |
| hud-sequence-keyboard | 1,264 | 161 |
| hud-sequence-demo | 1,703 | 213 |
| hud-sequence-gallery | 1,324 | 180 |
| Total | **4,291** | **554** |

Every call feeds the independent JS reconstruction. Its 320x62 lower dashboard
matches native RAM at all 554 samples. Separately, one JS update applied to
each native input frame matches all 64,000 resulting bytes: 35,456,000 byte
comparisons including unchanged scene bytes. This is not a new independent
554-scene rendering claim; scene evidence remains the earlier 287 comparisons.
All 31 archives, 38 attempt initializations, mask payloads and symbol bytes are
covered. Original hashes and archived observer/runner/config/build provenance
are checked. The observer only reads state and VGA memory. Initial hud-keyboard,
hud-demo and hud-gallery runs have valid sampled updates but lack every-call
logging; final evidence uses hud-sequence-* only.

hud-corpus-validation.json adds 467 unchanged original-x86 cases and 29,888,000
VGA-byte comparisons: 214 speed-threshold cases, 10 speed-loss cases, 66 resource
boundaries/wrap, 37 frames for each resource warning, 6 assist toggles, 92 progress
boundaries and 5 gravity values. Original mask expansion, pixel read/write and
self-modifying VGA blitter execute in Unicorn. Timeline output matches all 467
panels; twelve groups verify pause/finish freezing and retry initialization.
Digital sound is muted here; native sound evidence remains AUDIO-CHECKPOINT.md.

Browser evidence: hud-ui-validation.json,
recordings/cycle-01-20261010-140216-7b25751f.json and
screenshots/hud-instruments.png. The 327-step run includes jump and automatic
retry, saves/verifies in Python and replays in the browser. Inspection step 99
shows speed 7425 -> 23 segments, progress 3, full ten-segment meters and gravity 500.
No console warnings/errors observed. Python/JS still match the existing 4,667
native physics steps, 212 finish advances and 15 pause polls.

These HUD runs are accelerated. Physical keyboard/display latency and real-time
response have not been measured; finite coverage is not proof of all states.
Original fades/messages, profile persistence and remaining native game-cycle
coverage remain. Exact retry wait is lower priority than traversal feel.

## Reproduction and continuation

New files: scripts/extract-skyroads-hud.py, skyroads-hud.js,
capture-skyroads-hud-corpus.py, validate-skyroads-hud.js and
validate-skyroads-hud-corpus.js. Integration: skyroads-renderer-ui.js,
skyroads-physics.html, skyroads-prototype-server.py. Native runner adds --hud.
Graphics/hud-manifest.json and hud-*.bin retain source hashes and original masks.
Raw instructions and Ghidra exports: hud-instructions.txt, hud-helper-analysis.json,
hud-initialization-analysis.json, hud-function-annotations.json. Ten new function
names are saved in Ghidra; 65 documented functions total.

From project root:

```bash
runtime/re-venv/bin/python scripts/extract-skyroads-hud.py
node scripts/validate-skyroads-hud.js \
  analysis/skyroads/original-runs/hud-sequence-keyboard \
  analysis/skyroads/original-runs/hud-sequence-demo \
  analysis/skyroads/original-runs/hud-sequence-gallery
# Unicorn JIT needs a host context outside this Mac's restricted sandbox.
runtime/re-venv/bin/python scripts/capture-skyroads-hud-corpus.py
node scripts/validate-skyroads-hud-corpus.js
runtime/re-venv/bin/python scripts/skyroads-prototype-server.py --port 8766
```

Next: logical key-to-render response against a real-time original with explicit
machine/cycle/display settings, separated from physical latency. Extend native
cycles to frontal crashes, resource exhaustion and final-road completion, then
original fades/messages and profile persistence. Preserve deterministic replay.
