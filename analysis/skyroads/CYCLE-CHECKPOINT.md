# Gameplay cycle checkpoint — 2026-10-10, original graphics compared

Latest 2026-10-10: [real-time response and original menus](RESPONSE-MENUS-CHECKPOINT.md).
Original main/Controls/Help/30-road menu frames now match; preview at
http://127.0.0.1:8766/menu-viewer.html . Gameplay integration and fades remain.
Real-time native287-step and browser230-step checks pass; physical response,
initial timer phase and catch-up input remain explicitly unproven.

Latest milestone: [HUD-CHECKPOINT.md](HUD-CHECKPOINT.md). Dynamic instruments
match original code and native VGA RAM; 4,291 continuous calls,554 sampled panels
and 467 original-code cases pass. Physics/input/audio and replay identity are
unchanged. Next: real-time traversal response and remaining native cycle coverage.

Previous milestone: [AUDIO-CHECKPOINT.md](AUDIO-CHECKPOINT.md). Original music and
effects now play from the existing sound events. 21,552 native OPL writes and
55 tick sound requests match; all five digital effect driver cases pass.
Physics/input files and replay identity remain unchanged. Preserve original fades as later
functional work without requiring exact retry wait milliseconds.

Latest work: [GRAPHICS-CHECKPOINT.md](GRAPHICS-CHECKPOINT.md). Original VGA
projection, colors, tunnels, ship and shadows now replace analytical rendering.
287 native scene buffers match across all roads. Physics/input sources and
replay identity are unchanged; the native 4,667-step comparison was rerun.
The user prioritizes exact traversal feel. Original fades remain wanted;
exact retry waiting time is explicitly lower priority.

Previous milestone: [RUNNING-ORIGINAL.md](RUNNING-ORIGINAL.md). The full packed DOS
game now executes in a pinned ARM64 DOSBox-X reference. Python and JS each match
4,667 completed physics steps across three native runs, including the original
DEMO.REC, ordinary-road success, pause, failures, retries and progression.
**Full gameplay parity remains incomplete: wrapper transition timing differs.**

Current playable inspection UI: http://127.0.0.1:8766/physics-viewer.html
The server is running at handoff. Restart from the workspace with:

```bash
runtime/re-venv/bin/python scripts/skyroads-prototype-server.py --port 8766
```

## Completed

- Original start state, keyboard decoding, P pause protocol, crash/failure gates,
  finish sequence, retry/progression branches and notice wait recovered. Wrapper
  palette/message transitions are still missing in the clone.
- Browser executes local integer physics at 36.00428485 Hz. Timestamped input
  queue preserves simulation boundaries during catch-up; pause also polls between
  timer interrupts. Python verifies deterministic replay before saving.
- VGA drawing boundary recovered: draw after physics and the outer gate; retain
  the previous picture during original pause or return. Ice display-height offset
  and finish height reset are reproduced. Original VGA projection and span
  rendering are now compared independently against native scene buffers.
- Original core and skyroads-session-v1 remain unchanged. Ghidra project saved
  with 49 documented functions; graphics annotations/exports are saved separately.

## Earlier subsystem/oracle evidence

- 5,370 original x86 tick cases: JS matches complete state and intermediate trace.
- 6,926 whole-attempt wait boundaries plus 26 pause busy-poll transitions.
- 2,048 keyboard combinations; 36 IRQ install/make/repeat/break/restore sequences.
- 1,571 chained lifecycle frames: 1,194 failed-attempt frames and 377 success
  frames. Also 72 main return branches, 150 last-road branches, 85 notice frames.
- Local comparison: 322,185 intermediate events; 18 input-queue cases;
  137 original render-call boundaries.
- Final UI recording: recordings/cycle-01-20261009-204551-f792baea.json.
  All 162 samples match Python and the unchanged original attempt oracle;
  17 native key events, zero late inputs, maximum observed physics CPU 0.3 ms.
- HTTP final replay passes; 11 malformed/tampered saves and unrelated-origin
  request rejected; all four legacy recordings replay successfully.
- Earlier browser recordings covered short pause taps, opposing keys and two
  automatic retries. Their original-code report is cycle-ui-validation.previous.json.

Reports/corpora: cycle-validation.json, cycle-corpus.json, pause-poll-validation.json,
pause-poll-corpus.json, lifecycle-validation.json, lifecycle-corpus.json,
tick-corpus.jsonl, local-validation.json, presentation-corpus.json,
cycle-ui-validation.json, cycle-api-validation.json.
Screenshot: screenshots/gameplay-cycle.jpg.

## Verification boundaries

Physical keyboard-to-photon latency has NOT been measured against a running DOS
original. Logical frame equality does not establish experiential frame perfection.
The older subsystem oracle virtualizes graphics/files and uses synthetic success
fixtures. The new native reference executes the entire original, including VGA,
audio routines, real roads and profile writes in a copied drive. The clone still
has in-memory progression and incomplete instruments/audio/menus/transitions.
Joystick/mouse and full-program frontal crash/resource exhaustion remain untested.
DEMO.REC decoding is now verified, but browser automatic demo playback is pending.
The native seeded model checks all state; the canonical model excludes only three
documented unspecified stack words while checking every other field continuously.
Do not claim the full game has been reproduced.

V2 identity includes the Python/JS model, input UI and presentation code. Earlier
experimental v2 files belong to archived model revision a028e4a242d0e9bc and are
intentionally rejected by the current model. Source snapshots are under
model-revisions/a028e4a242d0e9bc/. The final recording above uses current identity.

## Current priority — original gameplay parity before Rust

User clarification: first make the game functionally and experientially faithful
to the original. Rust and platform delivery are later milestones. Do not begin
a Rust port as the next task. The subsystem comparisons above are strong evidence
for the implemented integer physics, not proof that the complete game is exact.

The running reference and initial continuous comparisons are now complete:
`original-runs/reference-keyboard`, `reference-demo-fast`, `reference-demo-slow`.
See `running-original-validation.json`, `running-original-js-validation.json`
and their observation corpus. Nine attempt returns, three successes, 212 finish
advances and 15 pause polls match at the documented attempt boundaries.

The first measured Game wrapper discrepancy is retained in each keyboard-run
`comparison.json`: after 287 matching physics steps, the clone immediately
restarts, while the original waits 2,176.69945 ms until its next initializer.
Other retries take 2,117–2,166 ms. The ordinary-road success updates the original
counter from 1 to 2 and saves copied CFG byte 6; the clone does not load/save it.
At slow CPU speed the demo finish advances 68 times while the timer reaches 72;
the Attempt model matches when supplied those observed timer deltas.

Next: compare input-to-image/audio
response during traversal against a real-time original. Extend native coverage
to frontal crash, resource exhaustion and final-road completion. Original
fade/message phases and profile initialization/persistence remain functional
work, with exact retry delay lower priority. Preserve integer physics and
deterministic replay, versioning model identity when those sources change.
Do not hard-code measured retry milliseconds: original fades depend on palette
state, timer behavior and rendering work.

Measure input sampling and input-to-visible-response against that defined DOS
reference. Check camera/motion, collision visibility, animations and audio cues
where they affect timing or the player's decisions. Modern rendering remains
allowed; pixel-identical artwork is not the completion criterion. Recover and
verify missing functional menu/progress-save behavior as well.

Keep a coverage matrix of verified behavior, discrepancies and untested paths.
Gameplay parity is the gate for the later port; document any remaining limits
instead of declaring universal frame-perfect equivalence from finite tests.

## Later destination — portable Rust game

After gameplay parity, port the established model to a platform-independent Rust
core with exact corpus/replay regression checks. Target runnable Windows, macOS
and Linux builds and a straightforward WebAssembly/web export. Platform hosts
provide rendering, input and audio while preserving the gameplay contract.
