# Local gameplay cycle prototype

Latest 2026-10-10: [real-time response and original menus](RESPONSE-MENUS-CHECKPOINT.md).
Original main/Controls/Help/30-road menu frames now match; preview at
http://127.0.0.1:8766/menu-viewer.html . Gameplay integration and fades remain.
Real-time native287-step and browser230-step checks pass; physical response,
initial timer phase and catch-up input remain explicitly unproven.

From /Users/donnybystrom/code/SRE:

```bash
runtime/re-venv/bin/python scripts/skyroads-prototype-server.py --port 8766
```

Open http://127.0.0.1:8766/physics-viewer.html. Runtime needs neither Ghidra nor
Unicorn. Integer physics/input/lifecycle run locally in JS; the Python server
loads catalog and verifies replay/save. Original cadence: 36.00428485 Hz.

## Controls

- Starta focuses the scene; arrows accelerate/brake/steer; Space jumps.
- P uses the original pause protocol: release P, press a game key, release all
  game keys to resume. Escape returns to road selection.
- Inspektionspaus, focus loss and hidden tab freeze the host clock separately.
- Ett steg, timeline and raw state support inspection; Återställ starts fresh.
- Replay verifies all recorded samples before playback; Spara körning verifies
  again before writing to analysis/skyroads/recordings/.
- Failures retry automatically and clear held keys as the original driver does.
  Original palette transitions around retry are not yet implemented; the current
  test surface starts the next attempt too early.

Archive indices 1–30 correspond to menu road indices 0–29. Archive 0 is the demo
road available for manual analysis. Its original DEMO.REC playback is now checked
against the full DOS game; automatic playback in this UI is still pending.
Save before changing roads/resetting. Timeline inspection does not branch history.

## Evidence and boundaries

Original dynamic instruments now render; see [HUD checkpoint](HUD-CHECKPOINT.md).
Speed/resources use original segment masks; progress, gravity and active jump
assistance follow original code. Instrumentstatus exposes the displayed values.
Pause/finish hold the panel; retry and timeline replay retain its proper history.

Original music/effects are now available; see [audio checkpoint](AUDIO-CHECKPOINT.md).
The first Starta/Replay or preview click activates audio. Ljud på, Musik and
Volym control playback; Musikspår exposes all ten original scores for inspection.
Music continues through original P-pause and retry; inspection pause freezes
playback. Recorded audio plans are extra metadata and do not change physics.

See [current checkpoint](CYCLE-CHECKPOINT.md) and [cycle format](CYCLE-FORMAT.md).
The [running-original comparison](RUNNING-ORIGINAL.md) checks continuous real
roads and records remaining transition timing and profile-persistence gaps.
All four legacy v1 recordings remain replayable. Final current-model v2 example:

```bash
runtime/re-venv/bin/python scripts/replay-skyroads-session.py \
  analysis/skyroads/recordings/cycle-01-20261009-204551-f792baea.json
```

The renderer now uses original VGA span banks, palette indices, ship sprites,
shadow and fixed perspective. See [graphics checkpoint](GRAPHICS-CHECKPOINT.md):
287 original scene buffers match, covering all roads. Static dashboard/world assets and dynamic indicators are decoded. Original
menus have a separate verified preview; gameplay integration and EGA remain.
Physical keyboard/display latency against DOS remains unmeasured. Original fades
are still wanted, but exact retry waiting time is lower priority than traversal.
