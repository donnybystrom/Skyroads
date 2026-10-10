# A recovered gameplay tick

`scripts/skyroads_tick.py` implements the gameplay update after input polling,
using the previously verified movement resolver and jump helpers. It preserves
the original integer widths, ordering, persistent stack state and exit checks.
**5,370 ticks match unchanged original x86**, including3,671 chained ticks,
all31 roads,127,137 collision probes and all25 required semantic branches.
Complete state and intermediate traces agree. The exact counts and code hashes
are in `tick-validation.json`; this is sampled equivalence, not an exhaustive
proof for every possible machine state.

## Execution boundary

The original fixture enters at **1000:2324**, immediately after the optional
per-tick input call, and normally stops at **1000:2afd**, after incrementing the
tick counter. If the completion condition is reached, it stops at the entry to
**1000:0f05**, before the finish animation executes. `completion_requested`
means the animation would be called; it is not the animation's return value.

No original instruction is patched or replaced with a host implementation.
The fixture executes the real collision, movement, jump, surface and sound
helpers. Its allowlist rejects unrelated code, and its write guard rejects
writes outside the test stack and the documented output globals.

Audio uses the original configuration `DS:451a=1` (muted), `DS:0cb6=1` (digital
mode). Requests still write `DS:af38=DS:1600`, and the original busy query tests
`timer < uint16(lastSoundTick+8)`. This preserves sound-related state without
running port operations or a digital audio driver. Other audio modes remain
outside this verification contract.

The supplied controls are post-poll throttle, direction and jump words. The
timer value is also explicit and fixed during each tick. Keyboard/joystick/
mouse polling, demo-input decoding, rendering, interrupt scheduling, pause
handling and the outer loop's delayed exits are outside the tick boundary.

## Persistent state

Global offsets are listed in the `GLOBALS` mapping in `skyroads_tick.py`.
Position/velocity/assist fields retain the meanings in `MOVEMENT-FORMAT.md`.
Additional fields include resources at5494/b13c, exit state456e, crash counter
456a, exit counter4558 and sound timestampaf38. The script's `fuel` and `oxygen`
names distinguish distance-related and time-related resource counters; their
arithmetic is verified independently of UI labels.

Nine words in the caller's stack must also survive between ticks:

| Offset from RunGameplayLoop BP | Port field | Meaning |
| --- | --- | --- |
| -02 | tick_counter | Processed tick count |
| -06 | assist_used | Assist already attempted during this jump |
| -08 | jumping | Jump has been initiated |
| -0a | jump_height | Height at jump initiation |
| -0c | grounded | Previous tick ended in a downward collision |
| -0e | surface8 | Surface8 steering behavior; persists while airborne |
| -10 | surface2 | Surface2 steering formula; cleared when airborne |
| -18 | edge_distance | Last successful lateral support-search distance |
| -1c | previous_target_height | Previous requested height before collision resolution |

Ghidra's `local_1e` naming corresponds to raw `BP-1c` here; use the raw offsets
in `gameplay-instructions.txt`, not the decompiler's generated local names.
The original entry does not initialize every one of these words. `TickState()`
defines an explicit synthetic initial frame; it does not claim to recover DOS
stack garbage. Boundary tests vary initially unspecified values, and sustained
trajectories carry the full compared state forward. Other scratch stack bytes
start as a5h in the original fixture.

## Update order

1. Look up the tile. Save whether the original tile word was nonzero. If the
   previous tick was grounded, select ground/upper surface and apply its effect.
2. Check road completion, including the tunnel-context predicate.
3. Resolve the previous vertical collision: stop or bounce vertical velocity.
4. If no exit state is set, accelerate, update steering and possibly start a jump.
5. If enabled, attempt jump assistance once above height14079 during a jump.
6. Apply gravity or the crash vertical animation rule.
7. Compute requested position; resolve movement with the verified186b routine.
8. Handle frontal obstruction, lateral shove, crash, side obstruction and landing.
9. Probe support to adjust edge drift; handle height underflow.
10. Drain resources, assign exit reasons, and increment the relevant counters.

This ordering explains why `PredictSafeLanding` cannot be used as the live
integrator: the live tick accelerates before advancing position, and surface2
changes the lateral formula. The predictor uses its own update order.

## Recovered rules

- Gravity is derived from metadata word0 as `-floor(word0*5760/400)`, stored16.
- Acceleration adds `75*throttle`; speed clamps to0..10922 after relevant changes.
- Direction input maps to steering `29*direction`, subject to jump/surface rules.
- A permitted jump sets vertical speed1152. It requires a nonzero tile word,
  no active jump, a pressed jump input, no exit state and gravity factor<20.
- Surface2 subtracts303 speed and removes the1560 lateral base term. Surface10
  adds303. Surface9 refills both resources to30000 while no exit is active.
  Surface12 starts its exit/crash state. Surface8 suppresses steering updates.
- Below ground, downward speed is forced to at least106 in magnitude. A crash
  uses a separate upward rule; below71 it adds39, otherwise it sets71. The
  addition can temporarily exceed71, which is preserved by the port.
- A sufficiently strong vertical collision bounces with
  `trunc(signed16(-5*verticalSpeed)/10)`. Its threshold is
  `uint16(gravityFactor*260)/8`, and edge drift can suppress the bounce.
- A frontal obstruction first tries a lateral shift of-928, then+928. If still
  blocked, speed>=3640 can initiate a crash. Side obstruction zeros steering,
  may cancel drift, and subtracts151 speed.
- Landing clears jump/assist flags, subtracts the temporary assist speed delta,
  and probes both sides at128-unit increments through14 increments. Asymmetric
  support changes drift by17; symmetric results clear it.
- The time-related resource drains by `30000/uint16(metadataWord2*36)` per tick.
  The distance-related one drains by the signed wrapped product
  `(30000/metadataWord1)*speed`, divided by65536.

Resource subtraction wraps16, then values above30000 are reset to zero. The
exit checks run in order: below ground sets3, empty distance-related resource
sets4, empty time-related resource sets5. Later checks can override a newly set
reason within that same block. Existing exit states instead increment the exit
counter. These small ordering details are observable in the comparisons.

## Reproduce and inspect

```bash
# Differential comparison against isolated unchanged x86.
runtime/re-venv/bin/python scripts/validate-skyroads-tick.py

# Portable simulator: no Unicorn, DOS, display or audio runtime.
runtime/re-venv/bin/python scripts/simulate-skyroads.py \
  --road 0 --ticks 160 --jump-at 25,60 \
  --output analysis/skyroads/simulations/road-00

# Replay a saved distinguishing case, including its matched intermediate trace.
runtime/re-venv/bin/python scripts/simulate-skyroads.py --replay-example shove_left
```

The simulator writes editable JSON and CSV trajectories. Tick numbers are
discrete update indices, not a claim about measured wall-clock seconds. It stops
when an exit state is first assigned or the finish-animation boundary is reached.
It does not implement the outer loop's later exit delay or animation.

The included road0 run accelerates with jumps requested at ticks25 and60. It
reaches height15435 and eventually falls at tick101 (102 updates). This is a
fixed input example, not an autopilot or a claim that the road was completed.

Evidence artifacts:

- `tick-validation.json`: results, semantic branch coverage, hashes and boundary.
- `tick-examples.json`: a reproducer for every required covered branch, including
  decoded road bytes, initial state, controls, output and matched trace.
- `tick-helper-analysis.json`: initial decompilation of surface/audio/input helpers.
- `gameplay-instructions.txt`: complete raw gameplay-loop instruction listing.
- `simulations/road-00/trajectory.json` and `simulations/road-03/trajectory.json`:
  portable model runs, distinct from the x86 oracle evidence.

## Next step

Connect the recovered tick to a controllable visual prototype, retaining a
deterministic input recording and a way to inspect raw state. Rendering can
initially use analytical geometry. Original perspective, palette, timing and
graphics still need their own reconstruction and verification. Keep the
simulation independent so visual work cannot silently alter integer physics.
