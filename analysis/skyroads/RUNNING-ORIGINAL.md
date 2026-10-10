# Continuous comparisons against the running original — 2026-10-09

The unchanged, packed `SKYROADS.EXE` now runs as a complete DOS application in
DOSBox-X on this ARM64 Mac. Both the existing Python and browser JavaScript
models match **4,667 completed physics steps** across three recorded runs,
plus three completion requests, 212 finish-animation advances and the recorded
pause/return boundaries. These are finite comparisons; two runs intentionally
repeat the same demo trajectory with different emulated CPU speeds.

The comparison also found an actual gameplay discrepancy: the clone retries
immediately, whereas the original executes palette transitions before the next
attempt. **Complete gameplay parity has not been achieved.** The verified
physics, browser model and replay identity were left unchanged in this step.

## Original reference and provenance

Source: `../../Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/`.
Original executable SHA-256:
`ce1b1ec1688eb853b6fbb11614793d8c4bef563b0d31e5cbd76cd1801832ec0f`.
Each run copies every game file to its own `drive-c/`; source hashes are checked
after execution and again during validation. The source originals are unchanged.

[DOSBox-X](https://github.com/joncampbell123/dosbox-x) is pinned to
`b60936a716c72e0978e940f813bab2cd40d43868`. The primary runs below use a locally
built ARM64 executable with SHA-256
`b5218bcc1873d52a758aea074d601b7b396c2c025c5c41244c9abf1c495742f1`.
Configuration: normal CPU core, 386, VGA, no XMS/EMS/UMB, SDL surface, turbo.
The complete original startup, unpacker, DOS/BIOS, resource loading, keyboard
interrupts, PIT, rendering and audio routines execute. Host audio is muted.
Runs are headless using SDL's dummy video driver; their times are **emulated
milliseconds**, not host elapsed time or physical input/display latency.

The observer in `../../scripts/dosbox-skyroads-probe.h` reads guest RAM and
registers at original instruction boundaries. It does not replace guest code,
registers, RAM, timer values or input state. In the keyboard scenario, scheduled
events enter through DOSBox's `KEYBOARD_AddKey` controller and are decoded by the
original guest interrupt handler. The successful ordinary-road attempt uses an
adaptive steering policy that reads lateral position at the render boundary;
it still controls the ship through hardware key events, without changing state.

Each primary run stores its exact configuration, probe source, emulator build
manifest, original-file hashes, post-run file hashes, JSONL observations, road
and demo RAM dumps, DOSBox log and native VGA screenshots. The older exploratory
runs remain separate. `runtime/dosbox-x-build.json` describes the current build.

## The original supplies a useful demo replay

`DEMO.REC` is **6,398 bytes**, SHA-256
`2bb53c6cd62f2cd2a8657cd05bf9e33054570c1e3e98dd89e18587156867016e`.
The game's mode 3 input path at recovered `1000:0a49..0acd` chooses an entry
using forward position. It is a built-in demonstration recording that we can
use as a regression reference:

```text
index     = unsigned_forward_position // 0x666
entry     = DEMO.REC[index]
throttle  = (entry & 3) - 1
direction = ((entry >> 2) & 3) - 1
jump      = (entry >> 4) & 1
```

Entries are **position indexed**, rather than frame indexed. Both validators
derive controls independently from their own carried-forward model position
and the original recording, then compare them to the original's decoded input.
The loaded demo road at archive index 0 is byte-identical to archive index 22
(menu index 21). The full demo reaches the original finish tunnel successfully.
Automatic demo playback is not yet exposed in our browser UI.

## Primary runs and results

| Run under `original-runs/` | CPU cycles/ms | Attempts | Completed physics steps | Result |
| --- | ---: | ---: | ---: | --- |
| `reference-keyboard` | 20,000 | 7 | 1,263 | Fall/retry, short-key pause/resume, Escape, ordinary-road success, progression, hazardous-ground death/retry |
| `reference-demo-fast` | 20,000 | 1 | 1,702 | Original demo reaches the finish tunnel |
| `reference-demo-slow` | 3,000 | 1 | 1,702 | Same physics trajectory; slower rendering changes finish wait advances |

The seven keyboard attempts use archive indices `1, 1, 1, 1, 2, 30, 30`;
completed step counts are `287, 283, 72, 382, 73, 93, 73`; return reasons are
`3, 3, 7, 0, 7, 2, 7`. The road-1 success is on original road bytes, with the
original camera/rendering executing, rather than a synthetic success fixture.

The road selector's Right key adds 15 and clamps at 29; three Right presses
therefore select archive 30. This scenario covers **hazardous ground (exit 2)**,
including 43 crash ticks. It does not establish a full-program frontal crash
(exit 1) comparison. Up/Down change the menu selection by one; Left subtracts 15.

The successful ordinary road advances its completion counter from 1 to 2 and
selects the next road. Native DOS saving changes only `SKYROADS.CFG` in the copied
drive: byte offset 6 changes from 1 to 2 in its 66 bytes. The clone's progression
branch matches the observed operation, but its UI does not yet load/save that
original profile. Saving a clone replay is separate from saving road progress.

The fast demo and normal-road success each execute 72 finish wait advances.
The slow demo executes **68**, while its finish timer still reaches 72.
The original advances position once per released wait; slower drawing can skip
timer counts. The existing `Attempt.advance(mask, elapsed)` reproduces this
when supplied the observed timer deltas. Browser rendering performance and its
host scheduler have not been shown to reproduce the same skipped-wait pattern.

Fresh emulator launches need not have identical raw timing traces. The earlier
`keyboard-full-reference` run has 1,264 steps: its third Escape attempt contains
73 steps, versus 72 here. Both traces pass continuously with their actual input
polls and PIT samples. Treat each hashed trace as the replay reference; the CPU
profile and millisecond key schedule alone are not a promise of identical
interrupt/input alignment in every new launch.

## Comparison contract

Models carry state continuously across each attempt, including the finish and
pause phases. There is no replacement of modeled physics state with observed
state between ticks. Native PIT samples and polled input masks are external
inputs to these comparisons; this does not independently verify host scheduling.

Two model variants are checked. One calibrates only the three documented
unspecified initial stack words (`jump_height`, `edge_distance`,
`previous_target_height`) at attempt entry and checks all 24 state fields.
The other retains the clone's canonical/retry seeds and compares all other
state fields continuously. Thus the tests also check that these differing
scratch-word seeds do not change the other compared state in these sessions.

The Python report additionally checks decoded road/config bytes, input polling,
outer-loop gates, return reasons, main retry/selection/progression branches,
source/copy integrity, palette fade arguments and notice timing. The JS validator
independently replays the emitted observations with the browser physics and
attempt model. Its result digest is
`d903222452af50ee824af3ca3e66c70f6e96815f7faaab9b95773d36d56eacff`.

- [Python report](running-original-validation.json): 4,667 steps, 4,670 input
  samples, 4,215 outer boundaries, 15 pause polls, one resume, nine returns.
- [JavaScript report](running-original-js-validation.json): same physics,
  completion, finish and pause/return comparisons pass.
- [Shared observation corpus](running-original-corpus.json): input and state
  boundaries derived from full-program traces.
- Per-run `comparison.json`: original timestamps, attempts, return reasons,
  CFG changes and the actual `Game` retry discrepancy below.

## Coverage and differences

| Behavior | Running-original evidence | Remaining boundary |
| --- | --- | --- |
| Start state and continuous integer physics | Nine attempts; seeded and canonical comparisons pass | Finite road/input coverage |
| Demo input and ordinary keyboard input | Independent decoding matches in all recorded input samples | Mouse/joystick and physical OS input latency untested |
| Pause and brief resume key | Original IRQ receives a 5 ms Space press; pause/resume state matches | Browser/OS-to-display timing unmeasured |
| Fall and hazardous-ground aftermath | Native returns 3 and 2; attempt state and retry branches match | Clone retry transition timing differs |
| Real-road success and finish | Road 1 plus demo pass; finish waits match at both CPU profiles | Wrapper fade/message timing missing in clone |
| Escape, selection and next-road progression | Native return 7 and progression branches checked | Full clone menu/profile persistence pending |
| Original profile save | Copied CFG changes; source files unchanged | Clone disk/local profile behavior not implemented |
| Frontal crash, fuel/oxygen exhaustion, all-roads ending | Earlier subsystem fixtures remain | Continuous full-program coverage still needed |
| Camera, audio cues and physical keyboard-to-photon timing | Original renders; screenshots preserved | Experiential equivalence still unverified |

At the first fall return, the actual Python `Game.advance` API has already
emitted `return(3), restart(2)` after 287 matching physics steps. The original
next initializer arrives **2,176.69945 ms later**. The other observed retries
take 2,166.29975 ms and 2,116.60585 ms. This is an executed comparison of the
current gameplay API, not merely an inference from the transition code.

The original requests fade durations of 36 timer counts, but execution time
depends on palette state and drawing. One initial fade completes in 52.8975 ms
because it starts black; later recorded fades are around one second.
Do not replace this behavior with an assumed constant two-second sleep.
The original success notice waits for 27 timer counts (749.64765 ms in the
keyboard run) and sits among palette/message transitions. The clone starts
its notice earlier in the wrapper sequence.

## Reproduce

Run from `/Users/donnybystrom/code/SRE`. Preserve existing run folders; choose
fresh names. The current build requires no global install. Build prerequisites
are the existing Xcode compiler, SDL2, libpng, FreeType, autoconf/pkg-config and
GNU automake. Automake 1.17 was built into `runtime/build-tools/` from
`downloads/automake-1.17.tar.xz` (configure with that local prefix, make/install).

```bash
bash scripts/build-skyroads-dosbox.sh > logs/dosbox-skyroads-build.log 2>&1
runtime/re-venv/bin/python scripts/run-skyroads-original.py \
  --name check-keyboard --keyboard --sessions 7 --cycles 20000
runtime/re-venv/bin/python scripts/run-skyroads-original.py \
  --name check-demo-fast --cycles 20000
runtime/re-venv/bin/python scripts/run-skyroads-original.py \
  --name check-demo-slow --cycles 3000
runtime/re-venv/bin/python scripts/validate-skyroads-running-original.py \
  analysis/skyroads/original-runs/check-keyboard \
  analysis/skyroads/original-runs/check-demo-fast \
  analysis/skyroads/original-runs/check-demo-slow
node scripts/validate-skyroads-running-original.js
```

To replay the already saved primary evidence, replace those three `check-*`
arguments with `reference-keyboard`, `reference-demo-fast`, `reference-demo-slow`.
Validation overwrites the combined corpus/reports with the selected run set.
For a visible original run, add `--visible --realtime`; visible/real-time
measurements were not part of this milestone. The keyboard steering scenario
is currently calibrated for the documented 20,000-cycle profile.

![Original VGA capture from the reference demo](original-runs/reference-demo-fast/captures/skyroads_001.png)

## Next checkpoint

Recover the original wrapper's fade/message phases, input handling during
transitions, and profile initialization/persistence. Add those phases to the
clone and compare complete event/timing sequences against these traces. Preserve
the integer core and deterministic replay; version recording identities when
lifecycle semantics change. Extend native sessions to frontal crash, exhausted
resources and the final-road ending. Measure physical input/display response
against a defined visible reference before claiming experiential frame perfection.
Rust and platform delivery follow gameplay parity.
