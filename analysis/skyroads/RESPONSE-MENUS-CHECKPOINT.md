# Real-time response and original menus — 2026-10-10

The latest step measures software input/physics/render boundaries in a running
original and recovers the original main, Controls, Help and road-selection menus.
The user is remote on mobile; verification was performed locally. Physics/input
identity is unchanged. This does not certify physical frame-perfect response.

## Real-time original and browser

Two unchanged packed-game runs use pinned DOSBox-X normal386, fixed20000 cycles,
turbo=false, VGA, SDL dummy video, muted host audio. Each has287 continuous
physics steps,16 pause observations and one attempt return. Both Python and JS
match; second run adds original IRQ09 return observations. Their independent
JS state digests agree. Existing accelerated reference evidence remains separate:
4,667 steps,212 finish advances,15 pause polls; digest
`d903222452af50ee824af3ca3e66c70f6e96815f7faaab9b95773d36d56eacff`.

Final native run: original-runs/response-irq-realtime-20000. Optional observer
records std::chrono monotonic host time plus PIC emulated time at controller
injection, keyboard IRQ return3bfd, PollGameplayInput return0af6, physics and
scene wrapper return22ef. All287 polls match latest observed IRQ held bits and
independent keyboard decoding. 408 IRQ returns include typematic and E0 prefix
events; they are not408 distinct human presses. Gameplay host/emulated duration
ratio1.0108 confirms approximately real-time pacing on this run.

Example controller-to-original-scene times (emulated milliseconds): initial
Up8.799, Space down30.557, Space release28.264, later Up30.083. Up release during
pause takes303.463ms to reach a normal scene because the game is paused; do not
summarize that as ordinary input lag. A5ms Space pulse reaches IRQ held bits and
the original pause busy loops even though it is gone before normal physics poll.

Browser recording recordings/cycle-01-20261010-145206-a95877b7.json has230 steps,
gas/jump/right/left/P-pause/short-resume/Escape. Python saved/replayed it; browser
playback also verified. Ten timer-path events measured10.3–22.8ms from event
receipt to canvas draw return (median16.65); three pause-path changes were
processed immediately. These are finite local software observations, not a
comparison of equivalent physical latency endpoints. Node/browser scheduling,
tool activity, compositor and screen scanout remain outside the measurement.

Important remaining response questions:

- Original PIT phase keeps running when the gameplay timer is zeroed; first
  physics step may arrive partway through a timer interval. Browser clockStart
  begins a fresh interval. Absolute initial phase is not proven equivalent.
- Under host stalls, the browser applies historically timestamped input per
  quantum; the original may poll once and reuse newest controls for catch-up
  ticks. Build a distinguishing native/browser case before changing this.
- Native endpoint is completion of VGA drawing, browser endpoint is canvas API
  return. Neither measures physical key travel, display refresh or photons.

Evidence: response-validation.json, response-realtime/ and response-irq-realtime/
comparison reports/corpora, and archived native manifests/probes/builds/configs.
skyroads-response-ui.js is an observer outside the deterministic identity; its
extra recording metadata does not affect replay. Its numbers describe processing
and draw boundaries, not proof that each key independently changes pixels.

## Original menus

Play the standalone preview at http://127.0.0.1:8766/menu-viewer.html .
It has original pixels/palettes and keyboard navigation; gameplay connection,
title animation, quit behavior, fades and durable profile updates remain later
work. Controls device/music selections only affect this preview. The existing
physics test remains at /physics-viewer.html.

menus-reference runs the original executable without guest patches, navigating
through controller events. It captures47 full64000-byte VGA pictures and768-byte
palette snapshots at DOS key-wait entries:

| Screen | Native frames |
| --- | ---: |
| Start/Controls/Help main selections | 7 |
| Controls five focus choices and music off/on | 8 |
| Help pages | 2 |
| Thirty selected roads | 30 |

The independent renderer reconstructs every frame from five source LZS
containers. **3,008,000 indexed bytes match**, plus every palette entry actually
referenced by those frames. Unused palette entries are intentionally outside
that claim. No captured framebuffer is used as a rendering asset. Twenty-eight
PICT blocks are extracted; not all are exercised by these47 comparisons.
HELPMENU.LZS contains a third picture, but RunHelpMenu consumes at most two;
the third picture's role remains to assign.

Main uses INTRO background/logo and three MAINMENU overlays. Controls uses
base200 background/base250 ten overlays (five focus plus five selection masks).
Input choices keyboard/joystick/mouse write DS4518; AdLib/none write DS451a.
Help accepts any DOS key for next page and Escape for early exit. Roads uses
GOMENU background and completion stars, including original opaque zeros in
star rectangles. Source SKYROADS.CFG already records first road completed once;
the preview reads that source profile rather than inventing blank progression.

Road selection is two columns of15 entries, ordered down each column. Up/Down
minus/plus1; Left subtracts15 or selects0; Right adds15 then clamps29. Enter
accepts; Escape returns. Completion stars cap at7. Main Up/Down clamp0..2.
Controls Left/Right clamp0..4, Up3->0/4->1, Down0->3/1,2->4.

Browser verification exercised music none/AdLib, both help pages, main return,
road Right+Down->road17, and final main picture. Console warnings/errors empty.
Screenshot screenshots/original-menus.png. Ghidra now has76 semantic function
annotations (11 new); save completed successfully. Raw code evidence and names:
menu-function-analysis.json, menu-function-annotations.json and
menu-annotation-results.json. Rendering code: skyroads-menus.js; extraction:
extract-skyroads-menus.py; assets: menus/manifest.json and indexed binaries.

## Reproduction and next step

```bash
runtime/re-venv/bin/python scripts/extract-skyroads-menus.py
node scripts/validate-skyroads-menus.js
runtime/re-venv/bin/python scripts/validate-skyroads-response.py
runtime/re-venv/bin/python scripts/validate-skyroads-running-original.py \
  analysis/skyroads/original-runs/response-irq-realtime-20000 \
  --output-dir analysis/skyroads/response-irq-realtime
node scripts/validate-skyroads-running-original.js analysis/skyroads/response-irq-realtime
```

To generate a fresh native run, rebuild if probe differs, then use a new name:
`run-skyroads-original.py --name NEW --keyboard --response --realtime` or
`--name NEW --menus`. Runner archives exact observer/build/runner/config hashes.
Validators' optional output directory keeps baseline evidence intact.

Next: integrate verified menus with the existing gameplay/selection state,
success/retry palette fades and original profile semantics. Keep keyboard mode
supported; label or defer original joystick/mouse modes until implemented.
Resolve initial timer phase/catch-up input with distinguishing response cases.
Further native cycle coverage still needs frontal crash, fuel/oxygen exhaustion
and final-road completion. Rust migration follows gameplay fidelity work.
